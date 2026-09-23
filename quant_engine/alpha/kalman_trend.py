"""Kalman filter — ước lượng xu hướng (trend/slope) ẩn dưới nhiễu giá.

Tham chiếu: mục 9.3 (b) — Growth+Quality score nhân thêm vào alpha thô để ra
Alpha_effective. Dùng khi regime đang trending.

Model: local linear trend trên log giá
  l_t = l_(t-1) + b_(t-1) + eta_t
  b_t = b_(t-1) + zeta_t

P2-1: hỗ trợ ``init_state`` để cập nhật incremental (1 bước / phiên mới)
thay vì refit toàn bộ lịch sử mỗi ngày — tương đương bộ lọc mở rộng.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def _filter_matrices(process_var: float, obs_var: float):
    f = np.array([[1.0, 1.0], [0.0, 1.0]], dtype=float)
    h = np.array([[1.0, 0.0]], dtype=float)
    q = np.diag([process_var, process_var * 0.1])
    r = np.array([[obs_var]], dtype=float)
    eye = np.eye(2, dtype=float)
    return f, h, q, r, eye


def _kalman_step(
    y_t: float,
    x: np.ndarray,
    p: np.ndarray,
    *,
    f: np.ndarray,
    h: np.ndarray,
    q: np.ndarray,
    r: np.ndarray,
    eye: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, float, float, float]:
    """Một bước predict+update. Trả (x, P, level, slope, slope_var)."""
    x = f @ x
    p = f @ p @ f.T + q
    innovation = float(y_t) - float((h @ x)[0])
    s = h @ p @ h.T + r
    k = p @ h.T @ np.linalg.inv(s)
    x = x + (k.ravel() * innovation)
    p = (eye - k @ h) @ p
    level = float(x[0])
    slope = float(x[1])
    slope_var = max(float(p[1, 1]), 0.0)
    return x, p, level, slope, slope_var


def pack_kalman_state(x: np.ndarray, p: np.ndarray, n: int) -> dict[str, Any]:
    """State cache theo ticker (không key theo n_returns)."""
    return {
        "x": np.asarray(x, dtype=float).copy(),
        "P": np.asarray(p, dtype=float).copy(),
        "n": int(n),
    }


def fit_kalman_trend(
    log_price_series,
    *,
    process_var: float = 1e-5,
    obs_var: float = 1e-4,
    init_state: dict[str, Any] | None = None,
    return_state: bool = False,
):
    """Return (level, slope, slope_variance) arrays aligned with input.

    Input: log-price series (pandas Series or array). Units: log(VND).

    init_state:
        Optional ``{x, P, n}`` sau ``n`` quan sát đã lọc. Chỉ xử lý ``y[n:]`` —
        tương đương chạy lại từ đầu trên cùng chuỗi (Kalman đệ quy).
        Nếu ``n`` không khớp hoặc lệch → bỏ state, fit full.
    return_state:
        Nếu True, trả thêm dict state cuối để cache theo ticker.
    """
    series = pd.Series(log_price_series, dtype=float).dropna()
    y = series.to_numpy(dtype=float)
    n = len(y)
    if n < 2:
        raise ValueError("log_price_series needs at least 2 points")

    level = np.empty(n)
    slope = np.empty(n)
    slope_var = np.empty(n)
    f, h, q, r, eye = _filter_matrices(process_var, obs_var)

    start_t = 0
    x = np.array([y[0], 0.0], dtype=float)
    p = np.eye(2, dtype=float)

    if init_state is not None:
        try:
            n0 = int(init_state["n"])
            x0 = np.asarray(init_state["x"], dtype=float).reshape(2)
            p0 = np.asarray(init_state["P"], dtype=float).reshape(2, 2)
        except (KeyError, TypeError, ValueError):
            n0 = -1
            x0 = None
            p0 = None
        # Chỉ resume khi đã lọc đúng prefix và còn ≥1 điểm mới.
        if n0 >= 2 and n0 < n and x0 is not None and p0 is not None:
            start_t = n0
            x = x0.copy()
            p = p0.copy()
            # Phần đã lọc: không cần lịch sử đầy đủ trừ khi caller dùng OU —
            # điền NaN; caller Kalman-only chỉ lấy iloc[-1].
            level[:start_t] = np.nan
            slope[:start_t] = np.nan
            slope_var[:start_t] = np.nan

    for t in range(start_t, n):
        if t == 0 and start_t == 0:
            x = np.array([y[0], 0.0], dtype=float)
            p = np.eye(2, dtype=float)
        x, p, lv, sl, sv = _kalman_step(
            y[t], x, p, f=f, h=h, q=q, r=r, eye=eye
        )
        level[t] = lv
        slope[t] = sl
        slope_var[t] = sv

    index = series.index
    out = (
        pd.Series(level, index=index, name="level"),
        pd.Series(slope, index=index, name="slope"),
        pd.Series(slope_var, index=index, name="slope_variance"),
    )
    if return_state:
        return (*out, pack_kalman_state(x, p, n))
    return out


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
