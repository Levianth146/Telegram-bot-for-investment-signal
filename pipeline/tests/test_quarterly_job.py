"""quarterly_job / daily_job hooks."""

from __future__ import annotations

import sys

import pytest

from data.ingest.scoring_frames import build_scoring_frames
from pipeline import daily_job, quarterly_job
from store import repository


def _annual(revenue, eps, equity):
    ebit = revenue * 0.2
    return {
        "revenue": revenue,
        "gross_profit": revenue * 0.4,
        "ebit": ebit,
        "ebitda": ebit * 1.2,
        "npat_parent": eps * 10,
        "eps": eps,
        "pretax_profit": ebit,
        "tax_expense": ebit * 0.2,
        "interest_expense": 5,
        "cash": 20,
        "receivables": 10,
        "inventory": 10,
        "current_assets": 80,
        "current_liabilities": 40,
        "short_term_debt": 25,
        "long_term_debt": 25,
        "total_assets": 200,
        "equity": equity,
        "cfo": 100,
        "capex": 20,
    }


def test_quarterly_job_dry_run(capsys):
    old = sys.argv
    try:
        sys.argv = ["quarterly_job", "--dry-run"]
        quarterly_job.main()
    finally:
        sys.argv = old
    out = capsys.readouterr().out
    assert "dry-run OK" in out


def test_quarterly_job_run_with_synthetic_frames(tmp_path):
    books = {
        ("AAA", y): _annual(80 + y, 1.0 + (y - 2020) * 0.1, 70 + y - 2020)
        for y in range(2020, 2025)
    }
    books.update(
        {
            ("BBB", y): _annual(50 + y - 2020, 0.5, 40)
            for y in range(2020, 2025)
        }
    )

    frames = build_scoring_frames(
        ["AAA", "BBB"],
        2022,
        2024,
        lambda t, y: books.get((t, y)),
    )
    db = tmp_path / "bot.db"
    result = quarterly_job.run(
        {"data_sources": {"financial_statements_backtest": {"assumed_publication_lag_days": 90}}},
        scoring_frames=frames,
        start_year=2022,
        end_year=2024,
        db_path=str(db),
        persist=True,
    )
    assert len(result["results"]) == 2
    assert result["filed_at"] == "2025-03-31"
    assert all(
        r["filed_at"] == "2025-03-31" for r in result["records"]["fundamental_scores"]
    )
    conn = repository.get_connection(str(db))
    watch = repository.get_watchlist(conn)
    conn.close()
    # watchlist may be empty if both FAIL; at least schema write succeeded
    assert isinstance(watch, list)


def test_quarterly_job_requires_inputs():
    with pytest.raises(ValueError):
        quarterly_job.run({}, start_year=2022, end_year=2024)


def test_daily_job_dry_run(capsys, tmp_path):
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.upsert_watchlist(
        conn,
        [{"as_of_date": "2025-01-01", "ticker": "VNM", "fundamental_view": "PASS"}],
    )
    conn.close()

    old = sys.argv
    try:
        sys.argv = ["daily_job", "--dry-run", "--db-path", str(db)]
        daily_job.main()
    finally:
        sys.argv = old
    out = capsys.readouterr().out
    assert "dry-run OK" in out
    assert "watchlist size: 1" in out


def test_quarterly_job_fetch_live_uses_mode_live(monkeypatch, tmp_path):
    """fetch_live=True phải gọi build_scoring_frames_from_providers(..., mode='live')."""
    import pandas as pd

    seen: dict = {}

    def fake_build(
        tickers,
        start_year,
        end_year,
        config=None,
        *,
        db_path="store/bot.db",
        mode="backtest",
    ):
        seen["mode"] = mode
        seen["tickers"] = list(tickers)
        return {}

    monkeypatch.setattr(
        quarterly_job, "build_scoring_frames_from_providers", fake_build
    )
    monkeypatch.setattr(
        quarterly_job,
        "score_current_universe",
        lambda *a, **k: (pd.DataFrame(), {}, {}),
    )
    monkeypatch.setattr(
        quarterly_job,
        "to_store_records",
        lambda *a, **k: {"fundamental_scores": [], "watchlist": []},
    )
    db = tmp_path / "bot.db"
    result = quarterly_job.run(
        {
            "data_sources": {
                "financial_statements_backtest": {"assumed_publication_lag_days": 90}
            }
        },
        tickers=["AAA"],
        start_year=2022,
        end_year=2024,
        db_path=str(db),
        persist=False,
        fetch_live=True,
    )
    assert seen.get("mode") == "live"
    assert seen.get("tickers") == ["AAA"]
    assert result["filed_at"] == "2025-03-31"
