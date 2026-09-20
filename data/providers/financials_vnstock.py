"""Vnstock live BCTC adapter — placeholder until field mapping is audited."""

from __future__ import annotations

from typing import Any


class VnstockFinancials:
    name = "vnstock"

    def get_annual(self, ticker: str, year: int) -> dict[str, Any] | None:
        raise NotImplementedError(
            "vnstock financial statements mapping not implemented — "
            "chain falls through to vnfinancialdata"
        )

    def get_latest(
        self, ticker: str, as_of_date: str | None = None
    ) -> dict[str, Any] | None:
        raise NotImplementedError(
            "vnstock live BCTC not implemented — chain falls through to vnfinancialdata"
        )
