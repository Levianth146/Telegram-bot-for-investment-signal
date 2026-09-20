"""Hawkes process — bộ lọc crowding (đám đông tự kích hoạt chính nó).

Tham chiếu: mục 9.5 và lớp 6 trong tài liệu framework. P2 — chỉ bật sau khi
docs/DATA_AUDIT.md xác nhận có đủ dữ liệu sự kiện (volume spike, chạm trần)
theo ngày (lý tưởng là intraday).

  lambda(t) = mu + sum(alpha * exp(-beta*(t - t_i)))
  branching_ratio n = alpha / beta

n tiến gần 1 => thị trường đang tự kích hoạt chính nó (rủi ro đảo chiều),
không phải phản ứng với thông tin mới từ bên ngoài.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np
import pandas as pd


def fit_hawkes(event_timestamps: Sequence[float]) -> dict[str, float]:
    """Estimate μ, α, β via a simple moment/OLS proxy (V1, no heavy MLE dependency).

    ``event_timestamps`` are sorted times in a common unit (e.g. day index).
    Falls back to a low branching ratio when too few events.
    """
    times = np.asarray(sorted(float(t) for t in event_timestamps), dtype=float)
    if len(times) < 5:
        return {"mu": 0.01, "alpha": 0.05, "beta": 0.5, "n_events": float(len(times))}

    # Inter-event gaps → coarse intensity / excitation proxy
    gaps = np.diff(times)
    gaps = gaps[gaps > 0]
    if len(gaps) == 0:
        return {"mu": 0.01, "alpha": 0.05, "beta": 0.5, "n_events": float(len(times))}

    mean_gap = float(np.mean(gaps))
    mu = 1.0 / max(mean_gap, 1e-6)
    # Short gaps relative to mean → self-excitation
    short = gaps[gaps < mean_gap]
    frac_short = float(len(short) / len(gaps))
    beta = 1.0 / max(float(np.median(gaps)), 1e-6)
    alpha = float(np.clip(frac_short * beta * 0.8, 0.0, beta * 0.95))
    return {
        "mu": float(mu),
        "alpha": float(alpha),
        "beta": float(beta),
        "n_events": float(len(times)),
    }


def branching_ratio(alpha: float, beta: float) -> float:
    """n = alpha / beta."""
    if beta <= 0:
        return 1.0
    return float(alpha / beta)


def crowding_size_multiplier(n: float, n_max: float = 0.9) -> float:
    """Giảm size khi n tiến gần n_max — mục 9.5 crowding overlay.

    n ≤ 0 → 1.0; n ≥ n_max → 0.0; linear decay in between.
    """
    if n_max <= 0:
        return 1.0
    if n <= 0:
        return 1.0
    if n >= n_max:
        return 0.0
    return float(max(0.0, 1.0 - float(n) / float(n_max)))


def fit_hawkes_from_returns(
    returns: pd.Series,
    *,
    spike_z: float = 2.0,
) -> dict[str, float]:
    """Build spike-event times from |return| z-scores, then fit Hawkes + branching ratio."""
    rets = pd.to_numeric(returns, errors="coerce").dropna()
    if len(rets) < 30:
        fitted = fit_hawkes([])
        fitted["branching_ratio"] = branching_ratio(fitted["alpha"], fitted["beta"])
        return fitted

    z = (rets - rets.mean()) / (rets.std(ddof=1) or 1.0)
    event_idx = np.flatnonzero(np.abs(z.to_numpy()) >= spike_z).astype(float)
    fitted = fit_hawkes(event_idx.tolist())
    fitted["branching_ratio"] = branching_ratio(fitted["alpha"], fitted["beta"])
    return fitted
