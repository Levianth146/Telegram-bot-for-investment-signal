"""Tests for sector_job dry-run."""

from __future__ import annotations

import sys

from pipeline import sector_job


def test_sector_job_dry_run(capsys):
    old = sys.argv
    try:
        sys.argv = ["sector_job", "--dry-run"]
        sector_job.main()
    finally:
        sys.argv = old
    assert "sector_job dry-run OK" in capsys.readouterr().out


def test_industry_to_mapping_row_normalizes_exchange():
    row = sector_job.industry_to_mapping_row(
        "fpt",
        {"industry_name": "Công nghệ", "exchange": "HSX"},
        updated_at="2024-07-01",
    )
    assert row is not None
    assert row["ticker"] == "FPT"
    assert row["market"] == "HOSE"

    vague = sector_job.industry_to_mapping_row(
        "ABC",
        {"industry_name": "X", "market": "VN"},
        updated_at="2024-07-01",
    )
    assert vague is not None
    assert vague["market"] is None
