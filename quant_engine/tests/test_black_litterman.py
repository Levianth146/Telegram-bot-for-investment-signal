"""Tests for Black-Litterman portfolio weights (no network)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_engine.portfolio.black_litterman import (
    black_litterman_weights,
    bl_portfolio_weights,
    build_views,
    equal_weight_fallback,
)
from quant_engine.signal_engine import generate_signals


def _close(n=120, drift=0.001, seed=0):
    rng = np.random.default_rng(seed)
    rets = drift + rng.normal(0, 0.015, size=n)
    prices = 50 * np.exp(np.cumsum(rets))
    dates = pd.bdate_range("2024-01-01", periods=n)
    return pd.Series(prices, index=dates.astype(str))


def test_equal_weight_fallback():
    assert equal_weight_fallback(["AAA", "BBB"]) == {"AAA": 0.5, "BBB": 0.5}


def test_build_views_and_bl_weights():
    p, q, omega, tickers = build_views(
        {"AAA": 1.5, "BBB": -0.5},
        {"AAA": 70.0, "BBB": 40.0},
    )
    assert tickers == ["AAA", "BBB"]
    assert p.shape == (2, 2)
    assert omega.shape == (2, 2)
    cov = np.array([[0.0004, 0.0001], [0.0001, 0.0005]])
    weights = black_litterman_weights(
        {"AAA": 2.0, "BBB": 1.0},
        cov,
        p,
        q,
        omega,
        tickers=tickers,
    )
    assert set(weights) == {"AAA", "BBB"}
    assert abs(sum(weights.values()) - 1.0) < 1e-9
    assert all(w >= 0 for w in weights.values())


def test_bl_portfolio_weights_from_closes():
    closes = {"AAA": _close(seed=1), "BBB": _close(drift=-0.001, seed=2)}
    weights = bl_portfolio_weights(
        closes,
        ["AAA", "BBB"],
        {"AAA": 0.8, "BBB": -0.3},
        {"AAA": 65.0, "BBB": 45.0},
    )
    assert abs(sum(weights.values()) - 1.0) < 1e-9


def test_generate_signals_bl_enabled():
    signals = generate_signals(
        {"AAA": _close(seed=1), "BBB": _close(drift=0.0, seed=2)},
        as_of_date="2024-06-28",
        fundamental_scores={
            "AAA": {"growth_score": 70, "quality_score": 65, "valuation_score": 60},
            "BBB": {"growth_score": 40, "quality_score": 40, "valuation_score": 45},
        },
        config={
            "quant_engine": {
                "regime_markov": {"enabled": True},
                "alpha_kalman_trend": {"enabled": True},
                "alpha_ou_meanreversion": {"enabled": False},
                "risk_garch": {"enabled": False},
                "portfolio_black_litterman": {"enabled": True, "tau": 0.05},
                "probabilistic_monte_carlo": {"enabled": False},
                "probabilistic_hawkes": {"enabled": False},
                "benchmark": "AAA",
                "sigma_target": 0.02,
                "w_max": 0.1,
            }
        },
    )
    assert len(signals) == 2
    methods = {row["ticker"]: row["reason_json"] for row in signals}
    assert "black_litterman" in methods["AAA"] or "equal_weight" in methods["AAA"]
