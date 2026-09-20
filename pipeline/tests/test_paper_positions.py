"""Tests for paper positions + Merton DD."""

from __future__ import annotations

from fundamental_filter.safety import merton_distance_to_default, safety_score
from pipeline.paper_positions import sync_positions_from_signals
from store import repository


def test_open_close_position(tmp_path):
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.open_position(
        conn,
        {
            "ticker": "AAA",
            "opened_at": "2024-06-01",
            "entry_price": 100.0,
            "stop_price": 90.0,
            "size_pct_nav": 0.05,
        },
    )
    open_rows = repository.get_open_positions(conn)
    assert len(open_rows) == 1
    repository.close_position(conn, "AAA", "2024-06-01", 110.0, "2024-06-10")
    assert repository.get_open_positions(conn) == []
    cur = conn.execute(
        "SELECT pnl_pct, status FROM positions WHERE ticker='AAA'"
    )
    row = dict(cur.fetchone())
    assert row["status"] == "CLOSED"
    assert abs(row["pnl_pct"] - 0.1) < 1e-9
    conn.close()


def test_sync_positions_from_signals(tmp_path):
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    signals = [
        {
            "date": "2024-06-28",
            "ticker": "AAA",
            "action": "BUY",
            "stop": 90.0,
            "size": 0.05,
        }
    ]
    result = sync_positions_from_signals(
        conn, signals, entry_price_by_ticker={"AAA": 100.0}
    )
    assert result["opened"] == 1
    signals_sell = [
        {
            "date": "2024-07-01",
            "ticker": "AAA",
            "action": "SELL",
            "stop": 90.0,
            "size": 0.05,
        }
    ]
    result2 = sync_positions_from_signals(
        conn, signals_sell, entry_price_by_ticker={"AAA": 105.0}
    )
    assert result2["closed"] == 1
    conn.close()


def test_merton_dd_formula():
    dd = merton_distance_to_default(
        equity_value=1e12,
        equity_vol=0.3,
        debt_face_value=2e11,
        risk_free_rate=0.05,
        horizon_years=1.0,
    )
    assert dd > 0

    disabled = safety_score({"score": 60.0}, {"fundamental_filter": {"safety_merton_dd": {"enabled": False}}})
    assert disabled["supporting"]["merton_dd_status"] == "disabled"

    enabled = safety_score(
        {
            "score": 60.0,
            "equity_value": 1e12,
            "equity_vol": 0.25,
            "debt_face_value": 3e11,
            "risk_free_rate": 0.04,
        },
        {"fundamental_filter": {"safety_merton_dd": {"enabled": True}}},
    )
    assert enabled["supporting"]["merton_dd"] is not None
    assert enabled["supporting"]["merton_dd_status"] == "computed_naive_bs2008"
