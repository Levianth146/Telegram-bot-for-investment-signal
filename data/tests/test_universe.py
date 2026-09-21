"""Universe CSV loader tests (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from data.universe import load_universe_tickers, resolve_tickers


def test_load_universe_tickers_sample():
    path = Path("data/universe/vn30_sample.csv")
    tickers = load_universe_tickers(path)
    assert "FPT" in tickers
    assert "VNM" in tickers
    assert len(tickers) >= 20
    assert len(tickers) == len(set(tickers))


def test_load_universe_tickers_comments(tmp_path):
    path = tmp_path / "u.csv"
    path.write_text("# comment\nticker\nAAA\n\nbbb\nAAA\n", encoding="utf-8")
    assert load_universe_tickers(path) == ["AAA", "BBB"]


def test_resolve_tickers_prefers_cli():
    assert resolve_tickers(tickers_csv="vnm,fpt", universe_file="missing.csv") == [
        "VNM",
        "FPT",
    ]


def test_normalize_exchange_aliases():
    from data.universe import normalize_exchange

    assert normalize_exchange("hsx") == "HOSE"
    assert normalize_exchange("HNX") == "HNX"
    assert normalize_exchange("UPCOM") == "UPCOM"
    assert normalize_exchange("VN") is None
    assert normalize_exchange(None) is None


def test_filter_tickers_drops_upcom_keeps_hose_and_unmapped():
    from data.universe import filter_tickers_by_exchange

    kept, dropped = filter_tickers_by_exchange(
        ["FPT", "ABC", "XYZ", "VNM"],
        market_by_ticker={
            "FPT": "HOSE",
            "ABC": "UPCOM",
            "XYZ": "VN",
            # VNM missing → keep
        },
        allowed_exchanges=["HOSE", "HNX"],
    )
    assert kept == ["FPT", "XYZ", "VNM"]
    assert dropped == ["ABC"]


def test_filter_tickers_for_config_uses_db(tmp_path):
    from data.universe import filter_tickers_for_config
    from store import repository

    db = tmp_path / "u.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.upsert_sector_mapping(
        conn,
        [
            {
                "ticker": "FPT",
                "market": "HOSE",
                "sector": "Tech",
                "industry": "IT",
                "subindustry": None,
                "updated_at": "2024-01-01",
            },
            {
                "ticker": "UPC1",
                "market": "UPCOM",
                "sector": "Other",
                "industry": "Misc",
                "subindustry": None,
                "updated_at": "2024-01-01",
            },
        ],
    )
    conn.close()
    kept, dropped = filter_tickers_for_config(
        ["FPT", "UPC1", "VNM"],
        {"universe": {"allowed_exchanges": ["HOSE", "HNX"]}},
        db_path=str(db),
    )
    assert kept == ["FPT", "VNM"]
    assert dropped == ["UPC1"]


def test_load_universe_missing_file():
    with pytest.raises(FileNotFoundError):
        load_universe_tickers("data/universe/does_not_exist.csv")
