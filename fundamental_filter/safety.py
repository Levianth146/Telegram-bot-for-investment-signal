"""Module Safety — Câu hỏi 3: Doanh nghiệp có an toàn tài chính không?

Tham chiếu: Mục 4 (Current/Quick/Cash Ratio, D/E, Net Debt/EBITDA,
Interest Coverage, DSO/DIO, và Merton Distance-to-Default ở mục 4.6 — P2,
chỉ bật sau khi qua docs/DATA_AUDIT.md).
"""

from __future__ import annotations


def net_debt_to_ebitda(net_debt: float, ebitda: float) -> float:
    """Mục 4.2 — headline metric của module Safety (xem mục 6.1)."""
    raise NotImplementedError


def interest_coverage(ebit: float, interest_expense: float) -> float:
    """Mục 4.3 — supporting metric, chỉ nói khi Net Debt/EBITDA đang xấu đi."""
    raise NotImplementedError


def merton_distance_to_default(
    equity_value: float,
    equity_vol: float,
    debt_face_value: float,
    risk_free_rate: float,
    horizon_years: float = 1.0,
) -> float:
    """Mục 4.6 (P2, ADVANCED) — Distance-to-Default theo Bharath & Shumway (2008).

    CHỈ bật khi pipeline/config.yaml có safety_merton_dd.enabled = true (sau
    khi audit dữ liệu nợ ở docs/DATA_AUDIT.md xác nhận khả thi). Nếu tắt,
    hàm gọi ở tầng trên phải fallback về None, không phạt điểm mã đó.
    """
    raise NotImplementedError


def safety_score(financials_history, config: dict) -> dict:
    """Tổng hợp điểm Safety. Đọc config['fundamental_filter']['safety_merton_dd']['enabled']
    để quyết định có tính DD hay không — xem mục 11.4 (fallback khi thiếu dữ liệu).
    """
    raise NotImplementedError
