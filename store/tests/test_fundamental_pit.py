"""Tests PIT cho ``get_latest_fundamental_scores`` + hygiene unknown share."""

from __future__ import annotations

from store import repository


def _fund_row(ticker: str, filed_at: str, period: str, view: str = "PASS") -> dict:
    return {
        "ticker": ticker,
        "filed_at": filed_at,
        "period": period,
        "growth_score": 0.5,
        "quality_score": 0.5,
        "safety_score": 0.5,
        "valuation_score": 0.5,
        "fundamental_view": view,
        "headline_json": "{}",
    }


def test_get_latest_fundamental_scores_pit_hides_future(tmp_path):
    """Hàng filed_at tương lai không lộ khi as_of = hôm nay; kỳ 2025 vẫn lấy được."""
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.upsert_fundamental_scores(
        conn,
        [
            _fund_row("FPT", "2026-03-31", "2025", "PASS"),
            _fund_row("FPT", "2027-03-31", "2026", "WATCH"),
            _fund_row("VNM", "2025-03-31", "2024", "PASS"),
            _fund_row("VNM", "2027-03-31", "2026", "FAIL"),
        ],
    )

    as_today = repository.get_latest_fundamental_scores(
        conn, ["FPT", "VNM"], as_of_date="2026-09-24"
    )
    assert set(as_today) == {"FPT", "VNM"}
    assert as_today["FPT"]["filed_at"] == "2026-03-31"
    assert as_today["FPT"]["fundamental_view"] == "PASS"
    assert as_today["VNM"]["filed_at"] == "2025-03-31"
    assert as_today["VNM"]["fundamental_view"] == "PASS"

    # as_of sau filed_at tương lai → lấy được hàng 2027.
    as_future = repository.get_latest_fundamental_scores(
        conn, ["FPT"], as_of_date="2027-04-01"
    )
    assert as_future["FPT"]["filed_at"] == "2027-03-31"
    assert as_future["FPT"]["fundamental_view"] == "WATCH"
    conn.close()


def test_get_sector_unknown_share(tmp_path):
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    assert repository.get_sector_unknown_share(conn) is None
    repository.upsert_sector_mapping(
        conn,
        [
            {
                "ticker": "AAA",
                "market": "HOSE",
                "sector": "Food",
                "industry": "Food",
                "subindustry": None,
                "updated_at": "2026-09-24",
            },
            {
                "ticker": "BBB",
                "market": "HOSE",
                "sector": "UNKNOWN",
                "industry": "UNKNOWN",
                "subindustry": None,
                "updated_at": "2026-09-24",
            },
            {
                "ticker": "CCC",
                "market": "HOSE",
                "sector": "Tech",
                "industry": "UNKNOWN",
                "subindustry": None,
                "updated_at": "2026-09-24",
            },
        ],
    )
    share = repository.get_sector_unknown_share(conn)
    assert share is not None
    assert abs(share - 2.0 / 3.0) < 1e-9
    conn.close()
