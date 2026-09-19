"""Ornstein-Uhlenbeck mean reversion — dùng khi regime đang đi ngang.

Tham chiếu: mục "Alpha, đi ngang" trong tài liệu framework.
  dr = theta * (mu - r) dt + sigma dW
  half_life = ln(2) / theta

CHỈ áp dụng cho mã đã qua Fundamental Filter (PASS/WATCH) — không dùng OU
để bắt "dao rơi" của một mã đang xấu đi thật (value trap, xem mục 12.2).
"""

from __future__ import annotations


def fit_ou_process(residual_series):
    """Ước lượng theta, mu, sigma từ chuỗi residual (giá - trend Kalman)."""
    raise NotImplementedError


def ou_half_life(theta: float) -> float:
    """half_life = ln(2) / theta."""
    raise NotImplementedError
