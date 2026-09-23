import math
import sys

import numpy as np
import pandas as pd


def safe_print(*args, **kwargs) -> None:
    """Print an toàn trên console Windows cp1252 (tránh crash vì ký tự Unicode như ≥)."""
    sep = kwargs.pop("sep", " ")
    end = kwargs.pop("end", "\n")
    file = kwargs.pop("file", None)
    flush = kwargs.pop("flush", False)
    text = sep.join(str(a) for a in args) + end
    stream = file if file is not None else sys.stdout
    try:
        stream.write(text)
        if flush:
            stream.flush()
    except UnicodeEncodeError:
        enc = getattr(stream, "encoding", None) or "ascii"
        stream.write(text.encode(enc, errors="replace").decode(enc, errors="replace"))
        if flush:
            stream.flush()


def validate_weights(weights, name="weights"):
    total = sum(weights.values())
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{name} sum to {total}, expected 1.0")


def normalize_available_weights(weights, values, multipliers=None):
    """Normalize configured weights over available components only.

    Multipliers express confidence, for example a LOW-quality peer component.
    Missing values receive no weight and are never converted to zero.
    """
    multipliers = multipliers or {}
    effective = {}
    unavailable = []
    discounted = []

    for component, base_weight in weights.items():
        value = values.get(component)
        if value is None or pd.isna(value):
            effective[component] = 0.0
            unavailable.append(component)
            continue
        multiplier = float(multipliers.get(component, 1.0))
        if multiplier < 0:
            raise ValueError(f"Negative confidence multiplier for {component}")
        effective[component] = float(base_weight) * multiplier
        if not math.isclose(multiplier, 1.0):
            discounted.append(component)

    total = sum(effective.values())
    if total <= 0:
        normalized = {component: 0.0 for component in weights}
        score = np.nan
    else:
        normalized = {
            component: effective_weight / total
            for component, effective_weight in effective.items()
        }
        score = sum(
            float(values[component]) * weight
            for component, weight in normalized.items()
            if weight > 0
        )
        score = float(np.clip(score, 0, 100))

    reasons = []
    if unavailable:
        reasons.append("unavailable=" + ",".join(unavailable))
    if discounted:
        reasons.append("discounted=" + ",".join(discounted))
    reason = "none" if not reasons else "; ".join(reasons)
    return score, normalized, reason
