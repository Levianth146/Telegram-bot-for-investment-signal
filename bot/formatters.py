"""Sinh câu giải thích tín hiệu theo quy tắc 'im lặng trừ khi cần giải thích' (mục 6.1)
và quyết định UX ở mục 9.7 của tài liệu framework: TA cổ điển (RSI, MA, Volume)
chỉ hiện trong khối "Tham khảo thêm", KHÔNG bao giờ được dùng để tính điểm
hay sizing — ranh giới này không được vi phạm ở bất kỳ đâu trong module này.

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

DISCLAIMER = (
    "⚠️ Sản phẩm học thuật, không phải tư vấn đầu tư, không thay thế tư vấn "
    "từ người có chứng chỉ hành nghề."
)

TA_REFERENCE_LABEL = "📊 Tham khảo thêm (không dùng để ra tín hiệu)"


def translate_regime(p_bull: float) -> str:
    """Dịch xác suất regime sang câu dễ hiểu — mục 9.7.

    Ví dụ: 0.78 -> "thị trường đang trong xu hướng tăng, độ tin cậy khá cao".
    Không đổi số liệu gốc, chỉ thêm câu diễn giải song song.
    """
    raise NotImplementedError


def translate_kalman_trend(t_stat: float) -> str:
    """Dịch t-stat của slope Kalman sang câu dễ hiểu.

    Ví dụ: 2.6 -> "xu hướng tăng rõ ràng". Ngưỡng phân loại (rõ ràng/mơ hồ/
    không có xu hướng) nên thống nhất với nhóm Alpha (P2), tránh mỗi người
    một chuẩn.
    """
    raise NotImplementedError


def format_ta_reference_block(ta_indicators: dict) -> str:
    """Ghép khối 'Tham khảo thêm' từ các chỉ số TA cổ điển đã tính sẵn (RSI,
    MA20/MA50, Volume/MA20 v.v.) — xem mục 9.7.

    QUAN TRỌNG: hàm này CHỈ được gọi ở bước hiển thị cuối cùng. Không import
    hay gọi bất kỳ hàm nào từ đây trong `fundamental_filter/` hoặc
    `quant_engine/` — TA không bao giờ được lan ngược vào logic tính điểm.

    `ta_indicators` ví dụ: {"rsi_14": 62, "ma_trend": "tăng", "volume_over_ma20": 1.3}
    """
    raise NotImplementedError


def format_signal_message(signal_row: dict, fundamental_row: dict, ta_indicators: dict | None = None) -> str:
    """Ghép mẫu tin nhắn đầy đủ theo mục 9.7:

        BUY — <ticker> | <ngày>
        Regime: ... (kèm câu dịch)
        Trend (Kalman): ... (kèm câu dịch)
        Entry/Stop/Size
        P(...) = .. | CVaR95 = ..

        [Tham khảo thêm — TA cổ điển, nếu ta_indicators được truyền vào]
        Disclaimer (LUÔN có ở cuối, mọi tin nhắn)

    `ta_indicators=None` -> bỏ qua khối tham khảo, không lỗi (feature này có
    thể tắt độc lập với mọi tầng P0/P1/P2 khác, vì nó thuần UX).
    """
    raise NotImplementedError
