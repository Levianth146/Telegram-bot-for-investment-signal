from datetime import date, datetime

from dnse_price import get_close_price, parse_as_of_date
from financial_data import get_latest_reported_financial_data
from shares_data import get_shares_outstanding


def calculate_market_cap(price, shares):
    if price is None or shares is None or shares <= 0:
        return None
    return price * shares


def calculate_pe(price, eps):
    if price is None or eps is None or eps <= 0:
        return None
    return price / eps


def calculate_book_value_per_share(equity, shares):
    if equity is None or shares is None or shares <= 0:
        return None
    return equity / shares


def calculate_pb(price, book_value_per_share, equity):
    if price is None or book_value_per_share is None or equity is None:
        return None
    if equity <= 0 or book_value_per_share == 0:
        return None
    return price / book_value_per_share


def calculate_total_debt(short_term_debt, long_term_debt):
    if short_term_debt is None or long_term_debt is None:
        return None
    return short_term_debt + long_term_debt


def calculate_enterprise_value(market_cap, total_debt, cash):
    if market_cap is None or total_debt is None or cash is None:
        return None
    return market_cap + total_debt - cash


def calculate_ev_to_ebitda(enterprise_value, ebitda):
    if enterprise_value is None or ebitda is None or ebitda <= 0:
        return None
    return enterprise_value / ebitda


def calculate_fcf(cfo, capex):
    if cfo is None or capex is None:
        return None
    return cfo - capex


def calculate_fcf_yield(fcf, market_cap):
    if fcf is None or market_cap is None or market_cap <= 0:
        return None
    return fcf / market_cap


def _to_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value).strip()).date()


def select_latest_published_financial(records, as_of_date):
    """Return the newest record that was public on the requested date."""
    cutoff = _to_date(as_of_date)
    eligible = []
    for record in records:
        publication_date = _to_date(record.get("publication_date"))
        period_end = _to_date(record.get("period_end"))
        if (
            publication_date is not None
            and period_end is not None
            and publication_date <= cutoff
            and period_end <= cutoff
        ):
            eligible.append((period_end, publication_date, record))
    if not eligible:
        return None
    return max(eligible, key=lambda item: (item[0], item[1]))[2]


def aggregate_ttm(quarterly_records, as_of_date):
    """Aggregate four consecutive, already-published quarters into TTM data."""
    cutoff = _to_date(as_of_date)
    published = {}
    for record in quarterly_records:
        publication_date = _to_date(record.get("publication_date"))
        period_end = _to_date(record.get("period_end"))
        if (
            publication_date is not None
            and period_end is not None
            and publication_date <= cutoff
            and period_end <= cutoff
        ):
            previous = published.get(period_end)
            if previous is None or publication_date > _to_date(
                previous.get("publication_date")
            ):
                published[period_end] = record

    latest_four = sorted(
        published.values(), key=lambda row: _to_date(row["period_end"])
    )[-4:]
    if len(latest_four) != 4:
        return None

    quarter_indexes = [
        _to_date(row["period_end"]).year * 4
        + ((_to_date(row["period_end"]).month - 1) // 3)
        for row in latest_four
    ]
    if any(
        right - left != 1
        for left, right in zip(quarter_indexes, quarter_indexes[1:])
    ):
        return None

    result = {}
    for field in ("eps", "ebitda", "cfo", "capex"):
        values = [row.get(field) for row in latest_four]
        result[field] = (
            None if any(value is None for value in values) else sum(values)
        )
    result["fcf"] = calculate_fcf(result["cfo"], result["capex"])

    latest = latest_four[-1]
    for field in ("equity", "short_term_debt", "long_term_debt", "cash"):
        result[field] = latest.get(field)

    result.update(
        {
            "financial_period": "TTM",
            "financial_period_end_date": str(_to_date(latest["period_end"])),
            "financial_publication_date": str(
                _to_date(latest["publication_date"])
            ),
            "earnings_basis": "TTM",
            "publication_date_missing": False,
            "point_in_time_safe": True,
        }
    )
    return result


def _warning_text(*sources):
    warnings = []
    for source in sources:
        warning = (source or {}).get("warning")
        if warning and warning not in warnings:
            warnings.append(warning)
    return " | ".join(warnings)


def get_valuation(ticker, as_of_date=None):
    """Build a live or historical valuation without mixing data vintages."""
    ticker = ticker.strip().upper()
    if isinstance(as_of_date, int):
        raise TypeError("as_of_date must be an ISO date, not a financial year")

    requested_date = (
        parse_as_of_date(as_of_date) if as_of_date is not None else None
    )
    price_data = get_close_price(
        ticker, requested_date, return_metadata=True
    )
    shares_data = get_shares_outstanding(ticker, requested_date)
    financial_result = get_latest_reported_financial_data(
        ticker, requested_date
    )
    financial_data = (financial_result or {}).get("data")

    price = (price_data or {}).get("price")
    shares = (shares_data or {}).get("shares_outstanding")
    market_cap = calculate_market_cap(price, shares)
    eps = (financial_data or {}).get("eps")
    equity = (financial_data or {}).get("equity")
    book_value_per_share = calculate_book_value_per_share(equity, shares)
    total_debt = calculate_total_debt(
        (financial_data or {}).get("short_term_debt"),
        (financial_data or {}).get("long_term_debt"),
    )
    enterprise_value = calculate_enterprise_value(
        market_cap, total_debt, (financial_data or {}).get("cash")
    )
    fcf = calculate_fcf(
        (financial_data or {}).get("cfo"),
        (financial_data or {}).get("capex"),
    )

    publication_missing = bool(
        (financial_result or {}).get("publication_date_missing", True)
    )
    components_safe = all(
        bool((source or {}).get("point_in_time_safe"))
        for source in (price_data, shares_data, financial_result)
    )
    point_in_time_safe = components_safe and not publication_missing

    return {
        "ticker": ticker,
        "valuation_mode": "HISTORICAL" if requested_date else "LIVE",
        "requested_as_of_date": str(requested_date) if requested_date else None,
        "as_of_date": (price_data or {}).get("price_date"),
        "price": price,
        "price_date": (price_data or {}).get("price_date"),
        "price_source": (price_data or {}).get("price_source"),
        "price_adjustment": (price_data or {}).get("price_adjustment"),
        "shares_outstanding": shares,
        "shares_date": (shares_data or {}).get("date"),
        "shares_source": (shares_data or {}).get("source"),
        "shares_fallback_used": bool(
            (shares_data or {}).get("historical_fallback_used", False)
        ),
        "financial_period": (financial_result or {}).get("financial_period"),
        "financial_period_end_date": (financial_result or {}).get(
            "period_end_date"
        ),
        "financial_publication_date": (financial_result or {}).get(
            "financial_publication_date"
        ),
        "earnings_basis": (financial_result or {}).get("earnings_basis"),
        "publication_date_missing": publication_missing,
        "point_in_time_safe": point_in_time_safe,
        "valuation_warnings": _warning_text(
            price_data, shares_data, financial_result
        ),
        "market_cap": market_cap,
        "pe": calculate_pe(price, eps),
        "book_value_per_share": book_value_per_share,
        "pb": calculate_pb(price, book_value_per_share, equity),
        "enterprise_value": enterprise_value,
        "ev_to_ebitda": calculate_ev_to_ebitda(
            enterprise_value, (financial_data or {}).get("ebitda")
        ),
        "fcf": fcf,
        "fcf_yield": calculate_fcf_yield(fcf, market_cap),
    }


if __name__ == "__main__":
    result = get_valuation("VNM")
    for name, value in result.items():
        print(f"{name}: {value}")
