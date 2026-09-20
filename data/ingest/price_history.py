"""OHLCV history helper for Tầng 2 — uses ``data.providers`` price chain."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from data.providers import get_price_provider, load_pipeline_config


def fetch_ohlcv(
    ticker: str,
    start: str,
    end: str,
    config: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Return normalized OHLCV for one ticker via the configured price chain."""
    cfg = dict(config) if config is not None else load_pipeline_config()
    provider = get_price_provider(cfg)
    return provider.get_ohlcv(ticker.strip().upper(), start, end)


def fetch_universe_ohlcv(
    tickers: list[str],
    start: str,
    end: str,
    config: Mapping[str, Any] | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for many tickers; skips failures (logs via ProviderError chain)."""
    from data.providers.base import ProviderError

    out: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            out[ticker.strip().upper()] = fetch_ohlcv(ticker, start, end, config)
        except (ProviderError, NotImplementedError, ValueError):
            continue
    return out


def to_close_series(ohlcv: pd.DataFrame) -> pd.Series:
    """Close prices indexed by date string — input for Kalman/GARCH stubs later."""
    frame = ohlcv.copy()
    if "date" not in frame.columns or "close" not in frame.columns:
        raise ValueError("ohlcv must include date and close columns")
    series = pd.to_numeric(frame["close"], errors="coerce")
    series.index = frame["date"].astype(str)
    series.name = "close"
    return series.dropna()


def cache_ohlcv(frame: pd.DataFrame, ticker: str, cache_dir: str | Path) -> Path:
    """Write parquet/csv under ``data/cache`` for offline reuse."""
    destination = Path(cache_dir)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / f"ohlcv_{ticker.strip().upper()}.csv"
    frame.to_csv(path, index=False)
    return path
