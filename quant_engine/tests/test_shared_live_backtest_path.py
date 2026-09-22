"""Smoke: live path và backtest dùng chung generate_signals + score_current_universe."""

from __future__ import annotations

import numpy as np
import pandas as pd

from backtest import engine as backtest_engine
from fundamental_filter import score_current_universe
from pipeline import daily_job
from quant_engine.signal_engine import generate_signals


def _close(n: int = 60, seed: int = 1) -> pd.Series:
    rng = np.random.default_rng(seed)
    rets = 0.0005 + rng.normal(0, 0.01, size=n)
    prices = 50 * np.exp(np.cumsum(rets))
    dates = pd.bdate_range("2024-01-02", periods=n)
    return pd.Series(prices, index=dates.strftime("%Y-%m-%d"), name="close")


def test_shared_imports_live_and_backtest():
    """ARCHITECTURE #2 — cùng symbol import, không bản sao riêng."""
    assert backtest_engine.generate_signals is generate_signals
    # daily_job cũng gọi cùng generate_signals (không copy logic)
    assert getattr(daily_job, "generate_signals", None) is generate_signals
    assert callable(score_current_universe)


def test_generate_signals_smoke_synthetic():
    closes = {"AAA": _close(), "VNINDEX": _close(seed=2)}
    signals = generate_signals(
        closes,
        as_of_date="2024-03-29",
        fundamental_scores={"AAA": {"fundamental_view": "PASS"}},
        index_ticker="VNINDEX",
        signal_tickers=["AAA"],
        config={
            "quant_engine": {
                "regime_markov": {"enabled": True},
                "alpha_kalman_trend": {"enabled": True},
                "alpha_ou_meanreversion": {"enabled": False},
                "risk_garch": {"enabled": True},
                "portfolio_black_litterman": {"enabled": False},
                "probabilistic_monte_carlo": {"enabled": False},
                "benchmark": "VNINDEX",
            }
        },
    )
    assert isinstance(signals, list)
