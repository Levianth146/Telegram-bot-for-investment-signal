"""Parity ProcessPool vs tuần tự — Phase 1 speed (không đổi metric)."""

from __future__ import annotations

import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from quant_engine.signal_engine import (
    _resolve_parallel_workers,
    generate_signals,
    shutdown_hotpath_pool,
)


def _cfg(workers: int | None) -> dict:
    return {
        "quant_engine": {
            "benchmark": "VNINDEX",
            "sigma_target": 0.02,
            "w_max": 0.10,
            "stop_k": 2.0,
            "bull_threshold": 0.55,
            "bear_threshold": 0.35,
            "min_slope_tstat": 1.0,
            "parallel_workers": workers,
            "regime_markov": {"enabled": True},
            "alpha_kalman_trend": {"enabled": True},
            "alpha_ou_meanreversion": {"enabled": False},
            "risk_garch": {"enabled": True},
            "portfolio_black_litterman": {"enabled": False},
            "probabilistic_monte_carlo": {"enabled": False},
            "probabilistic_hawkes": {"enabled": False},
        }
    }


def _closes(n_tickers: int = 4, n_days: int = 90) -> dict[str, pd.Series]:
    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2024-01-02", periods=n_days).strftime("%Y-%m-%d")
    out: dict[str, pd.Series] = {}
    names = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"][:n_tickers]
    for i, t in enumerate(names):
        walk = 100.0 + i * 3.0 + np.cumsum(rng.normal(0.04, 1.0, size=n_days))
        out[t] = pd.Series(walk, index=list(dates), name="close")
    walk_b = 1000.0 + np.cumsum(rng.normal(0.02, 0.8, size=n_days))
    out["VNINDEX"] = pd.Series(walk_b, index=list(dates), name="close")
    return out


def test_resolve_parallel_workers_auto_and_sequential():
    assert _resolve_parallel_workers(1, 8) == 1
    assert _resolve_parallel_workers(0, 8) == 1
    assert _resolve_parallel_workers(4, 3) == 3
    auto = _resolve_parallel_workers(None, 8)
    assert 1 <= auto <= min(int(os.cpu_count() or 1), 8)


def test_sequential_vs_parallel_parity_actions_sizes_sigmas():
    """Cùng input → action/size/sigma_hat giống nhau workers=1 vs workers≥2."""
    closes = _closes(n_tickers=4, n_days=90)
    tickers = [t for t in closes if t != "VNINDEX"]
    as_of = str(closes["AAA"].index[-1])
    funds = {
        t: {
            "growth_score": 60.0 + i,
            "quality_score": 55.0,
            "valuation_score": 50.0,
            "fundamental_view": "PASS",
        }
        for i, t in enumerate(tickers)
    }

    seq = generate_signals(
        closes,
        as_of_date=as_of,
        fundamental_scores=funds,
        index_ticker="VNINDEX",
        signal_tickers=tickers,
        config=_cfg(1),
    )
    par = generate_signals(
        closes,
        as_of_date=as_of,
        fundamental_scores=funds,
        index_ticker="VNINDEX",
        signal_tickers=tickers,
        config=_cfg(2),
    )

    assert len(seq) == len(par) == len(tickers)
    by_s = {r["ticker"]: r for r in seq}
    by_p = {r["ticker"]: r for r in par}
    assert sorted(by_s) == sorted(by_p) == sorted(tickers)
    for t in tickers:
        a, b = by_s[t], by_p[t]
        assert a["action"] == b["action"], t
        assert a["size"] == pytest.approx(b["size"], rel=1e-9, abs=1e-12), t
        if a["sigma_hat"] is None or b["sigma_hat"] is None:
            assert a["sigma_hat"] is None and b["sigma_hat"] is None
        else:
            assert a["sigma_hat"] == pytest.approx(
                b["sigma_hat"], rel=1e-7, abs=1e-10
            ), t


def test_kalman_cache_still_keyed_by_ticker_with_parallel():
    """Xác nhận P2-1 kalman_cache còn hoạt động khi workers≥2."""
    closes = _closes(n_tickers=2, n_days=60)
    cfg = _cfg(2)
    cfg["quant_engine"]["regime_markov"] = {"enabled": False}
    cfg["quant_engine"]["risk_garch"] = {"enabled": False}
    cache: dict = {}
    aaa = closes["AAA"]
    vni = closes["VNINDEX"]
    idx = list(aaa.index)
    cut1 = {"AAA": aaa.iloc[:58], "VNINDEX": vni.iloc[:58]}
    generate_signals(
        cut1,
        as_of_date=idx[57],
        signal_tickers=["AAA"],
        config=cfg,
        kalman_cache=cache,
    )
    assert set(cache.keys()) == {"AAA"}
    n_before = int(cache["AAA"]["n"])
    cut2 = {"AAA": aaa.iloc[:59], "VNINDEX": vni.iloc[:59]}
    generate_signals(
        cut2,
        as_of_date=idx[58],
        signal_tickers=["AAA"],
        config=cfg,
        kalman_cache=cache,
    )
    assert set(cache.keys()) == {"AAA"}
    assert int(cache["AAA"]["n"]) == n_before + 1


def test_p2_2_signal_tickers_none_still_in_ablation():
    """Smoke: P2-2 ablation vẫn truyền signal_tickers=None (không rewrite)."""
    text = Path("backtest/ablation.py").read_text(encoding="utf-8")
    assert "signal_tickers=None" in text
    assert text.count("signal_tickers=None") >= 3


@pytest.fixture(autouse=True)
def _close_pool_after_test():
    yield
    shutdown_hotpath_pool()
