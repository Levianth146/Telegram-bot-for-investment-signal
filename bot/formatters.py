"""Sinh câu giải thích tín hiệu theo quy tắc 'im lặng trừ khi cần giải thích' (mục 6.1).

Mỗi câu hỏi (Growth/Quality/Safety/Valuation) có 1 headline metric luôn nói,
và supporting metric chỉ xuất hiện khi headline bất thường. KHÔNG liệt kê hết
mọi chỉ số CORE trong tin nhắn bot.
"""

from __future__ import annotations

HEADLINE_METRICS = {
    "growth": "eps_cagr_3_5y",
    "quality": "roic",
    "safety": "net_debt_to_ebitda",
    "valuation": "pe_vs_median_peer",
}


def format_signal_message(signal_row: dict, fundamental_row: dict) -> str:
    """Ghép mẫu tin nhắn dạng:

    BUY — ABC | ngày
    Regime: ... | Trend/Quality: ... | Entry/Stop/Size: ...
    P(...) = .. | CVaR95 = ..
    Disclaimer học thuật (LUÔN có ở cuối, mọi tin nhắn — xem docs/ARCHITECTURE.md
    phần ghi chú pháp lý).
    """
    raise NotImplementedError


DISCLAIMER = (
    "⚠️ Sản phẩm học thuật phục vụ bài tập môn học, không phải khuyến nghị "
    "đầu tư, không thay thế tư vấn từ người có chứng chỉ hành nghề."
)
