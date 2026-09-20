import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from fundamental_config import PEER_SELECTION_CONFIG


BASE_DIR = Path(__file__).resolve().parent

HIGHER_IS_BETTER = [
    "revenue_growth_yoy",
    "revenue_cagr_3_year",
    "eps_cagr_3_year",
    "operating_margin",
    "roe",
    "roic",
    "interest_coverage",
    "cfo_to_debt",
    "fcf_yield",
]

LOWER_IS_BETTER = [
    "debt_to_equity",
    "net_debt_to_ebitda",
    "pe",
    "pb",
    "ev_to_ebitda",
]

OUTPUT_COLUMNS = [
    "ticker",
    "year",
    "metric",
    "raw_value",
    "direction",
    "peer_percentile",
    "valid_company_count",
    "peer_method",
    "peer_quality",
    "peer_count",
    "peer_industry",
    "peer_sub_industry",
    "size_filter_applied",
    "fallback_used",
    "peer_warning",
]


def get_snapshot_file(ticker, year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"peer_snapshot_{ticker_lower}_{year}.csv"


def get_percentile_file(ticker, year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"peer_percentile_{ticker_lower}_{year}.csv"


def get_selection_file(ticker, year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"peer_selection_{ticker_lower}_{year}.csv"


def calculate_metric_percentile(snapshot_df, metric, direction):
    raw_values = pd.to_numeric(snapshot_df[metric], errors="coerce")
    valid_company_count = int(raw_values.notna().sum())

    if valid_company_count < 2:
        percentiles = pd.Series(np.nan, index=snapshot_df.index, dtype=float)
    else:
        ascending = direction == "higher_is_better"
        ranks = raw_values.rank(method="average", ascending=ascending, na_option="keep")
        percentiles = (ranks - 1) / (valid_company_count - 1) * 100
        percentiles = percentiles.clip(lower=0, upper=100)

    return raw_values, percentiles, valid_company_count


def run_peer_percentile(
    ticker,
    year,
    snapshot_df=None,
    selection_df=None,
    persist=True,
):
    target_ticker = ticker.strip().upper()
    output_file = get_percentile_file(target_ticker, year)
    snapshot_file = get_snapshot_file(target_ticker, year)
    if snapshot_df is None:
        snapshot_df = pd.read_csv(snapshot_file)
    else:
        snapshot_df = snapshot_df.copy()
    if selection_df is None:
        selection_df = pd.read_csv(get_selection_file(target_ticker, year))
    else:
        selection_df = selection_df.copy()
    if len(selection_df) != 1:
        raise ValueError("Peer selection metadata must contain exactly one row")
    selection = selection_df.iloc[0].to_dict()

    required_columns = {"ticker", "year", *HIGHER_IS_BETTER, *LOWER_IS_BETTER}
    missing_columns = required_columns.difference(snapshot_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Snapshot CSV is missing required columns: {missing}")

    snapshot_df["ticker"] = snapshot_df["ticker"].astype(str).str.strip().str.upper()
    if target_ticker not in snapshot_df["ticker"].values:
        raise ValueError(f"Target ticker {target_ticker} is not present in {snapshot_file.name}")

    metric_directions = [
        *((metric, "higher_is_better") for metric in HIGHER_IS_BETTER),
        *((metric, "lower_is_better") for metric in LOWER_IS_BETTER),
    ]
    frames = []

    for metric, direction in metric_directions:
        raw_values, percentiles, valid_company_count = calculate_metric_percentile(
            snapshot_df, metric, direction
        )
        valid_peer_count = max(valid_company_count - 1, 0)
        if valid_peer_count < PEER_SELECTION_CONFIG["min_percentile_peers"]:
            percentiles = pd.Series(
                np.nan, index=snapshot_df.index, dtype=float
            )
        frames.append(
            pd.DataFrame(
                {
                    "ticker": snapshot_df["ticker"],
                    "year": snapshot_df["year"],
                    "metric": metric,
                    "raw_value": raw_values,
                    "direction": direction,
                    "peer_percentile": percentiles,
                    "valid_company_count": valid_company_count,
                    "peer_method": selection.get("peer_method"),
                    "peer_quality": selection.get("peer_quality"),
                    "peer_count": selection.get("peer_count"),
                    "peer_industry": selection.get("peer_industry"),
                    "peer_sub_industry": selection.get("peer_sub_industry"),
                    "size_filter_applied": selection.get("size_filter_applied"),
                    "fallback_used": selection.get("fallback_used"),
                    "peer_warning": selection.get("peer_warning"),
                }
            )
        )

    result_df = pd.concat(frames, ignore_index=True)[OUTPUT_COLUMNS]
    if persist:
        result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    target_rows = result_df.loc[
        result_df["ticker"].eq(target_ticker),
        [
            "metric",
            "raw_value",
            "direction",
            "peer_percentile",
            "valid_company_count",
        ],
    ]
    print(target_rows.to_string(index=False))

    total_company_count = len(snapshot_df)
    target_nan_metrics = target_rows.loc[
        target_rows["peer_percentile"].isna(), "metric"
    ].tolist()
    incomplete_metrics = (
        result_df.loc[
            result_df["valid_company_count"].lt(total_company_count),
            "metric",
        ]
        .drop_duplicates()
        .tolist()
    )

    print("\nSUMMARY")
    print(f"Total metrics calculated: {len(metric_directions)}")
    print(
        "Target metrics with NaN: "
        + (", ".join(target_nan_metrics) if target_nan_metrics else "none")
    )
    print(
        "Metrics with valid_company_count below total companies: "
        + (", ".join(incomplete_metrics) if incomplete_metrics else "none")
    )
    if persist:
        print(f"Saved to: {output_file.name}")

    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate peer metric percentiles.")
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("year", type=int, help="Financial year, for example 2025")
    args = parser.parse_args()
    run_peer_percentile(args.ticker, args.year)
