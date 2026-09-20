"""Regime — Markov switching trên chuỗi lợi nhuận (thường VN-Index).

Tham chiếu: Mục 8 lớp 1 / mục 9 — filtered P(state | F_t), không smoothed.
Câu hỏi: thị trường đang bull / bear / turbulent?

Fallback (khi fit Markov thất bại / series ngắn): soft-score từ rolling mean/vol.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


_STATE_NAMES = ("bull", "bear", "turbulent")


def _as_series(returns) -> pd.Series:
    series = pd.Series(returns, dtype=float).dropna()
    if series.empty:
        raise ValueError("returns series is empty")
    return series


def _heuristic_regime_probability(returns: pd.Series) -> dict[str, float]:
    """Soft bull/bear/turbulent from trailing mean and vol (no look-ahead)."""
    window = min(60, max(20, len(returns) // 3))
    trail = returns.iloc[-window:]
    mu = float(trail.mean())
    vol = float(trail.std(ddof=1)) if len(trail) > 1 else 0.0
    # Scores: positive drift → bull; negative → bear; high vol → turbulent
    bull = max(mu, 0.0) * 50.0
    bear = max(-mu, 0.0) * 50.0
    turbulent = vol * 30.0
    scores = np.array([bull, bear, turbulent], dtype=float) + 1e-6
    probs = scores / scores.sum()
    return {
        "bull": float(probs[0]),
        "bear": float(probs[1]),
        "turbulent": float(probs[2]),
        "method": "heuristic_rolling",
    }


def fit_markov_regime(index_returns, n_states: int = 3):
    """Fit Markov switching regression (statsmodels) on index returns.

    Returns a dict with ``result`` (fit object), ``state_labels`` mapping
    regime index → bull/bear/turbulent by sorted means, or raises on failure.
    """
    if n_states != 3:
        raise ValueError("V1 regime uses n_states=3 {bull, bear, turbulent}")
    series = _as_series(index_returns)
    if len(series) < 90:
        raise ValueError("Need at least 90 observations to fit Markov regime")

    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

    model = MarkovRegression(
        series,
        k_regimes=n_states,
        trend="c",
        switching_variance=True,
    )
    result = model.fit(disp=False)
    # Label by constant (mean) parameter: highest = bull, lowest = bear
    params = result.params
    means = []
    for regime in range(n_states):
        key = f"const[{regime}]"
        if key in params.index:
            means.append((regime, float(params[key])))
        else:
            # older statsmodels naming
            means.append((regime, float(result.params.iloc[regime])))
    ordered = sorted(means, key=lambda item: item[1])
    # lowest mean → bear, middle → turbulent, highest → bull
    state_labels = {
        ordered[0][0]: "bear",
        ordered[1][0]: "turbulent",
        ordered[2][0]: "bull",
    }
    return {
        "result": result,
        "state_labels": state_labels,
        "n_states": n_states,
        "method": "markov_regression",
    }


def filtered_regime_probability(model, returns_up_to_t) -> dict:
    """Return P(state | F_t) using only data through t (filtered, not smoothed).

    ``model`` is the dict from ``fit_markov_regime``, or ``None`` to force
    heuristic fallback on ``returns_up_to_t``.
    """
    series = _as_series(returns_up_to_t)
    if model is None:
        return _heuristic_regime_probability(series)

    try:
        result = model["result"]
        labels = model["state_labels"]
        # Filtered marginal probabilities — aligned with estimation sample.
        # For V1 we use the last filtered row of the fitted sample; caller
        # should pass returns_up_to_t matching the fit window end.
        filtered = result.filtered_marginal_probabilities
        last = filtered.iloc[-1]
        out = {name: 0.0 for name in _STATE_NAMES}
        for regime_idx, name in labels.items():
            out[name] = float(last.iloc[regime_idx])
        total = sum(out.values()) or 1.0
        return {
            "bull": out["bull"] / total,
            "bear": out["bear"] / total,
            "turbulent": out["turbulent"] / total,
            "method": model.get("method", "markov_regression"),
        }
    except Exception:  # noqa: BLE001 — never crash daily_job on regime
        return _heuristic_regime_probability(series)


def fit_or_fallback_regime(index_returns, n_states: int = 3) -> dict[str, Any]:
    """Fit Markov when series is long enough; otherwise heuristic probs only."""
    series = _as_series(index_returns)
    # Markov MLE is unstable on short samples — prefer heuristic under ~1y
    if len(series) < 252:
        probs = _heuristic_regime_probability(series)
        return {"model": None, "probabilities": probs}
    try:
        fitted = fit_markov_regime(series, n_states=n_states)
        probs = filtered_regime_probability(fitted, series)
        return {"model": fitted, "probabilities": probs}
    except Exception:  # noqa: BLE001
        probs = _heuristic_regime_probability(series)
        return {"model": None, "probabilities": probs}
