"""Stub BCTC vendors from config chain (CafeF, Vietstock)."""

from __future__ import annotations

from typing import Any


class CafeFFinancials:
    name = "cafef"

    def get_annual(self, ticker: str, year: int) -> dict[str, Any] | None:
        raise NotImplementedError("CafeF BCTC scrape not implemented yet")

    def get_latest(
        self, ticker: str, as_of_date: str | None = None
    ) -> dict[str, Any] | None:
        raise NotImplementedError("CafeF BCTC scrape not implemented yet")


class VietstockFinancials:
    name = "vietstock"

    def get_annual(self, ticker: str, year: int) -> dict[str, Any] | None:
        raise NotImplementedError("Vietstock BCTC scrape not implemented yet")

    def get_latest(
        self, ticker: str, as_of_date: str | None = None
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Vietstock BCTC scrape not implemented yet")
