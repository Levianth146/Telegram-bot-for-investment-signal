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


def fit_hawkes(event_timestamps) -> dict:
    """Ước lượng mu, alpha, beta bằng MLE. Trả về {"mu":.., "alpha":.., "beta":..}."""
    raise NotImplementedError


def branching_ratio(alpha: float, beta: float) -> float:
    """n = alpha / beta."""
    return alpha / beta


def crowding_size_multiplier(n: float, n_max: float = 0.9) -> float:
    """Giảm size khi n tiến gần n_max — xem mục 9.5 (Safety/Merton DD -> risk overlay,
    Hawkes áp dụng cùng nguyên tắc 'g giảm dần' cho crowding).
    """
    raise NotImplementedError
