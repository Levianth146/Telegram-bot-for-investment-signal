"""Module Growth — Câu hỏi 1: Doanh nghiệp có thật sự tăng trưởng không?

Tham chiếu: Mục 2 của tài liệu framework (Revenue/NPAT/EPS Growth, CAGR,
Growth Spread, Positive Growth Ratio, Growth Volatility).

Quy ước: mọi hàm nhận vào pandas.Series/DataFrame đã được `data/` chuẩn bị
sẵn theo point-in-time (đã lọc theo ngày công bố BCTC), KHÔNG tự gọi API
bên ngoài ở đây.
"""

from __future__ import annotations


def revenue_growth_yoy(revenue_t: float, revenue_t_minus_1: float) -> float:
    """Mục 2.1 — Revenue Growth YoY = (Rev_t - Rev_t-1) / Rev_t-1."""
    # TODO(P2 - phụ trách Growth): xử lý revenue_t_minus_1 <= 0 (chia 0 / âm)
    raise NotImplementedError


def growth_spread(npat_growth: float, revenue_growth: float) -> float:
    """Mục 2.2 — Growth Spread = NPAT Growth - Revenue Growth (chỉ báo chẩn đoán)."""
    raise NotImplementedError


def eps_cagr(eps_end: float, eps_begin: float, n_years: int) -> float:
    """Mục 2.3 — EPS CAGR_nY = (EPS_end / EPS_begin)^(1/n) - 1."""
    raise NotImplementedError


def positive_growth_ratio(growth_series) -> float:
    """Mục 2.5 — tỷ lệ số kỳ tăng trưởng dương / tổng số kỳ quan sát."""
    raise NotImplementedError


def growth_score(financials_history) -> dict:
    """Tổng hợp điểm Growth cho một mã, theo phương pháp z-score/percentile ở mục 10.

    Trả về dict gồm: {"score": float, "headline": {...}, "supporting": {...}}
    — xem mục 6.1 để biết headline/supporting metric nào cần trả ra cho bot.
    """
    raise NotImplementedError
