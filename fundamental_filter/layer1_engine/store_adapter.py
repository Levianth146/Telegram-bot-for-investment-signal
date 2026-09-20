"""Map layer1 classification results to store/schema.sql record shapes.

Does not write SQLite — returns dicts for pipeline/quarterly_job + repository
upserts (store layer owns persistence).
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd


_SCORE_COLUMNS = (
    "growth_score",
    "quality_score",
    "safety_score",
    "valuation_score",
)


def _headline_json(row: pd.Series) -> str:
    """Build headline_json per framework mục 6.1 (headline + supporting flags)."""
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
        "headline": {
            "growth": "eps_cagr_3y",
            "quality": "roic",
            "safety": "net_debt_to_ebitda",
            "valuation": "pe_vs_history_and_peer",
        },
    }
    if "classification_flags" in row.index and pd.notna(row.get("classification_flags")):
        payload["flags"] = str(row["classification_flags"])
    return json.dumps(payload, ensure_ascii=False)


def to_store_records(
    results_df: pd.DataFrame,
    *,
    as_of_date: str | None = None,
    filed_at: str | None = None,
    period: str | None = None,
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
    """
    if results_df is None or results_df.empty:
        return {"fundamental_scores": [], "watchlist": []}

    data = results_df.copy()
    if "classification" not in data.columns:
        raise ValueError("results_df must include classification column")

    view_col = "classification"
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

        score_row: dict[str, Any] = {
            "ticker": ticker,
            "filed_at": row_filed,
            "period": row_period,
            "fundamental_view": view,
            "headline_json": _headline_json(row),
        }
        for col in _SCORE_COLUMNS:
            value = row.get(col)
            score_row[col] = None if pd.isna(value) else float(value)
        scores.append(score_row)

        if view in {"PASS", "WATCH"}:
            watchlist.append(
                {
                    "as_of_date": row_as_of,
                    "ticker": ticker,
                    "fundamental_view": view,
                }
            )

    return {"fundamental_scores": scores, "watchlist": watchlist}
