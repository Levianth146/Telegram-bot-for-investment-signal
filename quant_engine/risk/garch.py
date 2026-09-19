"""GARCH/GJR-GARCH — dự báo biến động có điều kiện.

Tham chiếu: mục "Risk" trong tài liệu framework.
  sigma^2_t = omega + (alpha + gamma*1[eps<0]) * eps^2_(t-1) + beta * sigma^2_(t-1)

Dùng thư viện `arch` (pip install arch). Lưu ý: biên độ +-7% của HOSE làm cắt
cụt return quan sát được, nên vol có thể bị đánh giá thấp — cần lưu ý khi diễn giải.
"""

from __future__ import annotations


def fit_gjr_garch(returns_series):
    """Fit GJR-GARCH(1,1), trả về model đã fit."""
    raise NotImplementedError


def forecast_sigma(model, horizon: int = 1) -> float:
    """Dự báo sigma_hat cho phiên tiếp theo — ghi vào store.signals.sigma_hat."""
    raise NotImplementedError


def position_size(sigma_hat: float, sigma_target: float, w_max: float = 0.1) -> float:
    """size = min(w_max, sigma_target / sigma_hat)."""
    raise NotImplementedError


def stop_loss_price(entry_price: float, sigma_hat: float, k: float = 2.0) -> float:
    """stop = entry_price * (1 - k * sigma_hat)."""
    raise NotImplementedError
