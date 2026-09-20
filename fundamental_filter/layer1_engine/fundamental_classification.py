import argparse
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .fundamental_config import CLASSIFICATION_CONFIG


BASE_DIR = Path(__file__).resolve().parent

OUTPUT_COLUMNS = [
    "ticker",
    "year",
    "fundamental_score",
    "fundamental_percentile",
    "growth_score",
    "quality_score",
    "safety_score",
    "valuation_score",
    "safety_gate_status",
    "classification",
    "classification_reason",
    "classification_flags",
    "classification_mode",
    "percentile_used_for_classification",
    "classification_universe_size",
    "classification_as_of_date",
]


def _as_bool(value):
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def classify_fundamental_universe(universe_df, as_of_date=None, config=None):
    """Classify current-run universe into PASS/WATCH/FAIL (framework mục 10).

    ``config`` overrides CLASSIFICATION_CONFIG; prefer ``load_scoring_config()``
    so thresholds stay synced with pipeline/config.yaml.
    """
    cfg = config or CLASSIFICATION_CONFIG
    data = universe_df.copy()
    required = {
        "ticker",
        "year",
        "growth_score",
        "quality_score",
        "safety_score",
        "valuation_score",
        "fundamental_score",
        "safety_gate_status",
        "critical_data_quality_flag",
        "data_quality_flags",
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError(
            "Classification input is missing columns: "
            + ", ".join(sorted(missing))
        )

    data["ticker"] = data["ticker"].astype(str).str.strip().str.upper()
    if data["ticker"].duplicated().any():
        duplicates = data.loc[data["ticker"].duplicated(), "ticker"].tolist()
        raise ValueError(f"Duplicate classification tickers: {duplicates}")
    score_columns = [
        "growth_score",
        "quality_score",
        "safety_score",
        "valuation_score",
        "fundamental_score",
    ]
    for column in score_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    complete = data[score_columns].notna().all(axis=1)
    critical_gate = data["safety_gate_status"].eq("CRITICAL")
    critical_quality = data["critical_data_quality_flag"].map(_as_bool)
    eligible = complete & ~critical_gate & ~critical_quality
    eligible_count = int(eligible.sum())

    data["fundamental_percentile"] = np.nan
    if eligible_count >= 2:
        ranks = data.loc[eligible, "fundamental_score"].rank(
            method="average", ascending=True
        )
        data.loc[eligible, "fundamental_percentile"] = (
            (ranks - 1) / (eligible_count - 1) * 100
        ).clip(0, 100)

    pass_threshold = cfg["pass_percentile"] * 100
    watch_threshold = cfg["watch_percentile"] * 100
    absolute_pass_score = cfg["absolute_pass_score"]
    absolute_watch_score = cfg["absolute_watch_score"]
    module_floor = cfg["min_module_score_for_pass"]
    classification_mode = (
        "PERCENTILE"
        if eligible_count >= cfg["min_percentile_universe"]
        else "ABSOLUTE_FALLBACK"
    )
    classifications = []
    reasons = []
    all_flags = []
    percentile_usage = []

    for row in data.itertuples(index=False):
        flags = [
            flag
            for flag in str(row.data_quality_flags).split("|")
            if flag and flag.lower() != "nan"
        ]
        module_values = [
            row.growth_score,
            row.quality_score,
            row.safety_score,
            row.valuation_score,
        ]
        has_missing_data = (
            any(pd.isna(value) for value in module_values)
            or pd.isna(row.fundamental_score)
            or _as_bool(row.critical_data_quality_flag)
        )
        percentile_used = False

        if row.safety_gate_status == "CRITICAL":
            classification = "FAIL"
            reason = "SAFETY_CRITICAL"
            flags.append("SAFETY_CRITICAL")
        elif has_missing_data:
            classification = "WATCH"
            reason = "INSUFFICIENT_DATA"
            flags.append("INSUFFICIENT_DATA")
        else:
            module_floor_met = all(value >= module_floor for value in module_values)
            hist_available = True
            if "historical_valuation_available" in data.columns:
                hist_available = _as_bool(
                    getattr(row, "historical_valuation_available", True)
                )
            if classification_mode == "PERCENTILE":
                percentile_used = True
                if pd.isna(row.fundamental_percentile):
                    classification = "WATCH"
                    reason = "INSUFFICIENT_CLASSIFICATION_UNIVERSE"
                    flags.append("INSUFFICIENT_CLASSIFICATION_UNIVERSE")
                    percentile_used = False
                elif row.fundamental_percentile < watch_threshold:
                    classification = "FAIL"
                    reason = "BELOW_WATCH_PERCENTILE"
                elif row.safety_gate_status == "HIGH_RISK":
                    classification = "WATCH"
                    reason = "SAFETY_HIGH_RISK"
                    flags.append("SAFETY_HIGH_RISK")
                elif (
                    row.fundamental_percentile >= pass_threshold
                    and module_floor_met
                    and hist_available
                ):
                    classification = "PASS"
                    reason = "PASS_THRESHOLDS_MET"
                elif (
                    row.fundamental_percentile >= pass_threshold
                    and module_floor_met
                    and not hist_available
                ):
                    classification = "WATCH"
                    reason = "HISTORICAL_VALUATION_UNAVAILABLE"
                    flags.append("HISTORICAL_VALUATION_UNAVAILABLE")
                elif row.fundamental_percentile >= pass_threshold:
                    classification = "WATCH"
                    reason = "MODULE_FLOOR_NOT_MET"
                    flags.append("MODULE_FLOOR_NOT_MET")
                else:
                    classification = "WATCH"
                    reason = "MIDDLE_PERCENTILE"
            elif row.fundamental_score < absolute_watch_score:
                classification = "FAIL"
                reason = "BELOW_ABSOLUTE_WATCH_SCORE"
            elif row.safety_gate_status == "HIGH_RISK":
                classification = "WATCH"
                reason = "SAFETY_HIGH_RISK"
                flags.append("SAFETY_HIGH_RISK")
            elif (
                row.fundamental_score >= absolute_pass_score
                and module_floor_met
                and hist_available
            ):
                classification = "PASS"
                reason = "ABSOLUTE_PASS_THRESHOLDS_MET"
            elif (
                row.fundamental_score >= absolute_pass_score
                and module_floor_met
                and not hist_available
            ):
                classification = "WATCH"
                reason = "HISTORICAL_VALUATION_UNAVAILABLE"
                flags.append("HISTORICAL_VALUATION_UNAVAILABLE")
            elif row.fundamental_score >= absolute_pass_score:
                classification = "WATCH"
                reason = "MODULE_FLOOR_NOT_MET"
                flags.append("MODULE_FLOOR_NOT_MET")
            else:
                classification = "WATCH"
                reason = "ABSOLUTE_WATCH_RANGE"

        classifications.append(classification)
        reasons.append(reason)
        all_flags.append("|".join(dict.fromkeys(flags)))
        percentile_usage.append(percentile_used)

    data["classification"] = classifications
    data["classification_reason"] = reasons
    data["classification_flags"] = all_flags
    data["classification_mode"] = classification_mode
    data["percentile_used_for_classification"] = percentile_usage
    data["classification_universe_size"] = eligible_count
    data["classification_as_of_date"] = str(as_of_date or date.today())
    return data[OUTPUT_COLUMNS]


def get_output_file(start_year, end_year):
    return BASE_DIR / f"fundamental_classification_{start_year}_{end_year}.csv"


def run_fundamental_classification(
    start_year, end_year, universe_df, persist=True
):
    """Classify an explicit current-run universe; never scan old artifacts."""
    if universe_df is None or universe_df.empty:
        raise ValueError("Current-run Fundamental Score universe is required")
    result = classify_fundamental_universe(universe_df)
    output_file = get_output_file(start_year, end_year)
    if persist:
        result.to_csv(output_file, index=False, encoding="utf-8-sig")
    print(result.to_string(index=False))
    print("\nCLASSIFICATION COUNTS")
    print(result["classification"].value_counts().to_string())
    if persist:
        print(f"Saved to: {output_file.name}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify Fundamental universe.")
    parser.add_argument("start_year", type=int)
    parser.add_argument("end_year", type=int)
    parser.add_argument("input_csv", help="Explicit current-run Fundamental Score CSV")
    args = parser.parse_args()
    run_fundamental_classification(
        args.start_year, args.end_year, pd.read_csv(args.input_csv)
    )
