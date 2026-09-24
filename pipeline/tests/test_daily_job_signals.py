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
                "headline_json": '{"classification_reason": "PASS_THRESHOLDS_MET"}',
            },
            {
                "ticker": "BBB",
                "filed_at": "2024-03-31",
                "period": "2023",
                "growth_score": 55.0,
                "quality_score": 50.0,
                "safety_score": 48.0,
                "valuation_score": 45.0,
                "fundamental_view": "WATCH",
                "headline_json": '{"classification_reason": "MODULE_FLOOR_NOT_MET"}',
            },
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


def test_daily_job_defensive_gate_drops_insufficient(tmp_path):
    """Stale watchlist BAD (INSUFFICIENT) bị drop; GOOD WATCH đủ data được giữ."""
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    as_of = "2024-06-28"
    repository.upsert_watchlist(
        conn,
        [
            {"as_of_date": as_of, "ticker": "BAD", "fundamental_view": "WATCH"},
            {"as_of_date": as_of, "ticker": "GOOD", "fundamental_view": "WATCH"},
        ],
    )
    repository.upsert_fundamental_scores(
        conn,
        [
            {
                "ticker": "BAD",
                "filed_at": "2024-03-31",
                "period": "2023",
                "growth_score": 40.0,
                "quality_score": 40.0,
                "safety_score": 40.0,
                "valuation_score": 40.0,
                "fundamental_view": "WATCH",
                "headline_json": '{"classification_reason": "INSUFFICIENT_DATA"}',
            },
            {
                "ticker": "GOOD",
                "filed_at": "2024-03-31",
                "period": "2023",
                "growth_score": 55.0,
                "quality_score": 50.0,
                "safety_score": 48.0,
                "valuation_score": 45.0,
                "fundamental_view": "WATCH",
                "headline_json": '{"classification_reason": "MODULE_FLOOR_NOT_MET"}',
            },
        ],
    )
    conn.close()

    kept = daily_job.load_watchlist_tickers(str(db), as_of)
    assert kept == ["GOOD"]
    assert "BAD" not in kept


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


def _ohlcv_frame(n=40, seed=0):
    """Mini OHLCV DataFrame cho mock prepare_price_inputs (không network)."""
    rng = np.random.default_rng(seed)
    rets = 0.001 + rng.normal(0, 0.01, size=n)
    prices = 50 * np.exp(np.cumsum(rets))
    dates = pd.bdate_range("2024-01-01", periods=n)
    return pd.DataFrame(
        {
            "date": dates.astype(str),
            "open": prices,
            "high": prices,
            "low": prices,
            "close": prices,
            "volume": 1_000,
        }
    )


def test_d2_display_lookup_ingest_split_from_quant(tmp_path, monkeypatch):
    """D-2: upsert bars cho extra display; Quant/signal chỉ watchlist."""
    db = tmp_path / "bot.db"
    display_csv = tmp_path / "display_vn100.csv"
    display_csv.write_text("ticker\nAAA\nVCB\n", encoding="utf-8")

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
                "headline_json": '{"classification_reason": "PASS_THRESHOLDS_MET"}',
            },
        ],
    )
    conn.close()

    prepare_calls: list[dict] = []
    signal_tickers_seen: list[list[str] | None] = []

    def fake_prepare(
        tickers,
        config,
        *,
        lookback_days=365 * 3,
        end=None,
        extra_tickers=None,
    ):
        wanted = []
        seen: set[str] = set()
        for t in list(tickers) + list(extra_tickers or []):
            key = str(t).strip().upper()
            if key and key not in seen:
                wanted.append(key)
                seen.add(key)
        prepare_calls.append(
            {
                "tickers": [str(t).upper() for t in tickers],
                "extra": [str(t).upper() for t in (extra_tickers or [])],
                "lookback": lookback_days,
                "wanted": wanted,
            }
        )
        ohlcv = {
            t: _ohlcv_frame(seed=hash(t) % 10_000) for t in wanted
        }
        close = {
            t: pd.Series(df["close"].values, index=df["date"].values)
            for t, df in ohlcv.items()
        }
        return {
            "start": "2024-01-01",
            "end": end or "2024-06-28",
            "ohlcv": ohlcv,
            "close_series": close,
            "missing": [],
            "fetched": wanted,
        }

    real_generate = daily_job.generate_signals

    def spy_generate(series, **kwargs):
        signal_tickers_seen.append(list(kwargs.get("signal_tickers") or []))
        return real_generate(series, **kwargs)

    monkeypatch.setattr(daily_job, "prepare_price_inputs", fake_prepare)
    monkeypatch.setattr(daily_job, "generate_signals", spy_generate)

    cfg = {
        "universe": {
            "quant_from_watchlist": True,
            "display_lookup_enabled": True,
            "display_lookup_file": str(display_csv),
            "display_lookup_lookback_days": 250,
        },
        "quant_engine": {
            "regime_markov": {"enabled": True},
            "alpha_kalman_trend": {"enabled": True},
            "alpha_ou_meanreversion": {"enabled": False},
            "risk_garch": {"enabled": True},
            "portfolio_black_litterman": {"enabled": False},
            "benchmark": "VNINDEX",
            "sigma_target": 0.02,
            "w_max": 0.1,
        },
    }
    result = daily_job.run(
        cfg,
        db_path=str(db),
        as_of_date="2024-06-28",
        fetch_prices=True,
        persist=True,
        push=False,
    )

    assert {r["ticker"] for r in result["signals"]} == {"AAA"}
    assert "VCB" not in {r["ticker"] for r in result["signals"]}
    assert all("VCB" not in (st or []) for st in signal_tickers_seen)
    assert result["display_price_bars_upserted"] > 0

    # Lần 1 = Quant (watchlist + benchmark); lần 2 = display extra lookback 250
    assert len(prepare_calls) >= 2
    display_calls = [c for c in prepare_calls if c["lookback"] == 250]
    assert display_calls, "expected display prepare with lookback 250"
    assert display_calls[0]["tickers"] == ["VCB"]
    assert "AAA" not in display_calls[0]["tickers"]

    conn = repository.get_connection(str(db))
    closes_vcb = repository.get_price_closes(conn, "VCB", limit_days=500)
    closes_aaa = repository.get_price_closes(conn, "AAA", limit_days=500)
    stored = repository.get_latest_signals(conn, "2024-06-28")
    conn.close()
    assert len(closes_vcb) >= 2
    assert len(closes_aaa) >= 2
    assert {r["ticker"] for r in stored} == {"AAA"}


def test_d2_display_lookup_disabled_skips_extra_ingest(tmp_path, monkeypatch):
    """display_lookup_enabled=false → không prepare/upsert extra."""
    db = tmp_path / "bot.db"
    display_csv = tmp_path / "display.csv"
    display_csv.write_text("ticker\nAAA\nVCB\n", encoding="utf-8")

    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.upsert_watchlist(
        conn,
        [{"as_of_date": "2024-06-28", "ticker": "AAA", "fundamental_view": "PASS"}],
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
            },
        ],
    )
    conn.close()

    prepare_calls: list[dict] = []

    def fake_prepare(tickers, config, *, lookback_days=365 * 3, end=None, extra_tickers=None):
        wanted = [str(t).upper() for t in list(tickers) + list(extra_tickers or [])]
        prepare_calls.append({"lookback": lookback_days, "wanted": wanted})
        ohlcv = {t: _ohlcv_frame(seed=i) for i, t in enumerate(wanted)}
        close = {
            t: pd.Series(df["close"].values, index=df["date"].values)
            for t, df in ohlcv.items()
        }
        return {
            "start": "2024-01-01",
            "end": end or "2024-06-28",
            "ohlcv": ohlcv,
            "close_series": close,
            "missing": [],
            "fetched": wanted,
        }

    monkeypatch.setattr(daily_job, "prepare_price_inputs", fake_prepare)

    result = daily_job.run(
        {
            "universe": {
                "display_lookup_enabled": False,
                "display_lookup_file": str(display_csv),
                "display_lookup_lookback_days": 250,
            },
            "quant_engine": {
                "regime_markov": {"enabled": True},
                "alpha_kalman_trend": {"enabled": True},
                "alpha_ou_meanreversion": {"enabled": False},
                "risk_garch": {"enabled": True},
                "portfolio_black_litterman": {"enabled": False},
                "benchmark": "VNINDEX",
                "sigma_target": 0.02,
                "w_max": 0.1,
            },
        },
        db_path=str(db),
        as_of_date="2024-06-28",
        fetch_prices=True,
        persist=True,
        push=False,
    )
    assert result["display_price_bars_upserted"] == 0
    assert all(c["lookback"] != 250 for c in prepare_calls)
    conn = repository.get_connection(str(db))
    assert repository.get_price_closes(conn, "VCB", limit_days=500) == []
    conn.close()
