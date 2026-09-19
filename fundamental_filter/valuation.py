"""Module Valuation — Câu hỏi 4: Giá cổ phiếu hiện tại có hợp lý không?

Tham chiếu: Mục 5 (P/E, P/B, EV/EBITDA, FCF Yield, DCF + Margin of Safety).
Output của module này còn được dùng làm "view" cho Black-Litterman (mục 9.4
trong tài liệu framework) — không chỉ để chấm điểm PASS/WATCH/FAIL.
"""

from __future__ import annotations


def pe_ratio(price: float, eps: float) -> float:
    """Mục 5.1 — headline metric (so với median 5Y & peer, xem mục 6.1)."""
    raise NotImplementedError


def margin_of_safety(intrinsic_value: float, market_price: float) -> float:
    """Mục 5.5 — (Intrinsic Value - Market Price) / Intrinsic Value.

    ADVANCED (cần DCF với kịch bản Bear/Base/Bull) — dùng làm view Q dương
    cho Black-Litterman khi đủ dữ liệu.
    """
    raise NotImplementedError


def valuation_score(financials_history, market_data) -> dict:
    """Tổng hợp điểm Valuation + trả thêm view_signal cho quant_engine/portfolio/
    (xem mục 9.4: điểm nối Valuation Score -> Black-Litterman view).
    """
    raise NotImplementedError
