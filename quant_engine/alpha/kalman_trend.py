"""Kalman filter — ước lượng xu hướng (trend/slope) ẩn dưới nhiễu giá.

Tham chiếu: mục 9.3 (b) — Growth+Quality score nhân thêm vào alpha thô để ra
Alpha_effective. Dùng khi regime đang trending.

Model: local linear trend trên log giá
  l_t = l_(t-1) + b_(t-1) + eta_t
  b_t = b_(t-1) + zeta_t
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def fit_kalman_trend(
    log_price_series,
    *,
    process_var: float = 1e-5,
    obs_var: float = 1e-4,
):
    """Return (level, slope, slope_variance) arrays aligned with input.

    Input: log-price series (pandas Series or array). Units: log(VND).
    """
    series = pd.Series(log_price_series, dtype=float).dropna()
    y = series.to_numpy(dtype=float)
    n = len(y)
    if n < 2:
        raise ValueError("log_price_series needs at least 2 points")

    level = np.empty(n)
    slope = np.empty(n)
    slope_var = np.empty(n)

    x = np.array([y[0], 0.0], dtype=float)
    p = np.eye(2, dtype=float)
    f = np.array([[1.0, 1.0], [0.0, 1.0]], dtype=float)
    h = np.array([[1.0, 0.0]], dtype=float)
    q = np.diag([process_var, process_var * 0.1])
    r = np.array([[obs_var]], dtype=float)
    eye = np.eye(2, dtype=float)

    for t in range(n):
        x = f @ x
        p = f @ p @ f.T + q
        innovation = y[t] - float((h @ x)[0])
        s = h @ p @ h.T + r
        k = p @ h.T @ np.linalg.inv(s)
        x = x + (k.ravel() * innovation)
        p = (eye - k @ h) @ p
        level[t] = x[0]
        slope[t] = x[1]
        slope_var[t] = max(float(p[1, 1]), 0.0)

    index = series.index
    return (
        pd.Series(level, index=index, name="level"),
        pd.Series(slope, index=index, name="slope"),
        pd.Series(slope_var, index=index, name="slope_variance"),
    )


def slope_tstat(slope: float, slope_variance: float) -> float:
    """t-stat of Kalman slope — proxy for trend strength (framework mục 9.7)."""
    if slope_variance is None or slope_variance <= 0 or pd.isna(slope_variance):
        return float("nan")
    return float(slope) / float(np.sqrt(slope_variance))


def alpha_effective(
    alpha_raw: float, growth_score: float, quality_score: float
) -> float:
    """Mục 9.3 — Alpha_effective = Alpha_raw * f(Growth, Quality).

    f is monotone in the average of Growth/Quality scores (0–100 scale),
    clipped to [0.5, 1.5] so fundamentals cannot dominate price alpha.
    Missing scores → f = 1.0 (neutral).
    """
    if alpha_raw is None or pd.isna(alpha_raw):
        return float("nan")
    if (
        growth_score is None
        or quality_score is None
        or pd.isna(growth_score)
        or pd.isna(quality_score)
    ):
        factor = 1.0
    else:
        avg = (float(growth_score) + float(quality_score)) / 2.0
        factor = 0.5 + avg / 100.0
        factor = float(np.clip(factor, 0.5, 1.5))
    return float(alpha_raw) * factor
