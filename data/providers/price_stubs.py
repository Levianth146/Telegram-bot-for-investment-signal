"""Stub price vendors listed in config but not implemented yet."""

from __future__ import annotations

from typing import Any

import pandas as pd


class CafeFPriceProvider:
    name = "cafef"

    def get_close(
        self, ticker: str, as_of_date: str | None = None
    ) -> dict[str, Any] | None:
        raise NotImplementedError("CafeF price scrape not implemented yet")

    def get_ohlcv(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        raise NotImplementedError("CafeF OHLCV scrape not implemented yet")
