"""Monte Carlo (filtered historical simulation) — xác suất hóa tín hiệu.

Tham chiếu: mục "Monte Carlo" trong tài liệu framework.
Bootstrap residual chuẩn hóa z_t = eps_t / sigma_t từ GARCH, nhân lại với
sigma_hat dự báo, clip +-7% (biên độ HOSE), mô phỏng ~10,000 đường.

Output feed vào store.signals.p_tp_before_sl và cvar95 — đây là câu
"P(+8% trước -4.7% trong 10 phiên) = 57%" trong tin nhắn bot (mục 1.3 README bot).
"""

from __future__ import annotations


def simulate_price_paths(
    entry_price: float,
    sigma_hat: float,
    historical_residuals,
    horizon_days: int = 10,
    n_paths: int = 10_000,
    price_limit_pct: float = 0.07,
):
    """Trả về mảng (n_paths, horizon_days) đường giá mô phỏng."""
    raise NotImplementedError


def probability_tp_before_sl(paths, entry_price: float, tp_pct: float, sl_pct: float) -> float:
    """% kịch bản chạm TP trước khi chạm SL."""
    raise NotImplementedError


def cvar(paths, entry_price: float, alpha: float = 0.95) -> float:
    """Conditional Value at Risk ở mức alpha (CVaR95)."""
    raise NotImplementedError
