import argparse
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

HIGHER_IS_BETTER = [
    "revenue_growth_yoy",
    "npat_growth_yoy",
    "eps_growth_yoy",
    "revenue_cagr_3_year",
    "eps_cagr_3_year",
    "operating_margin",
    "roe",
    "roic",
    "cfo_to_npat",
    "interest_coverage",
    "cfo_to_debt",
]

LOWER_IS_BETTER = [
    "debt_to_equity",
    "net_debt_to_ebitda",
]

OUTPUT_COLUMNS = [
    "ticker",
    "year",
    "metric",
    "raw_value",
    "direction",
    "historical_percentile",
    "valid_year_count",
]


def get_fundamental_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return (
        BASE_DIR
        / f"historical_fundamental_{ticker_lower}_{start_year}_{end_year}.csv"
    )


def get_percentile_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return (
        BASE_DIR
        / f"historical_percentile_{ticker_lower}_{start_year}_{end_year}.csv"
    )


def calculate_metric_percentile(historical_df, metric, direction):
    raw_values = pd.to_numeric(historical_df[metric], errors="coerce")
    valid_year_count = int(raw_values.notna().sum())

    if valid_year_count < 2:
        percentiles = pd.Series(np.nan, index=historical_df.index, dtype=float)
    else:
        ascending = direction == "higher_is_better"
        ranks = raw_values.rank(method="average", ascending=ascending, na_option="keep")
        percentiles = (ranks - 1) / (valid_year_count - 1) * 100
        percentiles = percentiles.clip(lower=0, upper=100)

    return raw_values, percentiles, valid_year_count


def run_historical_percentile(ticker, start_year, end_year):
    target_ticker = ticker.strip().upper()
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    fundamental_file = get_fundamental_file(
        target_ticker, start_year, end_year
    )
    output_file = get_percentile_file(target_ticker, start_year, end_year)
    historical_df = pd.read_csv(fundamental_file)

    required_columns = {"ticker", "year", *HIGHER_IS_BETTER, *LOWER_IS_BETTER}
    missing_columns = required_columns.difference(historical_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Historical CSV is missing required columns: {missing}")

    historical_df["ticker"] = (
        historical_df["ticker"].astype(str).str.strip().str.upper()
    )
    historical_df = historical_df.loc[
        historical_df["ticker"].eq(target_ticker)
        & historical_df["year"].between(start_year, end_year)
    ].copy()
    historical_df = historical_df.sort_values("year").reset_index(drop=True)

    if historical_df.empty:
        raise ValueError(
            f"No rows for {target_ticker} from {start_year} to {end_year}"
        )

    metric_directions = [
        *((metric, "higher_is_better") for metric in HIGHER_IS_BETTER),
        *((metric, "lower_is_better") for metric in LOWER_IS_BETTER),
    ]
    frames = []

    for metric, direction in metric_directions:
        raw_values, percentiles, valid_year_count = calculate_metric_percentile(
            historical_df, metric, direction
        )
        frames.append(
            pd.DataFrame(
                {
                    "ticker": historical_df["ticker"],
                    "year": historical_df["year"],
                    "metric": metric,
                    "raw_value": raw_values,
                    "direction": direction,
                    "historical_percentile": percentiles,
                    "valid_year_count": valid_year_count,
                }
            )
        )

    result_df = pd.concat(frames, ignore_index=True)[OUTPUT_COLUMNS]
    result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    end_year_rows = result_df.loc[
        result_df["year"].eq(end_year),
        [
            "metric",
            "raw_value",
            "direction",
            "historical_percentile",
            "valid_year_count",
        ],
    ]
    print(end_year_rows.to_string(index=False))

    expected_year_count = end_year - start_year + 1
    end_year_nan_metrics = end_year_rows.loc[
        end_year_rows["historical_percentile"].isna(), "metric"
    ].tolist()
    incomplete_metrics = (
        result_df.loc[
            result_df["valid_year_count"].lt(expected_year_count), "metric"
        ]
        .drop_duplicates()
        .tolist()
    )

    print("\nSUMMARY")
    print(f"Total metrics calculated: {len(metric_directions)}")
    print(
        f"Metrics with NaN in {end_year}: "
        + (", ".join(end_year_nan_metrics) if end_year_nan_metrics else "none")
    )
    print(
        f"Metrics with valid_year_count below {expected_year_count}: "
        + (", ".join(incomplete_metrics) if incomplete_metrics else "none")
    )
    print(f"Saved to: {output_file.name}")

    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Calculate historical accounting metric percentiles."
    )
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("start_year", type=int, help="First financial year")
    parser.add_argument("end_year", type=int, help="Last financial year")
    args = parser.parse_args()
    run_historical_percentile(args.ticker, args.start_year, args.end_year)
