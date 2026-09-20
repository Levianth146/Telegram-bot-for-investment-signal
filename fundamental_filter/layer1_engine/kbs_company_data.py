import truststore

truststore.inject_into_ssl()

import pandas as pd
from vnstock import Reference


_company_cache = {}
_request_counts = {}


def get_kbs_company_data(ticker):
    ticker = ticker.strip().upper()

    if ticker in _company_cache:
        return _company_cache[ticker]

    _request_counts[ticker] = _request_counts.get(ticker, 0) + 1

    try:
        data = Reference().company(symbol=ticker).info(source="kbs")
    except (Exception, SystemExit):
        _company_cache[ticker] = None
        return None

    if data is None or data.empty:
        _company_cache[ticker] = None
        return None

    row = data.iloc[0]
    exchange = row.get("exchange")
    shares = row.get("outstanding_shares")
    shares_date = row.get("as_of_date")

    result = {
        "ticker": ticker,
        "exchange": None if pd.isna(exchange) else str(exchange),
        "shares_outstanding": None if pd.isna(shares) else int(shares),
        "shares_date": None if pd.isna(shares_date) else str(shares_date).split("T")[0],
    }
    _company_cache[ticker] = result
    return result
