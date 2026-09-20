from datetime import date, datetime

import numpy as np
import pandas as pd

from .fundamental_config import (
    PEER_QUALITY_MULTIPLIERS,
    VALUATION_COMPONENT_WEIGHTS,
    VALUATION_METRIC_WEIGHTS,
)
from .scoring_utils import normalize_available_weights, validate_weights


LOWER_IS_BETTER = {"pe", "pb", "ev_to_ebitda"}
HIGHER_IS_BETTER = {"fcf_yield"}
MIN_HISTORICAL_OBSERVATIONS = 4


def _to_date(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)).date()


def calculate_peer_valuation_score(peer_metric_scores):
    validate_weights(VALUATION_METRIC_WEIGHTS, "valuation metric weights")
    values = {
        metric: peer_metric_scores.get(metric)
        for metric in VALUATION_METRIC_WEIGHTS
    }
    if any(value is None or pd.isna(value) for value in values.values()):
        return np.nan
    return float(
        sum(values[metric] * weight for metric, weight in VALUATION_METRIC_WEIGHTS.items())
    )


def is_point_in_time_observation(record, as_of_date):
    cutoff = _to_date(as_of_date)
    if not bool(record.get("point_in_time_safe")):
        return False
    observation_date = _to_date(record.get("observation_date"))
    required_dates = [
        _to_date(record.get("price_date")),
        _to_date(record.get("shares_date")),
        _to_date(record.get("financial_publication_date")),
    ]
    return (
        observation_date is not None
        and observation_date <= cutoff
        and all(value is not None and value <= observation_date for value in required_dates)
    )


def calculate_historical_valuation_score(
    current_values, observations, as_of_date, min_observations=MIN_HISTORICAL_OBSERVATIONS
):
    valid = [
        record
        for record in observations
        if is_point_in_time_observation(record, as_of_date)
    ]
    metric_scores = {}
    for metric in VALUATION_METRIC_WEIGHTS:
        current = current_values.get(metric)
        history = pd.to_numeric(
            pd.Series([record.get(metric) for record in valid]), errors="coerce"
        ).dropna()
        if current is None or pd.isna(current) or len(history) < min_observations:
            metric_scores[metric] = np.nan
            continue
        combined = pd.concat(
            [history.reset_index(drop=True), pd.Series([float(current)])],
            ignore_index=True,
        )
        ascending = metric in HIGHER_IS_BETTER
        ranks = combined.rank(method="average", ascending=ascending)
        metric_scores[metric] = float(
            (ranks.iloc[-1] - 1) / (len(combined) - 1) * 100
        )

    available = {
        metric: score
        for metric, score in metric_scores.items()
        if not pd.isna(score)
    }
    if not available:
        return np.nan, metric_scores, len(valid)
    weights = {metric: VALUATION_METRIC_WEIGHTS[metric] for metric in available}
    total = sum(weights.values())
    score = sum(available[metric] * weights[metric] / total for metric in available)
    return float(np.clip(score, 0, 100)), metric_scores, len(valid)


def calculate_valuation_components(
    peer_valuation_score,
    historical_valuation_score=None,
    fundamental_context_score=None,
    peer_quality="HIGH",
):
    validate_weights(VALUATION_COMPONENT_WEIGHTS, "valuation component weights")
    values = {
        "peer": peer_valuation_score,
        "historical": historical_valuation_score,
        "fundamental_context": fundamental_context_score,
    }
    score, weights_used, reason = normalize_available_weights(
        VALUATION_COMPONENT_WEIGHTS,
        values,
        {
            "peer": PEER_QUALITY_MULTIPLIERS.get(
                str(peer_quality).upper(), 0.0
            )
        },
    )
    return {
        "peer_valuation_score": peer_valuation_score,
        "historical_valuation_score": historical_valuation_score,
        "fundamental_context_score": fundamental_context_score,
        "valuation_score": score,
        "valuation_component_weights_used": weights_used,
        "valuation_reweight_reason": reason,
        "historical_valuation_available": not pd.isna(
            historical_valuation_score
        ),
    }
