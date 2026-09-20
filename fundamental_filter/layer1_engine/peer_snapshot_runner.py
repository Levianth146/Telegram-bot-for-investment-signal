import argparse
import time
from pathlib import Path

import pandas as pd

from .fundamental_snapshot import get_fundamental_snapshot


SLEEP_SECONDS = 4
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
    "equity",
    "current_ratio",
    "quick_ratio",
    "debt_to_equity",
    "net_debt_to_ebitda",
    "interest_coverage",
    "cfo_to_debt",
    "price",
    "shares_outstanding",
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
    "shares_date",
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


def flatten_snapshot(snapshot):
    row = {
        "ticker": snapshot.get("ticker"),
        "year": snapshot.get("year"),
    }

    for group in ("growth", "quality", "safety", "valuation"):
        group_values = snapshot.get(group) or {}
        for column in COLUMNS[2:]:
            if column in group_values:
                row[column] = group_values[column]

    return {column: row.get(column) for column in COLUMNS}


def get_coverage_file(ticker, year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"peer_coverage_{ticker_lower}_{year}.csv"


def get_snapshot_file(ticker, year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"peer_snapshot_{ticker_lower}_{year}.csv"


def read_eligible_peers(coverage_file):
    coverage_df = pd.read_csv(coverage_file)

    required_columns = {"ticker", "eligible"}
    missing_columns = required_columns.difference(coverage_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Coverage CSV is missing required columns: {missing}")

    eligible = coverage_df["eligible"].astype(str).str.strip().str.lower().eq("true")
    return (
        coverage_df.loc[eligible, "ticker"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .tolist()
    )


def run_peer_snapshot(
    ticker,
    year,
    coverage_df=None,
    persist=True,
    sleep_seconds=SLEEP_SECONDS,
):
    target_ticker = ticker.strip().upper()
    output_file = get_snapshot_file(target_ticker, year)
    if coverage_df is None:
        eligible_tickers = read_eligible_peers(
            get_coverage_file(target_ticker, year)
        )
    else:
        required_columns = {"ticker", "eligible"}
        missing = required_columns.difference(coverage_df.columns)
        if missing:
            raise ValueError(
                "Coverage data is missing columns: " + ", ".join(sorted(missing))
            )
        eligible = coverage_df["eligible"].astype(bool)
        eligible_tickers = (
            coverage_df.loc[eligible, "ticker"]
            .dropna().astype(str).str.strip().str.upper().tolist()
        )

    peer_tickers = []
    seen = {target_ticker}
    for peer in eligible_tickers:
        if peer not in seen:
            peer_tickers.append(peer)
            seen.add(peer)

    tickers_to_run = peer_tickers + [target_ticker]
    rows = []
    peer_success_count = 0
    errors = []

    print(f"Eligible peers read from CSV: {len(peer_tickers)}")

    for index, current_ticker in enumerate(tickers_to_run):
        print(
            f"Running snapshot for {current_ticker} "
            f"({index + 1}/{len(tickers_to_run)})...",
            flush=True,
        )

        try:
            snapshot = get_fundamental_snapshot(current_ticker, year)
            rows.append(flatten_snapshot(snapshot))
            if index < len(peer_tickers):
                peer_success_count += 1
        except (Exception, SystemExit) as error:
            message = str(error).strip() or type(error).__name__
            errors.append((current_ticker, message))
            print(f"ERROR {current_ticker}: {message}", flush=True)

        if index < len(tickers_to_run) - 1:
            time.sleep(sleep_seconds)

    result_df = pd.DataFrame(rows, columns=COLUMNS)
    if persist:
        result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    columns_with_none = {
        column: int(result_df[column].isna().sum())
        for column in result_df.columns
        if result_df[column].isna().any()
    }

    print("\nSUMMARY")
    print(f"Eligible peers read from CSV: {len(peer_tickers)}")
    print(f"Successful peer snapshots: {peer_success_count}")
    if errors:
        print("Tickers with errors:")
        for ticker, message in errors:
            print(f"- {ticker}: {message}")
    else:
        print("Tickers with errors: none")
    print(f"Final dataset rows (including {target_ticker}): {len(result_df)}")
    if columns_with_none:
        print("Columns containing None/NaN (missing count):")
        for column, missing_count in columns_with_none.items():
            print(f"- {column}: {missing_count}")
    else:
        print("Columns containing None/NaN: none")
    if persist:
        print(f"Saved to: {output_file}")

    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build snapshots for eligible peers.")
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("year", type=int, help="Financial year, for example 2025")
    args = parser.parse_args()
    run_peer_snapshot(args.ticker, args.year)
