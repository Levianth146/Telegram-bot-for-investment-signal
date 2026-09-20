"""Tests for scoring helpers + store adapter shape (framework mục 10 / schema)."""
import pandas as pd

from fundamental_filter import scoring
from fundamental_filter.layer1_engine import load_scoring_config, to_store_records


def test_zscore_by_sector():
    assert scoring.zscore_by_sector(12.0, 10.0, 2.0) == 1.0


def test_load_scoring_config_reads_pipeline_yaml():
    cfg = load_scoring_config()
    assert cfg["pass_percentile"] == 0.60
    assert cfg["watch_percentile"] == 0.30  # mapped from fail_percentile
    assert cfg["config_loaded"] is True


def test_to_store_records_watchlist_excludes_fail():
    results = pd.DataFrame(
        [
            {
                "ticker": "AAA",
                "year": 2025,
                "growth_score": 70.0,
                "quality_score": 70.0,
                "safety_score": 70.0,
                "valuation_score": 70.0,
                "fundamental_score": 70.0,
                "fundamental_percentile": 80.0,
                "safety_gate_status": "OK",
                "classification": "PASS",
                "classification_reason": "PASS_THRESHOLDS_MET",
                "classification_flags": "",
                "classification_as_of_date": "2025-12-31",
            },
            {
                "ticker": "BBB",
                "year": 2025,
                "growth_score": 20.0,
                "quality_score": 20.0,
                "safety_score": 20.0,
                "valuation_score": 20.0,
                "fundamental_score": 20.0,
                "fundamental_percentile": 10.0,
                "safety_gate_status": "OK",
                "classification": "FAIL",
                "classification_reason": "BELOW_WATCH_PERCENTILE",
                "classification_flags": "",
                "classification_as_of_date": "2025-12-31",
            },
        ]
    )
    records = to_store_records(results, as_of_date="2025-12-31", period="2025Q4")
    assert len(records["fundamental_scores"]) == 2
    assert {r["fundamental_view"] for r in records["fundamental_scores"]} == {
        "PASS",
        "FAIL",
    }
    assert len(records["watchlist"]) == 1
    assert records["watchlist"][0]["ticker"] == "AAA"
    assert records["fundamental_scores"][0]["period"] == "2025Q4"
    assert "headline_json" in records["fundamental_scores"][0]


def test_aggregate_fundamental_view_single_ticker():
    view = scoring.aggregate_fundamental_view(
        {"score": 70.0},
        {"score": 70.0},
        {"score": 70.0},
        {"score": 70.0},
        {"ticker": "VNM", "year": 2025, "scoring": {"pass_percentile": 0.6, "fail_percentile": 0.3}},
    )
    assert view["fundamental_view"] in {"PASS", "WATCH", "FAIL"}
    assert view["ticker"] == "VNM"
    assert "growth_score" in view
