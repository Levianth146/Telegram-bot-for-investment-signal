"""Industry lookup via vnstock KBS.

Network deps are lazy so importing this module does not require truststore.
"""

from __future__ import annotations

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


def get_industry(ticker):
    ticker = ticker.strip().upper()
    _ensure_ssl()
    from vnstock import Reference

    try:
        data = Reference().equity.list_by_industry(source="kbs")
    except Exception:
        return None

    if data is None or data.empty:
        return None

    rows = data[data["symbol"] == ticker]
    if rows.empty:
        return None

    row = rows.iloc[0]
    return {
        "ticker": ticker,
        "industry_code": int(row["industry_code"]),
        "industry_name": row["industry_name"],
        "source": "KBS via vnstock",
    }


if __name__ == "__main__":
    for ticker in ["VNM", "FPT", "HPG", "MWG"]:
        print(get_industry(ticker))
