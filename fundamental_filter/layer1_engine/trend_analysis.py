import argparse
from pathlib import Path

import numpy as np
import pandas as pd


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
]

LOWER_IS_BETTER = [
    "debt_to_equity",
    "net_debt_to_ebitda",
]

OUTPUT_COLUMNS = [
    "ticker",
    "start_year",
    "end_year",
    "metric",
    "direction",
    "first_value",
    "latest_value",
    "raw_change",
    "improving_steps",
    "worsening_steps",
    "flat_steps",
    "valid_year_count",
    "overall_direction",
]


def get_fundamental_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return (
        BASE_DIR
        / f"historical_fundamental_{ticker_lower}_{start_year}_{end_year}.csv"
    )


def get_output_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"trend_analysis_{ticker_lower}_{start_year}_{end_year}.csv"


def classify_change(previous_value, current_value, direction):
    if current_value == previous_value:
        return "flat"

    if direction == "higher_is_better":
        return "improving" if current_value > previous_value else "worsening"

    return "improving" if current_value < previous_value else "worsening"


def get_overall_direction(first_value, latest_value, direction):
    if pd.isna(first_value) or pd.isna(latest_value):
        return np.nan
    if latest_value == first_value:
        return "FLAT"

    if direction == "higher_is_better":
        return "IMPROVING" if latest_value > first_value else "DETERIORATING"

    return "IMPROVING" if latest_value < first_value else "DETERIORATING"


def analyze_metric(historical_df, metric, direction, ticker, start_year, end_year):
    values = pd.to_numeric(historical_df[metric], errors="coerce")
    valid_values = values.dropna()
    valid_year_count = int(valid_values.count())

    if valid_year_count:
        first_value = valid_values.iloc[0]
        latest_value = valid_values.iloc[-1]
        raw_change = latest_value - first_value
    else:
        first_value = np.nan
        latest_value = np.nan
        raw_change = np.nan

    step_counts = {"improving": 0, "worsening": 0, "flat": 0}
    years = historical_df["year"].tolist()

    for index in range(1, len(historical_df)):
        if years[index] != years[index - 1] + 1:
            continue

        previous_value = values.iloc[index - 1]
        current_value = values.iloc[index]
        if pd.isna(previous_value) or pd.isna(current_value):
            continue

        classification = classify_change(
            previous_value, current_value, direction
        )
        step_counts[classification] += 1

    return {
        "ticker": ticker,
        "start_year": start_year,
        "end_year": end_year,
        "metric": metric,
        "direction": direction,
        "first_value": first_value,
        "latest_value": latest_value,
        "raw_change": raw_change,
        "improving_steps": step_counts["improving"],
        "worsening_steps": step_counts["worsening"],
        "flat_steps": step_counts["flat"],
        "valid_year_count": valid_year_count,
        "overall_direction": get_overall_direction(
            first_value, latest_value, direction
        ),
    }


def run_trend_analysis(
    ticker,
    start_year,
    end_year,
    historical_df=None,
    persist=True,
):
    target_ticker = ticker.strip().upper()
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    fundamental_file = get_fundamental_file(
        target_ticker, start_year, end_year
    )
    output_file = get_output_file(target_ticker, start_year, end_year)
    if historical_df is None:
        historical_df = pd.read_csv(fundamental_file)
    else:
        historical_df = historical_df.copy()

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
    rows = [
        analyze_metric(
            historical_df,
            metric,
            direction,
            target_ticker,
            start_year,
            end_year,
        )
        for metric, direction in metric_directions
    ]

    result_df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if persist:
        result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print(result_df.to_string(index=False))

    print("\nSUMMARY")
    for overall_direction in ("IMPROVING", "DETERIORATING", "FLAT"):
        metrics = result_df.loc[
            result_df["overall_direction"].eq(overall_direction), "metric"
        ].tolist()
        print(
            f"{overall_direction}: "
            + (", ".join(metrics) if metrics else "none")
        )

    print("\nSTEP COUNTS")
    for row in result_df.itertuples(index=False):
        print(
            f"{row.metric}: {row.improving_steps} / "
            f"{row.worsening_steps} / {row.flat_steps}"
        )

    if persist:
        print(f"Saved to: {output_file.name}")
    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze historical accounting metric trends."
    )
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("start_year", type=int, help="First financial year")
    parser.add_argument("end_year", type=int, help="Last financial year")
    args = parser.parse_args()
    run_trend_analysis(args.ticker, args.start_year, args.end_year)
