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
    "SELL": "Tránh mua mới",
    "WATCH": "Theo dõi — chưa đủ tín hiệu rõ",
}

# ban_phac §9 — không dùng «Khuyến nghị mua»; dùng «Tín hiệu hệ thống».
_ACTION_BANNER = {
    "BUY": "🟢 Tín hiệu hệ thống: MUA",
    "SELL": "🔴 Tín hiệu hệ thống: TRÁNH MUA MỚI",
    "WATCH": "🟡 Tín hiệu hệ thống: THEO DÕI",
}

_POSITION_ACTION_BANNER = {
    "HOLD": "🟢 Trạng thái vị thế: GIỮ (HOLD)",
    "REDUCE": "🟡 Trạng thái vị thế: GIẢM TỶ TRỌNG (REDUCE)",
    "EXIT": "🔴 Trạng thái vị thế: THOÁT (EXIT)",
}

_VIEW_VI = {
    "PASS": "Đạt — đủ điều kiện vào rổ giao dịch",
    "WATCH": "Theo dõi — còn điểm cần xác nhận (thường là định giá)",
    "FAIL": "Loại — chưa đủ điều kiện bộ lọc cơ bản",
}

# Trạng thái /check (ban_phac §6 + plan Phase A) — bot chỉ đọc store/.
CHECK_OUT_OF_SCOPE = "OUT_OF_SCOPE"
CHECK_EXCLUDED_FINANCIAL = "EXCLUDED_FINANCIAL"
CHECK_INSUFFICIENT = "INSUFFICIENT_FUNDAMENTAL"
CHECK_FAIL = "FUNDAMENTAL_FAIL"
CHECK_WATCH = "FUNDAMENTAL_WATCH"
CHECK_PASS = "FUNDAMENTAL_PASS"
CHECK_PASS_NO_SIGNAL = "FUNDAMENTAL_PASS_NO_SIGNAL"
CHECK_POSITION = "POSITION_AWARE"


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
    """Giải thích cách chia tỷ trọng — không lộ tên module.

    Lưu ý: tỷ trọng *từng mã* trên /signals và /positions là sizing GARCH
    (σ̂ → size), không phải equal-weight BL. Equal-weight chỉ là fallback
    khi tối ưu danh mục nâng cao tắt — khác với size từng vị thế.
    """
    key = str(method or "").strip().lower()
    if key in {"equal_weight", "equal-weight", "ew"}:
        return "chia đều các mã trong rổ (fallback danh mục; size mã vẫn theo biến động)"
    if "litterman" in key or key == "bl":
        return "tối ưu theo quan điểm mô hình (Black–Litterman)"
    if "garch" in key or key in {"vol_target", "volatility_target", "risk"}:
        return "theo biến động mục tiêu (GARCH), có trần %/mã"
    if not key or key in {"—", "-", "none", "null"}:
        return "theo biến động mục tiêu (GARCH), có trần %/mã"
    return "theo quy tắc danh mục hiện tại"


def _fmt_size_pct(size: Any, digits: int = 1) -> str:
    """Định dạng size thập phân → % hiển thị."""
    if size is None:
        return "—"
    try:
        return f"{float(size) * 100:.{digits}f}%"
    except (TypeError, ValueError):
        return "—"


def size_hits_w_max(size: Any, w_max: float = 0.10, *, tol: float = 1e-9) -> bool:
    """True nếu size chạm/vượt trần w_max (GARCH min(w_max, σ_target/σ̂))."""
    if size is None:
        return False
    try:
        return float(size) + tol >= float(w_max)
    except (TypeError, ValueError):
        return False


def format_size_with_cap(
    size: Any,
    *,
    w_max: float = 0.10,
    digits: int = 1,
) -> str:
    """Chuỗi tỷ trọng + ghi chú chạm trần nếu có."""
    pct = _fmt_size_pct(size, digits)
    if size_hits_w_max(size, w_max):
        return f"{pct} (chạm trần {float(w_max) * 100:.0f}%/mã)"
    return pct


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


def cap_action_for_fundamental(action: Any, fundamental_view: Any) -> str:
    """WATCH Fundamental không được nâng thành BUY (ban_phac §1.1 / plan P0)."""
    act = str(action or "WATCH").strip().upper()
    view = str(fundamental_view or "").strip().upper()
    if view == "WATCH" and act == "BUY":
        return "WATCH"
    if view == "FAIL":
        return "WATCH"
    return act if act in {"BUY", "SELL", "WATCH"} else "WATCH"


def map_position_action(action: Any) -> str:
    """BUY/SELL/WATCH (nghiên cứu) → HOLD/REDUCE/EXIT khi đang nắm giấy."""
    act = str(action or "WATCH").strip().upper()
    if act == "BUY":
        return "HOLD"
    if act == "SELL":
        return "EXIT"
    return "REDUCE"


def _classification_reason(fundamental_row: Mapping[str, Any] | None) -> str:
    from fundamental_filter.layer1_engine.eligibility import parse_classification_reason

    return parse_classification_reason(fundamental_row)


def is_insufficient_fundamental(fundamental_row: Mapping[str, Any] | None) -> bool:
    """True khi Layer 1 ghi thiếu dữ liệu (không đồng nhất với FAIL).

    Delegate sang domain eligibility — một định nghĩa dùng chung bot/pipeline.
    """
    from fundamental_filter.layer1_engine.eligibility import is_fundamental_insufficient

    return is_fundamental_insufficient(fundamental_row)


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
    """/start — 3 CTA theo ban_phac §3 (không ép subscribe trước)."""
    return "\n".join(
        [
            "Xin chào — Bot tín hiệu đầu tư (sản phẩm học thuật).",
            "",
            "Bot chỉ hiển thị kết quả đã tính sẵn sau mỗi phiên "
            "(không tự tải lại dữ liệu khi bạn gõ lệnh).",
            "",
            "▶ Chọn hướng bắt đầu:",
            "  📊 Xem thị trường & cơ hội → /signals",
            "  🔎 Tra cứu cổ phiếu → /check FPT",
            "  💼 Danh mục / vị thế → /positions",
            "",
            "Tuỳ chọn: /subscribe để nhận tin khi có tín hiệu phiên mới.",
            "Gõ /help để xem đầy đủ lệnh.",
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
            "• Tỷ trọng từng mã = sizing theo biến động (GARCH / σ̂), "
            f"có trần w_max — không phải chia đều; Black–Litterman chỉ khi bật cờ riêng",
            "• Khác biệt từng mã: hành động, điểm xu hướng, biến động, stop → /check",
            "• Khối “Tham khảo thêm” (RSI…) chỉ để đối chiếu, không quyết định mua/bán",
            "",
            DISCLAIMER,
        ]
    )


# Phân trang /signals — tối đa 10 đáng chú ý + 10 theo dõi mỗi trang (Phần C).
SIGNALS_PAGE_SIZE_NOTABLE = 10
SIGNALS_PAGE_SIZE_WATCH = 10
SIGNALS_PAGE_SIZE_SELL = 10


def _normalise_signal_rows(signal_rows: list[dict]) -> list[dict]:
    """Cap action theo fundamental_view (WATCH fund không hiện như MUA)."""
    normalised: list[dict] = []
    for row in signal_rows:
        item = dict(row)
        item["action"] = cap_action_for_fundamental(
            row.get("action"), row.get("fundamental_view")
        )
        normalised.append(item)
    return normalised


def _signals_by_action(normalised: list[dict]) -> dict[str, list[dict]]:
    """Nhóm BUY/WATCH/SELL, sort |score| giảm dần trong từng nhóm."""
    order = ("BUY", "WATCH", "SELL")
    by_action: dict[str, list[dict]] = {k: [] for k in order}
    for row in normalised:
        act = str(row.get("action") or "?").upper()
        if act in by_action:
            by_action[act].append(row)

    def _strength_key(row: dict) -> float:
        try:
            return abs(float(row.get("score")))
        except (TypeError, ValueError):
            return -1.0

    for act in order:
        by_action[act] = sorted(by_action[act], key=_strength_key, reverse=True)
    return by_action


def signals_total_pages(signal_rows: list[dict]) -> int:
    """Số trang /signals (1 khi rỗng hoặc đủ ngắn cho 1 trang)."""
    if not signal_rows:
        return 1
    by_action = _signals_by_action(_normalise_signal_rows(signal_rows))
    n_buy = len(by_action["BUY"])
    n_watch = len(by_action["WATCH"])
    n_sell = len(by_action["SELL"])
    pages = max(
        1,
        (n_buy + SIGNALS_PAGE_SIZE_NOTABLE - 1) // SIGNALS_PAGE_SIZE_NOTABLE,
        (n_watch + SIGNALS_PAGE_SIZE_WATCH - 1) // SIGNALS_PAGE_SIZE_WATCH,
        (n_sell + SIGNALS_PAGE_SIZE_SELL - 1) // SIGNALS_PAGE_SIZE_SELL,
    )
    return pages


def format_signals_list(
    signal_rows: list[dict],
    *,
    w_max: float = 0.10,
    page: int | None = None,
) -> str:
    """/signals — nhóm theo độ mạnh (ban_phac §4), không alphabet-first.

    Size hiển thị = GARCH position_size (≠ equal-weight / BL).

    ``page``: 0-based; ``None`` = in hết (tương thích test/chunk dài).
    Bot dùng ``page=0`` (+ nút phân trang) theo Phần C UX.
    """
    if not signal_rows:
        return (
            "📭 Chưa có tín hiệu phiên nào trong store.\n\n"
            "Danh sách này chỉ phản ánh mã thuộc pipeline chiến lược "
            "(watchlist sau lọc quý + daily Quant) — không phải toàn bộ thị trường.\n\n"
            "Tiếp: /subscribe · /watchlist\n\n"
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

    normalised = _normalise_signal_rows(signal_rows)
    by_action = _signals_by_action(normalised)

    n_buy = len(by_action["BUY"])
    n_sell = len(by_action["SELL"])
    n_watch = len(by_action["WATCH"])
    n_at_cap = sum(
        1 for r in normalised if size_hits_w_max(r.get("size"), w_max)
    )

    total_pages = signals_total_pages(signal_rows)
    use_page = page is not None
    page_i = 0
    if use_page:
        page_i = max(0, min(int(page), total_pages - 1))

    lines = [
        f"📋 Tín hiệu phiên gần nhất{f' · {day}' if day else ''}",
        "Chỉ mã thuộc strategy pipeline (không đại diện toàn thị trường).",
        f"Tóm tắt: Đáng chú ý {n_buy} · Theo dõi {n_watch} · Tránh mua mới {n_sell}",
        "",
    ]
    if use_page and total_pages > 1:
        lines.append(f"Trang {page_i + 1}/{total_pages} (tối đa 10 mã/nhóm).")
        lines.append("")
    if p_shared is not None:
        pct = f"{float(p_shared) * 100:.0f}%"
        lines.append(
            f"🌤 Khí hậu thị trường (chung mọi mã): nghiêng tăng ~{pct}"
        )
        lines.append(f"   → {translate_regime(p_shared)}")
        lines.append("")

    lines.append(
        f"Tỷ trọng gợi ý = sizing GARCH (biến động), trần {float(w_max) * 100:.0f}%/mã "
        "— không chia đều."
    )
    if n_at_cap:
        lines.append(
            f"⚠ {n_at_cap} mã đang chạm trần w_max "
            f"({float(w_max) * 100:.0f}%)."
        )
    lines.append("")

    # ban_phac §4: đáng chú ý → theo dõi → tránh mua mới; trong nhóm sort theo |score|.
    order = ("BUY", "WATCH", "SELL")
    headers = {
        "BUY": "🟢 Tín hiệu đáng chú ý",
        "WATCH": "🟡 Theo dõi",
        "SELL": "🔴 Tránh mua mới",
    }
    page_sizes = {
        "BUY": SIGNALS_PAGE_SIZE_NOTABLE,
        "WATCH": SIGNALS_PAGE_SIZE_WATCH,
        "SELL": SIGNALS_PAGE_SIZE_SELL,
    }

    for act in order:
        rows = by_action[act]
        if not rows:
            continue
        if use_page:
            size = page_sizes[act]
            start = page_i * size
            rows = rows[start : start + size]
            if not rows:
                continue
        lines.append(f"── {headers[act]} ({len(by_action[act])}) ──")
        for row in rows:
            size_txt = format_size_with_cap(row.get("size"), w_max=w_max)
            ticker = row.get("ticker")
            lines.append(
                f"• {ticker}  | điểm {_fmt_num(row.get('score'))}  "
                f"| biến động {_fmt_num(row.get('sigma_hat'), 4)}  "
                f"| tỷ trọng {size_txt}"
            )
            lines.append(f"  → Chi tiết: /check {ticker}")
        lines.append("")

    # Các action lạ (không BUY/WATCH/SELL) — chỉ khi không phân trang.
    if not use_page:
        known = set(order)
        for row in normalised:
            act = str(row.get("action") or "?").upper()
            if act in known:
                continue
            lines.append(
                f"• {row.get('action')} — {row.get('ticker')} | "
                f"điểm {_fmt_num(row.get('score'))} → /check {row.get('ticker')}"
            )

    lines.extend(
        [
            "Mẹo: /check <mã> để xem giải thích đầy đủ.",
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
        f"Theo BCTC năm (ước tính ngày công bố): {_fmt_day_vi(as_of)}",
        "(Không phải quý lịch · không phải ngày giao dịch phiên — tín hiệu xem /signals.)",
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


def format_action_changes_alert(changes: list[dict]) -> str:
    """Push ngắn khi action đổi (ban_phac §10) — không lặp full report."""
    if not changes:
        return ""
    lines = [
        "🔔 Đổi trạng thái tín hiệu",
        f"{len(changes)} mã đổi action so với lần trước:",
        "",
    ]
    for row in changes[:40]:
        ticker = row.get("ticker", "?")
        frm = translate_action(row.get("from_action"))
        to = translate_action(row.get("to_action"))
        lines.append(
            f"• {ticker}: {row.get('from_action')} → {row.get('to_action')} "
            f"({frm} → {to})"
        )
    if len(changes) > 40:
        lines.append(f"… và {len(changes) - 40} mã khác")
    lines.extend(
        [
            "",
            "Chi tiết: /signals · /check <mã>",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_signal_message(
    signal_row: dict,
    fundamental_row: dict | None = None,
    ta_indicators: dict | None = None,
    *,
    meta: Mapping[str, Any] | None = None,
    w_max: float = 0.10,
) -> str:
    """Ghép mẫu tin nhắn đầy đủ theo mục 9.7 (+ 4 khối /check) — giọng người dùng."""
    fundamental_row = fundamental_row or {}
    meta = dict(meta or {})
    reason = _reason_payload(signal_row)
    ticker = signal_row.get("ticker", "?")
    view_raw = fundamental_row.get("fundamental_view", "—")
    action = cap_action_for_fundamental(signal_row.get("action", "WATCH"), view_raw)
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
    size_pct = format_size_with_cap(size, w_max=w_max)
    weight = reason.get("portfolio_weight", size)
    weight_pct = (
        format_size_with_cap(weight, w_max=w_max)
        if weight is not None
        else size_pct
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

    watch_capped = (
        str(view_raw).upper() == "WATCH"
        and str(signal_row.get("action", "")).upper() == "BUY"
    )
    lines = [
        f"📌 {title}",
        f"Phiên giao dịch: {_fmt_day_vi(str(day)) if day else '—'}",
        "",
        _ACTION_BANNER.get(action, f"Tín hiệu hệ thống: {action}"),
        translate_action(action),
    ]
    if watch_capped:
        lines.append(
            "(Fundamental đang WATCH — không nâng thành MUA chính thức.)"
        )
    if str(view_raw).upper() == "WATCH":
        lines.append("Quant/Risk chỉ mang tính tham khảo cho mã WATCH.")
    lines.append("")

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
    lines.append(f"Tỷ trọng gợi ý (GARCH): {size_pct} danh mục")
    if weight is not None and weight != size:
        lines.append(f"Tỷ trọng sau tối ưu danh mục (nếu có): {weight_pct}")
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

    next_lines = [
        "",
        "▶ Tiếp theo:",
        f"  /chart {ticker} price  ·  /chart {ticker} risk  ·  /signals",
    ]
    if str(view_raw).upper() == "PASS":
        next_lines.append("  /subscribe — nhận báo khi tín hiệu đổi trạng thái")
    next_lines.extend(["", DISCLAIMER])
    lines.extend(next_lines)
    return "\n".join(lines)


def _check_header(ticker: str, meta: Mapping[str, Any] | None) -> list[str]:
    meta = dict(meta or {})
    bits = [str(ticker).upper()]
    market = meta.get("market") or ""
    industry = meta.get("industry") or ""
    if market:
        bits.append(f"({market})")
    if industry and str(industry).upper() not in {"UNKNOWN", "NONE"}:
        bits.append(f"— {industry}")
    lines = [f"📌 {' '.join(bits)}"]
    last_close = meta.get("last_close")
    if last_close is not None:
        lines.append(f"Giá gần nhất: {_fmt_num(last_close)}")
    return lines


def _fundamental_pillars_block(fundamental_row: Mapping[str, Any]) -> list[str]:
    """Khối 4 trụ + lý do phân loại (FAIL/WATCH/PASS)."""
    lines = [
        "① Doanh nghiệp",
        f"Kết luận: {translate_fundamental_view(fundamental_row.get('fundamental_view'))}",
    ]
    filed = fundamental_row.get("filed_at") or fundamental_row.get("period")
    if filed:
        lines.append(f"Kỳ BCTC / filed_at: {_fmt_day_vi(str(filed))}")
    payload = _headline_payload(fundamental_row)
    reason = _classification_reason(fundamental_row)
    if reason:
        lines.append(f"Lý do hệ thống: {reason}")
    pillar_lines, has_value = _pillar_headline_lines(payload)
    if has_value:
        lines.extend(pillar_lines)
    else:
        lines.append(
            f"4 trụ (điểm nội bộ): tăng trưởng {_fmt_num(fundamental_row.get('growth_score'))} · "
            f"chất lượng {_fmt_num(fundamental_row.get('quality_score'))} · "
            f"an toàn {_fmt_num(fundamental_row.get('safety_score'))} · "
            f"định giá {_fmt_num(fundamental_row.get('valuation_score'))}"
        )
    return lines


def format_check_out_of_scope(
    ticker: str,
    *,
    meta: Mapping[str, Any] | None = None,
    ta_indicators: dict | None = None,
) -> str:
    """OUT_OF_SCOPE — ngoài universe cấu hình; không bảo «đợi sau 15:00»."""
    t = ticker.strip().upper()
    meta = dict(meta or {})
    lines = _check_header(t, meta)
    lines.extend(
        [
            "",
            "⛔ Ngoài phạm vi chiến lược hiện tại",
            f"Câu chuyện ngắn: {t} không nằm trong universe cấu hình (CSV Tầng 1).",
            "Bot không chấm Fundamental/Quant cho mã ngoài phạm vi — "
            "đây không phải lỗi «chưa chạy daily» và không cần đợi phiên.",
        ]
    )
    if meta.get("store_has_price") is False and meta.get("last_close") is None:
        lines.append("Store hiện chưa có dữ liệu giá cho mã này.")
    ta_block = format_ta_reference_block(ta_indicators or {})
    if ta_block:
        lines.extend(["", ta_block])
    lines.extend(
        [
            "",
            "Xem mã đang hỗ trợ: /watchlist · /signals",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_check_excluded_financial(
    ticker: str,
    *,
    meta: Mapping[str, Any] | None = None,
    ta_indicators: dict | None = None,
) -> str:
    """EXCLUDED_FINANCIAL — V1 loại ngân hàng/chứng khoán/bảo hiểm.

    Vẫn hiện giá/TA tham khảo (ban_phac §6.1) — không đồng nhất với «thiếu data».
    """
    t = ticker.strip().upper()
    industry = (meta or {}).get("industry") or "ngành tài chính"
    lines = _check_header(t, meta)
    lines.extend(
        [
            "",
            "⛔ Ngoài phạm vi chiến lược V1 (tài chính)",
            f"Câu chuyện ngắn: {t} thuộc «{industry}» — bộ lọc V1 đang tắt "
            "nhóm ngân hàng / chứng khoán / bảo hiểm (exclude_financials).",
            "Không chạy Quant và không tạo tín hiệu giao dịch cho nhóm này — "
            "đây là quyết định phạm vi, không phải thiếu BCTC hay lỗi pipeline.",
            "",
            "Bạn vẫn có thể xem giá gần nhất (nếu store có) và khối "
            "«Tham khảo thêm» bên dưới — chỉ để định hướng, không phải khuyến nghị.",
            "",
        ]
    )
    ta_block = format_ta_reference_block(ta_indicators or {})
    if ta_block:
        lines.extend([ta_block, ""])
    else:
        lines.append(
            "(Chưa có đủ bars để tính TA tham khảo — thử /chart "
            f"{t} price khi pipeline đã ghi giá.)"
        )
        lines.append("")
    lines.extend(
        [
            f"Tiếp: /chart {t} price · /watchlist (mã phi tài chính).",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_check_insufficient(
    ticker: str,
    *,
    fundamental_row: Mapping[str, Any] | None = None,
    ta_indicators: dict | None = None,
    meta: Mapping[str, Any] | None = None,
) -> str:
    """INSUFFICIENT_FUNDAMENTAL — thiếu BCTC ≠ FAIL (ban_phac §6.1)."""
    t = ticker.strip().upper()
    lines = _check_header(t, meta)
    lines.extend(
        [
            "",
            "⚠️ Chưa đủ dữ liệu Fundamental",
            "Câu chuyện ngắn: thiếu dữ liệu ≠ doanh nghiệp xấu. "
            "Bot chưa chấm Layer 1 hoàn chỉnh → chưa chạy Quant → "
            "không có tín hiệu hệ thống.",
            "",
        ]
    )
    if fundamental_row:
        reason = _classification_reason(fundamental_row)
        if reason:
            lines.append(f"Ghi chú store: {reason}")
        lines.append(
            f"Điểm tạm (không dùng để kết luận): "
            f"G {_fmt_num(fundamental_row.get('growth_score'))} · "
            f"Q {_fmt_num(fundamental_row.get('quality_score'))} · "
            f"S {_fmt_num(fundamental_row.get('safety_score'))} · "
            f"V {_fmt_num(fundamental_row.get('valuation_score'))}"
        )
        lines.append("")
    else:
        lines.append("Store chưa có hàng fundamental_scores cho mã này.")
        lines.append("")
    ta_block = format_ta_reference_block(ta_indicators or {})
    if ta_block:
        lines.extend([ta_block, ""])
    lines.extend(
        [
            f"Tiếp: /chart {t} price · /watchlist",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_check_fundamental_fail(
    ticker: str,
    fundamental_row: Mapping[str, Any],
    *,
    ta_indicators: dict | None = None,
    meta: Mapping[str, Any] | None = None,
) -> str:
    """FUNDAMENTAL_FAIL — vẫn hiện 4 trụ + lý do; không Quant/khuyến nghị."""
    t = ticker.strip().upper()
    lines = _check_header(t, meta)
    lines.extend(
        [
            "",
            "⛔ Không vượt bộ lọc Fundamental",
            "(Khác với «thiếu dữ liệu» — đã chấm và không đạt ngưỡng chiến lược.)",
            "",
        ]
    )
    lines.extend(_fundamental_pillars_block(fundamental_row))
    lines.extend(
        [
            "",
            "Kết luận: không chạy Quant và không tạo tín hiệu giao dịch "
            "theo chiến lược hiện tại.",
        ]
    )
    ta_block = format_ta_reference_block(ta_indicators or {})
    if ta_block:
        lines.extend(["", ta_block])
    lines.extend(
        [
            "",
            f"Tiếp: /chart {t} fundamental · /watchlist",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_check_pass_no_signal(
    ticker: str,
    fundamental_row: Mapping[str, Any],
    *,
    ta_indicators: dict | None = None,
    meta: Mapping[str, Any] | None = None,
) -> str:
    """PASS nhưng chưa có hàng signals — nói rõ cần daily_job (không on-demand)."""
    t = ticker.strip().upper()
    lines = _check_header(t, meta)
    lines.extend(
        [
            "",
            "🟡 Fundamental PASS — chưa có tín hiệu Quant trong store",
            "Bot không chạy Quant on-demand. Cần daily_job ghi signals sau phiên.",
            "",
        ]
    )
    lines.extend(_fundamental_pillars_block(fundamental_row))
    ta_block = format_ta_reference_block(ta_indicators or {})
    if ta_block:
        lines.extend(["", ta_block])
    lines.extend(
        [
            "",
            f"Tiếp: /watchlist · /signals · /chart {t} price",
            "/subscribe — nhận báo khi tín hiệu đổi trạng thái",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_check_position_aware(
    position: Mapping[str, Any],
    signal_row: dict | None,
    fundamental_row: dict | None = None,
    *,
    ta_indicators: dict | None = None,
    meta: Mapping[str, Any] | None = None,
) -> str:
    """Ưu tiên P/L · HOLD/REDUCE/EXIT · stop khi có vị thế OPEN (ban_phac §8)."""
    ticker = str(position.get("ticker") or (signal_row or {}).get("ticker") or "?").upper()
    view = (fundamental_row or {}).get("fundamental_view")
    raw_action = (signal_row or {}).get("action", "WATCH")
    action = cap_action_for_fundamental(raw_action, view)
    pos_action = map_position_action(action)

    entry = position.get("entry_price")
    stop = position.get("stop_price")
    if signal_row and signal_row.get("stop") is not None:
        stop = signal_row.get("stop")
    last_close = (meta or {}).get("last_close")
    pnl_pct = None
    if entry is not None and last_close is not None:
        try:
            e = float(entry)
            if e:
                pnl_pct = float(last_close) / e - 1.0
        except (TypeError, ValueError):
            pnl_pct = None

    stop_dist = None
    if stop is not None and last_close is not None:
        try:
            s = float(stop)
            c = float(last_close)
            if c:
                stop_dist = (c - s) / c
        except (TypeError, ValueError):
            stop_dist = None

    lines = _check_header(ticker, meta)
    lines.extend(
        [
            "",
            "📦 ĐANG NẮM GIỮ (vị thế giấy)",
            _POSITION_ACTION_BANNER.get(pos_action, f"Trạng thái: {pos_action}"),
            "",
            "① P/L & vị thế",
            f"Giá vào: {_fmt_num(entry)}  ·  Giá hiện tại: {_fmt_num(last_close)}",
            f"P/L ước tính: {_fmt_pct(pnl_pct, 1)}",
            f"Mở ngày: {_fmt_day_vi(position.get('opened_at'))}  ·  "
            f"Tỷ trọng: {_fmt_pct(position.get('size_pct_nav'), 1)}",
            "",
            "② Risk",
            f"Stop hiện tại: {_fmt_num(stop)}",
            (
                f"Khoảng cách tới stop: {_fmt_pct(stop_dist, 1)}"
                if stop_dist is not None
                else "Khoảng cách tới stop: —"
            ),
            "",
            "③ Tín hiệu phiên → hành động vị thế",
            f"Tín hiệu hệ thống (nghiên cứu): {translate_action(action)}",
            f"→ Với vị thế đang mở: {pos_action}",
        ]
    )
    if fundamental_row:
        base_note = translate_fundamental_view(view)
        if is_insufficient_fundamental(fundamental_row):
            base_note = (
                "Chưa đủ dữ liệu Layer 1 đáng tin "
                f"(reason: {_classification_reason(fundamental_row) or '—'})"
            )
        elif str(view or "").upper() == "FAIL":
            base_note = (
                f"{translate_fundamental_view('FAIL')} — "
                "không còn trong Quant universe (vị thế giấy vẫn hiển thị)."
            )
        lines.extend(
            [
                "",
                "④ Fundamental (base Layer 1)",
                base_note,
            ]
        )
    ta_block = format_ta_reference_block(ta_indicators or {})
    if ta_block:
        lines.extend(["", ta_block])
    lines.extend(
        [
            "",
            f"Chi tiết nghiên cứu đầy đủ vẫn dùng cùng /check {ticker} "
            "(ưu tiên vị thế khi đang OPEN).",
            "Danh sách: /positions",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def resolve_base_check_state(
    *,
    in_universe: bool | None,
    is_financial: bool,
    exclude_financials: bool,
    fund: Mapping[str, Any] | None,
    signal: Mapping[str, Any] | None,
) -> str:
    """Base research state (không overlay vị thế) — ban_phac §5–6 / FLOW2."""
    if in_universe is False:
        return CHECK_OUT_OF_SCOPE
    # Tài chính V1 = EXCLUDED dù có/không hàng fund (không nhầm INSUFFICIENT).
    if exclude_financials and is_financial:
        return CHECK_EXCLUDED_FINANCIAL
    if fund is None:
        return CHECK_INSUFFICIENT
    if is_insufficient_fundamental(fund):
        return CHECK_INSUFFICIENT
    view = str(fund.get("fundamental_view") or "").upper()
    if view == "FAIL":
        return CHECK_FAIL
    if view == "WATCH":
        return CHECK_WATCH
    if view == "PASS":
        # Stale Quant không nâng PASS khi Layer 1 đã FAIL/INSUFFICIENT — đã chặn ở trên.
        return CHECK_PASS if signal else CHECK_PASS_NO_SIGNAL
    # Có hàng fund nhưng view lạ / trống → thiếu dữ liệu phân loại
    return CHECK_INSUFFICIENT


def resolve_check_state(
    *,
    in_universe: bool | None,
    is_financial: bool,
    exclude_financials: bool,
    fund: Mapping[str, Any] | None,
    signal: Mapping[str, Any] | None,
    has_open_position: bool,
) -> str:
    """State machine store-only cho /check (ban_phac §5–6).

    Position là overlay presentation; base Layer 1 lấy qua ``resolve_base_check_state``.
    """
    if has_open_position:
        return CHECK_POSITION
    return resolve_base_check_state(
        in_universe=in_universe,
        is_financial=is_financial,
        exclude_financials=exclude_financials,
        fund=fund,
        signal=signal,
    )


def format_check_by_state(
    state: str,
    ticker: str,
    *,
    fund: dict | None = None,
    signal: dict | None = None,
    position: dict | None = None,
    ta_indicators: dict | None = None,
    meta: Mapping[str, Any] | None = None,
    w_max: float = 0.10,
) -> str:
    """Điều phối formatter theo state — một cửa cho /check."""
    t = ticker.strip().upper()
    if state == CHECK_POSITION and position:
        return format_check_position_aware(
            position, signal, fund, ta_indicators=ta_indicators, meta=meta
        )
    if state == CHECK_OUT_OF_SCOPE:
        return format_check_out_of_scope(t, meta=meta, ta_indicators=ta_indicators)
    if state == CHECK_EXCLUDED_FINANCIAL:
        return format_check_excluded_financial(
            t, meta=meta, ta_indicators=ta_indicators
        )
    if state == CHECK_INSUFFICIENT:
        return format_check_insufficient(
            t, fundamental_row=fund, ta_indicators=ta_indicators, meta=meta
        )
    if state == CHECK_FAIL and fund:
        return format_check_fundamental_fail(
            t, fund, ta_indicators=ta_indicators, meta=meta
        )
    if state == CHECK_PASS_NO_SIGNAL and fund:
        return format_check_pass_no_signal(
            t, fund, ta_indicators=ta_indicators, meta=meta
        )
    if state in {CHECK_WATCH, CHECK_PASS} and signal:
        return format_signal_message(
            signal, fund, ta_indicators=ta_indicators, meta=meta, w_max=w_max
        )
    if state == CHECK_WATCH and fund and signal is None:
        # WATCH chưa có Quant — vẫn hiện Fundamental, không BUY.
        lines = _check_header(t, meta)
        lines.extend(
            [
                "",
                "🟡 Tín hiệu hệ thống: THEO DÕI",
                "Fundamental WATCH — chưa có hàng Quant trong store.",
                "",
            ]
        )
        lines.extend(_fundamental_pillars_block(fund))
        ta_block = format_ta_reference_block(ta_indicators or {})
        if ta_block:
            lines.extend(["", ta_block])
        lines.extend(["", DISCLAIMER])
        return "\n".join(lines)
    # Fallback an toàn
    return format_check_unavailable(
        t,
        in_watchlist=False,
        has_fundamental=fund is not None,
        in_universe_csv=None if state != CHECK_OUT_OF_SCOPE else False,
    )


def format_check_unavailable(
    ticker: str,
    *,
    in_watchlist: bool = False,
    has_fundamental: bool = False,
    in_universe_csv: bool | None = None,
) -> str:
    """Giải thích legacy khi thiếu ngữ cảnh đầy đủ — ưu tiên state machine mới."""
    t = ticker.strip().upper()
    if in_universe_csv is False:
        return format_check_out_of_scope(t)
    lines = [
        f"📭 Chưa có đủ dữ liệu store cho {t}.",
        "",
        "Bot chỉ đọc store (không tự crawl khi bạn gõ lệnh).",
        "",
    ]
    if not has_fundamental and not in_watchlist:
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
            "(cần chạy daily_job — không phải Quant on-demand)."
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


def format_positions(rows: list[dict], *, w_max: float = 0.10) -> str:
    """Bảng text cho /positions — size = GARCH (giống /signals), có ∑% + trần."""
    if not rows:
        return (
            "📭 Chưa có vị thế giấy đang mở.\n\n"
            "Hệ thống mở vị thế giấy khi phiên có khuyến nghị MUA.\n"
            "Tỷ trọng mỗi mã = sizing GARCH (không chia đều).\n"
            "Xem gợi ý hôm nay: /signals\n\n"
            + DISCLAIMER
        )
    total = 0.0
    n_sized = 0
    n_at_cap = 0
    for row in rows:
        size = row.get("size_pct_nav")
        if size is None:
            continue
        try:
            s = float(size)
        except (TypeError, ValueError):
            continue
        total += s
        n_sized += 1
        if size_hits_w_max(s, w_max):
            n_at_cap += 1

    lines = [
        "📦 Vị thế giấy đang mở",
        f"Số mã: {len(rows)}",
        f"∑ tỷ trọng ≈ {_fmt_pct(total, 1) if n_sized else '—'}  ·  "
        f"trần {float(w_max) * 100:.0f}%/mã (GARCH)",
        "",
    ]
    if n_at_cap:
        lines.append(
            f"⚠ {n_at_cap} mã đang chạm trần w_max — không phải lỗi chia đều."
        )
        lines.append("")
    for row in rows:
        size = row.get("size_pct_nav")
        size_txt = format_size_with_cap(size, w_max=w_max)
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
            "Chi tiết: /check <mã>  ·  So sánh gợi ý: /signals",
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
    checks: list[dict] | None = None,
    yearly: list[dict] | None = None,
) -> str:
    """Tóm tắt /backtest — báo cáo nghiên cứu OOS đã ghi sẵn (không cam kết lãi)."""
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
    by_base = {str(r.get("baseline") or ""): r for r in rows}
    fw = by_base.get("framework") or {}
    b0 = by_base.get("B0_buyhold") or {}
    n_fw = fw.get("n_trades")
    lines = [
        "📊 Báo cáo kiểm thử chiến lược (nghiên cứu ngoài mẫu)",
        "⚠️ Đây là kết quả nghiên cứu OOS đã ghi sẵn — "
        "không phải lãi/lỗ tài khoản thật, không cam kết lợi nhuận.",
        f"Phạm vi: {scope} · mã chạy: {run_id} · ghi ngày {_fmt_day_vi(run_at)}",
        "",
        "So sánh hiện có:",
        "• Mua đều & giữ (B0) — chuẩn tối thiểu",
        "• B1 TA / B2 CANSLIM — baseline song song (nếu có)",
        "• Theo khung hệ thống — lọc thị trường + xu hướng + rủi ro (OOS)",
        "",
    ]
    if "B1_ta" not in baselines or "B2_canslim" not in baselines:
        lines.append(
            "Thiếu baseline B1 (TA/EMA-RSI) và/hoặc B2 (CANSLIM) — "
            "schema đã dự phòng, ablation chưa tính/ghi đủ."
        )
        lines.append("")

    # Phát hiện hợp lệ: framework thua B0 trên OOS
    try:
        s_fw = float(fw["sharpe"]) if fw.get("sharpe") is not None else None
        s_b0 = float(b0["sharpe"]) if b0.get("sharpe") is not None else None
    except (TypeError, ValueError):
        s_fw, s_b0 = None, None
    if s_fw is not None and s_b0 is not None and s_fw < s_b0:
        lines.append(
            f"📌 Phát hiện hợp lệ: khung hệ thống (Sharpe OOS {_fmt_num(s_fw)}) "
            f"thua B0 ({_fmt_num(s_b0)}) trên mẫu này — "
            "giữ trong DECISIONS; không flip MC/BL."
        )
        lines.append("")

    try:
        if n_fw is not None and int(n_fw) < 30:
            lines.append(
                f"⚠️ Cỡ mẫu ngoài mẫu còn mỏng (số lệnh khung ≈ {int(n_fw)}; "
                "ngưỡng ý nghĩa ≥ 30). "
                "Sharpe/Calmar/Sortino chỉ mang tính minh hoạ."
            )
            lines.append("")
    except (TypeError, ValueError):
        pass

    for row in rows:
        base = row.get("baseline", "framework")
        if base == "B0_buyhold":
            title = "① Mua đều & giữ (B0)"
        elif base == "framework":
            title = "② Theo khung hệ thống (ngoài mẫu / OOS)"
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
            f"margin {_fmt_num(row.get('margin_bps'))} bps · "
            f"phục hồi ~"
            f"{row.get('max_drawdown_days') if row.get('max_drawdown_days') is not None else '—'} phiên"
        )
        if row.get("turnover") is not None:
            lines.append(f"Turnover (ước): {_fmt_num(row.get('turnover'), 4)}")
        if row.get("equity_curve_json"):
            lines.append("Biểu đồ đường vốn: xem ảnh bên dưới (cùng khung OOS).")
        lines.append("")

    if checks:
        lines.append("── Checks đã đăng ký trước (✅/❌) ──")
        for chk in checks:
            mark = "✅" if int(chk.get("passed") or 0) else "❌"
            name = chk.get("check_name") or "?"
            actual = chk.get("actual_value")
            thr = chk.get("threshold")
            lines.append(
                f"{mark} {name}: thực tế {_fmt_num(actual)} · "
                f"ngưỡng {_fmt_num(thr)}"
            )
            note = chk.get("note")
            if note:
                lines.append(f"   → {note}")
        lines.append("")

    if yearly:
        lines.append("── Theo năm (framework OOS) ──")
        for y in yearly:
            lines.append(
                f"• {y.get('year')}: Sharpe {_fmt_num(y.get('sharpe'))} · "
                f"CAGR {_fmt_pct(y.get('cagr'), 1)} · "
                f"lệnh {y.get('n_trades', '—')}"
            )
        lines.append("")

    lines.extend(
        [
            "Bấm nút bên dưới để xem từng view (So B0/B1/B2, theo năm, checks) — "
            "bot chỉ đọc store, không tính lại backtest.",
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
        "Ngày trên = BCTC năm + lag công bố ước tính (không phải quý lịch),",
        "cũng không phải ngày giao dịch hôm nay.",
        "Nếu cách hôm nay quá xa: cần chạy lại pipeline quý (BCTC năm mới) — không phải lỗi /sector.",
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


# ---------------------------------------------------------------------------
# Phần C — InlineKeyboard / ReplyKeyboard (chỉ điều hướng + đọc store)
# ---------------------------------------------------------------------------

# action ∈ {price, radar, ta, watch_add, pnl}; callback chk:<action>:<TICKER>
_CHECK_ACTIONS = frozenset({"price", "radar", "ta", "watch_add", "pnl"})


def _telegram_keyboard_imports():
    """Import lazy — giữ formatters importable khi chưa cài python-telegram-bot."""
    from telegram import (
        InlineKeyboardButton,
        InlineKeyboardMarkup,
        KeyboardButton,
        ReplyKeyboardMarkup,
    )

    return InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup


def assert_callback_data_ok(data: str) -> str:
    """Telegram giới hạn callback_data ≤ 64 byte (UTF-8)."""
    raw = data.encode("utf-8")
    if len(raw) > 64:
        raise ValueError(f"callback_data vượt 64 byte ({len(raw)}): {data!r}")
    return data


def check_keyboard_rows(
    state: str,
    ticker: str,
    *,
    has_price_bars: bool = False,
) -> list[list[tuple[str, str]]]:
    """Sinh hàng nút /check theo state (C-2) — chưa bọc InlineKeyboardMarkup.

    Trả về ``[[(label, callback_data), ...], ...]``.
    """
    t = ticker.strip().upper()
    rows: list[list[tuple[str, str]]] = []
    row: list[tuple[str, str]] = []

    def _add(label: str, action: str) -> None:
        cb = assert_callback_data_ok(f"chk:{action}:{t}")
        row.append((label, cb))

    if state == CHECK_POSITION:
        _add("📉 Xem P/L chi tiết", "pnl")

    if state in (CHECK_OUT_OF_SCOPE, CHECK_EXCLUDED_FINANCIAL, CHECK_INSUFFICIENT):
        if has_price_bars:
            _add("📈 TA tham khảo", "ta")
    elif state == CHECK_FAIL:
        _add("🎯 Radar Fundamental", "radar")
        if has_price_bars:
            _add("📈 TA tham khảo", "ta")
    elif state in (
        CHECK_WATCH,
        CHECK_PASS_NO_SIGNAL,
        CHECK_PASS,
        CHECK_POSITION,
    ):
        if has_price_bars:
            _add("📊 Biểu đồ giá", "price")
        _add("🎯 Radar Fundamental", "radar")
        if has_price_bars:
            _add("📈 TA tham khảo", "ta")
        _add("⭐ Theo dõi mã này", "watch_add")

    if row:
        # Telegram: tối đa ~8 nút/hàng; tách 2 hàng nếu dài.
        if len(row) <= 3:
            rows.append(row)
        else:
            rows.append(row[:2])
            rows.append(row[2:])
    return rows


def build_check_keyboard(
    state: str,
    ticker: str,
    *,
    has_price_bars: bool = False,
):
    """InlineKeyboard dưới kết quả /check — không đổi ``resolve_check_state``."""
    InlineKeyboardButton, InlineKeyboardMarkup, _, _ = _telegram_keyboard_imports()
    spec = check_keyboard_rows(state, ticker, has_price_bars=has_price_bars)
    if not spec:
        return None
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(text=lab, callback_data=cb) for lab, cb in r]
            for r in spec
        ]
    )


def build_signals_keyboard(page: int, total_pages: int):
    """Nút ◀ / Trang X/Y / ▶ — ``page:signals:<n>`` (0-based)."""
    InlineKeyboardButton, InlineKeyboardMarkup, _, _ = _telegram_keyboard_imports()
    if total_pages <= 1:
        return None
    page_i = max(0, min(int(page), total_pages - 1))
    row = []
    if page_i > 0:
        row.append(
            InlineKeyboardButton(
                "◀ Trước",
                callback_data=assert_callback_data_ok(f"page:signals:{page_i - 1}"),
            )
        )
    row.append(
        InlineKeyboardButton(
            f"Trang {page_i + 1}/{total_pages}",
            callback_data=assert_callback_data_ok(f"page:signals:{page_i}"),
        )
    )
    if page_i < total_pages - 1:
        row.append(
            InlineKeyboardButton(
                "Tiếp ▶",
                callback_data=assert_callback_data_ok(f"page:signals:{page_i + 1}"),
            )
        )
    return InlineKeyboardMarkup([row])


def build_backtest_keyboard(run_id: str):
    """View switcher /backtest — ``bt:<view>:<run_id>``; chỉ đọc store khi bấm."""
    InlineKeyboardButton, InlineKeyboardMarkup, _, _ = _telegram_keyboard_imports()
    rid = str(run_id or "latest")[:40]
    views = (
        ("So B0", "b0"),
        ("So B1", "b1"),
        ("So B2", "b2"),
        ("Theo năm", "yearly"),
        ("Bảng checks", "checks"),
    )
    buttons = []
    for label, view in views:
        cb = assert_callback_data_ok(f"bt:{view}:{rid}")
        buttons.append(InlineKeyboardButton(label, callback_data=cb))
    # 3 + 2 hàng cho dễ bấm trên mobile
    return InlineKeyboardMarkup([buttons[:3], buttons[3:]])


def build_regime_keyboard():
    """Nút điều hướng /regime → logic /signals."""
    InlineKeyboardButton, InlineKeyboardMarkup, _, _ = _telegram_keyboard_imports()
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "Xem theo từng mã →",
                    callback_data=assert_callback_data_ok("nav:signals"),
                )
            ]
        ]
    )


def build_start_reply_keyboard():
    """ReplyKeyboard cố định cho /start — điền lệnh vào ô chat."""
    _, _, KeyboardButton, ReplyKeyboardMarkup = _telegram_keyboard_imports()
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("/check"),
                KeyboardButton("/signals"),
                KeyboardButton("/regime"),
                KeyboardButton("/positions"),
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def format_backtest_checks_only(
    checks: list[dict] | None,
    *,
    scope: str,
    run_id: str,
) -> str:
    """Text-only bảng checks khi bấm nút bt:checks (không tính lại backtest)."""
    lines = [
        f"📋 Checks đã đăng ký · {scope} · {run_id}",
        "",
    ]
    if not checks:
        lines.append("Chưa có check nào trong store cho lần chạy này.")
    else:
        for chk in checks:
            mark = "✅" if int(chk.get("passed") or 0) else "❌"
            name = chk.get("check_name") or "?"
            lines.append(
                f"{mark} {name}: thực tế {_fmt_num(chk.get('actual_value'))} · "
                f"ngưỡng {_fmt_num(chk.get('threshold'))}"
            )
            note = chk.get("note")
            if note:
                lines.append(f"   → {note}")
    lines.extend(["", DISCLAIMER])
    return "\n".join(lines)


def format_watch_add_ack(ticker: str, *, on_system_watchlist: bool) -> str:
    """Phản hồi nút watch_add — chỉ đọc store, không ghi pipeline watchlist."""
    t = ticker.strip().upper()
    if on_system_watchlist:
        body = (
            f"✓ {t} đang trong rổ theo dõi hệ thống (sau lọc quý).\n"
            f"Xem: /watchlist · /check {t}"
        )
    else:
        body = (
            f"ℹ {t} chưa có trong rổ lọc quý của hệ thống.\n"
            f"Bot không thêm mã vào pipeline khi bấm nút "
            "(chỉ đọc store).\n"
            f"Tiếp: /watchlist · /check {t} · /subscribe"
        )
    return f"{body}\n\n{DISCLAIMER}"

