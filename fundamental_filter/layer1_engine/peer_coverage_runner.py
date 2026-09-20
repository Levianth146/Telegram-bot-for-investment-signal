import argparse
import time
from pathlib import Path

import pandas as pd

from .peer_coverage import check_peer_coverage
from .peer_group import get_peer_group
from .peer_selector import select_peer_universe


BASE_DIR = Path(__file__).resolve().parent


def get_coverage_file(ticker, year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"peer_coverage_{ticker_lower}_{year}.csv"


def get_selection_file(ticker, year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"peer_selection_{ticker_lower}_{year}.csv"


def run_peer_coverage(ticker, year, persist=True, sleep_seconds=4):
    ticker = ticker.strip().upper()
    peer_group = get_peer_group(ticker)

    if peer_group is None:
        print("Không lấy được peer group.")
        return None

    peer_symbols = peer_group["peer_symbols"]
    target_coverage = check_peer_coverage(ticker, year)
    rows = []

    for index, peer in enumerate(peer_symbols):
        print(f"Đang kiểm tra {peer} ({index + 1}/{len(peer_symbols)})...", flush=True)

        try:
            result = check_peer_coverage(peer, year)
        except (Exception, SystemExit) as error:
            message = str(error).strip()
            message = message.splitlines()[0] if message else type(error).__name__
            result = {
                "ticker": peer,
                "exchange": None,
                "financial_ok": False,
                "missing_financial_fields": None,
                "price_ok": False,
                "price": None,
                "shares_ok": False,
                "shares_outstanding": None,
                "market_cap": None,
                "eligible": False,
                "reason": f"Runner error: {message}",
            }

        rows.append(result)

        if index < len(peer_symbols) - 1:
            time.sleep(sleep_seconds)

    result_df = pd.DataFrame(rows)
    result_df["coverage_eligible"] = result_df["eligible"]
    selected_tickers, selection_metadata = select_peer_universe(
        ticker,
        result_df,
        industry_code=peer_group.get("industry_code"),
        industry_name=peer_group.get("industry_name"),
        target_market_cap=target_coverage.get("market_cap"),
        target_sub_industry=peer_group.get("sub_industry"),
    )
    result_df["selected_peer"] = result_df["ticker"].isin(selected_tickers)
    not_selected = result_df["coverage_eligible"] & ~result_df["selected_peer"]
    result_df.loc[not_selected, "reason"] = "NOT_SELECTED_BY_PEER_SELECTOR"
    result_df["eligible"] = result_df["selected_peer"]
    for field, value in selection_metadata.items():
        if field != "ticker":
            result_df[field] = value
    if persist:
        output_file = get_coverage_file(ticker, year)
        result_df.to_csv(output_file, index=False, encoding="utf-8-sig")
        pd.DataFrame([selection_metadata]).to_csv(
            get_selection_file(ticker, year), index=False, encoding="utf-8-sig"
        )

    print("\nBẢNG COVERAGE")
    print(result_df.to_string(index=False))

    eligible_df = result_df[result_df["selected_peer"]]
    excluded_df = result_df[~result_df["selected_peer"]]

    print("\nTỔNG KẾT")
    print("Tổng số peer:", len(result_df))
    print("Số peer eligible:", len(eligible_df))
    print("Số peer bị loại:", len(excluded_df))
    print("\nSố bị loại theo reason:")
    print(excluded_df["reason"].value_counts().to_string())
    print("\nTicker eligible:", eligible_df["ticker"].tolist())
    print("\nTicker excluded kèm reason:")
    print(excluded_df[["ticker", "reason"]].to_string(index=False))

    print("\nPEER SELECTION")
    for field, value in selection_metadata.items():
        print(f"{field}: {value}")

    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check data coverage for a peer group.")
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("year", type=int, help="Financial year, for example 2025")
    args = parser.parse_args()
    run_peer_coverage(args.ticker, args.year)
