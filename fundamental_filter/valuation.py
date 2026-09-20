"""Module Valuation — Câu hỏi 4: Giá cổ phiếu hiện tại có hợp lý không?

Tham chiếu: Mục 5 (P/E, P/B, EV/EBITDA, FCF Yield, DCF + Margin of Safety).
Output của module này còn được dùng làm "view" cho Black-Litterman (mục 9.4
trong tài liệu framework) — không chỉ để chấm điểm PASS/WATCH/FAIL.
"""

from __future__ import annotations

from .layer1_engine.ratios_valuation import calculate_pe as _calculate_pe


def pe_ratio(price: float, eps: float) -> float:
    """Mục 5.1 — headline metric (so với median 5Y & peer, xem mục 6.1)."""
    result = _calculate_pe(price, eps)
    if result is None:
        raise ValueError("pe_ratio requires finite price and positive EPS")
    return float(result)


def margin_of_safety(intrinsic_value: float, market_price: float) -> float:
    """Mục 5.5 — (Intrinsic Value - Market Price) / Intrinsic Value.

    ADVANCED (cần DCF với kịch bản Bear/Base/Bull) — dùng làm view Q dương
    cho Black-Litterman khi đủ dữ liệu.
    """
    if intrinsic_value is None or market_price is None or intrinsic_value == 0:
        raise ValueError("margin_of_safety requires non-zero intrinsic_value")
    return float((intrinsic_value - market_price) / intrinsic_value)


def valuation_score(financials_history, market_data) -> dict:
    """Tổng hợp điểm Valuation + trả thêm view_signal cho quant_engine/portfolio/
    (xem mục 9.4: điểm nối Valuation Score -> Black-Litterman view).
    """
    if isinstance(financials_history, dict):
        score = financials_history.get("score", financials_history.get("valuation_score"))
        headline = financials_history.get("headline") or {
            "metric": "pe_vs_history_and_peer",
            "value": financials_history.get("pe"),
        }
        supporting = dict(financials_history.get("supporting") or {})
    elif financials_history is None:
        raise ValueError("financials_history is required")
    else:
        score = float(financials_history)
        headline = {"metric": "pe_vs_history_and_peer"}
        supporting = {}

    market_data = market_data or {}
    view_signal = market_data.get("view_signal")
    if view_signal is None and score is not None:
        # Neutral default until BL consumes MoS / peer-history consensus (9.4)
        view_signal = "neutral"

    return {
        "score": score,
        "headline": headline,
        "supporting": supporting,
        "view_signal": view_signal,
    }
