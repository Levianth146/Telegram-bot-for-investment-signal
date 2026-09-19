"""Module Quality — Câu hỏi 2: Lợi nhuận có chất lượng và hiệu quả không?

Tham chiếu: Mục 3 (Gross/Operating/Net Margin, ROA/ROE/ROIC, DuPont,
Cash Conversion, Accrual Ratio).
"""

from __future__ import annotations


def roic(nopat: float, invested_capital: float) -> float:
    """Mục 3.2 — ROIC = NOPAT / Invested Capital. Headline metric của module này (mục 6.1)."""
    raise NotImplementedError


def dupont_decomposition(net_margin: float, asset_turnover: float, equity_multiplier: float) -> float:
    """Mục 3.3 — ROE = Net Margin x Asset Turnover x Equity Multiplier.

    Dùng làm supporting metric: chỉ nói tới khi ROE (headline) cao bất thường,
    để phân biệt "giỏi thật" với "nhờ đòn bẩy".
    """
    return net_margin * asset_turnover * equity_multiplier


def cash_conversion(cfo: float, npat: float) -> float:
    """Mục 3.4 — Cash Conversion = CFO / NPAT."""
    raise NotImplementedError


def quality_score(financials_history) -> dict:
    """Tổng hợp điểm Quality — xem mục 10 (percentile theo ngành) và mục 6.1 (headline=ROIC)."""
    raise NotImplementedError
