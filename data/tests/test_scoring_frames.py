"""Tests for scoring_frames builder (no network)."""

from __future__ import annotations

import pandas as pd

from data.ingest.fundamental_metrics import compute_year_metrics
from data.ingest.pit import assumed_filed_at
from data.ingest.scoring_frames import (
    build_scoring_frames,
    is_financial_industry,
)
from fundamental_filter import score_current_universe, to_store_records
from fundamental_filter.layer1_engine.ratios_safety import (
    cfo_to_debt,
    interest_coverage,
    net_debt_to_ebitda,
)


def _annual(revenue, eps, equity, ebit=None, ebitda=None, cfo=100, debt=50, cash=20):
    ebit = revenue * 0.2 if ebit is None else ebit
    ebitda = ebit * 1.2 if ebitda is None else ebitda
    return {
        "revenue": revenue,
        "gross_profit": revenue * 0.4,
        "ebit": ebit,
        "ebitda": ebitda,
        "npat_parent": eps * 10,
        "eps": eps,
        "pretax_profit": ebit,
        "tax_expense": ebit * 0.2,
        "interest_expense": 5,
        "cash": cash,
        "receivables": 10,
        "inventory": 10,
        "current_assets": 80,
        "current_liabilities": 40,
        "short_term_debt": debt / 2,
        "long_term_debt": debt / 2,
        "total_assets": 200,
        "equity": equity,
        "cfo": cfo,
        "capex": 20,
    }


def test_compute_year_metrics_revenue_growth():
    current = _annual(120, 2.0, 100)
    previous = _annual(100, 1.5, 90)
    row = compute_year_metrics("VNM", 2024, current, previous, None)
    assert abs(row["revenue_growth_yoy"] - 0.2) < 1e-12
    assert abs(row["npat_growth_yoy"] - (20 / 15 - 1)) < 1e-12
    assert abs(row["eps_growth_yoy"] - (2.0 / 1.5 - 1)) < 1e-12
    assert abs(row["cfo_to_npat"] - (100 / 20)) < 1e-12


def test_safety_edge_cases():
    assert net_debt_to_ebitda(-10, -1) == 0.0
    assert net_debt_to_ebitda(50, -1) == 99.0
    assert interest_coverage(100, 0) == 999.0
    assert interest_coverage(-10, 0) == 0.0
    assert cfo_to_debt(80, 0) == 1.0


def test_assumed_filed_at():
    assert assumed_filed_at(2024, 90) == "2025-03-31"


def test_exclude_financials_and_industry_peers():
    books = {}
    for ticker, base in [("AAA", 100), ("BBB", 80), ("CCC", 60), ("VCB", 200)]:
        for year, mult in [(2021, 0.8), (2022, 0.9), (2023, 1.0), (2024, 1.2)]:
            books[(ticker, year)] = _annual(base * mult, mult, base)

    def fetch_annual(ticker, year):
        return books.get((ticker, year))

    industries = {
        "AAA": "Thực phẩm",
        "BBB": "Thực phẩm",
        "CCC": "Thực phẩm",
        "VCB": "Ngân hàng",
    }
    assert is_financial_industry(industries["VCB"])

    frames = build_scoring_frames(
        ["AAA", "BBB", "CCC", "VCB"],
        2022,
        2024,
        fetch_annual,
        fetch_price=lambda t: 50.0,
        fetch_shares=lambda t: 10.0,
        industry_by_ticker=industries,
        exclude_financials=True,
        min_industry_peers=3,
    )
    assert set(frames) == {"AAA", "BBB", "CCC"}
    assert frames["AAA"]["peer_method"].iloc[0] == "INDUSTRY"
    assert frames["AAA"]["peer_count"].iloc[0] == 3
    assert not pd.isna(frames["AAA"]["fundamental_context_score"].iloc[0])


def test_historical_valuation_with_year_end_prices():
    """≥4 prior year-end closes + assumed lag → hist valuation available."""
    books = {}
    for year in range(2019, 2025):
        mult = 1.0 + (year - 2019) * 0.1
        books[("AAA", year)] = _annual(100 * mult, 1.0 * mult, 80 * mult)
        books[("BBB", year)] = _annual(50 * mult, 0.5 * mult, 40 * mult)

    def fetch_annual(ticker, year):
        return books.get((ticker, year))

    def fetch_year_price(ticker, year):
        # Rising prices → richer valuation history for percentile
        base = 40.0 if ticker == "AAA" else 15.0
        return base * (1.0 + (year - 2019) * 0.08)

    frames = build_scoring_frames(
        ["AAA", "BBB"],
        2022,
        2024,
        fetch_annual,
        fetch_year_price=fetch_year_price,
        fetch_shares=lambda t: 10.0,
        publication_lag_days=90,
    )
    assert bool(frames["AAA"]["historical_valuation_available"].iloc[0]) is True
    assert not pd.isna(frames["AAA"]["historical_valuation_score"].iloc[0])

    results, _, _ = score_current_universe(frames, 2022, 2024)
    assert "HISTORICAL_VALUATION_UNAVAILABLE" not in set(
        results["classification_reason"].astype(str)
    )


def test_industries_from_sector_mapping(tmp_path):
    from data.ingest.scoring_frames import industries_from_sector_mapping
    from store import repository

    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.upsert_sector_mapping(
        conn,
        [
            {
                "ticker": "AAA",
                "market": "VN",
                "sector": "Consumer",
                "industry": "Thực phẩm",
                "subindustry": None,
                "updated_at": "2024-01-01",
            }
        ],
    )
    conn.close()
    industries = industries_from_sector_mapping(["AAA", "BBB"], db_path=str(db))
    assert industries == {"AAA": "Thực phẩm"}


def test_build_scoring_frames_and_score(tmp_path):
    books = {
        ("AAA", 2021): _annual(80, 1.0, 70),
        ("AAA", 2022): _annual(90, 1.1, 75),
        ("AAA", 2023): _annual(100, 1.2, 80),
        ("AAA", 2024): _annual(120, 1.5, 90),
        ("BBB", 2021): _annual(50, 0.5, 40),
        ("BBB", 2022): _annual(55, 0.55, 42),
        ("BBB", 2023): _annual(60, 0.6, 45),
        ("BBB", 2024): _annual(65, 0.65, 48),
    }

    def fetch_annual(ticker, year):
        return books.get((ticker, year))

    frames = build_scoring_frames(
        ["AAA", "BBB"],
        2022,
        2024,
        fetch_annual,
        fetch_price=lambda t: 50.0 if t == "AAA" else 20.0,
        fetch_shares=lambda t: 10.0,
    )
    assert set(frames) == {"AAA", "BBB"}
    assert "peer_percentile" in frames["AAA"].columns
    assert frames["AAA"]["peer_method"].iloc[0] == "UNIVERSE_CROSS_SECTION"
    # Without fetch_year_price, prior-year valuation metrics stay empty → no hist gate
    assert bool(frames["AAA"]["historical_valuation_available"].iloc[0]) is False

    results, metrics, _ = score_current_universe(frames, 2022, 2024)
    assert len(results) == 2
    assert set(results["classification"]) <= {"WATCH", "FAIL"}
    records = to_store_records(results, filed_at="2025-03-31")
    assert len(records["fundamental_scores"]) == 2
    assert all(r["filed_at"] == "2025-03-31" for r in records["fundamental_scores"])
    assert all(r["fundamental_view"] in {"PASS", "WATCH"} for r in records["watchlist"])
