"""OHLCV history helper for Tầng 2 — uses ``data.providers`` price chain."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from data.providers import get_price_provider, load_pipeline_config

logger = logging.getLogger(__name__)

# Default live delay between per-ticker OHLCV calls (vendor rate-limit cushion).
_DEFAULT_REQUEST_DELAY_MS = 250


def request_delay_seconds(config: Mapping[str, Any] | None = None) -> float:
    """Seconds to sleep between universe OHLCV fetches (0 disables)."""
    cfg = dict(config) if config is not None else load_pipeline_config()
    price = dict((cfg.get("data_sources") or {}).get("price") or {})
    raw = price.get("request_delay_ms", _DEFAULT_REQUEST_DELAY_MS)
    try:
        ms = int(raw)
    except (TypeError, ValueError):
        ms = _DEFAULT_REQUEST_DELAY_MS
    return max(ms, 0) / 1000.0


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
    """Fetch OHLCV for many tickers; skips failures (logs via ProviderError chain).

    Honours ``data_sources.price.request_delay_ms`` between tickers (default 250).
    """
    from data.providers.base import ProviderError

    cfg = dict(config) if config is not None else load_pipeline_config()
    delay = request_delay_seconds(cfg)
    out: dict[str, pd.DataFrame] = {}
    wanted = [str(t).strip().upper() for t in tickers if str(t).strip()]
    for index, ticker in enumerate(wanted):
        if index > 0 and delay > 0:
            time.sleep(delay)
        try:
            out[ticker] = fetch_ohlcv(ticker, start, end, cfg)
        except (ProviderError, NotImplementedError, ValueError) as exc:
            logger.warning("OHLCV skip %s: %s", ticker, exc)
            continue
    missing = sorted(set(wanted) - set(out))
    if missing:
        logger.warning(
            "OHLCV missing %s/%s tickers: %s",
            len(missing),
            len(wanted),
            ",".join(missing[:20]) + ("..." if len(missing) > 20 else ""),
        )
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
