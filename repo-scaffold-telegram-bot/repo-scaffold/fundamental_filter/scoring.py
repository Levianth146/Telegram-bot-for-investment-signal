"""Tổng hợp 4 module (Growth/Quality/Safety/Valuation) thành Fundamental View.

Tham chiếu: Mục 10 — phương pháp percentile/z-score theo ngành, PASS/WATCH/FAIL
theo percentile chứ không theo ngưỡng tuyệt đối.
"""

from __future__ import annotations


def zscore_by_sector(value: float, sector_median: float, sector_mad: float) -> float:
    """Bước 1 mục 10 — z = (x - median_nganh) / MAD_nganh."""
    raise NotImplementedError


def aggregate_fundamental_view(growth: dict, quality: dict, safety: dict, valuation: dict, config: dict) -> dict:
    """Bước 3-4 mục 10 — điểm module -> điểm tổng hợp -> PASS/WATCH/FAIL theo percentile
    (`config['scoring']['pass_percentile']`, `fail_percentile`).

    Trả về dict ghi vào bảng `fundamental_scores` / `watchlist` (store/schema.sql).
    """
    raise NotImplementedError
