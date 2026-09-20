"""Tổng hợp 4 module (Growth/Quality/Safety/Valuation) thành Fundamental View.

Tham chiếu: Mục 10 — phương pháp percentile/z-score theo ngành, PASS/WATCH/FAIL
theo percentile chứ không theo ngưỡng tuyệt đối.

Universe production path: ``score_current_universe`` + ``to_store_records``
(re-exported below). ``aggregate_fundamental_view`` is the single-ticker
absolute-fallback helper only.
"""

from __future__ import annotations

import pandas as pd

from .layer1_engine import (
    load_scoring_config,
    score_current_universe,
    to_store_records,
)
from .layer1_engine.fundamental_classification import classify_fundamental_universe

__all__ = [
    "zscore_by_sector",
    "aggregate_fundamental_view",
    "score_current_universe",
    "to_store_records",
    "load_scoring_config",
    "classify_fundamental_universe",
]


def zscore_by_sector(value: float, sector_median: float, sector_mad: float) -> float:
    """Bước 1 mục 10 — z = (x - median_nganh) / MAD_nganh."""
    if sector_mad is None or sector_mad == 0:
        raise ValueError("sector_mad must be non-zero")
    return float((value - sector_median) / sector_mad)


def _module_score(module: dict | float | None) -> float | None:
    if module is None:
        return None
    if isinstance(module, dict):
        score = module.get("score")
        return None if score is None else float(score)
    return float(module)


def aggregate_fundamental_view(
    growth: dict, quality: dict, safety: dict, valuation: dict, config: dict
) -> dict:
    """Bước 3-4 mục 10 — điểm module -> điểm tổng hợp -> PASS/WATCH/FAIL theo percentile
    (`config['scoring']['pass_percentile']`, `fail_percentile`).

    Trả về dict ghi vào bảng `fundamental_scores` / `watchlist` (store/schema.sql).

    For a full cross-sectional universe, prefer ``layer1_engine.score_current_universe``
    then ``to_store_records``. This helper classifies a single ticker (absolute
    fallback) when only four module dicts are available.
    """
    cfg = load_scoring_config()
    if config:
        scoring = config.get("scoring") or {}
        if "pass_percentile" in scoring:
            cfg["pass_percentile"] = float(scoring["pass_percentile"])
        if "fail_percentile" in scoring:
            cfg["watch_percentile"] = float(scoring["fail_percentile"])
        if "fundamental_filter" in config:
            cfg["fundamental_filter"] = config["fundamental_filter"]

    # Force absolute fallback for single-ticker aggregation
    cfg = {**cfg, "min_percentile_universe": 10**9}

    g = _module_score(growth)
    q = _module_score(quality)
    s = _module_score(safety)
    v = _module_score(valuation)
    available = [x for x in (g, q, s, v) if x is not None]
    fundamental_score = sum(available) / len(available) if len(available) == 4 else None

    universe = pd.DataFrame(
        [
            {
                "ticker": (config or {}).get("ticker", "UNKNOWN"),
                "year": (config or {}).get("year", 0),
                "growth_score": g,
                "quality_score": q,
                "safety_score": s,
                "valuation_score": v,
                "fundamental_score": fundamental_score,
                "safety_gate_status": (safety or {}).get("safety_gate_status", "OK")
                if isinstance(safety, dict)
                else "OK",
                "critical_data_quality_flag": len(available) < 4,
                "data_quality_flags": "" if len(available) == 4 else "MISSING_MODULES",
            }
        ]
    )
    classified = classify_fundamental_universe(universe, config=cfg)
    records = to_store_records(classified)
    score_row = records["fundamental_scores"][0] if records["fundamental_scores"] else {}
    return {
        **score_row,
        "classification": classified.iloc[0]["classification"],
        "classification_reason": classified.iloc[0]["classification_reason"],
        "watchlist_eligible": classified.iloc[0]["classification"] in {"PASS", "WATCH"},
        "growth": growth,
        "quality": quality,
        "safety": safety,
        "valuation": valuation,
    }
