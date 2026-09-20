"""vnfinancialdata annual BCTC — wraps transitional layer1 financial_data."""

from __future__ import annotations

from typing import Any

from .base import ProviderError


class VnFinancialDataStatements:
    name = "vnfinancialdata"

    def get_annual(self, ticker: str, year: int) -> dict[str, Any] | None:
        try:
            from fundamental_filter.layer1_engine.financial_data import (
                get_financial_data,
            )
        except ImportError as exc:
            raise ProviderError(f"vnfinancialdata adapter unavailable: {exc}") from exc
        try:
            return get_financial_data(ticker, year)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc

    def get_latest(
        self, ticker: str, as_of_date: str | None = None
    ) -> dict[str, Any] | None:
        try:
            from fundamental_filter.layer1_engine.financial_data import (
                get_latest_reported_financial_data,
            )
        except ImportError as exc:
            raise ProviderError(f"vnfinancialdata adapter unavailable: {exc}") from exc
        try:
            return get_latest_reported_financial_data(ticker, as_of_date)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc
