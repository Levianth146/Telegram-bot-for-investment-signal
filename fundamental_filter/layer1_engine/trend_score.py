import argparse
from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

DIRECTION_SCORES = {
    "IMPROVING": 100.0,
    "FLAT": 50.0,
    "DETERIORATING": 0.0,
}

OUTPUT_COLUMNS = [
    "ticker",
    "metric",
    "direction",
    "overall_direction",
    "improving_steps",
    "worsening_steps",
    "flat_steps",
    "direction_score",
    "consistency_score",
    "trend_score",
]


def get_analysis_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"trend_analysis_{ticker_lower}_{start_year}_{end_year}.csv"


def get_output_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"trend_score_{ticker_lower}_{start_year}_{end_year}.csv"


def run_trend_score(
    ticker,
    start_year,
    end_year,
    trend_df=None,
    persist=True,
):
    target_ticker = ticker.strip().upper()
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    analysis_file = get_analysis_file(target_ticker, start_year, end_year)
    output_file = get_output_file(target_ticker, start_year, end_year)
    if trend_df is None:
        trend_df = pd.read_csv(analysis_file)
    else:
        trend_df = trend_df.copy()

    required_columns = {
        "ticker",
        "metric",
        "direction",
        "overall_direction",
        "improving_steps",
        "worsening_steps",
        "flat_steps",
    }
    missing_columns = required_columns.difference(trend_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Trend analysis CSV is missing required columns: {missing}")

    trend_df["ticker"] = trend_df["ticker"].astype(str).str.strip().str.upper()
    trend_df = trend_df.loc[trend_df["ticker"].eq(target_ticker)].copy()
    if trend_df.empty:
        raise ValueError(f"No trend analysis rows found for {target_ticker}")

    for column in ("improving_steps", "worsening_steps", "flat_steps"):
        trend_df[column] = pd.to_numeric(trend_df[column], errors="coerce")

    total_steps = (
        trend_df["improving_steps"]
        + trend_df["worsening_steps"]
        + trend_df["flat_steps"]
    )
    trend_df["consistency_score"] = np.where(
        total_steps.eq(0),
        np.nan,
        (
            trend_df["improving_steps"]
            + 0.5 * trend_df["flat_steps"]
        )
        / total_steps
        * 100,
    )
    trend_df["direction_score"] = trend_df["overall_direction"].map(
        DIRECTION_SCORES
    )
    trend_df["trend_score"] = (
        0.5 * trend_df["direction_score"]
        + 0.5 * trend_df["consistency_score"]
    ).clip(lower=0, upper=100)

    result_df = trend_df[OUTPUT_COLUMNS]
    output_file = get_output_file(target_ticker, start_year, end_year)
    if persist:
        result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    printed_columns = [
        "metric",
        "overall_direction",
        "improving_steps",
        "worsening_steps",
        "direction_score",
        "consistency_score",
        "trend_score",
    ]
    print(result_df[printed_columns].to_string(index=False))

    exception_metrics = result_df.loc[
        result_df["overall_direction"].eq("DETERIORATING")
        & result_df["improving_steps"].gt(result_df["worsening_steps"]),
        "metric",
    ].tolist()

    print("\nSUMMARY")
    print(
        "DETERIORATING with improving_steps > worsening_steps: "
        + (", ".join(exception_metrics) if exception_metrics else "none")
    )
    if persist:
        print(f"Saved to: {output_file.name}")
    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate metric trend scores.")
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("start_year", type=int, help="First financial year")
    parser.add_argument("end_year", type=int, help="Last financial year")
    args = parser.parse_args()
    run_trend_score(args.ticker, args.start_year, args.end_year)
