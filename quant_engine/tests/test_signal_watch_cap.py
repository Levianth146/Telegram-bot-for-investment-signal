"""Fundamental WATCH không được nâng thành BUY trong signal_engine."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_engine.signal_engine import _decide_action, generate_signals


def _close(n=80, drift=0.002, seed=1):
    rng = np.random.default_rng(seed)
    rets = drift + rng.normal(0, 0.01, size=n)
    prices = 50 * np.exp(np.cumsum(rets))
    dates = pd.bdate_range("2024-01-01", periods=n)
    return pd.Series(prices, index=dates.astype(str))


def test_decide_action_caps_buy_when_fundamental_watch():
    buy = _decide_action(
        p_bull=0.9,
        alpha_eff=0.05,
        tstat=3.0,
        bull_threshold=0.55,
        bear_threshold=0.35,
        min_tstat=1.0,
        fundamental_view=None,
    )
    assert buy == "BUY"
    capped = _decide_action(
        p_bull=0.9,
        alpha_eff=0.05,
        tstat=3.0,
        bull_threshold=0.55,
        bear_threshold=0.35,
        min_tstat=1.0,
        fundamental_view="WATCH",
    )
    assert capped == "WATCH"


def test_generate_signals_watch_never_buy():
    close = _close()
    idx = _close(drift=0.001, seed=2)
    signals = generate_signals(
        {"AAA": close, "VNINDEX": idx},
        as_of_date="2024-06-28",
        fundamental_scores={
            "AAA": {
                "growth_score": 70,
                "quality_score": 65,
                "valuation_score": 55,
                "fundamental_view": "WATCH",
            }
        },
        index_ticker="VNINDEX",
        signal_tickers=["AAA"],
        config={
            "quant_engine": {
                "regime_markov": {"enabled": False},
                "alpha_kalman_trend": {"enabled": True},
                "risk_garch": {"enabled": False},
                "portfolio_black_litterman": {"enabled": False},
                "probabilistic_monte_carlo": {"enabled": False},
                "bull_threshold": 0.0,
                "bear_threshold": 0.0,
                "min_tstat": 0.0,
                "sigma_target": 0.02,
                "w_max": 0.1,
            }
        },
    )
    assert len(signals) == 1
    assert signals[0]["action"] != "BUY"
    assert signals[0]["action"] in {"WATCH", "SELL"}
