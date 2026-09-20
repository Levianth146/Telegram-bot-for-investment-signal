"""Sector / industry via vnstock KBS — wraps transitional layer1 industry_data."""

from __future__ import annotations

from typing import Any

from .base import ProviderError


class VnstockSectorProvider:
    name = "vnstock"

    def get_industry(self, ticker: str) -> dict[str, Any] | None:
        try:
            from fundamental_filter.layer1_engine.industry_data import get_industry
        except ImportError as exc:
            raise ProviderError(f"sector adapter unavailable: {exc}") from exc
        try:
            return get_industry(ticker)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc
