import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .fundamental_config import MODULE_METRIC_WEIGHTS
from .safety_scoring import (
    ABSOLUTE_SAFETY_WEIGHTS,
    calculate_safety_components,
    get_safety_gate_status,
    validate_safety_weights,
)
from .scoring_utils import safe_print
from .valuation_scoring import (
    calculate_peer_valuation_score,
    calculate_valuation_components,
)


BASE_DIR = Path(__file__).resolve().parent

MODULE_WEIGHTS = MODULE_METRIC_WEIGHTS

OUTPUT_COLUMNS = [
    "ticker",
    "year",
    "module",
    "module_score",
    "available_metric_count",
    "required_metric_count",
    "available_weight",
    "missing_metrics",
    "absolute_safety_score",
    "peer_relative_score",
    "safety_trend_score",
    "safety_gate_status",
    "safety_component_weights_used",
    "safety_reweight_reason",
    "peer_valuation_score",
    "historical_valuation_score",
    "historical_valuation_available",
    "historical_valuation_reason",
    "fundamental_context_score",
    "valuation_component_weights_used",
    "valuation_reweight_reason",
    "peer_method",
    "peer_quality",
    "peer_count",
    "peer_warning",
]


def get_metric_score_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"metric_score_{ticker_lower}_{start_year}_{end_year}.csv"


def get_output_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"module_score_{ticker_lower}_{start_year}_{end_year}.csv"


def validate_module_weights():
    validate_safety_weights()
    for module, weights in MODULE_WEIGHTS.items():
        total_weight = sum(weights.values())
        if not math.isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(
                f"Weights for {module} sum to {total_weight}, expected 1.0"
            )


def run_module_score(
    ticker,
    start_year,
    end_year,
    metric_df=None,
    persist=True,
):
    target_ticker = ticker.strip().upper()
    current_year = end_year
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    validate_module_weights()
    input_file = get_metric_score_file(target_ticker, start_year, end_year)
    output_file = get_output_file(target_ticker, start_year, end_year)
    if metric_df is None:
        metric_df = pd.read_csv(input_file)
    else:
        metric_df = metric_df.copy()

    required_columns = {
        "ticker",
        "year",
        "module",
        "metric",
        "raw_value",
        "peer_percentile",
        "trend_score",
        "equity",
        "absolute_metric_score",
        "metric_score",
        "peer_method",
        "peer_quality",
        "peer_count",
        "peer_warning",
        "historical_valuation_score",
        "historical_valuation_available",
        "historical_valuation_reason",
        "fundamental_context_score",
    }
    missing_columns = required_columns.difference(metric_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Metric score CSV is missing required columns: {missing}")

    metric_df["ticker"] = metric_df["ticker"].astype(str).str.strip().str.upper()
    metric_df = metric_df.loc[
        metric_df["ticker"].eq(target_ticker)
        & metric_df["year"].eq(current_year)
    ].copy()
    for column in (
        "raw_value",
        "peer_percentile",
        "trend_score",
        "equity",
        "absolute_metric_score",
        "metric_score",
    ):
        metric_df[column] = pd.to_numeric(metric_df[column], errors="coerce")

    if metric_df.empty:
        raise ValueError(f"No metric score rows found for {target_ticker} {current_year}")
    if metric_df["metric"].duplicated().any():
        duplicates = metric_df.loc[
            metric_df["metric"].duplicated(), "metric"
        ].tolist()
        raise ValueError(f"Duplicate metrics in metric score CSV: {duplicates}")

    scores_by_metric = metric_df.set_index("metric")["metric_score"]
    safety_rows = metric_df.loc[metric_df["module"].eq("SAFETY")].set_index(
        "metric"
    )
    safety_raw_values = safety_rows["raw_value"].to_dict()
    safety_peer_scores = safety_rows["peer_percentile"].to_dict()
    safety_trend_scores = safety_rows["trend_score"].to_dict()
    peer_quality = metric_df["peer_quality"].iloc[0]
    peer_method = metric_df["peer_method"].iloc[0]
    peer_count = metric_df["peer_count"].iloc[0]
    peer_warning = metric_df["peer_warning"].iloc[0]
    safety_components = calculate_safety_components(
        safety_raw_values,
        safety_peer_scores,
        safety_trend_scores,
        peer_quality=peer_quality,
    )
    equity_values = metric_df["equity"].dropna()
    equity = equity_values.iloc[0] if not equity_values.empty else np.nan
    safety_gate_status = get_safety_gate_status(safety_raw_values, equity)
    valuation_rows = metric_df.loc[
        metric_df["module"].eq("VALUATION")
    ].set_index("metric")
    peer_valuation_score = calculate_peer_valuation_score(
        valuation_rows["peer_percentile"].to_dict()
    )
    historical_valuation_score = pd.to_numeric(
        metric_df["historical_valuation_score"], errors="coerce"
    ).dropna()
    historical_valuation_score = (
        historical_valuation_score.iloc[0]
        if not historical_valuation_score.empty
        else np.nan
    )
    fundamental_context_score = pd.to_numeric(
        metric_df["fundamental_context_score"], errors="coerce"
    ).dropna()
    fundamental_context_score = (
        fundamental_context_score.iloc[0]
        if not fundamental_context_score.empty
        else np.nan
    )
    valuation_components = calculate_valuation_components(
        peer_valuation_score,
        historical_valuation_score,
        fundamental_context_score,
        peer_quality=peer_quality,
    )
    rows = []

    for module, weights in MODULE_WEIGHTS.items():
        missing_metrics = []
        available_metric_count = 0
        available_weight = 0.0
        weighted_score = 0.0

        for metric, metric_weight in weights.items():
            metric_score = scores_by_metric.get(metric, np.nan)
            if pd.isna(metric_score):
                missing_metrics.append(metric)
                continue

            available_metric_count += 1
            available_weight += metric_weight
            weighted_score += metric_score * metric_weight

        module_score = np.nan if missing_metrics else weighted_score
        if module == "SAFETY":
            module_score = safety_components["safety_score"]
        elif module == "VALUATION":
            module_score = valuation_components["valuation_score"]
        if not pd.isna(module_score) and not 0 <= module_score <= 100:
            raise ValueError(f"Module score outside 0-100 for {module}: {module_score}")

        rows.append(
            {
                "ticker": target_ticker,
                "year": current_year,
                "module": module,
                "module_score": module_score,
                "available_metric_count": available_metric_count,
                "required_metric_count": len(weights),
                "available_weight": available_weight,
                "missing_metrics": ", ".join(missing_metrics),
                "absolute_safety_score": (
                    safety_components["absolute_safety_score"]
                    if module == "SAFETY"
                    else np.nan
                ),
                "peer_relative_score": (
                    safety_components["peer_relative_score"]
                    if module == "SAFETY"
                    else np.nan
                ),
                "safety_trend_score": (
                    safety_components["safety_trend_score"]
                    if module == "SAFETY"
                    else np.nan
                ),
                "safety_gate_status": (
                    safety_gate_status if module == "SAFETY" else ""
                ),
                "safety_component_weights_used": (
                    json.dumps(safety_components["safety_component_weights_used"])
                    if module == "SAFETY"
                    else ""
                ),
                "safety_reweight_reason": (
                    safety_components["safety_reweight_reason"]
                    if module == "SAFETY"
                    else ""
                ),
                "peer_valuation_score": (
                    valuation_components["peer_valuation_score"]
                    if module == "VALUATION"
                    else np.nan
                ),
                "historical_valuation_score": (
                    valuation_components["historical_valuation_score"]
                    if module == "VALUATION"
                    else np.nan
                ),
                "historical_valuation_available": (
                    valuation_components["historical_valuation_available"]
                    if module == "VALUATION"
                    else np.nan
                ),
                "historical_valuation_reason": (
                    metric_df["historical_valuation_reason"].iloc[0]
                    if module == "VALUATION"
                    else ""
                ),
                "fundamental_context_score": (
                    valuation_components["fundamental_context_score"]
                    if module == "VALUATION"
                    else np.nan
                ),
                "valuation_component_weights_used": (
                    json.dumps(
                        valuation_components["valuation_component_weights_used"]
                    )
                    if module == "VALUATION"
                    else ""
                ),
                "valuation_reweight_reason": (
                    valuation_components["valuation_reweight_reason"]
                    if module == "VALUATION"
                    else ""
                ),
                "peer_method": peer_method,
                "peer_quality": peer_quality,
                "peer_count": peer_count,
                "peer_warning": peer_warning,
            }
        )

    result_df = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    if persist:
        result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    # persist=False = đường batch/backtest: không dump bảng (spam + crash cp1252).
    if persist:
        printed_df = result_df[
            [
                "module",
                "module_score",
                "available_metric_count",
                "required_metric_count",
                "available_weight",
                "missing_metrics",
                "absolute_safety_score",
                "peer_relative_score",
                "safety_trend_score",
                "safety_gate_status",
                "peer_valuation_score",
                "historical_valuation_score",
                "historical_valuation_available",
                "valuation_reweight_reason",
                "peer_method",
                "peer_quality",
                "peer_count",
            ]
        ].copy()
        printed_df["missing_metrics"] = printed_df["missing_metrics"].replace(
            "", "none"
        )
        safe_print(printed_df.to_string(index=False))

        nan_modules = result_df.loc[
            result_df["module_score"].isna(), "module"
        ].tolist()
        safe_print("\nSUMMARY")
        safe_print(f"Total modules: {len(result_df)}")
        safe_print(
            "Modules with NaN module_score: "
            + (", ".join(nan_modules) if nan_modules else "none")
        )
        for module in MODULE_WEIGHTS:
            score = result_df.loc[
                result_df["module"].eq(module), "module_score"
            ].iloc[0]
            safe_print(
                f"{module} score: {score:.6f}"
                if not pd.isna(score)
                else f"{module} score: NaN"
            )
        safe_print("Fundamental Score has not been calculated.")
        safe_print(f"Saved to: {output_file.name}")

    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate module scores.")
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("start_year", type=int, help="First historical year")
    parser.add_argument("end_year", type=int, help="Current financial year")
    args = parser.parse_args()
    run_module_score(args.ticker, args.start_year, args.end_year)
