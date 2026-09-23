"""Map layer1 classification results to store/schema.sql record shapes.

Does not write SQLite — returns dicts for pipeline/quarterly_job + repository
upserts (store layer owns persistence).
"""

from __future__ import annotations

import json
from typing import Any, Mapping

import pandas as pd

from fundamental_filter.layer1_engine.eligibility import (
    build_data_quality_payload,
    is_quant_eligible_fundamental,
)


_SCORE_COLUMNS = (
    "growth_score",
    "quality_score",
    "safety_score",
    "valuation_score",
)

# metric key trong scoring_frames (raw) → id khung 6.1
_HEADLINE_SPECS = (
    ("growth", "eps_cagr_3_year", "eps_cagr_3y"),
    ("quality", "roic", "roic"),
    ("safety", "net_debt_to_ebitda", "net_debt_to_ebitda"),
    ("valuation", "pe", "pe_vs_history_and_peer"),
)

# supporting: chỉ gắn khi bất thường (ngưỡng đơn giản, mục 6.1)
_SUPPORTING_SPECS = (
    ("growth", "revenue_cagr_3_year", "revenue_cagr_3y"),
    ("quality", "roe", "roe"),
    ("safety", "interest_coverage", "interest_coverage"),
    ("valuation", "pb", "pb"),
)


def _finite(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        num = float(value)
    except (TypeError, ValueError):
        return None
    if num != num or num in (float("inf"), float("-inf")):
        return None
    return num


def latest_raw_metrics(scoring_df: pd.DataFrame | None) -> dict[str, float]:
    """Lấy ``raw_value`` năm mới nhất từ scoring frame (long: metric/year/raw_value)."""
    if scoring_df is None or getattr(scoring_df, "empty", True):
        return {}
    if "metric" not in scoring_df.columns or "raw_value" not in scoring_df.columns:
        return {}
    df = scoring_df
    if "year" in df.columns and df["year"].notna().any():
        max_year = df["year"].max()
        df = df.loc[df["year"] == max_year]
    out: dict[str, float] = {}
    for _, row in df.iterrows():
        key = str(row.get("metric") or "").strip()
        val = _finite(row.get("raw_value"))
        if key and val is not None:
            out[key] = val
    return out


def _is_abnormal(pillar: str, metric_key: str, value: float, headline_vals: Mapping[str, float | None]) -> bool:
    """Heuristic supporting — im lặng trừ khi cần giải thích (mục 6.1)."""
    if pillar == "safety" and metric_key == "interest_coverage":
        return value < 2.0
    if pillar == "safety":
        nd = headline_vals.get("net_debt_to_ebitda")
        return nd is not None and nd > 4.0
    if pillar == "quality" and metric_key == "roe":
        roic = headline_vals.get("roic")
        if roic is None:
            return False
        # ROE cao bất thường so với ROIC → nghi đòn bẩy
        return value > 0.25 and (value - roic) > 0.10
    if pillar == "growth" and metric_key == "revenue_cagr_3_year":
        eps = headline_vals.get("eps_cagr_3_year")
        if eps is None:
            return False
        # tăng trưởng doanh thu và EPS lệch mạnh
        return abs(value - eps) > 0.15
    if pillar == "valuation" and metric_key == "pb":
        pe = headline_vals.get("pe")
        return pe is not None and (pe > 40 or pe < 0)
    return False


def _headline_json(
    row: pd.Series,
    *,
    raw_metrics: Mapping[str, float] | None = None,
) -> str:
    """Build headline_json per framework mục 6.1 (headline values + supporting flags)."""
    metrics = dict(raw_metrics or {})
    for key in (
        "eps_cagr_3_year",
        "roic",
        "net_debt_to_ebitda",
        "pe",
        "pb",
        "roe",
        "revenue_cagr_3_year",
        "interest_coverage",
    ):
        if key not in metrics:
            got = _finite(row.get(key))
            if got is not None:
                metrics[key] = got

    headline: dict[str, Any] = {}
    headline_vals: dict[str, float | None] = {}
    for pillar, raw_key, frame_id in _HEADLINE_SPECS:
        val = metrics.get(raw_key)
        headline_vals[raw_key] = val
        headline[pillar] = {
            "metric": frame_id,
            "raw_metric": raw_key,
            "value": val,
        }

    supporting: dict[str, Any] = {}
    for pillar, raw_key, frame_id in _SUPPORTING_SPECS:
        val = metrics.get(raw_key)
        if val is None:
            continue
        if _is_abnormal(pillar, raw_key, val, headline_vals):
            supporting[pillar] = {
                "metric": frame_id,
                "raw_metric": raw_key,
                "value": val,
            }

    payload: dict[str, Any] = {
        "fundamental_score": (
            None if pd.isna(row.get("fundamental_score")) else float(row["fundamental_score"])
        ),
        "fundamental_percentile": (
            None
            if pd.isna(row.get("fundamental_percentile"))
            else float(row["fundamental_percentile"])
        ),
        "safety_gate_status": row.get("safety_gate_status"),
        "classification_reason": row.get("classification_reason")
        or row.get("classification_flags"),
        "headline": headline,
        "supporting": supporting,
    }
    if "classification_flags" in row.index and pd.notna(row.get("classification_flags")):
        payload["flags"] = str(row["classification_flags"])
    # Diagnostic thiếu dữ liệu — chỉ khi pipeline biết chắc (không bịa metric list).
    dq = build_data_quality_payload(row)
    if dq:
        payload["data_quality"] = dq
    return json.dumps(payload, ensure_ascii=False)


def to_store_records(
    results_df: pd.DataFrame,
    *,
    as_of_date: str | None = None,
    filed_at: str | None = None,
    period: str | None = None,
    scoring_frames: Mapping[str, pd.DataFrame] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Convert scored+classified universe to fundamental_scores + watchlist rows.

    Parameters
    ----------
    results_df:
        Output of ``score_current_universe`` / classify merge — must include
        ticker, module scores, ``classification`` (PASS/WATCH/FAIL).
    as_of_date:
        Watchlist date; defaults to ``classification_as_of_date`` or today.
    filed_at:
        Point-in-time filing date for fundamental_scores; defaults to as_of_date.
    period:
        Reporting period label (e.g. ``2025Q4``); defaults to ``{year}`` if present.
    scoring_frames:
        Optional map ticker → scoring input (long). Dùng để ghi giá trị headline 6.1.
    """
    if results_df is None or results_df.empty:
        return {"fundamental_scores": [], "watchlist": []}

    data = results_df.copy()
    if "classification" not in data.columns:
        raise ValueError("results_df must include classification column")

    view_col = "classification"
    frames = scoring_frames or {}
    scores: list[dict[str, Any]] = []
    watchlist: list[dict[str, Any]] = []

    for _, row in data.iterrows():
        ticker = str(row["ticker"]).strip().upper()
        view = str(row[view_col]).strip().upper()
        row_as_of = (
            as_of_date
            or (
                str(row["classification_as_of_date"])
                if "classification_as_of_date" in row.index
                and pd.notna(row.get("classification_as_of_date"))
                else None
            )
        )
        if not row_as_of:
            row_as_of = pd.Timestamp.today().strftime("%Y-%m-%d")

        row_filed = filed_at or row_as_of
        if period is not None:
            row_period = period
        elif "year" in row.index and pd.notna(row.get("year")):
            row_period = str(int(row["year"]))
        else:
            row_period = row_as_of[:4]

        raw = latest_raw_metrics(frames.get(ticker))
        score_row: dict[str, Any] = {
            "ticker": ticker,
            "filed_at": row_filed,
            "period": row_period,
            "fundamental_view": view,
            "headline_json": _headline_json(row, raw_metrics=raw),
        }
        for col in _SCORE_COLUMNS:
            value = row.get(col)
            score_row[col] = None if pd.isna(value) else float(value)
        scores.append(score_row)

        # Vẫn persist mọi score (kể cả INSUFFICIENT/FAIL); watchlist chỉ Quant-eligible.
        if is_quant_eligible_fundamental(score_row):
            watchlist.append(
                {
                    "as_of_date": row_as_of,
                    "ticker": ticker,
                    "fundamental_view": view,
                }
            )

    return {"fundamental_scores": scores, "watchlist": watchlist}
