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


def _eligible_row(
    ticker: str,
    *,
    classification: str,
    reason: str,
    growth: float | None = 60.0,
    quality: float | None = 60.0,
    safety: float | None = 60.0,
    valuation: float | None = 60.0,
    fundamental_score: float | None = 60.0,
) -> dict:
    return {
        "ticker": ticker,
        "year": 2025,
        "growth_score": growth,
        "quality_score": quality,
        "safety_score": safety,
        "valuation_score": valuation,
        "fundamental_score": fundamental_score,
        "fundamental_percentile": 50.0,
        "safety_gate_status": "OK",
        "classification": classification,
        "classification_reason": reason,
        "classification_flags": "",
        "classification_as_of_date": "2025-12-31",
    }


def test_to_store_records_t1_pass_in_watchlist():
    """T1 — PASS đủ dữ liệu → watchlist."""
    records = to_store_records(
        pd.DataFrame(
            [_eligible_row("AAA", classification="PASS", reason="PASS_THRESHOLDS_MET")]
        ),
        as_of_date="2025-12-31",
    )
    assert [r["ticker"] for r in records["watchlist"]] == ["AAA"]


def test_to_store_records_t2_watch_eligible_in_watchlist():
    """T2 — WATCH đủ dữ liệu (MODULE_FLOOR) → watchlist."""
    records = to_store_records(
        pd.DataFrame(
            [
                _eligible_row(
                    "BBB", classification="WATCH", reason="MODULE_FLOOR_NOT_MET"
                )
            ]
        ),
        as_of_date="2025-12-31",
    )
    assert [r["ticker"] for r in records["watchlist"]] == ["BBB"]


def test_to_store_records_t3_insufficient_persists_score_not_watchlist():
    """T3 — WATCH + INSUFFICIENT_DATA → vẫn lưu score, không vào watchlist."""
    records = to_store_records(
        pd.DataFrame(
            [_eligible_row("CCC", classification="WATCH", reason="INSUFFICIENT_DATA")]
        ),
        as_of_date="2025-12-31",
    )
    assert len(records["fundamental_scores"]) == 1
    assert records["fundamental_scores"][0]["ticker"] == "CCC"
    assert records["watchlist"] == []
    import json

    payload = json.loads(records["fundamental_scores"][0]["headline_json"])
    assert payload.get("data_quality", {}).get("critical_data_quality_flag") is True


def test_to_store_records_t4_missing_module_not_watchlist():
    """T4 — thiếu một trụ → insufficient → không Quant-eligible."""
    records = to_store_records(
        pd.DataFrame(
            [
                _eligible_row(
                    "DDD",
                    classification="WATCH",
                    reason="MIDDLE_PERCENTILE",
                    growth=None,
                )
            ]
        ),
        as_of_date="2025-12-31",
    )
    assert len(records["fundamental_scores"]) == 1
    assert records["watchlist"] == []


def test_to_store_records_t5_fail_not_watchlist():
    """T5 — FAIL → không watchlist (regression)."""
    records = to_store_records(
        pd.DataFrame(
            [
                _eligible_row(
                    "EEE", classification="FAIL", reason="BELOW_WATCH_PERCENTILE"
                )
            ]
        ),
        as_of_date="2025-12-31",
    )
    assert len(records["fundamental_scores"]) == 1
    assert records["watchlist"] == []


def test_to_store_records_headline_values_from_scoring_frames():
    results = pd.DataFrame(
        [
            {
                "ticker": "VNM",
                "year": 2024,
                "growth_score": 60.0,
                "quality_score": 60.0,
                "safety_score": 60.0,
                "valuation_score": 60.0,
                "fundamental_score": 60.0,
                "fundamental_percentile": 70.0,
                "safety_gate_status": "OK",
                "classification": "PASS",
                "classification_reason": "PASS_THRESHOLDS_MET",
                "classification_flags": "",
                "classification_as_of_date": "2025-03-31",
            }
        ]
    )
    frames = {
        "VNM": pd.DataFrame(
            [
                {"ticker": "VNM", "year": 2024, "metric": "eps_cagr_3_year", "raw_value": 0.24},
                {"ticker": "VNM", "year": 2024, "metric": "roic", "raw_value": 0.15},
                {"ticker": "VNM", "year": 2024, "metric": "net_debt_to_ebitda", "raw_value": 0.8},
                {"ticker": "VNM", "year": 2024, "metric": "pe", "raw_value": 18.5},
            ]
        )
    }
    records = to_store_records(
        results, as_of_date="2025-03-31", period="2024", scoring_frames=frames
    )
    import json

    payload = json.loads(records["fundamental_scores"][0]["headline_json"])
    assert payload["headline"]["growth"]["value"] == 0.24
    assert payload["headline"]["quality"]["value"] == 0.15
    assert payload["headline"]["safety"]["value"] == 0.8
    assert payload["headline"]["valuation"]["value"] == 18.5


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
