"""DNSE price adapter — wraps transitional layer1 I/O until code moves here."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .base import ProviderError


class DnsePriceProvider:
    name = "dnse"

    def get_close(
        self, ticker: str, as_of_date: str | None = None
    ) -> dict[str, Any] | None:
        try:
            from fundamental_filter.layer1_engine.dnse_price import get_close_price
        except ImportError as exc:
            raise ProviderError(f"dnse adapter unavailable: {exc}") from exc
        try:
            return get_close_price(ticker, as_of_date, return_metadata=True)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc

    def get_ohlcv(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        # ponytail: DNSE OpenAPI path here is close-only today; chain falls through
        # to vnstock for multi-year OHLCV+volume (Tầng 2).
        raise NotImplementedError(
            "DNSE multi-year OHLCV+volume not wired — use vnstock in price chain"
        )
