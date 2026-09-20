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
