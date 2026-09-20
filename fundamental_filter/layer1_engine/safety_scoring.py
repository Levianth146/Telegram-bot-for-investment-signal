import math

import numpy as np
import pandas as pd

from fundamental_config import (
    ABSOLUTE_SAFETY_WEIGHTS,
    FINAL_SAFETY_WEIGHTS,
    PEER_QUALITY_MULTIPLIERS,
    SAFETY_ANCHORS,
    SAFETY_GATE_THRESHOLDS,
)
from scoring_utils import normalize_available_weights


PEER_SAFETY_WEIGHTS = ABSOLUTE_SAFETY_WEIGHTS.copy()
TREND_SAFETY_WEIGHTS = ABSOLUTE_SAFETY_WEIGHTS.copy()


def _is_missing(value):
    return value is None or pd.isna(value)


def validate_safety_weights():
    for name, weights in (
        ("absolute", ABSOLUTE_SAFETY_WEIGHTS),
        ("peer", PEER_SAFETY_WEIGHTS),
        ("trend", TREND_SAFETY_WEIGHTS),
        ("final", FINAL_SAFETY_WEIGHTS),
    ):
        total = sum(weights.values())
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
            raise ValueError(f"Safety {name} weights sum to {total}, expected 1.0")


def score_from_anchors(value, anchors):
    """Piecewise-linear interpolation with output clamped to 0-100."""
    if _is_missing(value):
        return np.nan

    numeric_value = float(value)
    ordered = sorted((float(x), float(score)) for x, score in anchors)
    if numeric_value <= ordered[0][0]:
        return float(np.clip(ordered[0][1], 0, 100))
    if numeric_value >= ordered[-1][0]:
        return float(np.clip(ordered[-1][1], 0, 100))

    for (left_x, left_score), (right_x, right_score) in zip(
        ordered, ordered[1:]
    ):
        if left_x <= numeric_value <= right_x:
            fraction = (numeric_value - left_x) / (right_x - left_x)
            score = left_score + fraction * (right_score - left_score)
            return float(np.clip(score, 0, 100))

    raise ValueError("Unable to interpolate safety score")


def calculate_absolute_metric_score(metric, raw_value):
    if metric not in SAFETY_ANCHORS:
        raise ValueError(f"Unknown Safety metric: {metric}")
    if _is_missing(raw_value):
        return np.nan
    if metric == "debt_to_equity" and float(raw_value) < 0:
        return np.nan
    return score_from_anchors(raw_value, SAFETY_ANCHORS[metric])


def weighted_score(values, weights):
    """Strict weighted score: no zero fill and no weight renormalization."""
    missing = [metric for metric in weights if _is_missing(values.get(metric))]
    if missing:
        return np.nan
    score = sum(float(values[metric]) * weight for metric, weight in weights.items())
    return float(np.clip(score, 0, 100))


def calculate_safety_components(
    raw_values, peer_scores, trend_scores, peer_quality="HIGH"
):
    validate_safety_weights()
    absolute_metric_scores = {
        metric: calculate_absolute_metric_score(metric, raw_values.get(metric))
        for metric in ABSOLUTE_SAFETY_WEIGHTS
    }
    absolute_safety_score = weighted_score(
        absolute_metric_scores, ABSOLUTE_SAFETY_WEIGHTS
    )
    peer_relative_score = weighted_score(peer_scores, PEER_SAFETY_WEIGHTS)
    safety_trend_score = weighted_score(trend_scores, TREND_SAFETY_WEIGHTS)
    components = {
        "absolute_safety_score": absolute_safety_score,
        "peer_relative_score": peer_relative_score,
        "safety_trend_score": safety_trend_score,
    }
    safety_score, weights_used, reweight_reason = normalize_available_weights(
        FINAL_SAFETY_WEIGHTS,
        components,
        {
            "peer_relative_score": PEER_QUALITY_MULTIPLIERS.get(
                str(peer_quality).upper(), 0.0
            )
        },
    )
    if pd.isna(absolute_safety_score):
        safety_score = np.nan
        reweight_reason = (
            "absolute_safety_score is required; " + reweight_reason
        )
    return {
        "absolute_metric_scores": absolute_metric_scores,
        **components,
        "safety_score": safety_score,
        "safety_component_weights_used": weights_used,
        "safety_reweight_reason": reweight_reason,
    }


def get_safety_gate_status(raw_values, equity=None):
    interest_coverage = raw_values.get("interest_coverage")
    if not _is_missing(equity) and float(equity) <= 0:
        return "CRITICAL"
    if (
        not _is_missing(interest_coverage)
        and float(interest_coverage)
        < SAFETY_GATE_THRESHOLDS["critical_interest_coverage"]
    ):
        return "CRITICAL"

    high_risk_conditions = [
        (
            not _is_missing(raw_values.get("net_debt_to_ebitda"))
            and float(raw_values["net_debt_to_ebitda"])
            > SAFETY_GATE_THRESHOLDS["high_risk_net_debt_to_ebitda"]
        ),
        (
            not _is_missing(raw_values.get("debt_to_equity"))
            and float(raw_values["debt_to_equity"])
            > SAFETY_GATE_THRESHOLDS["high_risk_debt_to_equity"]
        ),
        (
            not _is_missing(raw_values.get("cfo_to_debt"))
            and float(raw_values["cfo_to_debt"])
            < SAFETY_GATE_THRESHOLDS["high_risk_cfo_to_debt"]
        ),
        (
            not _is_missing(interest_coverage)
            and float(interest_coverage)
            < SAFETY_GATE_THRESHOLDS["high_risk_interest_coverage"]
        ),
    ]
    return (
        "HIGH_RISK"
        if sum(high_risk_conditions)
        >= SAFETY_GATE_THRESHOLDS["high_risk_condition_count"]
        else "NORMAL"
    )
