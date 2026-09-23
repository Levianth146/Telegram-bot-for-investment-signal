"""P0-1: sizing inverse-vol / w_max trên tập BUY — không pha loãng 1/N watchlist."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from quant_engine import signal_engine
from quant_engine.signal_engine import generate_signals


def _close(n=80, drift=0.002, seed=1, start="2024-01-01"):
    rng = np.random.default_rng(seed)
    rets = drift + rng.normal(0, 0.01, size=n)
    prices = 50 * np.exp(np.cumsum(rets))
    dates = pd.bdate_range(start, periods=n)
    return pd.Series(prices, index=dates.astype(str))


def test_buy_sizing_not_diluted_by_full_watchlist(monkeypatch):
    """20 mã watchlist, 2 mã BUY → size không còn ≈ 1/20."""
    n_watch = 20
    buy_names = ["AAA", "BBB"]
    closes = {f"T{i:02d}": _close(seed=i + 1) for i in range(n_watch - 2)}
    closes["AAA"] = _close(seed=100, drift=0.003)
    closes["BBB"] = _close(seed=101, drift=0.003)
    closes["VNINDEX"] = _close(seed=0, drift=0.001)

    # Patch decide: uncapped → BUY; capped theo fundamental_view PASS/WATCH.
    real_decide = signal_engine._decide_action

    def decide_by_fund(**kwargs):
        view = kwargs.get("fundamental_view")
        if view is None:
            return "BUY"
        if str(view).upper() == "PASS":
            return "BUY"
        return "WATCH"

    monkeypatch.setattr(signal_engine, "_decide_action", decide_by_fund)

    fund = {}
    for t in closes:
        if t == "VNINDEX":
            continue
        fund[t] = {
            "growth_score": 70,
            "quality_score": 70,
            "valuation_score": 60,
            "fundamental_view": "PASS" if t in buy_names else "WATCH",
        }

    w_max = 0.10
    signals = generate_signals(
        closes,
        as_of_date="2024-06-28",
        fundamental_scores=fund,
        index_ticker="VNINDEX",
        signal_tickers=[t for t in closes if t != "VNINDEX"],
        config={
            "quant_engine": {
                "w_max": w_max,
                "sigma_target": 0.02,
                "regime_markov": {"enabled": False},
                "alpha_kalman_trend": {"enabled": True},
                "alpha_ou_meanreversion": {"enabled": False},
                "risk_garch": {"enabled": True},
                "portfolio_black_litterman": {"enabled": False},
                "probabilistic_monte_carlo": {"enabled": False},
                "probabilistic_hawkes": {"enabled": False},
                "bull_threshold": 0.55,
                "bear_threshold": 0.35,
                "min_slope_tstat": 0.0,
            }
        },
    )
    by_ticker = {s["ticker"]: s for s in signals}
    buy_rows = [by_ticker[t] for t in buy_names]
    assert all(r["action"] == "BUY" for r in buy_rows)
    sizes = [float(r["size"]) for r in buy_rows]
    total_buy = sum(sizes)
    # Trước bug: mỗi mã ~1/20 = 0.05; sau fix: chia trên 2 BUY → thường lớn hơn hẳn 2/20.
    assert total_buy > 2.0 / n_watch + 0.05
    assert all(s <= w_max + 1e-9 for s in sizes)
    assert all(s > 1.0 / n_watch for s in sizes)

    # Non-BUY phải size 0
    for t, row in by_ticker.items():
        if t not in buy_names:
            assert float(row["size"]) == 0.0

    reason = json.loads(buy_rows[0]["reason_json"])
    assert reason.get("weight_method") == "w_max_only"
    assert reason.get("n_buy_universe") == 2

    monkeypatch.setattr(signal_engine, "_decide_action", real_decide)
