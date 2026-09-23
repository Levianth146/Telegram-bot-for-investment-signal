"""Tests eligibility Layer 1 → Quant + replace_watchlist batch-safe."""

from __future__ import annotations

from fundamental_filter.layer1_engine.eligibility import (
    is_fundamental_insufficient,
    is_quant_eligible_fundamental,
)
from store import repository


def test_replace_watchlist_removes_stale_keeps_other(tmp_path):
    """AAA PASS→FAIL: khỏi watchlist; BBB không bị xóa (batch-safe)."""
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    as_of = "2025-03-31"
    repository.upsert_watchlist(
        conn,
        [
            {"as_of_date": as_of, "ticker": "AAA", "fundamental_view": "PASS"},
            {"as_of_date": as_of, "ticker": "BBB", "fundamental_view": "WATCH"},
        ],
    )
    repository.upsert_fundamental_scores(
        conn,
        [
            {
                "ticker": "AAA",
                "filed_at": as_of,
                "period": "2024",
                "growth_score": 70.0,
                "quality_score": 65.0,
                "safety_score": 60.0,
                "valuation_score": 55.0,
                "fundamental_view": "FAIL",
                "headline_json": '{"classification_reason": "BELOW_WATCH_PERCENTILE"}',
            }
        ],
    )
    repository.replace_watchlist_for_tickers(
        conn,
        as_of_date=as_of,
        processed_tickers=["AAA"],
        eligible_rows=[],  # AAA không còn eligible
    )
    wl = repository.get_watchlist(conn, as_of)
    conn.close()
    assert "AAA" not in wl
    assert "BBB" in wl


def test_is_fundamental_insufficient_critical_flag_without_word():
    """C5 helper — flag critical dù reason không chứa chữ INSUFFICIENT."""
    row = {
        "fundamental_view": "WATCH",
        "growth_score": 50.0,
        "quality_score": 50.0,
        "safety_score": 50.0,
        "valuation_score": 50.0,
        "headline_json": (
            '{"classification_reason": "MIDDLE_PERCENTILE", '
            '"data_quality": {"critical_data_quality_flag": true}}'
        ),
    }
    assert is_fundamental_insufficient(row) is True
    assert is_quant_eligible_fundamental(row) is False
