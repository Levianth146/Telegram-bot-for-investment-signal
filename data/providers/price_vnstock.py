"""Vnstock price adapter — OHLCV history for Tầng 2 (when deps installed)."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .base import ProviderError


class VnstockPriceProvider:
    name = "vnstock"

    def get_close(
        self, ticker: str, as_of_date: str | None = None
    ) -> dict[str, Any] | None:
        if as_of_date:
            start, end = as_of_date, as_of_date
        else:
            # Live: pull a short recent window instead of a century of history
            end = pd.Timestamp.today().strftime("%Y-%m-%d")
            start = (pd.Timestamp.today() - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
        frame = self.get_ohlcv(ticker, start=start, end=end)
        if frame is None or frame.empty:
            return None
        row = frame.iloc[-1]
        return {
            "price": float(row["close"]),
            "price_date": str(row["date"]),
            "price_source": "vnstock",
            "volume": (
                float(row["volume"])
                if "volume" in row.index and pd.notna(row["volume"])
                else None
            ),
            "point_in_time_safe": as_of_date is not None,
        }

    def get_ohlcv(self, ticker: str, start: str, end: str) -> pd.DataFrame:
        try:
            from vnstock import Quote
        except ImportError as exc:
            raise ProviderError(f"vnstock not installed: {exc}") from exc
        try:
            quote = Quote(symbol=ticker.strip().upper(), source="VCI")
            raw = quote.history(start=start, end=end)
        except Exception as exc:  # noqa: BLE001
            raise ProviderError(str(exc)) from exc
        if raw is None or getattr(raw, "empty", True):
            raise ProviderError(f"vnstock returned empty history for {ticker}")
        frame = raw.copy()
        # Normalize common vnstock column names
        rename = {}
        for col in frame.columns:
            lower = str(col).lower()
            if lower in {"time", "tradingdate", "ngay"}:
                rename[col] = "date"
            elif lower == "close":
                rename[col] = "close"
            elif lower == "volume":
                rename[col] = "volume"
            elif lower == "open":
                rename[col] = "open"
            elif lower == "high":
                rename[col] = "high"
            elif lower == "low":
                rename[col] = "low"
        frame = frame.rename(columns=rename)
        if "date" not in frame.columns or "close" not in frame.columns:
            raise ProviderError(
                f"vnstock history missing date/close columns: {list(frame.columns)}"
            )
        if "volume" not in frame.columns:
            frame["volume"] = pd.NA
        frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
        return frame[["date", "open", "high", "low", "close", "volume"]].reset_index(
            drop=True
        ) if set(["open", "high", "low"]).issubset(frame.columns) else frame[
            ["date", "close", "volume"]
        ].reset_index(drop=True)
