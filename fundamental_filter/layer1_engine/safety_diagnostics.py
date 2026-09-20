import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from safety_scoring import calculate_safety_components, get_safety_gate_status


BASE_DIR = Path(__file__).resolve().parent
SAFETY_METRICS = [
    "debt_to_equity",
    "net_debt_to_ebitda",
    "interest_coverage",
    "cfo_to_debt",
]

OUTPUT_COLUMNS = [
    "ticker",
    "year",
    "metric",
    "raw_value",
    "peer_percentile",
    "historical_percentile",
    "trend_score",
    "peer_quality",
    "absolute_metric_score",
    "metric_score",
    "relative_position",
    "trend_status",
]

SUMMARY_COLUMNS = [
    "ticker",
    "safety_score",
    "absolute_safety_score",
    "peer_relative_score",
    "safety_trend_score",
    "safety_gate_status",
    "lowest_safety_metric",
    "lowest_metric_score",
    "lowest_peer_percentile_metric",
    "lowest_peer_percentile",
]


def get_scoring_input_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"scoring_input_{ticker_lower}_{start_year}_{end_year}.csv"


def get_metric_score_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"metric_score_{ticker_lower}_{start_year}_{end_year}.csv"


def get_output_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return (
        BASE_DIR
        / f"safety_diagnostics_{ticker_lower}_{start_year}_{end_year}.csv"
    )


def get_relative_position(peer_percentile):
    if pd.isna(peer_percentile):
        return np.nan
    if peer_percentile >= 75:
        return "HIGH"
    if peer_percentile >= 25:
        return "MIDDLE"
    return "LOW"


def get_trend_status(trend_score):
    if pd.isna(trend_score):
        return np.nan
    if trend_score > 50:
        return "IMPROVING_BIAS"
    if trend_score == 50:
        return "NEUTRAL"
    return "DETERIORATING_BIAS"


def build_summary(diagnostics_df, ticker, equity):
    indexed = diagnostics_df.set_index("metric")
    components = calculate_safety_components(
        indexed["raw_value"].to_dict(),
        indexed["peer_percentile"].to_dict(),
        indexed["trend_score"].to_dict(),
        peer_quality=diagnostics_df["peer_quality"].iloc[0],
    )
    safety_gate_status = get_safety_gate_status(
        indexed["raw_value"].to_dict(), equity
    )
    valid_metric_scores = diagnostics_df.dropna(subset=["metric_score"])
    if valid_metric_scores.empty:
        lowest_safety_metric = np.nan
        lowest_metric_score = np.nan
    else:
        lowest_score_index = valid_metric_scores["metric_score"].idxmin()
        lowest_safety_metric = diagnostics_df.loc[lowest_score_index, "metric"]
        lowest_metric_score = diagnostics_df.loc[lowest_score_index, "metric_score"]

    valid_peer_percentiles = diagnostics_df.dropna(subset=["peer_percentile"])
    if valid_peer_percentiles.empty:
        lowest_peer_percentile_metric = np.nan
        lowest_peer_percentile = np.nan
    else:
        lowest_peer_index = valid_peer_percentiles["peer_percentile"].idxmin()
        lowest_peer_percentile_metric = diagnostics_df.loc[
            lowest_peer_index, "metric"
        ]
        lowest_peer_percentile = diagnostics_df.loc[
            lowest_peer_index, "peer_percentile"
        ]

    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "safety_score": components["safety_score"],
                "absolute_safety_score": components["absolute_safety_score"],
                "peer_relative_score": components["peer_relative_score"],
                "safety_trend_score": components["safety_trend_score"],
                "safety_gate_status": safety_gate_status,
                "lowest_safety_metric": lowest_safety_metric,
                "lowest_metric_score": lowest_metric_score,
                "lowest_peer_percentile_metric": lowest_peer_percentile_metric,
                "lowest_peer_percentile": lowest_peer_percentile,
            }
        ],
        columns=SUMMARY_COLUMNS,
    )


def run_safety_diagnostics(ticker, start_year, end_year):
    target_ticker = ticker.strip().upper()
    current_year = end_year
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    scoring_df = pd.read_csv(
        get_scoring_input_file(target_ticker, start_year, end_year)
    )
    metric_df = pd.read_csv(
        get_metric_score_file(target_ticker, start_year, end_year)
    )

    scoring_columns = {
        "ticker",
        "year",
        "module",
        "metric",
        "raw_value",
        "peer_percentile",
        "historical_percentile",
        "trend_score",
        "equity",
        "peer_quality",
    }
    metric_columns = {
        "ticker",
        "year",
        "module",
        "metric",
        "absolute_metric_score",
        "metric_score",
    }
    missing_scoring_columns = scoring_columns.difference(scoring_df.columns)
    missing_metric_columns = metric_columns.difference(metric_df.columns)
    if missing_scoring_columns:
        missing = ", ".join(sorted(missing_scoring_columns))
        raise ValueError(f"Scoring input CSV is missing required columns: {missing}")
    if missing_metric_columns:
        missing = ", ".join(sorted(missing_metric_columns))
        raise ValueError(f"Metric score CSV is missing required columns: {missing}")

    for dataframe in (scoring_df, metric_df):
        dataframe["ticker"] = (
            dataframe["ticker"].astype(str).str.strip().str.upper()
        )

    scoring_safety = scoring_df.loc[
        scoring_df["ticker"].eq(target_ticker)
        & scoring_df["year"].eq(current_year)
        & scoring_df["module"].eq("SAFETY")
        & scoring_df["metric"].isin(SAFETY_METRICS),
        [
            "ticker",
            "year",
            "metric",
            "raw_value",
            "peer_percentile",
            "historical_percentile",
            "trend_score",
            "peer_quality",
        ],
    ].copy()
    equity_values = pd.to_numeric(
        scoring_df.loc[
            scoring_df["ticker"].eq(target_ticker)
            & scoring_df["year"].eq(current_year),
            "equity",
        ],
        errors="coerce",
    ).dropna()
    equity = equity_values.iloc[0] if not equity_values.empty else np.nan
    metric_safety = metric_df.loc[
        metric_df["ticker"].eq(target_ticker)
        & metric_df["year"].eq(current_year)
        & metric_df["module"].eq("SAFETY")
        & metric_df["metric"].isin(SAFETY_METRICS),
        ["ticker", "year", "metric", "absolute_metric_score", "metric_score"],
    ].copy()

    diagnostics_df = scoring_safety.merge(
        metric_safety,
        on=["ticker", "year", "metric"],
        how="outer",
        validate="one_to_one",
    )
    metric_order = {metric: index for index, metric in enumerate(SAFETY_METRICS)}
    diagnostics_df["metric_order"] = diagnostics_df["metric"].map(metric_order)
    diagnostics_df = diagnostics_df.sort_values("metric_order").drop(
        columns="metric_order"
    )

    missing_metric_rows = [
        metric for metric in SAFETY_METRICS if metric not in diagnostics_df["metric"].values
    ]
    if missing_metric_rows:
        raise ValueError(f"Missing Safety metric rows: {missing_metric_rows}")

    diagnostics_df["relative_position"] = diagnostics_df[
        "peer_percentile"
    ].apply(get_relative_position)
    diagnostics_df["trend_status"] = diagnostics_df["trend_score"].apply(
        get_trend_status
    )
    diagnostics_df = diagnostics_df[OUTPUT_COLUMNS]

    summary_df = build_summary(diagnostics_df, target_ticker, equity)
    output_file = get_output_file(target_ticker, start_year, end_year)
    diagnostics_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    print(diagnostics_df.to_string(index=False))
    print("\nSUMMARY")
    print(summary_df.to_string(index=False))
    print("Relative position and trend status are descriptive only.")
    print("Safety Gate is diagnostic only; no stock-level risk conclusion was made.")
    print(f"Saved to: {output_file.name}")

    return diagnostics_df, summary_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build Safety metric diagnostics.")
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("start_year", type=int, help="First historical year")
    parser.add_argument("end_year", type=int, help="Current financial year")
    args = parser.parse_args()
    run_safety_diagnostics(args.ticker, args.start_year, args.end_year)
