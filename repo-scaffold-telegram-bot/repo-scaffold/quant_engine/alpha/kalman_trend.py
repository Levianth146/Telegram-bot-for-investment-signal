"""Kalman filter — ước lượng xu hướng (trend/slope) ẩn dưới nhiễu giá.

Tham chiếu: mục 9.3 (b) — Growth+Quality score nhân thêm vào alpha thô để ra
Alpha_effective. Dùng khi regime đang trending.

Model: local linear trend trên log giá
  l_t = l_(t-1) + b_(t-1) + eta_t
  b_t = b_(t-1) + zeta_t
"""

from __future__ import annotations


def fit_kalman_trend(log_price_series):
    """Trả về (level, slope, slope_variance) theo thời gian."""
    raise NotImplementedError


def alpha_effective(alpha_raw: float, growth_score: float, quality_score: float) -> float:
    """Mục 9.3 — Alpha_effective = Alpha_raw * f(Growth score, Quality score).

    f là hàm tăng đơn điệu, giới hạn trong [0.5, 1.5] để không lấn át tín hiệu giá.
    """
    raise NotImplementedError
