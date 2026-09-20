"""Quant P0 unit tests — no network."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from quant_engine.alpha.kalman_trend import alpha_effective, fit_kalman_trend, slope_tstat
from quant_engine.alpha.ou_meanrev import fit_ou_process, ou_half_life
from quant_engine.portfolio.black_litterman import equal_weight_fallback
from quant_engine.regime import filtered_regime_probability, fit_or_fallback_regime
from quant_engine.risk.garch import position_size, rolling_sigma_fallback, stop_loss_price
from quant_engine.signal_engine import generate_signals


def _synthetic_close(n=120, drift=0.001, seed=0) -> pd.Series:
    rng = np.random.default_rng(seed)
    rets = drift + rng.normal(0, 0.015, size=n)
    prices = 100 * np.exp(np.cumsum(rets))
    dates = pd.bdate_range("2024-01-01", periods=n)
    return pd.Series(prices, index=dates.astype(str), name="close")


def test_alpha_effective_bounds():
    assert alpha_effective(1.0, 0, 0) == pytest.approx(0.5)
    assert alpha_effective(1.0, 100, 100) == pytest.approx(1.5)
    assert alpha_effective(2.0, 50, 50) == pytest.approx(2.0)


def test_kalman_trend_on_uptrend():
    close = _synthetic_close(drift=0.002, seed=1)
    level, slope, svar = fit_kalman_trend(np.log(close))
    assert len(level) == len(close)
    tstat = slope_tstat(float(slope.iloc[-1]), float(svar.iloc[-1]))
    assert tstat > 0


def test_ou_half_life():
    assert ou_half_life(math.log(2)) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        ou_half_life(0.0)
    # Mean-reverting residual around 0
    t = np.arange(80)
    resid = 0.5 * np.exp(-0.1 * t) + np.random.default_rng(0).normal(0, 0.05, size=80)
    params = fit_ou_process(resid)
    assert params["theta"] > 0


def test_position_size_and_stop():
    # min(w_max=0.1, 0.02/0.04=0.5) → capped at w_max
    assert position_size(0.04, 0.02, w_max=0.1) == pytest.approx(0.1)
    assert position_size(0.4, 0.02, w_max=0.1) == pytest.approx(0.05)
    assert stop_loss_price(100.0, 0.02, k=2.0) == pytest.approx(96.0)


def test_regime_heuristic_fallback():
    rets = _synthetic_close(drift=0.002).pct_change().dropna()
    pack = fit_or_fallback_regime(rets)
    probs = pack["probabilities"]
    assert abs(sum(probs[k] for k in ("bull", "bear", "turbulent")) - 1.0) < 1e-9
    fallback = filtered_regime_probability(None, rets)
    assert "bull" in fallback


def test_equal_weight_fallback():
    weights = equal_weight_fallback(["aaa", "BBB"])
    assert weights == {"AAA": 0.5, "BBB": 0.5}


def test_generate_signals_writes_schema_fields(tmp_path):
    close_a = _synthetic_close(drift=0.002, seed=2)
    close_b = _synthetic_close(drift=-0.001, seed=3)
    signals = generate_signals(
        {"AAA": close_a, "BBB": close_b},
        as_of_date="2024-06-28",
        fundamental_scores={
            "AAA": {"growth_score": 70, "quality_score": 65},
            "BBB": {"growth_score": 40, "quality_score": 40},
        },
        config={
            "quant_engine": {
                "regime_markov": {"enabled": True},
                "alpha_kalman_trend": {"enabled": True},
                "alpha_ou_meanreversion": {"enabled": True},
                "risk_garch": {"enabled": True},
                "portfolio_black_litterman": {"enabled": False},
                "sigma_target": 0.02,
                "w_max": 0.1,
                "benchmark": "AAA",
            }
        },
    )
    assert len(signals) == 2
    for row in signals:
        assert row["date"] == "2024-06-28"
        assert row["action"] in {"BUY", "WATCH", "SELL"}
        assert 0.0 <= row["p_regime"] <= 1.0
        assert row["size"] >= 0.0
        assert row["reason_json"]


def test_rolling_sigma_fallback():
    rets = _synthetic_close().pct_change().dropna()
    sigma = rolling_sigma_fallback(rets, window=20)
    assert sigma > 0
