"""Module Quality — Câu hỏi 2: Lợi nhuận có chất lượng và hiệu quả không?

Tham chiếu: Mục 3 (Gross/Operating/Net Margin, ROA/ROE/ROIC, DuPont,
Cash Conversion, Accrual Ratio).
"""

from __future__ import annotations

from .layer1_engine.ratios_quality import cfo_to_npat as _cfo_to_npat
from .layer1_engine.ratios_quality import roic as _roic


def roic(nopat: float, invested_capital: float) -> float:
    """Mục 3.2 — ROIC = NOPAT / Invested Capital. Headline metric của module này (mục 6.1)."""
    result = _roic(nopat, invested_capital)
    if result is None:
        raise ValueError("roic requires finite NOPAT and non-zero invested capital")
    return float(result)


def dupont_decomposition(net_margin: float, asset_turnover: float, equity_multiplier: float) -> float:
    """Mục 3.3 — ROE = Net Margin x Asset Turnover x Equity Multiplier.

    Dùng làm supporting metric: chỉ nói tới khi ROE (headline) cao bất thường,
    để phân biệt "giỏi thật" với "nhờ đòn bẩy".
    """
    return net_margin * asset_turnover * equity_multiplier


def cash_conversion(cfo: float, npat: float) -> float:
    """Mục 3.4 — Cash Conversion = CFO / NPAT."""
    result = _cfo_to_npat(cfo, npat)
    if result is None:
        raise ValueError("cash_conversion requires finite CFO and non-zero NPAT")
    return float(result)


def quality_score(financials_history) -> dict:
    """Tổng hợp điểm Quality — xem mục 10 (percentile theo ngành) và mục 6.1 (headline=ROIC)."""
    if isinstance(financials_history, dict):
        score = financials_history.get("score", financials_history.get("quality_score"))
        headline = financials_history.get("headline") or {
            "metric": "roic",
            "value": financials_history.get("roic"),
        }
        supporting = financials_history.get("supporting") or {}
        return {"score": score, "headline": headline, "supporting": supporting}
    if financials_history is None:
        raise ValueError("financials_history is required")
    return {
        "score": float(financials_history),
        "headline": {"metric": "roic"},
        "supporting": {},
    }
