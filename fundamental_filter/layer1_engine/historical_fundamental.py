import argparse
from pathlib import Path

import pandas as pd

from .financial_data import get_financial_data
from . import ratios_growth as growth
from . import ratios_quality as quality
from . import ratios_safety as safety


BASE_DIR = Path(__file__).resolve().parent

COLUMNS = [
    "ticker",
    "year",
    "revenue_growth_yoy",
    "npat_growth_yoy",
    "revenue_cagr_3_year",
    "eps_growth_yoy",
    "eps_cagr_3_year",
    "cfo_growth_yoy",
    "fcf",
    "gross_margin",
    "operating_margin",
    "roe",
    "roic",
    "cfo_to_npat",
    "current_ratio",
    "quick_ratio",
    "debt_to_equity",
    "net_debt_to_ebitda",
    "interest_coverage",
    "cfo_to_debt",
]


def get_output_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return (
        BASE_DIR
        / f"historical_fundamental_{ticker_lower}_{start_year}_{end_year}.csv"
    )


def get_value(data, name):
    if data is None:
        return None
    return data.get(name)


def get_historical_fundamental(ticker, start_year, end_year, persist=True):
    ticker = ticker.strip().upper()
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    financial_data = {}
    for data_year in range(start_year - 3, end_year + 1):
        try:
            financial_data[data_year] = get_financial_data(ticker, data_year)
        except (Exception, SystemExit) as error:
            message = str(error).strip() or type(error).__name__
            print(f"ERROR {ticker} {data_year}: {message}")
            financial_data[data_year] = None

    rows = []
    for year in range(start_year, end_year + 1):
        current = financial_data.get(year)
        previous = financial_data.get(year - 1)
        three_years_ago = financial_data.get(year - 3)

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
            get_value(current, "equity"),
            current_debt,
            get_value(current, "cash"),
        )
        previous_capital = quality.invested_capital(
            get_value(previous, "equity"),
            previous_debt,
            get_value(previous, "cash"),
        )
        average_capital = quality.average_invested_capital(
            current_capital, previous_capital
        )

        debt = safety.total_debt(
            get_value(current, "short_term_debt"),
            get_value(current, "long_term_debt"),
        )
        current_net_debt = safety.net_debt(
            debt, get_value(current, "cash")
        )

        rows.append(
            {
                "ticker": ticker,
                "year": year,
                "revenue_growth_yoy": growth.revenue_growth_yoy(
                    get_value(current, "revenue"),
                    get_value(previous, "revenue"),
                ),
                "npat_growth_yoy": growth.npat_growth_yoy(
                    get_value(current, "npat_parent"),
                    get_value(previous, "npat_parent"),
                ),
                "revenue_cagr_3_year": growth.revenue_cagr_3_year(
                    get_value(current, "revenue"),
                    get_value(three_years_ago, "revenue"),
                ),
                "eps_growth_yoy": growth.eps_growth_yoy(
                    get_value(current, "eps"),
                    get_value(previous, "eps"),
                ),
                "eps_cagr_3_year": growth.eps_cagr_3_year(
                    get_value(current, "eps"),
                    get_value(three_years_ago, "eps"),
                ),
                "cfo_growth_yoy": growth.cfo_growth_yoy(
                    get_value(current, "cfo"),
                    get_value(previous, "cfo"),
                ),
                "fcf": growth.free_cash_flow(
                    get_value(current, "cfo"),
                    get_value(current, "capex"),
                ),
                "gross_margin": quality.gross_margin(
                    get_value(current, "gross_profit"),
                    get_value(current, "revenue"),
                ),
                "operating_margin": quality.operating_margin(
                    get_value(current, "ebit"),
                    get_value(current, "revenue"),
                ),
                "roe": quality.roe(
                    get_value(current, "npat_parent"),
                    get_value(current, "equity"),
                    get_value(previous, "equity"),
                ),
                "roic": quality.roic(current_nopat, average_capital),
                "cfo_to_npat": quality.cfo_to_npat(
                    get_value(current, "cfo"),
                    get_value(current, "npat_parent"),
                ),
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
                    get_value(current, "ebit"),
                    get_value(current, "interest_expense"),
                ),
                "cfo_to_debt": safety.cfo_to_debt(
                    get_value(current, "cfo"), debt
                ),
            }
        )

    result_df = pd.DataFrame(rows, columns=COLUMNS)
    if persist:
        output_file = get_output_file(ticker, start_year, end_year)
        result_df.to_csv(output_file, index=False, encoding="utf-8-sig")
    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build historical accounting fundamentals."
    )
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("start_year", type=int, help="First financial year")
    parser.add_argument("end_year", type=int, help="Last financial year")
    args = parser.parse_args()

    result = get_historical_fundamental(
        args.ticker, args.start_year, args.end_year
    )
    print(result.to_string(index=False))
    print(
        "Saved to:",
        get_output_file(args.ticker, args.start_year, args.end_year).name,
    )
