from .financial_data import get_financial_data
from . import ratios_growth as growth
from . import ratios_quality as quality
from . import ratios_safety as safety
from .ratios_valuation import get_valuation


def get_data(ticker, year):
    try:
        return get_financial_data(ticker, year)
    except Exception:
        return None


def get_value(data, name):
    if data is None:
        return None
    return data.get(name)


def get_fundamental_snapshot(ticker, year):
    ticker = ticker.strip().upper()
    current = get_data(ticker, year)
    previous = get_data(ticker, year - 1)
    three_years_ago = get_data(ticker, year - 3)

    growth_result = {
        "revenue_growth_yoy": growth.revenue_growth_yoy(
            get_value(current, "revenue"), get_value(previous, "revenue")
        ),
        "npat_growth_yoy": growth.npat_growth_yoy(
            get_value(current, "npat_parent"), get_value(previous, "npat_parent")
        ),
        "revenue_cagr_3_year": growth.revenue_cagr_3_year(
            get_value(current, "revenue"),
            get_value(three_years_ago, "revenue"),
        ),
        "eps_growth_yoy": growth.eps_growth_yoy(
            get_value(current, "eps"), get_value(previous, "eps")
        ),
        "eps_cagr_3_year": growth.eps_cagr_3_year(
            get_value(current, "eps"), get_value(three_years_ago, "eps")
        ),
        "cfo_growth_yoy": growth.cfo_growth_yoy(
            get_value(current, "cfo"), get_value(previous, "cfo")
        ),
        "fcf": growth.free_cash_flow(
            get_value(current, "cfo"), get_value(current, "capex")
        ),
    }

    current_tax_rate = quality.tax_rate(
        get_value(current, "tax_expense"),
        get_value(current, "pretax_profit"),
    )
    current_nopat = quality.nopat(
        get_value(current, "ebit"), current_tax_rate
    )
    current_debt = quality.total_debt(
        get_value(current, "short_term_debt"),
        get_value(current, "long_term_debt"),
    )
    previous_debt = quality.total_debt(
        get_value(previous, "short_term_debt"),
        get_value(previous, "long_term_debt"),
    )
    current_capital = quality.invested_capital(
        get_value(current, "equity"), current_debt, get_value(current, "cash")
    )
    previous_capital = quality.invested_capital(
        get_value(previous, "equity"), previous_debt, get_value(previous, "cash")
    )
    average_capital = quality.average_invested_capital(
        current_capital, previous_capital
    )

    quality_result = {
        "gross_margin": quality.gross_margin(
            get_value(current, "gross_profit"), get_value(current, "revenue")
        ),
        "operating_margin": quality.operating_margin(
            get_value(current, "ebit"), get_value(current, "revenue")
        ),
        "roe": quality.roe(
            get_value(current, "npat_parent"),
            get_value(current, "equity"),
            get_value(previous, "equity"),
        ),
        "roic": quality.roic(current_nopat, average_capital),
        "cfo_to_npat": quality.cfo_to_npat(
            get_value(current, "cfo"), get_value(current, "npat_parent")
        ),
    }

    debt = safety.total_debt(
        get_value(current, "short_term_debt"),
        get_value(current, "long_term_debt"),
    )
    current_net_debt = safety.net_debt(debt, get_value(current, "cash"))

    safety_result = {
        "equity": get_value(current, "equity"),
        "current_ratio": safety.current_ratio(
            get_value(current, "current_assets"),
            get_value(current, "current_liabilities"),
        ),
        "quick_ratio": safety.quick_ratio(
            get_value(current, "current_assets"),
            get_value(current, "inventory"),
            get_value(current, "current_liabilities"),
        ),
        "debt_to_equity": safety.debt_to_equity(
            debt, get_value(current, "equity")
        ),
        "net_debt_to_ebitda": safety.net_debt_to_ebitda(
            current_net_debt, get_value(current, "ebitda")
        ),
        "interest_coverage": safety.interest_coverage(
            get_value(current, "ebit"), get_value(current, "interest_expense")
        ),
        "cfo_to_debt": safety.cfo_to_debt(
            get_value(current, "cfo"), debt
        ),
    }

    # Valuation is live and therefore must not be paired with ``year`` as if
    # that integer were a historical as-of date. The valuation layer selects
    # its own latest reported financial period and records the data vintage.
    valuation = get_valuation(ticker)
    valuation_result = {
        name: get_value(valuation, name)
        for name in [
            "price",
            "shares_outstanding",
            "shares_date",
            "market_cap",
            "pe",
            "pb",
            "ev_to_ebitda",
            "fcf_yield",
            "valuation_mode",
            "requested_as_of_date",
            "as_of_date",
            "price_date",
            "price_source",
            "price_adjustment",
            "shares_source",
            "shares_fallback_used",
            "financial_period",
            "financial_period_end_date",
            "financial_publication_date",
            "earnings_basis",
            "publication_date_missing",
            "point_in_time_safe",
            "valuation_warnings",
        ]
    }

    return {
        "ticker": ticker,
        "year": year,
        "growth": growth_result,
        "quality": quality_result,
        "safety": safety_result,
        "valuation": valuation_result,
    }


if __name__ == "__main__":
    snapshot = get_fundamental_snapshot("VNM", 2025)

    print("ticker:", snapshot["ticker"])
    print("year:", snapshot["year"])

    for group in ["growth", "quality", "safety", "valuation"]:
        print(f"\n{group.upper()}")
        for name, value in snapshot[group].items():
            print(f"{name}: {value}")
