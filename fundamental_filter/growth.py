"""Module Growth — Câu hỏi 1: Doanh nghiệp có thật sự tăng trưởng không?

Tham chiếu: Mục 2 của tài liệu framework (Revenue/NPAT/EPS Growth, CAGR,
Growth Spread, Positive Growth Ratio, Growth Volatility).

Quy ước: mọi hàm nhận vào pandas.Series/DataFrame đã được `data/` chuẩn bị
sẵn theo point-in-time (đã lọc theo ngày công bố BCTC), KHÔNG tự gọi API
bên ngoài ở đây.
"""

from __future__ import annotations

from .layer1_engine.ratios_growth import revenue_growth_yoy as _revenue_growth_yoy


def revenue_growth_yoy(revenue_t: float, revenue_t_minus_1: float) -> float:
    """Mục 2.1 — Revenue Growth YoY = (Rev_t - Rev_t-1) / Rev_t-1."""
    result = _revenue_growth_yoy(revenue_t, revenue_t_minus_1)
    if result is None:
        raise ValueError("revenue_growth_yoy requires finite revenues with prior != 0")
    return float(result)


def growth_spread(npat_growth: float, revenue_growth: float) -> float:
    """Mục 2.2 — Growth Spread = NPAT Growth - Revenue Growth (chỉ báo chẩn đoán)."""
    return float(npat_growth) - float(revenue_growth)


def eps_cagr(eps_end: float, eps_begin: float, n_years: int) -> float:
    """Mục 2.3 — EPS CAGR_nY = (EPS_end / EPS_begin)^(1/n) - 1."""
    if n_years <= 0:
        raise ValueError("n_years must be positive")
    if eps_end is None or eps_begin is None or eps_end <= 0 or eps_begin <= 0:
        raise ValueError("eps_cagr requires positive EPS at both ends")
    return float((eps_end / eps_begin) ** (1 / n_years) - 1)


def positive_growth_ratio(growth_series) -> float:
    """Mục 2.5 — tỷ lệ số kỳ tăng trưởng dương / tổng số kỳ quan sát."""
    values = list(growth_series)
    if not values:
        raise ValueError("growth_series must be non-empty")
    positive = sum(1 for value in values if value is not None and value > 0)
    return positive / len(values)


def growth_score(financials_history) -> dict:
    """Tổng hợp điểm Growth cho một mã, theo phương pháp z-score/percentile ở mục 10.

    Trả về dict gồm: {"score": float, "headline": {...}, "supporting": {...}}
    — xem mục 6.1 để biết headline/supporting metric nào cần trả ra cho bot.

    ``financials_history`` may be a pre-computed module score float/dict from
    ``layer1_engine.score_current_universe``, or a mapping with key ``score``.
    Full peer/trend scoring lives in layer1_engine (pure path).
    """
    if isinstance(financials_history, dict):
        score = financials_history.get("score", financials_history.get("growth_score"))
        headline = financials_history.get("headline") or {
            "metric": "eps_cagr_3y",
            "value": financials_history.get("eps_cagr_3_year"),
        }
        supporting = financials_history.get("supporting") or {}
        return {"score": score, "headline": headline, "supporting": supporting}
    if financials_history is None:
        raise ValueError("financials_history is required")
    return {
        "score": float(financials_history),
        "headline": {"metric": "eps_cagr_3y"},
        "supporting": {},
    }
