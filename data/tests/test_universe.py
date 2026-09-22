"""Universe CSV loader tests (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from data.universe import (
    fundamental_universe_file,
    load_fundamental_universe,
    load_universe_tickers,
    quant_from_watchlist,
    resolve_tickers,
    smoke_universe_file,
)


def test_load_universe_tickers_sample():
    path = Path("data/universe/vn30_sample.csv")
    tickers = load_universe_tickers(path)
    assert "FPT" in tickers
    assert "VNM" in tickers
    assert len(tickers) >= 20
    assert len(tickers) == len(set(tickers))


def test_load_hose_liquid_35():
    path = Path("data/universe/hose_liquid_35.csv")
    tickers = load_universe_tickers(path)
    assert len(tickers) >= 30
    assert len(tickers) <= 40
    assert "FPT" in tickers and "DPM" in tickers
    assert len(tickers) == len(set(tickers))


def test_load_vn100():
    """Smoke-load VN100 CSV — không chạy quarterly live."""
    path = Path("data/universe/vn100.csv")
    tickers = load_universe_tickers(path)
    assert len(tickers) == 100
    assert len(tickers) == len(set(tickers))
    # Có trong hose_liquid + ngân hàng (exclude_financials xử lý ở Tier1, vẫn nằm CSV)
    assert "FPT" in tickers and "VNM" in tickers and "VCB" in tickers
    # Không phải sample nhỏ
    assert "ACB" in tickers


def test_pipeline_config_fundamental_vs_smoke():
    """Config chọn VN100 Tier1; hose_liquid_35 vẫn là smoke_file."""
    with Path("pipeline/config.yaml").open(encoding="utf-8") as handle:
        cfg = yaml.safe_load(handle) or {}
    assert fundamental_universe_file(cfg) == "data/universe/vn100.csv"
    assert smoke_universe_file(cfg) == "data/universe/hose_liquid_35.csv"
    assert quant_from_watchlist(cfg) is True
    assert (cfg.get("fundamental_filter") or {}).get("exclude_financials") is True
    assert (cfg.get("backtest") or {}).get("walk_forward", {}).get("test_months") == 6
    # MC/BL vẫn off
    qe = cfg.get("quant_engine") or {}
    assert (qe.get("portfolio_black_litterman") or {}).get("enabled") is False
    assert (qe.get("probabilistic_monte_carlo") or {}).get("enabled") is False
    fund = load_fundamental_universe(cfg)
    assert len(fund) == 100
    smoke = load_universe_tickers(smoke_universe_file(cfg))
    assert 30 <= len(smoke) <= 40


def test_fundamental_universe_file_prefers_fundamental_key():
    cfg = {
        "universe": {
            "file": "data/universe/hose_liquid_35.csv",
            "fundamental_file": "data/universe/vn100.csv",
        }
    }
    assert fundamental_universe_file(cfg) == "data/universe/vn100.csv"
    assert fundamental_universe_file({"universe": {"file": "a.csv"}}) == "a.csv"
    assert fundamental_universe_file({}) is None


def test_quant_from_watchlist_default_true():
    assert quant_from_watchlist({}) is True
    assert quant_from_watchlist({"universe": {}}) is True
    assert quant_from_watchlist({"universe": {"quant_from_watchlist": False}}) is False


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
