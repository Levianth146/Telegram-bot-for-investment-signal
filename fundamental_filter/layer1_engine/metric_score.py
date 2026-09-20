import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .fundamental_config import (
    GROWTH_QUALITY_COMPONENT_WEIGHTS,
    PEER_QUALITY_MULTIPLIERS,
)
from .safety_scoring import calculate_absolute_metric_score
from .scoring_utils import normalize_available_weights


BASE_DIR = Path(__file__).resolve().parent

OUTPUT_COLUMNS = [
    "ticker",
    "year",
    "module",
    "metric",
    "raw_value",
    "peer_percentile",
    "historical_percentile",
    "trend_score",
    "equity",
    "absolute_metric_score",
    "peer_method",
    "peer_quality",
    "peer_count",
    "peer_warning",
    "historical_valuation_score",
    "historical_valuation_available",
    "historical_valuation_reason",
    "fundamental_context_score",
    "absolute_weight_used",
    "peer_weight_used",
    "trend_weight_used",
    "score_reweight_reason",
    "metric_score",
]


def _peer_multiplier(row):
    quality = str(row.get("peer_quality", "HIGH")).upper()
    return PEER_QUALITY_MULTIPLIERS.get(quality, 0.0)


def _peer_trend_score(row):
    score, weights, reason = normalize_available_weights(
        GROWTH_QUALITY_COMPONENT_WEIGHTS,
        {"peer": row["peer_percentile"], "trend": row["trend_score"]},
        {"peer": _peer_multiplier(row)},
    )
    return pd.Series(
        {
            "metric_score": score,
            "peer_weight_used": weights["peer"],
            "trend_weight_used": weights["trend"],
            "score_reweight_reason": reason,
        }
    )


def _safety_metric_score(row):
    weights = {"absolute": 0.60, "peer": 0.25, "trend": 0.15}
    score, used, reason = normalize_available_weights(
        weights,
        {
            "absolute": row["absolute_metric_score"],
            "peer": row["peer_percentile"],
            "trend": row["trend_score"],
        },
        {"peer": _peer_multiplier(row)},
    )
    return pd.Series(
        {
            "metric_score": score,
            "absolute_weight_used": used["absolute"],
            "peer_weight_used": used["peer"],
            "trend_weight_used": used["trend"],
            "score_reweight_reason": reason,
        }
    )


def calculate_metric_scores(scoring_df):
    result = scoring_df.copy()
    if "peer_quality" not in result.columns:
        result["peer_quality"] = "HIGH"
    growth_mask = result["module"].eq("GROWTH")
    quality_mask = result["module"].eq("QUALITY")
    safety_mask = result["module"].eq("SAFETY")
    valuation_mask = result["module"].eq("VALUATION")

    known_modules = growth_mask | quality_mask | safety_mask | valuation_mask
    if not known_modules.all():
        unknown_modules = result.loc[~known_modules, "module"].unique().tolist()
        raise ValueError(f"Unknown modules in scoring input: {unknown_modules}")

    result["absolute_metric_score"] = np.nan
    result.loc[safety_mask, "absolute_metric_score"] = result.loc[
        safety_mask
    ].apply(
        lambda row: calculate_absolute_metric_score(
            row["metric"], row["raw_value"]
        ),
        axis=1,
    )

    for column in (
        "metric_score",
        "absolute_weight_used",
        "peer_weight_used",
        "trend_weight_used",
    ):
        result[column] = np.nan
    result["score_reweight_reason"] = "none"

    diagnostic_cfo_mask = result["metric"].eq("cfo_growth_yoy")
    result.loc[diagnostic_cfo_mask, "score_reweight_reason"] = "diagnostic_only"

    growth_quality_mask = (growth_mask | quality_mask) & ~diagnostic_cfo_mask
    if growth_quality_mask.any():
        calculated = result.loc[growth_quality_mask].apply(
            _peer_trend_score, axis=1
        )
        result.loc[growth_quality_mask, calculated.columns] = calculated.values
    if safety_mask.any():
        calculated = result.loc[safety_mask].apply(_safety_metric_score, axis=1)
        result.loc[safety_mask, calculated.columns] = calculated.values
    result.loc[valuation_mask, "metric_score"] = result.loc[
        valuation_mask, "peer_percentile"
    ]
    result.loc[diagnostic_cfo_mask, [
        "peer_percentile",
        "trend_score",
        "metric_score",
        "peer_weight_used",
        "trend_weight_used",
    ]] = np.nan
    result.loc[diagnostic_cfo_mask, "score_reweight_reason"] = "diagnostic_only"
    return result


def get_scoring_input_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"scoring_input_{ticker_lower}_{start_year}_{end_year}.csv"


def get_output_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"metric_score_{ticker_lower}_{start_year}_{end_year}.csv"


def run_metric_score(
    ticker,
    start_year,
    end_year,
    scoring_df=None,
    persist=True,
):
    target_ticker = ticker.strip().upper()
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    input_file = get_scoring_input_file(target_ticker, start_year, end_year)
    output_file = get_output_file(target_ticker, start_year, end_year)
    if scoring_df is None:
        scoring_df = pd.read_csv(input_file)
    else:
        scoring_df = scoring_df.copy()

    required_columns = {
        "ticker",
        "year",
        "module",
        "metric",
        "raw_value",
        "peer_percentile",
        "historical_percentile",
        "trend_score",
        "equity",
        "peer_method",
        "peer_quality",
        "peer_count",
        "peer_warning",
        "historical_valuation_score",
        "historical_valuation_available",
        "historical_valuation_reason",
        "fundamental_context_score",
    }
    missing_columns = required_columns.difference(scoring_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Scoring input CSV is missing required columns: {missing}")

    scoring_df["ticker"] = (
        scoring_df["ticker"].astype(str).str.strip().str.upper()
    )
    scoring_df = scoring_df.loc[
        scoring_df["ticker"].eq(target_ticker)
        & scoring_df["year"].eq(end_year)
    ].copy()
    if scoring_df.empty:
        raise ValueError(f"No scoring input rows found for {target_ticker} {end_year}")

    for column in (
        "raw_value",
        "peer_percentile",
        "historical_percentile",
        "trend_score",
        "equity",
    ):
        scoring_df[column] = pd.to_numeric(scoring_df[column], errors="coerce")
    scoring_df = calculate_metric_scores(scoring_df)

    valid_scores = scoring_df["metric_score"].dropna()
    if not valid_scores.between(0, 100).all():
        invalid_metrics = scoring_df.loc[
            scoring_df["metric_score"].notna()
            & ~scoring_df["metric_score"].between(0, 100),
            "metric",
        ].tolist()
        raise ValueError(f"Metric scores outside 0-100: {invalid_metrics}")

    result_df = scoring_df[OUTPUT_COLUMNS]
    if persist:
        result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    printed_columns = [
        "module",
        "metric",
        "peer_percentile",
        "historical_percentile",
        "trend_score",
        "absolute_metric_score",
        "peer_weight_used",
        "trend_weight_used",
        "score_reweight_reason",
        "metric_score",
    ]
    print(result_df[printed_columns].to_string(index=False))

    nan_metrics = result_df.loc[result_df["metric_score"].isna(), "metric"].tolist()
    print("\nSUMMARY")
    print(f"Valid metric scores: {int(result_df['metric_score'].notna().sum())}")
    print(
        "Metrics with NaN metric_score: "
        + (", ".join(nan_metrics) if nan_metrics else "none")
    )
    print(
        "Minimum metric_score: "
        + (f"{valid_scores.min():.6f}" if not valid_scores.empty else "NaN")
    )
    print(
        "Maximum metric_score: "
        + (f"{valid_scores.max():.6f}" if not valid_scores.empty else "NaN")
    )
    print("Module Score and Fundamental Score have not been calculated.")
    if persist:
        print(f"Saved to: {output_file.name}")

    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate core metric scores.")
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("start_year", type=int, help="First historical year")
    parser.add_argument("end_year", type=int, help="Current financial year")
    args = parser.parse_args()
    run_metric_score(args.ticker, args.start_year, args.end_year)
