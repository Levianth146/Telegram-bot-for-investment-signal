"""Peer group via vnstock KBS + curated overrides.

Network deps are lazy so importing this module does not require truststore.
"""

from __future__ import annotations

from .fundamental_config import CURATED_PEERS
from .industry_data import get_industry

_ssl_ready = False


def _ensure_ssl() -> None:
    global _ssl_ready
    if _ssl_ready:
        return
    try:
        import truststore

        truststore.inject_into_ssl()
    except ImportError:
        pass
    _ssl_ready = True


def get_peer_group(ticker):
    ticker = ticker.strip().upper()
    industry = get_industry(ticker)

    if industry is None:
        return None

    _ensure_ssl()
    from vnstock import Reference

    try:
        data = Reference().equity.list_by_industry(source="kbs")
    except Exception:
        return None

    if data is None or data.empty:
        return None

    rows = data[data["industry_code"] == industry["industry_code"]]
    peer_symbols = []

    candidate_symbols = rows["symbol"].tolist() + CURATED_PEERS.get(ticker, [])
    for symbol in candidate_symbols:
        if not isinstance(symbol, str):
            continue

        symbol = symbol.strip().upper()
        if symbol and symbol != ticker and symbol not in peer_symbols:
            peer_symbols.append(symbol)

    return {
        "ticker": ticker,
        "industry_code": industry["industry_code"],
        "industry_name": industry["industry_name"],
        "peer_count": len(peer_symbols),
        "peer_symbols": peer_symbols,
        "source": "KBS via vnstock",
    }


if __name__ == "__main__":
    result = get_peer_group("VNM")

    if result is not None:
        print("ticker:", result["ticker"])
        print("industry_code:", result["industry_code"])
        print("industry_name:", result["industry_name"])
        print("peer_count:", result["peer_count"])
        print("peer_symbols:", result["peer_symbols"][:20])
