"""Provider protocols — shared contracts for all vendor adapters."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import pandas as pd


class ProviderError(Exception):
    """Raised when a single vendor fails; chain may try the next source."""


@runtime_checkable
class PriceProvider(Protocol):
    """Giá/khối lượng — Tầng 2 (+ valuation close cho Tầng 1)."""

    name: str

    def get_close(
        self, ticker: str, as_of_date: str | None = None
    ) -> dict[str, Any] | None:
        """Close price (+ metadata). ``as_of_date=None`` → live/latest."""
        ...

    def get_ohlcv(
        self, ticker: str, start: str, end: str
    ) -> pd.DataFrame:
        """Daily OHLCV with columns including ``date``, ``close``, ``volume``.

        Required for Regime/Kalman/GARCH. May raise ``ProviderError`` /
        ``NotImplementedError`` until the vendor adapter supports history.
        """
        ...


@runtime_checkable
class FinancialStatementProvider(Protocol):
    """BCTC — Tầng 1. Prefer point-in-time ``filed_at`` when available."""

    name: str

    def get_annual(self, ticker: str, year: int) -> dict[str, Any] | None:
        """Annual statement fields used by Growth/Quality/Safety/Valuation."""
        ...

    def get_latest(
        self, ticker: str, as_of_date: str | None = None
    ) -> dict[str, Any] | None:
        """Latest published snapshot as of date (PIT). May be incomplete."""
        ...


@runtime_checkable
class SectorProvider(Protocol):
    """Phân ngành ICB — peer z-score + ``store.sector_mapping``."""

    name: str

    def get_industry(self, ticker: str) -> dict[str, Any] | None:
        ...
