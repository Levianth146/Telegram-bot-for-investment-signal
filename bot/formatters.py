"""Sinh câu giải thích tín hiệu theo quy tắc 'im lặng trừ khi cần giải thích' (mục 6.1)
và quyết định UX ở mục 9.7 của tài liệu framework: TA cổ điển (RSI, MA, Volume)
chỉ hiện trong khối "Tham khảo thêm", KHÔNG bao giờ được dùng để tính điểm
hay sizing — ranh giới này không được vi phạm ở bất kỳ đâu trong module này.

Mỗi câu hỏi (Growth/Quality/Safety/Valuation) có 1 headline metric luôn nói,
và supporting metric chỉ xuất hiện khi headline bất thường. KHÔNG liệt kê hết
mọi chỉ số CORE trong tin nhắn bot.
"""

from __future__ import annotations

import json
from typing import Any, Mapping

# Mã nội bộ (framework) — chỉ dùng trong code/test, không đưa ra tin nhắn bot.
HEADLINE_METRICS = {
    "growth": "eps_cagr_3y",
    "quality": "roic",
    "safety": "net_debt_to_ebitda",
    "valuation": "pe_vs_history_and_peer",
}

# Giải thích tiếng người dùng cho /check (mục 9.7 / 6.1).
HEADLINE_VI = {
    "growth": "tăng trưởng lợi nhuận vài năm gần đây",
    "quality": "hiệu quả dùng vốn",
    "safety": "nợ so với khả năng sinh tiền",
    "valuation": "giá so với lịch sử và cùng ngành",
}

HEADLINE_METRIC_VI = {
    "eps_cagr_3y": "EPS CAGR 3 năm",
    "eps_cagr_3_year": "EPS CAGR 3 năm",
    "roic": "ROIC",
    "net_debt_to_ebitda": "Nợ ròng / EBITDA",
    "pe_vs_history_and_peer": "P/E",
    "pe": "P/E",
    "revenue_cagr_3y": "Doanh thu CAGR 3 năm",
    "revenue_cagr_3_year": "Doanh thu CAGR 3 năm",
    "roe": "ROE",
    "interest_coverage": "Khả năng trả lãi",
    "pb": "P/B",
}

DISCLAIMER = (
    "⚠️ Sản phẩm học thuật — không phải tư vấn đầu tư, "
    "không thay thế tư vấn từ người có chứng chỉ hành nghề."
)

TA_REFERENCE_LABEL = "📊 Tham khảo thêm (không dùng để ra tín hiệu)"

_ACTION_VI = {
    "BUY": "Nghiêng mua / giữ",
    "SELL": "Nghiêng giảm / tránh",
    "WATCH": "Theo dõi — chưa đủ tín hiệu rõ",
}

_ACTION_BANNER = {
    "BUY": "🟢 KHUYẾN NGHỊ: MUA",
    "SELL": "🔴 KHUYẾN NGHỊ: GIẢM / TRÁNH",
    "WATCH": "🟡 KHUYẾN NGHỊ: THEO DÕI",
}

_VIEW_VI = {
    "PASS": "Đạt — đủ điều kiện vào rổ giao dịch",
    "WATCH": "Theo dõi — còn điểm cần xác nhận (thường là định giá)",
    "FAIL": "Loại — chưa đủ điều kiện bộ lọc cơ bản",
}


def translate_regime(p_bull: float) -> str:
    """Dịch xác suất regime sang câu dễ hiểu — mục 9.7."""
    if p_bull is None:
        return "chưa đủ dữ liệu thị trường"
    p = float(p_bull)
    if p >= 0.70:
        return "thị trường đang trong xu hướng tăng, độ tin cậy khá cao"
    if p >= 0.55:
        return "thị trường nghiêng tăng, độ tin cậy vừa phải"
    if p >= 0.45:
        return "thị trường đi ngang / chưa rõ xu hướng"
    if p >= 0.30:
        return "thị trường nghiêng giảm"
    return "thị trường đang trong xu hướng giảm, độ tin cậy khá cao"


def translate_kalman_trend(t_stat: float) -> str:
    """Dịch t-stat của slope Kalman sang câu dễ hiểu."""
    if t_stat is None:
        return "chưa đủ dữ liệu xu hướng"
    t = float(t_stat)
    if t >= 2.0:
        return "xu hướng tăng rõ ràng"
    if t >= 1.0:
        return "xu hướng tăng nhẹ"
    if t > -1.0:
        return "không có xu hướng rõ"
    if t > -2.0:
        return "xu hướng giảm nhẹ"
    return "xu hướng giảm rõ ràng"


def translate_weight_method(method: Any) -> str:
    """Giải thích cách chia tỷ trọng — không lộ tên module."""
    key = str(method or "").strip().lower()
    if key in {"equal_weight", "equal-weight", "ew"}:
        return "chia đều các mã trong rổ"
    if "litterman" in key or key == "bl":
        return "tối ưu theo quan điểm mô hình (Black–Litterman)"
    if not key or key in {"—", "-", "none", "null"}:
        return "chia đều các mã trong rổ"
    return "theo quy tắc danh mục hiện tại"


def translate_sigma_method(method: Any) -> str:
    """Giải thích cách ước biến động — Tier 2 risk (không lộ tên module)."""
    key = str(method or "").strip().lower()
    if "garch" in key or "gjr" in key:
        return "ước từ biến động có cụm (lặng/động xen kẽ)"
    if "ewma" in key or "hist" in key:
        return "ước từ biến động gần đây"
    if not key or key in {"—", "-", "none", "null"}:
        return "ước từ biến động gần đây"
    return "ước từ biến động gần đây"


def translate_alpha_method(method: Any) -> str:
    """Giải thích cách ước xu hướng riêng mã."""
    key = str(method or "").strip().lower()
    if "kalman" in key:
        return "ước từ đường xu hướng giá (làm mượt nhiễu ngắn hạn)"
    if "ou" in key or "mean" in key:
        return "ước từ mức giá lệch khỏi trung bình gần đây"
    if not key or key in {"—", "-", "none", "null"}:
        return "ước từ biến động giá gần đây"
    return "ước từ biến động giá gần đây"


def translate_action(action: Any) -> str:
    key = str(action or "WATCH").strip().upper()
    return _ACTION_VI.get(key, key)


def translate_fundamental_view(view: Any) -> str:
    """PASS/WATCH/FAIL → câu tiếng Việt ngắn."""
    key = str(view or "").strip().upper()
    if not key or key in {"—", "-", "NONE", "NULL"}:
        return "—"
    gloss = _VIEW_VI.get(key)
    if gloss:
        return f"{key} — {gloss}"
    return key


def _rsi_gloss(rsi: float) -> str:
    if rsi >= 70:
        return "vùng quá mua (tham khảo)"
    if rsi <= 30:
        return "vùng quá bán (tham khảo)"
    return "vùng trung tính (tham khảo)"


def format_ta_reference_block(ta_indicators: dict) -> str:
    """Ghép khối 'Tham khảo thêm' từ các chỉ số TA cổ điển đã tính sẵn."""
    if not ta_indicators:
        return ""
    parts = [TA_REFERENCE_LABEL]
    if "rsi_14" in ta_indicators and ta_indicators["rsi_14"] is not None:
        rsi = float(ta_indicators["rsi_14"])
        parts.append(f"• RSI(14): {rsi:.1f} — {_rsi_gloss(rsi)}")
    if ta_indicators.get("ma_trend"):
        parts.append(f"• Đường trung bình: {ta_indicators['ma_trend']}")
    if "volume_over_ma20" in ta_indicators and ta_indicators["volume_over_ma20"] is not None:
        parts.append(
            f"• Khối lượng / TB 20 phiên: {ta_indicators['volume_over_ma20']:.2f}x"
        )
    parts.append("→ Biểu đồ TA: /chart <mã> ta")
    return "\n".join(parts)


def _fmt_num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def _fmt_pct(value: Any, digits: int = 1) -> str:
    """0.017 → 1.7%."""
    if value is None:
        return "—"
    try:
        return f"{float(value) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_day_vi(iso: str | None) -> str:
    """2025-03-31 → 31/03/2025."""
    if not iso:
        return "—"
    s = str(iso)[:10]
    parts = s.split("-")
    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"
    return s


def _reason_payload(signal_row: dict) -> dict:
    raw = signal_row.get("reason_json")
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(str(raw))
    except json.JSONDecodeError:
        return {}


def _data_gap_note(reason: Mapping[str, Any]) -> str | None:
    """Framework 11.4 — nói rõ khi thiếu góc nhìn dữ liệu."""
    err = str(reason.get("error") or "").strip()
    if err == "insufficient_price_history":
        n = reason.get("n")
        n_txt = f" (chỉ {n} phiên)" if n is not None else ""
        return (
            f"⚠️ Thiếu dữ liệu giá đủ dài{n_txt} — "
            "tín hiệu phiên này chỉ mang tính theo dõi."
        )
    if reason.get("monte_carlo_error"):
        return "⚠️ Chưa ước được xác suất chạm mục tiêu (mô phỏng chưa chạy)."
    return None


def _headline_payload(fundamental_row: Mapping[str, Any]) -> dict:
    """Parse ``headline_json`` từ fundamental_scores (mục 6.1)."""
    raw = fundamental_row.get("headline_json")
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        data = json.loads(str(raw))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _fmt_metric_value(metric_id: str, value: Any) -> str:
    """Định dạng giá trị headline/supporting cho tin nhắn."""
    try:
        num = float(value)
    except (TypeError, ValueError):
        return "—"
    mid = str(metric_id or "").lower()
    if mid in {
        "eps_cagr_3y",
        "eps_cagr_3_year",
        "roic",
        "roe",
        "revenue_cagr_3y",
        "revenue_cagr_3_year",
        "fcf_yield",
    }:
        return f"{num * 100:.1f}%" if abs(num) <= 5 else f"{num:.2f}"
    if mid in {"pe", "pe_vs_history_and_peer", "pb", "net_debt_to_ebitda", "interest_coverage"}:
        return f"{num:.2f}"
    return _fmt_num(num)


def _pillar_headline_lines(payload: Mapping[str, Any]) -> tuple[list[str], bool]:
    """Trả (dòng headline 6.1, có_ít_nhất_một_value)."""
    raw_h = payload.get("headline")
    lines: list[str] = []
    has_value = False
    if not isinstance(raw_h, dict):
        return lines, False
    order = ("growth", "quality", "safety", "valuation")
    for pillar in order:
        cell = raw_h.get(pillar)
        if not isinstance(cell, dict):
            # dạng cũ: chỉ tên metric string
            if isinstance(cell, str) and cell:
                lines.append(f"• {HEADLINE_VI.get(pillar, pillar)}: (chưa có số)")
            continue
        mid = str(cell.get("metric") or cell.get("raw_metric") or "")
        label = HEADLINE_METRIC_VI.get(mid) or HEADLINE_VI.get(pillar, pillar)
        val = cell.get("value")
        if val is None:
            lines.append(f"• {label}: chưa có số")
            continue
        has_value = True
        lines.append(f"• {label}: {_fmt_metric_value(mid, val)}")
    supporting = payload.get("supporting")
    if isinstance(supporting, dict) and supporting:
        for pillar, cell in supporting.items():
            if not isinstance(cell, dict):
                continue
            mid = str(cell.get("metric") or cell.get("raw_metric") or "")
            label = HEADLINE_METRIC_VI.get(mid) or mid
            val = cell.get("value")
            if val is None:
                continue
            lines.append(f"• (bổ sung) {label}: {_fmt_metric_value(mid, val)}")
    return lines, has_value


def _headline_block_lines(fundamental_row: Mapping[str, Any]) -> list[str]:
    """Vài dòng nhẹ từ headline_json — không dump toàn bộ supporting metrics."""
    payload = _headline_payload(fundamental_row)
    if not payload:
        return [
            (
                "Nhìn chủ yếu vào: "
                f"{HEADLINE_VI['growth']}; {HEADLINE_VI['quality']}; "
                f"{HEADLINE_VI['safety']}; {HEADLINE_VI['valuation']}."
            )
        ]
    pillar_lines, has_value = _pillar_headline_lines(payload)
    if has_value and pillar_lines:
        lines = list(pillar_lines)
    else:
        lines = [
            (
                "Nhìn chủ yếu vào: "
                f"{HEADLINE_VI['growth']}; {HEADLINE_VI['quality']}; "
                f"{HEADLINE_VI['safety']}; {HEADLINE_VI['valuation']}."
            )
        ]
    gate = payload.get("safety_gate_status")
    if gate and str(gate).upper() not in {"OK", "PASS", "NONE", ""}:
        lines.append(f"Cổng an toàn: {gate}")
    return lines


def format_welcome() -> str:
    """/start — chào + 3 bước bắt đầu nhanh (framework mục 9.7)."""
    return "\n".join(
        [
            "Xin chào — Bot tín hiệu đầu tư (sản phẩm học thuật).",
            "",
            "Bot chỉ hiển thị kết quả đã tính sẵn sau mỗi phiên "
            "(không tự tải lại dữ liệu khi bạn gõ lệnh).",
            "",
            "▶ Bắt đầu nhanh (3 bước):",
            "  1. /subscribe — nhận tin khi có tín hiệu phiên mới",
            "  2. /signals — xem gợi ý mua / giảm / theo dõi hôm nay",
            "  3. /check FPT — giải thích chi tiết một mã",
            "",
            "Gõ /help để xem đầy đủ lệnh và ý nghĩa từng lệnh.",
            "",
            DISCLAIMER,
        ]
    )


def format_help() -> str:
    """/help — mục lục lệnh rõ ràng, tách khỏi /start."""
    return "\n".join(
        [
            "📖 Hướng dẫn lệnh",
            "",
            "― Xem tín hiệu ―",
            "• /signals — danh sách gợi ý phiên gần nhất",
            "• /check <mã> — 4 khối giải thích (cơ bản → thị trường → xu hướng → rủi ro)",
            "• /watchlist — rổ mã sau bộ lọc doanh nghiệp",
            "• /regime — thị trường chung đang nghiêng tăng hay giảm",
            "",
            "― Biểu đồ ―",
            "• /chart <mã> price — giá gần đây (+ regime nếu có)",
            "• /chart <mã> fundamental — radar 4 trụ cơ bản",
            "• /chart <mã> risk — dải biến động GARCH/rolling",
            "• /chart <mã> prob — Monte Carlo (khi có dữ liệu)",
            "• /chart <mã> ta — RSI / đường TB / khối lượng (chỉ tham khảo)",
            "• /backtest — ablation + equity/DD/rolling Sharpe",
            "",
            "― Theo dõi & trạng thái ―",
            "• /subscribe · /unsubscribe — bật/tắt nhận tin tự động",
            "• /positions — vị thế giấy đang mở",
            "• /sector [ngành] — tổng quan theo ngành",
            "• /backtest [scope] — kết quả backtest đã tính sẵn",
            "• /status — lần chạy gần nhất + cờ mô hình",
            "• /about — giới thiệu ngắn + disclaimer",
            "",
            "⚠ Lưu ý hay gây hiểu nhầm:",
            "• “Khí hậu thị trường” trên /signals là chung cả rổ "
            "(thường theo VNINDEX) — cùng một mức cho mọi mã",
            "• Tỷ trọng đang chia đều; khác nhau rõ khi bật tối ưu danh mục nâng cao",
            "• Khác biệt từng mã: hành động, điểm xu hướng, biến động, stop → /check",
            "• Khối “Tham khảo thêm” (RSI…) chỉ để đối chiếu, không quyết định mua/bán",
            "",
            DISCLAIMER,
        ]
    )


def format_signals_list(signal_rows: list[dict]) -> str:
    """Một dòng/mã cho /signals — nhóm theo hành động + CTA /check."""
    if not signal_rows:
        return (
            "📭 Chưa có tín hiệu phiên nào.\n\n"
            "Thường có sau khi hệ thống chạy xong phiên (khoảng sau 15:00).\n"
            "Nếu vẫn trống → báo admin kiểm tra lịch daily.\n\n"
            "Tiếp: /subscribe để nhận tin khi có dữ liệu.\n\n"
            + DISCLAIMER
        )

    day = signal_rows[0].get("date") or ""
    p_vals = [
        float(r["p_regime"])
        for r in signal_rows
        if r.get("p_regime") is not None
    ]
    p_shared = None
    if p_vals:
        p_vals_sorted = sorted(p_vals)
        p_shared = p_vals_sorted[len(p_vals_sorted) // 2]

    n_buy = sum(1 for r in signal_rows if str(r.get("action")).upper() == "BUY")
    n_sell = sum(1 for r in signal_rows if str(r.get("action")).upper() == "SELL")
    n_watch = sum(1 for r in signal_rows if str(r.get("action")).upper() == "WATCH")

    lines = [
        f"📋 Tín hiệu phiên gần nhất{f' · {day}' if day else ''}",
        f"Tóm tắt: Mua {n_buy} · Giảm {n_sell} · Theo dõi {n_watch}",
        "",
    ]
    if p_shared is not None:
        pct = f"{float(p_shared) * 100:.0f}%"
        lines.append(
            f"🌤 Khí hậu thị trường (chung mọi mã): nghiêng tăng ~{pct}"
        )
        lines.append(f"   → {translate_regime(p_shared)}")
        lines.append(
            "Tỷ trọng dưới đây đang chia đều. "
            "Số khác nhau theo mã: điểm xu hướng / biến động."
        )
        lines.append("")

    order = ("BUY", "SELL", "WATCH")
    headers = {
        "BUY": "🟢 MUA",
        "SELL": "🔴 GIẢM / TRÁNH",
        "WATCH": "🟡 THEO DÕI",
    }
    by_action: dict[str, list[dict]] = {k: [] for k in order}
    other: list[dict] = []
    for row in signal_rows:
        act = str(row.get("action") or "?").upper()
        if act in by_action:
            by_action[act].append(row)
        else:
            other.append(row)

    for act in order:
        rows = by_action[act]
        if not rows:
            continue
        lines.append(f"── {headers[act]} ({len(rows)}) ──")
        for row in rows:
            size = row.get("size")
            size_pct = (
                f"{float(size) * 100:.1f}%"
                if size is not None
                else "—"
            )
            ticker = row.get("ticker")
            lines.append(
                f"• {ticker}  | điểm {_fmt_num(row.get('score'))}  "
                f"| biến động {_fmt_num(row.get('sigma_hat'), 4)}  "
                f"| tỷ trọng ≈{size_pct}"
            )
            lines.append(f"  → Chi tiết: /check {ticker}")
        lines.append("")

    for row in other:
        lines.append(
            f"• {row.get('action')} — {row.get('ticker')} | "
            f"điểm {_fmt_num(row.get('score'))} → /check {row.get('ticker')}"
        )

    lines.extend(
        [
            "Mẹo: /check <mã> để xem regime · alpha · rủi ro & tỷ trọng; "
            "/chart <mã> price để xem giá.",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_watchlist(rows: list[dict]) -> str:
    if not rows:
        return (
            "📭 Rổ lọc doanh nghiệp đang trống.\n\n"
            "Cần chạy lọc theo quý (báo cáo tài chính) trước.\n\n"
            + DISCLAIMER
        )
    as_of = rows[0].get("as_of_date", "")
    pass_rows = [
        r for r in rows if str(r.get("fundamental_view", "")).upper() == "PASS"
    ]
    watch_rows = [
        r for r in rows if str(r.get("fundamental_view", "")).upper() == "WATCH"
    ]

    lines = [
        "📌 Rổ lọc doanh nghiệp",
        f"Cập nhật theo báo cáo gần nhất · ngày công bố ước tính: {_fmt_day_vi(as_of)}",
        "(Đây không phải ngày giao dịch phiên — tín hiệu phiên xem /signals.)",
        "",
    ]
    if pass_rows:
        lines.append(f"🟢 Đạt ({len(pass_rows)}) — đủ điều kiện vào rổ")
        lines.append(" · ".join(str(r.get("ticker")) for r in pass_rows))
        lines.append("")
    if watch_rows:
        lines.append(f"🟡 Theo dõi ({len(watch_rows)}) — cần xem thêm")
        lines.append(" · ".join(str(r.get("ticker")) for r in watch_rows))
        lines.append("")
    lines.extend(
        [
            "Gõ /check <mã> để xem chi tiết từng mã.",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_regime_message(p_bull: float | None, as_of: str | None = None) -> str:
    header = f"🌤 Khí hậu thị trường{f' · {as_of}' if as_of else ''}"
    if p_bull is None:
        body = (
            "Chưa có dữ liệu phiên gần nhất.\n"
            "Thử lại sau khi hệ thống chạy xong phiên (thường sau 15:00)."
        )
    else:
        pct = f"{float(p_bull) * 100:.0f}%"
        body = (
            f"Xác suất nghiêng tăng: ~{pct}\n"
            f"→ {translate_regime(p_bull)}\n\n"
            "Đây là mức chung cả rổ (thường theo VNINDEX), không riêng từng mã.\n"
            "Tiếp: /signals để xem gợi ý theo mã."
        )
    return f"{header}\n\n{body}\n\n{DISCLAIMER}"


def format_signal_message(
    signal_row: dict,
    fundamental_row: dict | None = None,
    ta_indicators: dict | None = None,
    *,
    meta: Mapping[str, Any] | None = None,
) -> str:
    """Ghép mẫu tin nhắn đầy đủ theo mục 9.7 (+ 4 khối /check) — giọng người dùng."""
    fundamental_row = fundamental_row or {}
    meta = dict(meta or {})
    reason = _reason_payload(signal_row)
    ticker = signal_row.get("ticker", "?")
    action = str(signal_row.get("action", "WATCH")).upper()
    day = signal_row.get("date", "")

    p_regime = signal_row.get("p_regime")
    p_line = "Chưa có dữ liệu khí hậu thị trường."
    if p_regime is not None:
        try:
            pct = f"{float(p_regime) * 100:.0f}%"
            p_line = (
                f"Xác suất nghiêng tăng: ~{pct}\n"
                f"→ {translate_regime(p_regime)}"
            )
        except (TypeError, ValueError):
            pass

    size = signal_row.get("size")
    size_pct = f"{float(size) * 100:.1f}%" if size is not None else "—"
    weight = reason.get("portfolio_weight", size)
    weight_pct = (
        f"{float(weight) * 100:.1f}%" if weight is not None else size_pct
    )

    market = meta.get("market") or ""
    industry = meta.get("industry") or ""
    last_close = meta.get("last_close")
    header_bits = [str(ticker)]
    if market:
        header_bits.append(f"({market})")
    if industry and str(industry).upper() not in {"UNKNOWN", "NONE"}:
        header_bits.append(f"— {industry}")
    title = " ".join(header_bits)

    view_raw = fundamental_row.get("fundamental_view", "—")
    lines = [
        f"📌 {title}",
        f"Phiên giao dịch: {_fmt_day_vi(str(day)) if day else '—'}",
        "",
        _ACTION_BANNER.get(action, f"KHUYẾN NGHỊ: {action}"),
        translate_action(action),
        "",
    ]

    gap = _data_gap_note(reason)
    if gap:
        lines.extend([gap, ""])

    lines.extend(
        [
            "① Doanh nghiệp",
            f"Kết luận: {translate_fundamental_view(view_raw)}",
        ]
    )
    # Mục 6.1: ưu tiên headline metric thật; điểm 0–100 chỉ fallback.
    payload = _headline_payload(fundamental_row)
    pct = payload.get("fundamental_percentile")
    if pct is not None:
        try:
            lines.append(f"Xếp hạng trong nhóm ngành: khoảng {_fmt_num(pct, 0)}/100")
        except (TypeError, ValueError):
            pass
    pillar_lines, has_value = _pillar_headline_lines(payload)
    if has_value:
        lines.extend(pillar_lines)
    else:
        lines.append(
            f"Điểm nội bộ (tạm): tăng trưởng {_fmt_num(fundamental_row.get('growth_score'))} · "
            f"chất lượng {_fmt_num(fundamental_row.get('quality_score'))} · "
            f"an toàn {_fmt_num(fundamental_row.get('safety_score'))} · "
            f"định giá {_fmt_num(fundamental_row.get('valuation_score'))}"
        )
        lines.append(
            "Ghi chú: chưa có chỉ số gốc mục 6.1 trong store — chạy lại lọc quý để cập nhật."
        )

    lines.extend(
        [
            "",
            "② Thị trường chung",
            p_line.replace("Xác suất nghiêng tăng:", "Khả năng thị trường tăng:").replace(
                "→ ", ""
            ),
            "",
            "③ Xu hướng mã này",
            f"{translate_kalman_trend(reason.get('slope_tstat'))} "
            f"(điểm {_fmt_num(signal_row.get('score'))})",
        ]
    )

    lines.append("")
    lines.append("④ Rủi ro & tỷ trọng")
    if last_close is not None:
        lines.append(f"Giá gần nhất: {_fmt_num(last_close)}")
    lines.append(
        f"Biến động ngày: {_fmt_pct(signal_row.get('sigma_hat'), 2)}  ·  "
        f"Cắt lỗ gợi ý: {_fmt_num(signal_row.get('stop'))}"
    )
    lines.append(f"Tỷ trọng gợi ý: khoảng {size_pct} danh mục")
    if signal_row.get("p_tp_before_sl") is not None:
        lines.append(
            f"Xác suất chạm mục tiêu trước cắt lỗ: {_fmt_pct(signal_row.get('p_tp_before_sl'), 0)}"
        )
    else:
        lines.append("Mô phỏng xác suất (nâng cao): chưa bật")
    if signal_row.get("cvar95") is not None:
        lines.append(f"Rủi ro đuôi ước tính: {_fmt_num(signal_row.get('cvar95'))}")

    ta_block = format_ta_reference_block(ta_indicators or {})
    if ta_block:
        lines.extend(["", ta_block])

    lines.extend(
        [
            "",
            "▶ Tiếp theo:",
            f"  /chart {ticker} price  ·  /chart {ticker} risk  ·  /signals",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_check_unavailable(
    ticker: str,
    *,
    in_watchlist: bool = False,
    has_fundamental: bool = False,
    in_universe_csv: bool | None = None,
) -> str:
    """Giải thích vì sao /check không có tín hiệu phiên — không đổ lỗi vendor mơ hồ."""
    t = ticker.strip().upper()
    lines = [
        f"📭 Chưa có tín hiệu phiên cho {t}.",
        "",
        "Bot chỉ đọc store (không tự crawl khi bạn gõ lệnh).",
        "Tín hiệu phiên chỉ sinh cho mã đã vào rổ lọc (PASS/WATCH) sau daily_job.",
        "",
    ]
    if in_universe_csv is False:
        lines.append(
            f"• {t} không nằm trong universe cấu hình (vd hose_liquid_35) "
            "→ Tầng 1/2 không chấm mã này."
        )
    elif not has_fundamental and not in_watchlist:
        lines.append(
            f"• {t} chưa có điểm cơ bản trong store "
            "(chưa chạy / chưa vào lần lọc quý gần nhất)."
        )
    elif has_fundamental and not in_watchlist:
        lines.append(
            f"• {t} có điểm cơ bản nhưng FAIL / không vào watchlist "
            "→ daily_job không sinh tín hiệu."
        )
    elif in_watchlist:
        lines.append(
            f"• {t} đang trong watchlist nhưng chưa có hàng signals "
            "(cần chạy daily_job / lịch sau 15:00)."
        )
    lines.extend(
        [
            "",
            "Xem mã đang có: /signals · /watchlist",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_positions(rows: list[dict]) -> str:
    """Bảng text cho /positions."""
    if not rows:
        return (
            "📭 Chưa có vị thế giấy đang mở.\n\n"
            "Hệ thống mở vị thế giấy khi phiên có khuyến nghị MUA.\n"
            "Xem gợi ý hôm nay: /signals\n\n"
            + DISCLAIMER
        )
    lines = [
        "📦 Vị thế giấy đang mở",
        f"Số mã: {len(rows)}",
        "",
    ]
    for row in rows:
        size = row.get("size_pct_nav")
        size_txt = _fmt_pct(size, 1) if size is not None else "—"
        lines.extend(
            [
                f"• {row.get('ticker')}",
                f"  Giá vào: {_fmt_num(row.get('entry_price'))}  ·  "
                f"Cắt lỗ: {_fmt_num(row.get('stop_price'))}",
                f"  Tỷ trọng: {size_txt}  ·  Mở ngày: {_fmt_day_vi(row.get('opened_at'))}",
                "",
            ]
        )
    lines.extend(
        [
            "Chi tiết: /check <mã>",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_backtest_results(
    rows: list[dict],
    scope: str,
    *,
    available_scopes: list[str] | None = None,
) -> str:
    """Tóm tắt /backtest — báo cáo nghiên cứu đã ghi sẵn."""
    if not rows:
        lines = [
            f"📭 Chưa có báo cáo kiểm thử cho «{scope}».",
            "",
            "Bot chỉ xem kết quả đã chạy sẵn (không tính lại khi bạn gõ lệnh).",
            "",
        ]
        scopes = [s for s in (available_scopes or []) if s]
        if scopes:
            lines.append("Đang có: " + ", ".join(f"«{s}»" for s in scopes))
            lines.append(f"Thử: /backtest {scopes[0]}")
            lines.append("")
        lines.extend(
            [
                "Trong lúc chờ: /signals · /watchlist · /check <mã>",
                "",
                DISCLAIMER,
            ]
        )
        return "\n".join(lines)
    run_id = rows[0].get("run_id", "?")
    run_at = str(rows[0].get("run_at", ""))[:10]
    baselines = {str(r.get("baseline") or "") for r in rows}
    n_fw = next(
        (r.get("n_trades") for r in rows if r.get("baseline") == "framework"),
        None,
    )
    lines = [
        "📊 Báo cáo kiểm thử chiến lược (nghiên cứu)",
        "⚠️ Đây không phải lãi/lỗ tài khoản thật của bạn.",
        f"Phạm vi: {scope} · mã chạy: {run_id} · ghi ngày {_fmt_day_vi(run_at)}",
        "",
        "So sánh hiện có:",
        "• Mua đều & giữ (B0) — chuẩn tối thiểu",
        "• Theo khung hệ thống — lọc thị trường + xu hướng + rủi ro",
        "",
    ]
    if "B1_ta" not in baselines or "B2_canslim" not in baselines:
        lines.append(
            "Thiếu baseline B1 (TA/EMA-RSI) và B2 (CANSLIM) — "
            "schema đã dự phòng, ablation chưa tính/ghi song song."
        )
        lines.append("")
    try:
        if n_fw is not None and int(n_fw) < 10:
            lines.append(
                f"⚠️ Cỡ mẫu ngoài mẫu còn mỏng (số lệnh khung ≈ {int(n_fw)}). "
                "Sharpe/Calmar chỉ mang tính sơ bộ — chưa đủ để kết luận chắc."
            )
            lines.append("")
    except (TypeError, ValueError):
        pass
    for row in rows:
        base = row.get("baseline", "framework")
        if base == "B0_buyhold":
            title = "① Mua đều & giữ (B0)"
        elif base == "framework":
            title = "② Theo khung hệ thống (ngoài mẫu)"
        elif base == "B1_ta":
            title = "① B1 — TA/EMA-RSI"
        elif base == "B2_canslim":
            title = "① B2 — CANSLIM"
        else:
            title = f"① Cách «{base}»"
        lines.append(f"── {title} ──")
        lines.append(
            f"Tăng trưởng/năm: {_fmt_pct(row.get('cagr'), 1)}  ·  "
            f"Sharpe: {_fmt_num(row.get('sharpe'))}"
        )
        lines.append(
            f"Sụt tối đa: {_fmt_pct(row.get('max_drawdown'), 1)}  ·  "
            f"Số lệnh: {row.get('n_trades', '—')}"
        )
        lines.append(
            f"Sortino {_fmt_num(row.get('sortino'))} · "
            f"Calmar {_fmt_num(row.get('calmar'))} · "
            f"phục hồi ~{row.get('max_drawdown_days') if row.get('max_drawdown_days') is not None else '—'} phiên"
        )
        if row.get("equity_curve_json"):
            lines.append("Biểu đồ đường vốn: xem ảnh bên dưới (nếu có).")
        lines.append("")
    lines.extend(
        [
            "Ảnh kèm (khi đủ dữ liệu): đường vốn, sụt giảm, Sharpe trượt.",
            "Tiếp: /signals · /check <mã> · /chart <mã> price",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_sector_overview(
    rows: list[dict],
    as_of: str | None = None,
    *,
    has_sector_mapping: bool = True,
    has_watchlist: bool = True,
) -> str:
    """Tổng quan /sector — top-down theo industry."""
    if not rows:
        reasons = []
        if not has_watchlist:
            reasons.append("chưa có watchlist (chạy lọc quý)")
        if not has_sector_mapping:
            reasons.append("chưa có phân loại ngành (chạy sector_job)")
        if has_watchlist and has_sector_mapping:
            reasons.append("không khớp ngày / bộ lọc ngành trống")
        why = "; ".join(reasons) if reasons else "thiếu dữ liệu store"
        return (
            f"📭 Chưa có tổng quan ngành ({why}).\n\n"
            "Trong lúc chờ:\n"
            "  • /watchlist — rổ đạt / theo dõi hiện có\n"
            "  • /signals — tín hiệu phiên\n"
            "  • /check <mã> — chi tiết một mã\n"
            "  • /chart <mã> price — biểu đồ giá\n\n"
            + DISCLAIMER
        )
    header = f"🏷 Tổng quan theo ngành · {_fmt_day_vi(as_of) if as_of else '—'}"
    lines = [
        header,
        "Ngày trên = lần lọc báo cáo gần nhất (ước tính ngày công bố),",
        "không phải ngày giao dịch hôm nay.",
        "Nếu cách hôm nay quá xa: cần chạy lại pipeline quý (BCTC mới) — không phải lỗi /sector.",
        "",
    ]
    for row in rows:
        lines.append(
            f"• {row.get('industry', '?')}: "
            f"đạt {row.get('n_pass', 0)} · "
            f"theo dõi {row.get('n_watch', 0)} · "
            f"loại {row.get('n_fail', 0)}"
        )
    lines.extend(
        [
            "",
            "Đạt/Theo dõi = còn trong rổ · Loại = không vào rổ.",
            "Tiếp: /watchlist · /check <mã> · /signals",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_status(
    *,
    config_flags: dict[str, bool],
    latest_signal_date: str | None,
    watchlist_n: int,
    open_positions_n: int,
) -> str:
    """/status — cờ config + timestamp store (không fit model)."""
    lines = [
        "⚙ Trạng thái hệ thống",
        "",
        (
            f"• Tín hiệu mới nhất: {latest_signal_date}"
            if latest_signal_date
            else "• Tín hiệu mới nhất: (chưa có)"
        ),
        f"• Số mã trong watchlist: {watchlist_n}",
        f"• Vị thế đang mở: {open_positions_n}",
        "",
        "Cờ mô hình (bật/tắt):",
    ]
    flag_vi = {
        "regime_markov": "Khí hậu thị trường",
        "alpha_kalman_trend": "Xu hướng riêng mã",
        "risk_garch": "Ước biến động / cắt lỗ",
        "portfolio_black_litterman": "Tối ưu tỷ trọng nâng cao",
        "probabilistic_monte_carlo": "Mô phỏng xác suất",
        "probabilistic_hawkes": "Lọc đông đúc",
        "safety_merton_dd": "An toàn tín dụng nâng cao",
        "sector_overview_command": "Lệnh /sector",
    }
    for key, enabled in sorted(config_flags.items()):
        label = flag_vi.get(key, key)
        lines.append(f"  • {label}: {'BẬT' if enabled else 'tắt'}")
    lines.extend(
        [
            "",
            "Tiếp: /signals · /help",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)
