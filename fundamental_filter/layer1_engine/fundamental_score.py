import argparse
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .fundamental_config import FUNDAMENTAL_MODULE_WEIGHTS
from .scoring_utils import safe_print


BASE_DIR = Path(__file__).resolve().parent

MODULE_WEIGHTS = FUNDAMENTAL_MODULE_WEIGHTS

OUTPUT_COLUMNS = [
    "ticker",
    "year",
    "growth_score",
    "quality_score",
    "safety_score",
    "valuation_score",
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
    "data_quality_flags",
    "critical_data_quality_flag",
    "fundamental_score",
    "available_module_count",
    "missing_modules",
]


def get_module_score_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"module_score_{ticker_lower}_{start_year}_{end_year}.csv"


def get_output_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"fundamental_score_{ticker_lower}_{start_year}_{end_year}.csv"


def validate_module_weights():
    total_weight = sum(MODULE_WEIGHTS.values())
    if not math.isclose(total_weight, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"Module weights sum to {total_weight}, expected 1.0")


def run_fundamental_score(
    ticker,
    start_year,
    end_year,
    module_df=None,
    persist=True,
):
    target_ticker = ticker.strip().upper()
    current_year = end_year
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    validate_module_weights()
    input_file = get_module_score_file(target_ticker, start_year, end_year)
    output_file = get_output_file(target_ticker, start_year, end_year)
    if module_df is None:
        module_df = pd.read_csv(input_file)
    else:
        module_df = module_df.copy()

    required_columns = {
        "ticker",
        "year",
        "module",
        "module_score",
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
    }
    missing_columns = required_columns.difference(module_df.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Module score CSV is missing required columns: {missing}")

    module_df["ticker"] = module_df["ticker"].astype(str).str.strip().str.upper()
    module_df = module_df.loc[
        module_df["ticker"].eq(target_ticker)
        & module_df["year"].eq(current_year)
    ].copy()
    module_df["module_score"] = pd.to_numeric(
        module_df["module_score"], errors="coerce"
    )

    if module_df["module"].duplicated().any():
        duplicates = module_df.loc[
            module_df["module"].duplicated(), "module"
        ].tolist()
        raise ValueError(f"Duplicate modules in module score CSV: {duplicates}")

    scores_by_module = module_df.set_index("module")["module_score"]
    module_scores = {
        module: scores_by_module.get(module, np.nan)
        for module in MODULE_WEIGHTS
    }
    missing_modules = [
        module for module, score in module_scores.items() if pd.isna(score)
    ]
    available_module_count = len(MODULE_WEIGHTS) - len(missing_modules)

    safety_rows = module_df.loc[module_df["module"].eq("SAFETY")]
    if len(safety_rows) != 1:
        raise ValueError(f"Expected one SAFETY module row, found {len(safety_rows)}")
    safety_row = safety_rows.iloc[0]
    valuation_rows = module_df.loc[module_df["module"].eq("VALUATION")]
    if len(valuation_rows) != 1:
        raise ValueError(
            f"Expected one VALUATION module row, found {len(valuation_rows)}"
        )
    valuation_row = valuation_rows.iloc[0]

    if missing_modules:
        fundamental_score = np.nan
    else:
        fundamental_score = sum(
            module_scores[module] * weight
            for module, weight in MODULE_WEIGHTS.items()
        )

    if not pd.isna(fundamental_score) and not 0 <= fundamental_score <= 100:
        raise ValueError(
            f"Fundamental score outside 0-100: {fundamental_score}"
        )

    data_quality_flags = []
    if missing_modules:
        data_quality_flags.append("MISSING_MODULES")
    if str(valuation_row["historical_valuation_available"]).lower() != "true":
        data_quality_flags.append("HISTORICAL_VALUATION_UNAVAILABLE")
    if str(valuation_row["peer_quality"]).upper() == "LOW":
        data_quality_flags.append("LOW_PEER_QUALITY")
    critical_data_quality_flag = bool(missing_modules)

    row = {
        "ticker": target_ticker,
        "year": current_year,
        "growth_score": module_scores["GROWTH"],
        "quality_score": module_scores["QUALITY"],
        "safety_score": module_scores["SAFETY"],
        "valuation_score": module_scores["VALUATION"],
        "absolute_safety_score": safety_row["absolute_safety_score"],
        "peer_relative_score": safety_row["peer_relative_score"],
        "safety_trend_score": safety_row["safety_trend_score"],
        "safety_gate_status": safety_row["safety_gate_status"],
        "safety_component_weights_used": safety_row[
            "safety_component_weights_used"
        ],
        "safety_reweight_reason": safety_row["safety_reweight_reason"],
        "peer_valuation_score": valuation_row["peer_valuation_score"],
        "historical_valuation_score": valuation_row[
            "historical_valuation_score"
        ],
        "historical_valuation_available": valuation_row[
            "historical_valuation_available"
        ],
        "historical_valuation_reason": valuation_row[
            "historical_valuation_reason"
        ],
        "fundamental_context_score": valuation_row[
            "fundamental_context_score"
        ],
        "valuation_component_weights_used": valuation_row[
            "valuation_component_weights_used"
        ],
        "valuation_reweight_reason": valuation_row[
            "valuation_reweight_reason"
        ],
        "peer_method": valuation_row["peer_method"],
        "peer_quality": valuation_row["peer_quality"],
        "peer_count": valuation_row["peer_count"],
        "peer_warning": valuation_row["peer_warning"],
        "data_quality_flags": "|".join(data_quality_flags),
        "critical_data_quality_flag": critical_data_quality_flag,
        "fundamental_score": fundamental_score,
        "available_module_count": available_module_count,
        "missing_modules": ", ".join(missing_modules),
    }
    result_df = pd.DataFrame([row], columns=OUTPUT_COLUMNS)
    if persist:
        result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    # persist=False = đường batch/backtest: không dump bảng (spam + crash cp1252).
    if persist:
        printed_df = result_df.copy()
        printed_df["missing_modules"] = printed_df["missing_modules"].replace(
            "", "none"
        )
        safe_print(printed_df.to_string(index=False))

        safe_print("\nSUMMARY")
        safe_print(f"Growth Score: {row['growth_score']:.6f}")
        safe_print(f"Quality Score: {row['quality_score']:.6f}")
        safe_print(f"Safety Score: {row['safety_score']:.6f}")
        safe_print(f"Valuation Score: {row['valuation_score']:.6f}")
        safe_print(
            f"Fundamental Score: {fundamental_score:.6f}"
            if not pd.isna(fundamental_score)
            else "Fundamental Score: NaN"
        )
        safe_print(
            "All four modules available: "
            + ("yes" if available_module_count == 4 else "no")
        )
        safe_print(
            "Safety Gate is diagnostic; classification is computed downstream."
        )
        safe_print(f"Saved to: {output_file.name}")

    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate the fundamental score.")
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("start_year", type=int, help="First historical year")
    parser.add_argument("end_year", type=int, help="Current financial year")
    args = parser.parse_args()
    run_fundamental_score(args.ticker, args.start_year, args.end_year)
