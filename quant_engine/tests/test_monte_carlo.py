"""Monte Carlo P1 unit tests."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_engine.probabilistic.monte_carlo import (
    cvar,
    monte_carlo_signal_stats,
    probability_tp_before_sl,
    simulate_price_paths,
)
from quant_engine.signal_engine import generate_signals


def test_simulate_and_stats():
    rng = np.random.default_rng(0)
    resid = rng.normal(0, 1, size=80)
    paths = simulate_price_paths(
        100.0, 0.02, resid, horizon_days=10, n_paths=500, rng=rng
    )
    assert paths.shape == (500, 10)
    p = probability_tp_before_sl(paths, 100.0, 0.08, 0.04)
    assert 0.0 <= p <= 1.0
    cv = cvar(paths, 100.0, 0.95)
    assert cv <= 0.0 or abs(cv) < 1.0  # typically negative


def test_monte_carlo_wrapper():
    rets = pd.Series(np.random.default_rng(1).normal(0, 0.015, size=100))
    out = monte_carlo_signal_stats(
        50.0, 0.02, rets, stop_price=48.0, n_paths=300, horizon_days=8
    )
    assert out["p_tp_before_sl"] is not None
    assert out["cvar95"] is not None


def test_generate_signals_fills_mc_when_enabled():
    n = 80
    rng = np.random.default_rng(2)
    rets = 0.001 + rng.normal(0, 0.012, size=n)
    prices = 100 * np.exp(np.cumsum(rets))
    dates = pd.bdate_range("2024-01-01", periods=n).strftime("%Y-%m-%d")
    close = pd.Series(prices, index=dates)
    signals = generate_signals(
        {"AAA": close},
        as_of_date=str(dates[-1]),
        config={
            "quant_engine": {
                "regime_markov": {"enabled": True},
                "alpha_kalman_trend": {"enabled": True},
                "alpha_ou_meanreversion": {"enabled": False},
                "risk_garch": {"enabled": False},
                "portfolio_black_litterman": {"enabled": False},
                "probabilistic_monte_carlo": {
                    "enabled": True,
                    "n_paths": 200,
                    "horizon_days": 5,
                    "tp_pct": 0.08,
                },
                "benchmark": "AAA",
                "sigma_target": 0.02,
                "w_max": 0.1,
            }
        },
    )
    assert len(signals) == 1
    assert signals[0]["p_tp_before_sl"] is not None
    assert signals[0]["cvar95"] is not None
