"""Black-Litterman — phân bổ danh mục kết hợp baseline thị trường + view riêng.

Tham chiếu: mục 9.4 — Valuation score (Margin of Safety, P/E vs median) tạo
thêm một view độc lập với view từ Alpha (Kalman/momentum). Đây là P1 — nếu
tắt trong pipeline/config.yaml, fallback về equal-weight/fixed sizing
(KHÔNG được crash pipeline).

  mu_BL = [(tau*Sigma)^-1 + P'*Omega^-1*P]^-1 * [(tau*Sigma)^-1*pi + P'*Omega^-1*Q]
"""

from __future__ import annotations


def build_views(alpha_signals: dict, valuation_signals: dict) -> tuple:
    """Ghép view từ Alpha và view từ Valuation thành ma trận P, vector Q, Omega.

    Xem mục 9.4: hai phép so sánh 5.6 (historical/peer) lệch nhau -> giảm độ
    tin cậy Omega thay vì bỏ view.
    """
    raise NotImplementedError


def black_litterman_weights(market_caps, cov_matrix, P, Q, Omega, tau: float = 0.05):
    """Trả về vector trọng số danh mục theo Black-Litterman."""
    raise NotImplementedError


def equal_weight_fallback(tickers: list[str]) -> dict:
    """Fallback khi portfolio_black_litterman.enabled = false (mục 11.1, P1 có thể tắt)."""
    raise NotImplementedError
