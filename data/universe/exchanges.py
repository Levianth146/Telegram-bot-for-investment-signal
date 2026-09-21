"""Tra cứu sàn HOSE/HNX/UPCOM (live via vnstock Listing) — chỉ gọi từ pipeline I/O."""

from __future__ import annotations

from typing import Any

from data.universe import normalize_exchange

_CACHE: dict[str, str] | None = None


def load_symbol_exchange_map(*, force_refresh: bool = False) -> dict[str, str]:
    """Map ticker → HOSE|HNX|UPCOM từ vnstock Listing (một lần / process).

    ``symbols_by_exchange`` trả về bảng đủ sàn; cột ``exchange`` là nguồn chuẩn.
    """
    global _CACHE
    if _CACHE is not None and not force_refresh:
        return _CACHE

    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass

    from vnstock import Listing

    frame = Listing().symbols_by_exchange("HOSE")
    mapping: dict[str, str] = {}
    if frame is None or getattr(frame, "empty", True):
        _CACHE = mapping
        return mapping

    for _, row in frame.iterrows():
        symbol = str(row.get("symbol") or "").strip().upper()
        if not symbol:
            continue
        exch = normalize_exchange(row.get("exchange"))
        if exch:
            mapping[symbol] = exch
    _CACHE = mapping
    return mapping


def enrich_industry_info_with_exchange(
    ticker: str,
    info: dict[str, Any] | None,
    *,
    exchange_map: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Gắn ``exchange``/``market`` đã chuẩn hoá vào payload industry (nếu thiếu)."""
    if not info:
        return None
    out = dict(info)
    ticker_u = str(ticker).strip().upper()
    existing = normalize_exchange(out.get("market") or out.get("exchange"))
    if existing:
        out["market"] = existing
        out["exchange"] = existing
        return out
    lookup = exchange_map if exchange_map is not None else load_symbol_exchange_map()
    found = lookup.get(ticker_u)
    if found:
        out["market"] = found
        out["exchange"] = found
    return out
