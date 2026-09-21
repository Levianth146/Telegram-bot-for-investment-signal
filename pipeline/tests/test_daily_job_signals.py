"""Tests for daily_job signal persistence (no network)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline import daily_job
from store import repository


def _close(n=100, drift=0.001, seed=0):
    rng = np.random.default_rng(seed)
    rets = drift + rng.normal(0, 0.015, size=n)
    prices = 50 * np.exp(np.cumsum(rets))
    dates = pd.bdate_range("2024-01-01", periods=n)
    return pd.Series(prices, index=dates.astype(str))


def test_daily_job_run_with_synthetic_closes(tmp_path):
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.upsert_watchlist(
        conn,
        [
            {"as_of_date": "2024-06-28", "ticker": "AAA", "fundamental_view": "PASS"},
            {"as_of_date": "2024-06-28", "ticker": "BBB", "fundamental_view": "WATCH"},
        ],
    )
    repository.upsert_fundamental_scores(
        conn,
        [
            {
                "ticker": "AAA",
                "filed_at": "2024-03-31",
                "period": "2023",
                "growth_score": 70.0,
                "quality_score": 65.0,
                "safety_score": 60.0,
                "valuation_score": 55.0,
                "fundamental_view": "PASS",
                "headline_json": "{}",
            }
        ],
    )
    conn.close()

    result = daily_job.run(
        {
            "quant_engine": {
                "regime_markov": {"enabled": True},
                "alpha_kalman_trend": {"enabled": True},
                "alpha_ou_meanreversion": {"enabled": True},
                "risk_garch": {"enabled": True},
                "portfolio_black_litterman": {"enabled": False},
                "benchmark": "VNINDEX",
                "sigma_target": 0.02,
                "w_max": 0.1,
            }
        },
        db_path=str(db),
        as_of_date="2024-06-28",
        fetch_prices=False,
        close_by_ticker={
            "AAA": _close(seed=1),
            "BBB": _close(drift=-0.001, seed=2),
            "VNINDEX": _close(drift=0.0005, seed=3),
        },
        persist=True,
        push=False,
    )
    assert len(result["signals"]) == 2
    assert {r["ticker"] for r in result["signals"]} == {"AAA", "BBB"}
    assert result["benchmark_loaded"] is True
    assert result["price_bars_upserted"] > 0
    conn = repository.get_connection(str(db))
    stored = repository.get_latest_signals(conn, "2024-06-28")
    closes_aaa = repository.get_price_closes(conn, "AAA", limit_days=500)
    conn.close()
    assert len(stored) == 2
    assert {r["ticker"] for r in stored} == {"AAA", "BBB"}
    assert len(closes_aaa) >= 2


def test_backfill_from_store_uses_price_bars(tmp_path):
    """Backfill tính lại từ giá đã lưu — không bịa sigma/p_regime."""
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.upsert_watchlist(
        conn,
        [
            {"as_of_date": "2024-06-28", "ticker": "AAA", "fundamental_view": "PASS"},
        ],
    )
    repository.upsert_fundamental_scores(
        conn,
        [
            {
                "ticker": "AAA",
                "filed_at": "2024-03-31",
                "period": "2023",
                "growth_score": 70.0,
                "quality_score": 65.0,
                "safety_score": 60.0,
                "valuation_score": 55.0,
                "fundamental_view": "PASS",
                "headline_json": "{}",
            }
        ],
    )
    # Seed 40 phiên giá (AAA + VNINDEX)
    bars = []
    for name, seed in (("AAA", 1), ("VNINDEX", 3)):
        s = _close(n=40, seed=seed)
        for day, val in s.items():
            bars.append(
                {
                    "ticker": name,
                    "date": str(day)[:10],
                    "open": float(val),
                    "high": float(val),
                    "low": float(val),
                    "close": float(val),
                    "volume": 1_000,
                }
            )
    repository.upsert_price_bars(conn, bars)
    conn.close()

    cfg = {
        "quant_engine": {
            "regime_markov": {"enabled": True},
            "alpha_kalman_trend": {"enabled": True},
            "alpha_ou_meanreversion": {"enabled": False},
            "risk_garch": {"enabled": True},
            "portfolio_black_litterman": {"enabled": False},
            "benchmark": "VNINDEX",
            "sigma_target": 0.02,
            "w_max": 0.1,
        }
    }
    bf = daily_job.backfill_from_store(cfg, db_path=str(db), days=5, push=False)
    assert bf["signals_upserted_days"] >= 3
    conn = repository.get_connection(str(db))
    n_dates = conn.execute("SELECT COUNT(DISTINCT date) AS n FROM signals").fetchone()[
        "n"
    ]
    conn.close()
    assert n_dates >= 3
