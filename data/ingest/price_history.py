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
_DEFAULT_CACHE_DIR = "data/cache"


def _price_cfg(config: Mapping[str, Any] | None) -> dict[str, Any]:
    cfg = dict(config) if config is not None else load_pipeline_config()
    return dict((cfg.get("data_sources") or {}).get("price") or {})


def request_delay_seconds(config: Mapping[str, Any] | None = None) -> float:
    """Seconds to sleep between universe OHLCV fetches (0 disables)."""
    price = _price_cfg(config)
    raw = price.get("request_delay_ms", _DEFAULT_REQUEST_DELAY_MS)
    try:
        ms = int(raw)
    except (TypeError, ValueError):
        ms = _DEFAULT_REQUEST_DELAY_MS
    return max(ms, 0) / 1000.0


def cache_ohlcv_enabled(config: Mapping[str, Any] | None = None) -> bool:
    """Whether to read/write CSV OHLCV under ``cache_dir`` (default on)."""
    price = _price_cfg(config)
    return bool(price.get("cache_ohlcv", True))


def resolve_cache_dir(config: Mapping[str, Any] | None = None) -> Path:
    price = _price_cfg(config)
    return Path(str(price.get("cache_dir") or _DEFAULT_CACHE_DIR))


def cache_ohlcv_path(
    ticker: str,
    start: str,
    end: str,
    cache_dir: str | Path,
) -> Path:
    """Stable path keyed by ticker + window (TTL = reuse same start/end)."""
    safe_start = str(start).replace(":", "").replace("/", "-")
    safe_end = str(end).replace(":", "").replace("/", "-")
    return (
        Path(cache_dir)
        / f"ohlcv_{ticker.strip().upper()}_{safe_start}_{safe_end}.csv"
    )


def load_cached_ohlcv(
    ticker: str,
    start: str,
    end: str,
    cache_dir: str | Path,
) -> pd.DataFrame | None:
    """Load cached OHLCV if file exists and has date/close; else None."""
    path = cache_ohlcv_path(ticker, start, end, cache_dir)
    if not path.is_file():
        return None
    try:
        frame = pd.read_csv(path)
    except (OSError, ValueError, pd.errors.EmptyDataError):
        return None
    if frame is None or frame.empty:
        return None
    if "date" not in frame.columns or "close" not in frame.columns:
        return None
    return frame


def cache_ohlcv(
    frame: pd.DataFrame,
    ticker: str,
    cache_dir: str | Path,
    *,
    start: str | None = None,
    end: str | None = None,
) -> Path:
    """Write CSV under ``cache_dir`` for offline reuse.

    When ``start``/``end`` given, filename includes the window; otherwise
    legacy ``ohlcv_{TICKER}.csv``.
    """
    destination = Path(cache_dir)
    destination.mkdir(parents=True, exist_ok=True)
    if start is not None and end is not None:
        path = cache_ohlcv_path(ticker, start, end, destination)
    else:
        path = destination / f"ohlcv_{ticker.strip().upper()}.csv"
    frame.to_csv(path, index=False)
    return path


def fetch_ohlcv(
    ticker: str,
    start: str,
    end: str,
    config: Mapping[str, Any] | None = None,
) -> pd.DataFrame:
    """Return normalized OHLCV for one ticker via the configured price chain.

    Uses disk cache when ``data_sources.price.cache_ohlcv`` is true (default).
    """
    cfg = dict(config) if config is not None else load_pipeline_config()
    symbol = ticker.strip().upper()
    if cache_ohlcv_enabled(cfg):
        cached = load_cached_ohlcv(symbol, start, end, resolve_cache_dir(cfg))
        if cached is not None:
            logger.debug("OHLCV cache hit %s %s..%s", symbol, start, end)
            return cached

    provider = get_price_provider(cfg)
    frame = provider.get_ohlcv(symbol, start, end)
    if cache_ohlcv_enabled(cfg) and frame is not None and not frame.empty:
        cache_ohlcv(frame, symbol, resolve_cache_dir(cfg), start=start, end=end)
    return frame


def fetch_universe_ohlcv(
    tickers: list[str],
    start: str,
    end: str,
    config: Mapping[str, Any] | None = None,
) -> dict[str, pd.DataFrame]:
    """Fetch OHLCV for many tickers; skips failures (logs via ProviderError chain).

    Honours ``data_sources.price.request_delay_ms`` between **network** fetches
    (cache hits do not sleep). Default delay 250ms.
    """
    from data.providers.base import ProviderError

    cfg = dict(config) if config is not None else load_pipeline_config()
    delay = request_delay_seconds(cfg)
    use_cache = cache_ohlcv_enabled(cfg)
    cache_dir = resolve_cache_dir(cfg) if use_cache else None
    out: dict[str, pd.DataFrame] = {}
    wanted = [str(t).strip().upper() for t in tickers if str(t).strip()]
    network_calls = 0
    for ticker in wanted:
        if use_cache and cache_dir is not None:
            cached = load_cached_ohlcv(ticker, start, end, cache_dir)
            if cached is not None:
                out[ticker] = cached
                continue
        if network_calls > 0 and delay > 0:
            time.sleep(delay)
        try:
            # Bypass cache re-check inside fetch_ohlcv by calling provider path
            # after miss — fetch_ohlcv will write cache on success.
            out[ticker] = fetch_ohlcv(ticker, start, end, cfg)
            network_calls += 1
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
