"""Ornstein-Uhlenbeck mean reversion — dùng khi regime đang đi ngang.

Tham chiếu: mục "Alpha, đi ngang" trong tài liệu framework.
  dr = theta * (mu - r) dt + sigma dW
  half_life = ln(2) / theta

CHỈ áp dụng cho mã đã qua Fundamental Filter (PASS/WATCH) — không dùng OU
để bắt "dao rơi" của mã đang xấu đi thật (value trap, mục 12.2).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def fit_ou_process(residual_series) -> dict:
    """Estimate theta, mu, sigma from residual series (price − Kalman level).

    Discrete AR(1): r_t = a + b * r_{t-1} + e_t
      theta = 1 - b
      mu = a / theta
      sigma = std(e)
    """
    series = pd.Series(residual_series, dtype=float).dropna()
    if len(series) < 10:
        return {"theta": float("nan"), "mu": float("nan"), "sigma": float("nan")}

    x = series.iloc[:-1].to_numpy(dtype=float)
    y = series.iloc[1:].to_numpy(dtype=float)
    # y = b*x + a
    b, a = np.polyfit(x, y, 1)
    theta = 1.0 - float(b)
    if abs(theta) < 1e-8:
        mu = float("nan")
    else:
        mu = float(a) / theta
    resid = y - (a + b * x)
    sigma = float(np.std(resid, ddof=1)) if len(resid) > 1 else float("nan")
    return {"theta": float(theta), "mu": mu, "sigma": sigma}


def ou_half_life(theta: float) -> float:
    """half_life = ln(2) / theta (sessions). Requires theta > 0."""
    if theta is None or pd.isna(theta) or float(theta) <= 0:
        raise ValueError("theta must be positive for a finite OU half-life")
    return math.log(2) / float(theta)
