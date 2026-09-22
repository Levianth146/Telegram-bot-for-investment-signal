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


def _markov_converged(result) -> bool:
    """True nếu MLE hội tụ (hoặc API không expose → giả định OK)."""
    mle = getattr(result, "mle_retvals", None)
    if not isinstance(mle, dict):
        return True
    if "converged" not in mle:
        return True
    return bool(mle.get("converged"))


def _label_states_by_mean_and_variance(params, n_states: int = 3) -> dict[int, str]:
    """Turbulent = highest switching variance; bull/bear = mean trên state còn lại.

    Rule deterministic (docs/DECISIONS): sigma2 cao nhất → turbulent; trong 2 state
    còn lại mean cao → bull, mean thấp → bear.
    """
    means: list[tuple[int, float]] = []
    variances: list[tuple[int, float]] = []
    for regime in range(n_states):
        mean_key = f"const[{regime}]"
        if mean_key in params.index:
            means.append((regime, float(params[mean_key])))
        else:
            means.append((regime, float(params.iloc[regime])))
        var_key = f"sigma2[{regime}]"
        if var_key in params.index:
            variances.append((regime, float(params[var_key])))
        else:
            # Fallback: không có switching var → dùng rank mean (middle = turbulent).
            variances.append((regime, float("nan")))

    if all(pd.isna(v) for _, v in variances):
        ordered = sorted(means, key=lambda item: item[1])
        return {
            ordered[0][0]: "bear",
            ordered[1][0]: "turbulent",
            ordered[2][0]: "bull",
        }

    turbulent_idx = max(
        variances, key=lambda item: item[1] if not pd.isna(item[1]) else -1.0
    )[0]
    remaining = [(idx, mu) for idx, mu in means if idx != turbulent_idx]
    remaining_sorted = sorted(remaining, key=lambda item: item[1])
    return {
        remaining_sorted[0][0]: "bear",
        turbulent_idx: "turbulent",
        remaining_sorted[-1][0]: "bull",
    }


def fit_markov_regime(index_returns, n_states: int = 3):
    """Fit Markov switching regression (statsmodels) on index returns.

    Reject non-converged MLE (caller fallback ``heuristic_nonconverged_markov``).
    State labels: turbulent = highest switching variance; bull/bear by mean.
    """
    if n_states != 3:
        raise ValueError("V1 regime uses n_states=3 {bull, bear, turbulent}")
    series = _as_series(index_returns)
    if len(series) < 90:
        raise ValueError("Need at least 90 observations to fit Markov regime")

    from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression

    import warnings

    model = MarkovRegression(
        series,
        k_regimes=n_states,
        trend="c",
        switching_variance=True,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        result = model.fit(disp=False)
        conv_warned = any(
            "converg" in str(getattr(w, "message", "")).lower() for w in caught
        )
    if conv_warned or not _markov_converged(result):
        raise RuntimeError("markov_mle_nonconverged")

    state_labels = _label_states_by_mean_and_variance(result.params, n_states)
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
    """Fit Markov when series is long enough; otherwise heuristic probs only.

    Chuỗi rỗng (vd. ngày đầu backtest khi benchmark chưa có giá) → xác suất
    trung tính, không raise — pipeline/backtest không được crash vì thiếu điểm.
    """
    series = pd.Series(index_returns, dtype=float).dropna()
    if series.empty:
        return {
            "model": None,
            "probabilities": {
                "bull": 0.5,
                "bear": 0.25,
                "turbulent": 0.25,
                "method": "empty_returns_neutral",
            },
        }
    # Markov MLE is unstable on short samples — prefer heuristic under ~1y
    if len(series) < 252:
        probs = _heuristic_regime_probability(series)
        return {"model": None, "probabilities": probs}
    try:
        fitted = fit_markov_regime(series, n_states=n_states)
        probs = filtered_regime_probability(fitted, series)
        return {"model": fitted, "probabilities": probs}
    except RuntimeError as exc:
        if "nonconverged" in str(exc).lower():
            probs = _heuristic_regime_probability(series)
            probs = {**probs, "method": "heuristic_nonconverged_markov"}
            return {"model": None, "probabilities": probs}
        probs = _heuristic_regime_probability(series)
        return {"model": None, "probabilities": probs}
    except Exception:  # noqa: BLE001
        probs = _heuristic_regime_probability(series)
        return {"model": None, "probabilities": probs}
