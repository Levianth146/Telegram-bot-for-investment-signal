"""Point-in-time helpers for assumed BCTC publication dates."""

from __future__ import annotations

from datetime import date, timedelta


def assumed_filed_at(year: int, lag_days: int = 90) -> str:
    """Return ISO date = period-end (31 Dec ``year``) + ``lag_days``.

    Used when vendor has no real ``filed_at`` (see docs/DATA_AUDIT.md §4b).
    """
    if lag_days < 0:
        raise ValueError("lag_days must be non-negative")
    return (date(int(year), 12, 31) + timedelta(days=int(lag_days))).isoformat()
