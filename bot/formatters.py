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
from datetime import date, datetime
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

# UX Redesign: một dòng cố định cuối mọi lệnh (tránh lặp đoạn dài).
DISCLAIMER = "⚠ Học thuật · không phải tư vấn đầu tư."

# Marker tách tóm tắt / chi tiết — tin đầu cắt trước marker; chk:detail lấy phần sau.
DETAIL_MARKER = "── Chi tiết ──"


def academic_disclaimer() -> str:
    """Disclaimer học thuật ngắn — dùng cuối mọi lệnh Telegram."""
    return DISCLAIMER


def check_summary_text(full: str) -> str:
    """Tin đầu /check: chỉ phần trước DETAIL_MARKER + disclaimer ngắn."""
    text = str(full or "")
    if DETAIL_MARKER in text:
        head = text.split(DETAIL_MARKER, 1)[0].rstrip()
        # Bỏ disclaimer dài/ngắn nếu đã có ở cuối head — gắn lại 1 lần.
        for marker in (DISCLAIMER, "⚠️ Sản phẩm học thuật"):
            if marker in head:
                head = head.rsplit(marker, 1)[0].rstrip()
        return f"{head}\n\n{DISCLAIMER}"
    return text


def check_detail_text(full: str, *, ticker: str = "") -> str:
    """Nội dung sau khi bấm ▾ Xem đầy đủ số liệu (chk:detail)."""
    text = str(full or "")
    t = (ticker or "").strip().upper()
    prefix = f"▾ Chi tiết · {t}\n\n" if t else "▾ Chi tiết\n\n"
    if DETAIL_MARKER in text:
        body = text.split(DETAIL_MARKER, 1)[1].strip()
        return f"{prefix}{body}"
    return f"{prefix}{text}"


def _pnl_traffic_icon(pnl: float | None) -> str:
    """🟢 lãi / 🔴 lỗ / ⚪ chưa có P/L — icon trước số có ngưỡng."""
    if pnl is None:
        return "⚪"
    try:
        v = float(pnl)
    except (TypeError, ValueError):
        return "⚪"
    if v > 0:
        return "🟢"
    if v < 0:
        return "🔴"
    return "⚪"


TA_REFERENCE_LABEL = "📊 Tham khảo thêm (không dùng để ra tín hiệu)"

_ACTION_VI = {
    "BUY": "Nghiêng mua / giữ",
    "SELL": "Tránh mua mới",
    # D-9: nói vì sao + gợi ý bước tiếp (không chỉ «chưa đủ»).
    "WATCH": "Theo dõi — xu hướng/điểm chưa đủ rõ để mở mới; thêm /watchlist hoặc /subscribe",
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


def regime_label_prefix(p_bull: float | None) -> str:
    """Nhãn ngắn theo p_bull — cùng ngưỡng hiển thị với translate_regime (D-3).

    Không đổi model/ngưỡng Quant; chỉ bỏ tiền tố cứng «nghiêng tăng».
    """
    if p_bull is None:
        return "chưa rõ"
    try:
        p = float(p_bull)
    except (TypeError, ValueError):
        return "chưa rõ"
    if p >= 0.55:
        return "nghiêng tăng"
    if p >= 0.45:
        return "đi ngang"
    return "nghiêng giảm"


def regime_traffic_light(p_bull: float | None) -> str:
    """Đèn giao thông /regime (FinBot-style) — cùng ngưỡng regime_label_prefix."""
    if p_bull is None:
        return "⚪"
    try:
        p = float(p_bull)
    except (TypeError, ValueError):
        return "⚪"
    if p >= 0.55:
        return "🟢"
    if p >= 0.45:
        return "🟡"
    return "🔴"


def regime_session_compare(
    p_bull: float | None, prev_p_bull: float | None
) -> str | None:
    """So sánh khí hậu với phiên trước (E-3 /regime) — chỉ copy, không đổi model."""
    if p_bull is None or prev_p_bull is None:
        return None
    try:
        float(p_bull)
        float(prev_p_bull)
    except (TypeError, ValueError):
        return None
    curr = regime_label_prefix(p_bull)
    prev = regime_label_prefix(prev_p_bull)
    if curr == prev:
        return f"So với phiên trước: không đổi ({prev})."
    return f"So với phiên trước: đã chuyển từ {prev} sang {curr}."


def _parse_iso_date(value: Any) -> date | None:
    """Parse YYYY-MM-DD (hoặc datetime ISO) → date; lỗi → None."""
    if value is None:
        return None
    s = str(value).strip()[:10]
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        try:
            return datetime.fromisoformat(str(value).strip().replace("Z", "")).date()
        except ValueError:
            return None


def holding_sessions_from_opened_at(
    opened_at: Any,
    as_of: Any = None,
) -> int | None:
    """Số ngày lịch từ opened_at → as_of (hoặc hôm nay) — hiển thị «giữ N phiên».

    Round2: không đếm phiên HOSE riêng; chênh lệch ngày đủ cho UX vị thế giấy.
    """
    opened = _parse_iso_date(opened_at)
    if opened is None:
        return None
    end = _parse_iso_date(as_of) if as_of is not None else date.today()
    if end is None:
        end = date.today()
    delta = (end - opened).days
    return max(0, int(delta))


# D-9: tên check kỹ thuật → ngôn ngữ nhà đầu tư (không đổi ngưỡng).
_BACKTEST_CHECK_VI = {
    "MIN_SHARPE_IMPROVEMENT_OOS": "Cải thiện Sharpe ngoài mẫu so với mua & giữ",
    "MIN_TRADES_FOR_SIGNIFICANCE": "Số lệnh đủ để kết luận có ý nghĩa",
    "MAX_TURNOVER": "Vòng quay danh mục (không vượt trần)",
    "CONCENTRATED_WEIGHT": "Tỷ trọng tập trung vào một mã",
}


def translate_backtest_check_name(name: Any) -> str:
    """Dịch tên check ablation ra câu dễ hiểu (D-9)."""
    key = str(name or "").strip()
    if not key:
        return "?"
    return _BACKTEST_CHECK_VI.get(key, key)


def _pillar_score_scale_note() -> str:
    """Mốc thang điểm 0–100 cho người không quen quant (D-9)."""
    return "(thang 0–100; khoảng ≥60 thường được coi là khá)"


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
    """Định dạng size thập phân → % hiển thị (D-4: 0 / <0.5% / else).

    Phân biệt «không mở» với «rất nhỏ» — không đổi công thức sizing.
    """
    if size is None:
        return "Không mở vị thế mã này"
    try:
        s = float(size)
    except (TypeError, ValueError):
        return "—"
    if s == 0.0:
        return "Không mở vị thế mã này"
    if 0.0 < s < 0.005:
        return "Tỷ trọng rất nhỏ (<0.5%) — gần như không đáng kể"
    return f"{s * 100:.{digits}f}%"


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
    """Chuỗi tỷ trọng + ghi chú chạm trần nếu có (chỉ khi size ≥ 0.5%)."""
    pct = _fmt_size_pct(size, digits)
    try:
        s = float(size) if size is not None else None
    except (TypeError, ValueError):
        s = None
    # Nhánh D-4 mô tả bằng chữ — không ghép «chạm trần».
    if s is None or s == 0.0 or (0.0 < s < 0.005):
        return pct
    if size_hits_w_max(size, w_max):
        return f"{pct} (chạm trần {float(w_max) * 100:.0f}%/mã)"
    return pct


def format_chart_skip_note(chart_name: str, exc: BaseException) -> str:
    """Dòng ngắn khi ChartDataError — D-6 không nuốt im."""
    reason = str(exc).strip() or "chưa đủ dữ liệu"
    if len(reason) > 140:
        reason = reason[:137] + "…"
    return f"(Biểu đồ {chart_name}: {reason})"


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


def format_cvar95_line(cvar95: Any) -> str:
    """Dòng CVaR 95% kèm ngữ cảnh dấu âm/dương (D-9)."""
    num = _fmt_num(cvar95)
    try:
        v = float(cvar95)
    except (TypeError, ValueError):
        return f"Rủi ro đuôi ước tính (CVaR 95%): {num}"
    if v < 0:
        gloss = "số âm ≈ mức lỗ trung bình ở nhóm phiên xấu nhất (~5%)"
    elif v > 0:
        gloss = "số dương ≈ vẫn dương ngay cả ở nhóm phiên xấu (~5%)"
    else:
        gloss = "xấp xỉ hòa vốn ở nhóm phiên xấu (~5%)"
    return f"Rủi ro đuôi ước tính (CVaR 95%): {num} — {gloss}"


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


def format_as_of_session_line(as_of: str | None) -> str | None:
    """Dòng timestamp đồng bộ /check · /positions · /tinhtrangdulieu."""
    if not as_of:
        return None
    return f"Dữ liệu tính đến phiên {_fmt_day_vi(str(as_of)[:10])}"


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
    """/start — mockup UX Redesign: 3 nhánh gọn, không lặp EOD (đẩy sang /tinhtrangdulieu)."""
    return "\n".join(
        [
            "🤖 Bot tín hiệu đầu tư VN — trợ lý phân tích cổ phiếu VN (sản phẩm học thuật)",
            "",
            "📊 1. Thị trường & cơ hội hôm nay",
            "   └ /signals — mã đáng chú ý sau khi lọc theo chiến lược",
            "   └ /regime — thị trường đang nghiêng tăng hay giảm",
            "",
            "🔎 2. Tra cứu một mã cụ thể",
            "   └ /check FPT (ví dụ) — sức khoẻ doanh nghiệp + xu hướng + rủi ro",
            "   └ Hoặc gõ thẳng mã 3 ký tự",
            "",
            "💼 3. Danh mục đang theo dõi",
            "   └ /positions — vị thế giấy đang mở",
            "   └ /watchlist — rổ mã đã qua vòng lọc doanh nghiệp",
            "",
            "ⓘ /help — đầy đủ lệnh · /tinhtrangdulieu — dữ liệu cập nhật khi nào",
            DISCLAIMER,
        ]
    )


def format_help() -> str:
    """/help — nhóm theo nhu cầu (E-3) + ví dụ cú pháp mỗi lệnh (Round2 Phần 6)."""
    return "\n".join(
        [
            "📖 Hướng dẫn theo nhu cầu",
            "",
            "― Khám phá thị trường ―",
            "• /signals — gợi ý phiên gần nhất",
            "  ví dụ: /signals",
            "• /regime — khí hậu thị trường chung (đèn + điểm)",
            "  ví dụ: /regime",
            "• /watchlist — rổ sau lọc doanh nghiệp (BCTC năm)",
            "  ví dụ: /watchlist",
            "• /sector [ngành] — tổng quan theo ngành",
            "  ví dụ: /sector   ·  /sector Ngân hàng",
            "",
            "― Tra cứu 1 mã ―",
            "• /check <mã> — kết luận → vì sao → chi tiết",
            "  ví dụ: /check FPT",
            "• /chart <mã> price|fundamental|risk|ta — biểu đồ tham khảo",
            "  ví dụ: /chart VNM price",
            "",
            "― Quản lý vị thế ―",
            "• /positions — vị thế giấy + tổng P/L ước tính",
            "  ví dụ: /positions",
            "• /subscribe · /unsubscribe — bật/tắt tin phiên mới",
            "  ví dụ: /subscribe",
            "",
            "― Xem thêm ―",
            "• /backtest [scope] — báo cáo kiểm thử ngoài mẫu",
            "  ví dụ: /backtest portfolio",
            "• /tinhtrangdulieu — EOD vs realtime (bot chỉ đọc store)",
            "  ví dụ: /tinhtrangdulieu",
            "• /status — mirror tình trạng dữ liệu + cờ hệ thống",
            "• /about — giới thiệu ngắn",
            "",
            "⚠ Lưu ý hay gây hiểu nhầm:",
            "• «Khí hậu thị trường» trên /signals là chung cả rổ "
            "(thường theo VNINDEX) — cùng một mức cho mọi mã",
            "• Tỷ trọng từng mã = theo biến động mục tiêu, có trần %/mã "
            "— không chia đều; tối ưu danh mục nâng cao chỉ khi bật riêng",
            "• Khối «Tham khảo thêm» (RSI…) chỉ để đối chiếu, không quyết định mua/bán",
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


def signals_total_pages(signal_rows: list[dict], *, action_filter: str | None = None) -> int:
    """Số trang /signals (1 khi rỗng hoặc đủ ngắn cho 1 trang)."""
    if not signal_rows:
        return 1
    by_action = _signals_by_action(_normalise_signal_rows(signal_rows))
    filt = str(action_filter or "").upper() or None
    if filt in ("BUY", "WATCH", "SELL"):
        n = len(by_action[filt])
        size = {
            "BUY": SIGNALS_PAGE_SIZE_NOTABLE,
            "WATCH": SIGNALS_PAGE_SIZE_WATCH,
            "SELL": SIGNALS_PAGE_SIZE_SELL,
        }[filt]
        return max(1, (n + size - 1) // size) if n else 1
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


def signals_action_counts(signal_rows: list[dict]) -> dict[str, int]:
    """Đếm BUY/WATCH/SELL sau cap fundamental — dùng opener keyboard."""
    by_action = _signals_by_action(_normalise_signal_rows(signal_rows))
    return {
        "BUY": len(by_action["BUY"]),
        "WATCH": len(by_action["WATCH"]),
        "SELL": len(by_action["SELL"]),
    }


def _signals_shared_p_regime(signal_rows: list[dict]) -> float | None:
    p_vals = [
        float(r["p_regime"])
        for r in signal_rows
        if r.get("p_regime") is not None
    ]
    if not p_vals:
        return None
    p_vals_sorted = sorted(p_vals)
    return p_vals_sorted[len(p_vals_sorted) // 2]


def format_signals_summary(
    signal_rows: list[dict],
    *,
    w_max: float = 0.10,
) -> str:
    """Tin đầu /signals — chỉ kết luận + khí hậu; danh sách mã sau nút bấm."""
    if not signal_rows:
        return (
            "📭 Chưa có tín hiệu phiên nào trong store.\n\n"
            "Danh sách này chỉ phản ánh mã thuộc pipeline chiến lược "
            "(watchlist sau lần rà lọc doanh nghiệp gần nhất + daily Quant) "
            "— không phải toàn bộ thị trường.\n\n"
            "Tiếp: /subscribe · /watchlist\n\n"
            + DISCLAIMER
        )

    day = signal_rows[0].get("date") or ""
    day_vi = _fmt_day_vi(str(day)[:10]) if day else ""
    by_action = _signals_by_action(_normalise_signal_rows(signal_rows))
    n_buy = len(by_action["BUY"])
    n_watch = len(by_action["WATCH"])
    n_sell = len(by_action["SELL"])
    p_shared = _signals_shared_p_regime(signal_rows)

    buy_icon = "🟢" if n_buy > 0 else "🔴"
    lines = [
        (
            f"📋 Tín hiệu phiên {day_vi or 'gần nhất'} — "
            f"{buy_icon} {n_buy} mã đáng mua · "
            f"🟡 {n_watch} theo dõi · ⚫ {n_sell} tránh mua mới"
        ),
        "",
    ]
    if p_shared is not None:
        # Mockup: 1 câu khí hậu → hạn chế mua mới khi nghiêng giảm.
        if float(p_shared) < 0.45 and n_buy == 0:
            lines.append(
                f"Thị trường chung đang {regime_label_prefix(p_shared)} "
                f"({translate_regime(p_shared)}) → hệ thống KHÔNG đề xuất mã mua mới "
                "phiên này, kể cả mã doanh nghiệp tốt."
            )
        else:
            pct = f"{float(p_shared) * 100:.0f}%"
            lines.append(
                f"→ Khí hậu chung: {regime_label_prefix(p_shared)} (~{pct}) — "
                f"{translate_regime(p_shared)}"
            )
        lines.append("")
    lines.extend(
        [
            "Chỉ mã thuộc pipeline chiến lược — không đại diện toàn thị trường.",
            f"Tỷ trọng gợi ý = theo biến động mục tiêu, trần "
            f"{float(w_max) * 100:.0f}%/mã — không chia đều.",
            "",
            "Bấm nút bên dưới để xem danh sách mã (điểm · biến động · tỷ trọng).",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_signals_list(
    signal_rows: list[dict],
    *,
    w_max: float = 0.10,
    page: int | None = None,
    action_filter: str | None = None,
) -> str:
    """Danh sách /signals theo nhóm (sau nút bấm) hoặc full khi ``page is None``.

    Size hiển thị = GARCH position_size (≠ equal-weight / BL).

    ``page``: 0-based; ``None`` = in hết (tương thích test/chunk dài).
    ``action_filter``: BUY|WATCH|SELL — chỉ một nhóm (UX collapse).
    """
    if not signal_rows:
        return (
            "📭 Chưa có tín hiệu phiên nào trong store.\n\n"
            "Danh sách này chỉ phản ánh mã thuộc pipeline chiến lược "
            "(watchlist sau lần rà lọc doanh nghiệp gần nhất + daily Quant) "
            "— không phải toàn bộ thị trường.\n\n"
            "Tiếp: /subscribe · /watchlist\n\n"
            + DISCLAIMER
        )

    day = signal_rows[0].get("date") or ""
    p_shared = _signals_shared_p_regime(signal_rows)

    normalised = _normalise_signal_rows(signal_rows)
    by_action = _signals_by_action(normalised)

    n_buy = len(by_action["BUY"])
    n_sell = len(by_action["SELL"])
    n_watch = len(by_action["WATCH"])
    n_at_cap = sum(
        1 for r in normalised if size_hits_w_max(r.get("size"), w_max)
    )

    filt = str(action_filter or "").upper() or None
    if filt and filt not in ("BUY", "WATCH", "SELL"):
        filt = None

    # Phân trang theo nhóm đang xem (hoặc max các nhóm khi full).
    if filt:
        n_group = len(by_action[filt])
        size_map = {
            "BUY": SIGNALS_PAGE_SIZE_NOTABLE,
            "WATCH": SIGNALS_PAGE_SIZE_WATCH,
            "SELL": SIGNALS_PAGE_SIZE_SELL,
        }
        page_size = size_map[filt]
        total_pages = max(1, (n_group + page_size - 1) // page_size) if n_group else 1
    else:
        total_pages = signals_total_pages(signal_rows)
    use_page = page is not None
    page_i = 0
    if use_page:
        page_i = max(0, min(int(page), total_pages - 1))

    lines = [
        f"📋 Tín hiệu phiên gần nhất{f' · {day}' if day else ''}",
        (
            f"Kết luận: phiên này có {n_buy} mã đáng chú ý, "
            f"{n_watch} đang theo dõi, {n_sell} nên tránh mua mới."
        ),
        "Chỉ mã thuộc pipeline chiến lược — không đại diện toàn thị trường.",
        "",
    ]
    if use_page and total_pages > 1:
        lines.append(f"Trang {page_i + 1}/{total_pages} (tối đa 10 mã/nhóm).")
        lines.append("")
    if p_shared is not None and not filt:
        pct = f"{float(p_shared) * 100:.0f}%"
        lines.append(
            f"→ Vì sao khí hậu chung: "
            f"{regime_label_prefix(p_shared)} (~{pct}) — {translate_regime(p_shared)}"
        )
        lines.append("")

    lines.append(
        f"Tỷ trọng gợi ý = theo biến động mục tiêu, trần "
        f"{float(w_max) * 100:.0f}%/mã — không chia đều."
    )
    if n_at_cap and not filt:
        lines.append(
            f"⚠ {n_at_cap} mã đang chạm trần "
            f"{float(w_max) * 100:.0f}%/mã."
        )
    lines.append("")

    order = ("BUY", "WATCH", "SELL") if not filt else (filt,)
    headers = {
        "BUY": "🟢 Tín hiệu đáng chú ý",
        "WATCH": "🟡 Theo dõi",
        "SELL": "🔴 Tránh mua mới",
    }
    badges = {"BUY": "🟢", "WATCH": "🟡", "SELL": "🔴"}
    page_sizes = {
        "BUY": SIGNALS_PAGE_SIZE_NOTABLE,
        "WATCH": SIGNALS_PAGE_SIZE_WATCH,
        "SELL": SIGNALS_PAGE_SIZE_SELL,
    }

    for act in order:
        rows = by_action[act]
        if act == "BUY" and n_buy == 0:
            lines.append(f"── {headers[act]} (0) ──")
            lines.append(
                "• Chưa có mã đạt đủ điều kiện mua — thị trường đang trong "
                "giai đoạn thận trọng theo mô hình (chưa đủ điều kiện «đáng chú ý»)."
            )
            lines.append("")
            continue
        if not rows:
            continue
        if use_page:
            size = page_sizes[act]
            start = page_i * size
            rows = rows[start : start + size]
            if not rows:
                continue
        lines.append(f"── {headers[act]} ({len(by_action[act])}) ──")
        badge = badges[act]
        for row in rows:
            size_txt = format_size_with_cap(row.get("size"), w_max=w_max)
            ticker = row.get("ticker")
            score = row.get("score")
            try:
                sc = float(score) if score is not None else None
            except (TypeError, ValueError):
                sc = None
            score_icon = "🟢" if sc is not None and sc > 0 else (
                "🔴" if sc is not None and sc < 0 else "🟡"
            )
            lines.append(
                f"• {badge} {ticker}  | {score_icon} điểm {_fmt_num(score)}  "
                f"| biến động {_fmt_num(row.get('sigma_hat'), 4)}  "
                f"| tỷ trọng {size_txt}"
            )
            lines.append(f"  → Chi tiết: /check {ticker}")
        lines.append("")

    if not use_page and not filt:
        known = set(("BUY", "WATCH", "SELL"))
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


def format_watchlist(
    rows: list[dict],
    *,
    view_filter: str | None = None,
) -> str:
    """/watchlist — tin đầu chỉ đếm; danh sách mã khi ``view_filter``=PASS|WATCH."""
    if not rows:
        return (
            "📭 Rổ lọc doanh nghiệp đang trống.\n\n"
            "Cần chạy lần rà lọc doanh nghiệp (BCTC năm) trước.\n\n"
            + DISCLAIMER
        )
    as_of = rows[0].get("as_of_date", "")
    pass_rows = [
        r for r in rows if str(r.get("fundamental_view", "")).upper() == "PASS"
    ]
    watch_rows = [
        r for r in rows if str(r.get("fundamental_view", "")).upper() == "WATCH"
    ]
    filt = str(view_filter or "").upper() or None

    if filt == "PASS":
        lines = [
            f"📂 Danh sách ĐẠT — {len(pass_rows)} mã",
            f"Theo BCTC năm (ước tính ngày công bố): {_fmt_day_vi(as_of)}",
            "",
            " · ".join(str(r.get("ticker")) for r in pass_rows) if pass_rows else "(trống)",
            "",
            "Gõ /check <mã> để xem chi tiết từng mã.",
            "",
            DISCLAIMER,
        ]
        return "\n".join(lines)
    if filt == "WATCH":
        lines = [
            f"📂 Danh sách THEO DÕI — {len(watch_rows)} mã",
            f"Theo BCTC năm (ước tính ngày công bố): {_fmt_day_vi(as_of)}",
            "",
            " · ".join(str(r.get("ticker")) for r in watch_rows) if watch_rows else "(trống)",
            "",
            "Gõ /check <mã> để xem chi tiết từng mã.",
            "",
            DISCLAIMER,
        ]
        return "\n".join(lines)

    # Opener — mockup: chỉ đếm + ghi chú BCTC năm.
    lines = [
        "📂 Rổ lọc doanh nghiệp — theo BCTC năm gần nhất đã công bố (không phải theo quý)",
        "",
        f"🟢 {len(pass_rows)} mã ĐẠT — đủ điều kiện vào rổ giao dịch",
        f"🟡 {len(watch_rows)} mã THEO DÕI — cần xem thêm trước khi vào rổ",
        "",
        "ⓘ \"BCTC năm\" nghĩa là hệ thống dùng báo cáo tài chính CẢ NĂM gần nhất, "
        "không chấm theo từng quý.",
        f"Ngày {_fmt_day_vi(as_of)} là ngày ước tính công ty công bố báo cáo đó, "
        "không phải ngày giao dịch.",
        "",
        "Bấm nút bên dưới để xem danh sách mã.",
        "",
        DISCLAIMER,
    ]
    return "\n".join(lines)


def format_regime_message(
    p_bull: float | None,
    as_of: str | None = None,
    *,
    prev_p_bull: float | None = None,
) -> str:
    """/regime — mockup: 1 dòng khí hậu (không lặp Kết luận + %), vì sao + ảnh hưởng."""
    day = _fmt_day_vi(as_of) if as_of else ""
    header = f"🌡 Khí hậu thị trường{f' — {day}' if day else ''}"
    if p_bull is None:
        body_parts = [
            "Kết luận: chưa có dữ liệu phiên gần nhất.",
            "→ Vì sao: store chưa có p_regime sau daily.",
            "Thử lại sau khi hệ thống chạy xong phiên (thường sau 15:00).",
        ]
        as_of_line = format_as_of_session_line(as_of)
        if as_of_line:
            body_parts.insert(0, as_of_line)
        body = "\n".join(body_parts)
    else:
        light = regime_traffic_light(p_bull)
        score = float(p_bull) * 100.0
        body_parts = [
            (
                f"{light} {regime_label_prefix(p_bull).capitalize()} "
                f"(mô hình tin khá chắc, điểm {score:.0f}/100)"
                if float(p_bull) < 0.45 or float(p_bull) >= 0.70
                else (
                    f"{light} {regime_label_prefix(p_bull).capitalize()} "
                    f"(điểm {score:.0f}/100)"
                )
            ),
        ]
        cmp_line = regime_session_compare(p_bull, prev_p_bull)
        if cmp_line:
            # Mockup: «So với hôm qua: không đổi.»
            body_parts.append(cmp_line.replace("So với phiên trước", "So với hôm qua"))
        else:
            body_parts.append("So với hôm qua: —")
        body_parts.extend(
            [
                "",
                f"→ Vì sao: {translate_regime(p_bull)}",
                (
                    "→ Ảnh hưởng: hệ thống hạn chế đề xuất mua mới cho đến khi "
                    "tín hiệu đổi chiều."
                    if float(p_bull) < 0.55
                    else "→ Ảnh hưởng: hệ thống có thể đề xuất mua mới khi đủ điều kiện mã."
                ),
            ]
        )
        body = "\n".join(body_parts)
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
            # Cùng công thức D-3 (tránh «nghiêng tăng ~0%» mâu thuẫn).
            p_line = (
                f"Khí hậu: {regime_label_prefix(p_regime)} (~{pct}) — "
                f"{translate_regime(p_regime)}"
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
    # E-1: kết luận 1 câu → vì sao → chi tiết (4 khối).
    action_banner = _ACTION_BANNER.get(action, f"Tín hiệu hệ thống: {action}")
    if str(view_raw).upper() == "PASS" and action == "WATCH":
        story = (
            f"{ticker} đạt chuẩn doanh nghiệp nhưng hệ thống chưa thấy điểm vào rõ."
        )
    elif str(view_raw).upper() == "PASS" and action == "BUY":
        story = (
            f"{ticker} đạt chuẩn doanh nghiệp và có tín hiệu đáng chú ý."
        )
    elif str(view_raw).upper() == "PASS" and action == "SELL":
        story = (
            f"{ticker} đạt chuẩn doanh nghiệp nhưng nên tránh mua mới."
        )
    else:
        story = f"{ticker} — xem tín hiệu hệ thống bên dưới."
    lines = [
        f"📌 {title}",
        f"Phiên giao dịch: {_fmt_day_vi(str(day)) if day else '—'}",
    ]
    as_of_line = format_as_of_session_line(str(day)[:10] if day else None)
    if as_of_line:
        lines.append(as_of_line)
    lines.extend(
        [
            "",
            f"Kết luận: {story}",
            action_banner,
            translate_action(action),
        ]
    )
    if watch_capped:
        lines.append(
            "(Fundamental đang WATCH — không nâng thành MUA chính thức.)"
        )
    if str(view_raw).upper() == "WATCH":
        lines.append("Quant/Risk chỉ mang tính tham khảo cho mã WATCH.")
    lines.append("")
    lines.append("→ Vì sao:")
    view_u = str(view_raw).upper()
    if view_u == "PASS":
        fund_icon, fund_txt = "🟢", translate_fundamental_view(view_raw)
    elif view_u == "WATCH":
        fund_icon, fund_txt = "🟡", translate_fundamental_view(view_raw)
    elif view_u == "FAIL":
        fund_icon, fund_txt = "🔴", translate_fundamental_view(view_raw)
    else:
        fund_icon, fund_txt = "⚪", translate_fundamental_view(view_raw)
    lines.append(f"  {fund_icon} Doanh nghiệp: {fund_txt}")
    if p_regime is not None:
        try:
            reg_icon = regime_traffic_light(float(p_regime))
            lines.append(
                f"  {reg_icon} Thị trường chung: {regime_label_prefix(p_regime)}, "
                f"{translate_regime(p_regime)}"
            )
        except (TypeError, ValueError):
            lines.append(f"  ⚪ Thị trường: {p_line}")
    else:
        lines.append("  ⚪ Thị trường chung: chưa có dữ liệu")
    slope = reason.get("slope_tstat")
    trend_plain = translate_kalman_trend(slope)
    try:
        abs_t = abs(float(slope)) if slope is not None else None
    except (TypeError, ValueError):
        abs_t = None
    if abs_t is not None and abs_t >= 2:
        trend_icon = "🟢" if float(slope) > 0 else "🔴"
    else:
        trend_icon = "⚪"
    lines.append(f"  {trend_icon} Xu hướng riêng mã: {trend_plain}")
    lines.append("")
    lines.append(DETAIL_MARKER)

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
            f"định giá {_fmt_num(fundamental_row.get('valuation_score'))} "
            f"{_pillar_score_scale_note()}"
        )
        lines.append(
            "Ghi chú: chưa có chỉ số gốc mục 6.1 trong store — chạy lại lần rà lọc doanh nghiệp để cập nhật."
        )

    lines.extend(
        [
            "",
            "② Thị trường chung",
            p_line.replace("Khí hậu:", "Khả năng thị trường:"),
            "",
            "③ Xu hướng mã này",
        ]
    )
    # D-5: tách Kalman (slope_tstat) khỏi điểm tổng hợp (score).
    lines.append(
        f"{translate_kalman_trend(slope)} "
        f"(t-stat {_fmt_num(slope)}; |t|≥2 ≈ xu hướng rõ so với nhiễu)"
    )
    score = signal_row.get("score")
    if score is not None:
        lines.append(f"Điểm tổng hợp: {_fmt_num(score)}")

    lines.append("")
    lines.append("④ Rủi ro & tỷ trọng")
    if last_close is not None:
        lines.append(f"Giá gần nhất: {_fmt_num(last_close)}")
    lines.append(
        f"Biến động ngày: {_fmt_pct(signal_row.get('sigma_hat'), 2)}  ·  "
        f"Cắt lỗ gợi ý: {_fmt_num(signal_row.get('stop'))}"
    )
    # D-4: nhánh chữ không thêm «danh mục» phía sau.
    try:
        _sz = float(size) if size is not None else None
    except (TypeError, ValueError):
        _sz = None
    if _sz is None or _sz == 0.0 or (0.0 < _sz < 0.005):
        lines.append(f"Tỷ trọng gợi ý: {size_pct}")
    else:
        lines.append(f"Tỷ trọng gợi ý: {size_pct} danh mục")
    if weight is not None and weight != size:
        lines.append(f"Tỷ trọng sau tối ưu danh mục (nếu có): {weight_pct}")
    if signal_row.get("p_tp_before_sl") is not None:
        lines.append(
            f"Xác suất chạm mục tiêu trước cắt lỗ: {_fmt_pct(signal_row.get('p_tp_before_sl'), 0)}"
        )
    else:
        # D-9: ngôn ngữ sản phẩm, không «chưa bật» kiểu config.
        lines.append(
            "Bot chưa chạy mô phỏng xác suất nâng cao cho mã này."
        )
    if signal_row.get("cvar95") is not None:
        lines.append(format_cvar95_line(signal_row.get("cvar95")))

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
    # Round2: timestamp đồng bộ /check — ưu tiên as_of / signal_date / price_date.
    as_of = (
        meta.get("as_of")
        or meta.get("signal_date")
        or meta.get("price_date")
    )
    as_of_line = format_as_of_session_line(
        str(as_of)[:10] if as_of else None
    )
    if as_of_line:
        lines.append(as_of_line)
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
            f"định giá {_fmt_num(fundamental_row.get('valuation_score'))} "
            f"{_pillar_score_scale_note()}"
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
            f"Kết luận: {t} ngoài phạm vi chiến lược hiện tại.",
            "→ Vì sao: không nằm trong universe cấu hình (CSV Tầng 1); "
            "bot không chấm Fundamental/Quant cho mã ngoài phạm vi.",
            "→ Gợi ý: xem mã đang hỗ trợ qua /watchlist · /signals.",
            "",
            "── Chi tiết ──",
            "⛔ Ngoài phạm vi chiến lược hiện tại",
            # D-2: giá (nếu có) chỉ tham khảo — ngoài scope ≠ thiếu dữ liệu
            "Đây là dữ liệu tham khảo giá — mã ngoài phạm vi chiến lược, "
            "không phải vì thiếu dữ liệu.",
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
            f"Kết luận: {t} thuộc nhóm tài chính — ngoài phạm vi chiến lược V1.",
            f"→ Vì sao: ngành «{industry}»; bộ lọc V1 tắt ngân hàng / "
            "chứng khoán / bảo hiểm (exclude_financials).",
            "→ Gợi ý: xem /watchlist (mã phi tài chính) hoặc /chart "
            f"{t} price để tham khảo giá.",
            "",
            "── Chi tiết ──",
            "⛔ Ngoài phạm vi chiến lược V1 (tài chính)",
            "Không chạy Quant và không tạo tín hiệu giao dịch cho nhóm này — "
            "đây là quyết định phạm vi, không phải thiếu BCTC hay lỗi pipeline.",
            # D-2: có giá tham khảo ≠ đã được chấm chiến lược
            "Đây là dữ liệu tham khảo giá — mã này bị loại khỏi chiến lược do "
            "thuộc nhóm tài chính, không phải vì thiếu dữ liệu.",
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
            f"Kết luận: {t} chưa đủ dữ liệu doanh nghiệp để chấm điểm.",
            "→ Vì sao: thiếu BCTC/chỉ số Layer 1 hoàn chỉnh → chưa chạy Quant "
            "→ không có tín hiệu hệ thống (thiếu dữ liệu ≠ doanh nghiệp xấu).",
            f"→ Gợi ý: /chart {t} price · /watchlist.",
            "",
            "── Chi tiết ──",
            "⚠️ Chưa đủ dữ liệu Fundamental",
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
            f"Kết luận: {t} không vượt bộ lọc doanh nghiệp hiện tại.",
            "→ Vì sao: đã chấm Layer 1 và không đạt ngưỡng "
            "(khác với «thiếu dữ liệu»).",
            f"→ Gợi ý: /chart {t} fundamental · /watchlist.",
            "",
            "── Chi tiết ──",
            "⛔ Không vượt bộ lọc Fundamental",
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
            f"Kết luận: {t} đạt chuẩn doanh nghiệp (PASS) nhưng "
            "hệ thống CHƯA có tín hiệu Quant trong store.",
            "→ Vì sao: bot không chạy Quant on-demand — cần daily_job "
            "ghi signals sau phiên.",
            "→ Gợi ý: thêm theo dõi (/subscribe) hoặc xem /signals · "
            f"/chart {t} price.",
            "",
            "── Chi tiết ──",
            "🟡 Fundamental PASS — chưa có tín hiệu Quant trong store",
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
    pos_concl = _POSITION_ACTION_BANNER.get(
        pos_action, f"Trạng thái: {pos_action}"
    )
    pnl_txt = _fmt_pct(pnl_pct, 1)
    lines.extend(
        [
            "",
            f"Kết luận: đang nắm {ticker} (vị thế giấy) — {pos_concl}.",
            f"→ P/L ước tính: {pnl_txt}",
            "→ Vì sao: ưu tiên trạng thái vị thế hơn tín hiệu nghiên cứu "
            "khi đang OPEN (ban_phac §8).",
            "",
            "── Chi tiết ──",
            "📦 ĐANG NẮM GIỮ (vị thế giấy)",
            pos_concl,
            "",
            "① P/L & vị thế",
            f"Giá vào: {_fmt_num(entry)}  ·  Giá hiện tại: {_fmt_num(last_close)}",
            f"P/L ước tính: {pnl_txt}",
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
                f"Kết luận: {t} đang theo dõi (Fundamental WATCH) — "
                "chưa có hàng Quant trong store.",
                "→ Vì sao: WATCH không nâng thành MUA; thiếu tín hiệu phiên.",
                "",
                "── Chi tiết ──",
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
            "(chưa chạy / chưa vào lần rà lọc doanh nghiệp gần nhất)."
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


def format_positions(
    rows: list[dict],
    *,
    w_max: float = 0.10,
    last_closes: Mapping[str, float] | None = None,
    as_of: str | None = None,
    detail: bool = False,
) -> str:
    """Bảng /positions — opener: icon P/L + giữ N phiên; giá vào/cắt lỗ chỉ khi detail."""
    paper_disclaimer = (
        "ⓘ Vị thế giấy = bot mô phỏng mở khi có tín hiệu MUA, giữ đến khi có tín hiệu "
        "BÁN rõ ràng cho đúng mã đó — KHÔNG tự động cắt lỗ theo giá; mức cắt lỗ "
        "chỉ để bạn tham khảo."
    )
    if not rows:
        return (
            "📭 Chưa có vị thế giấy đang mở.\n\n"
            f"{paper_disclaimer}\n\n"
            "Kết luận: chưa có mã nào đang nắm trên sổ giấy.\n"
            "→ Hệ thống mở vị thế giấy khi phiên có khuyến nghị MUA.\n"
            "Tỷ trọng mỗi mã = theo biến động mục tiêu (không chia đều).\n"
            "Xem gợi ý hôm nay: /signals\n\n"
            + DISCLAIMER
        )
    closes = dict(last_closes or {})
    total = 0.0
    n_sized = 0
    n_at_cap = 0
    pnl_weight_sum = 0.0
    size_weight_sum = 0.0
    computed: list[dict[str, Any]] = []
    for row in rows:
        size = row.get("size_pct_nav")
        s_f: float | None
        try:
            s_f = float(size) if size is not None else None
        except (TypeError, ValueError):
            s_f = None
        if s_f is not None:
            total += s_f
            n_sized += 1
            if size_hits_w_max(s_f, w_max):
                n_at_cap += 1
        ticker = str(row.get("ticker") or "").upper()
        entry = row.get("entry_price")
        last = closes.get(ticker)
        if last is None and row.get("last_close") is not None:
            try:
                last = float(row["last_close"])
            except (TypeError, ValueError):
                last = None
        pnl_one = None
        if entry is not None and last is not None:
            try:
                e = float(entry)
                if e:
                    pnl_one = float(last) / e - 1.0
                    if s_f is not None:
                        pnl_weight_sum += pnl_one * s_f
                        size_weight_sum += s_f
            except (TypeError, ValueError):
                pnl_one = None
        hold_n = holding_sessions_from_opened_at(row.get("opened_at"), as_of)
        computed.append(
            {
                "row": row,
                "ticker": ticker or str(row.get("ticker") or ""),
                "entry": entry,
                "stop": row.get("stop_price"),
                "size_txt": format_size_with_cap(size, w_max=w_max),
                "pnl": pnl_one,
                "hold_n": hold_n,
            }
        )

    portfolio_pnl = (
        pnl_weight_sum / size_weight_sum if size_weight_sum > 0 else None
    )
    pnl_icon = _pnl_traffic_icon(portfolio_pnl)

    if detail:
        lines = [
            f"▾ Chi tiết vị thế giấy — {len(rows)} mã",
            paper_disclaimer,
        ]
    else:
        lines = [
            (
                f"💼 Vị thế giấy đang mở — {len(rows)} mã"
                + (
                    f" · tổng P/L ước tính: {pnl_icon} {_fmt_pct(portfolio_pnl, 1)}"
                    if portfolio_pnl is not None
                    else " · chưa đủ giá để ước tổng P/L"
                )
            ),
            "",
            paper_disclaimer,
        ]
    as_of_line = format_as_of_session_line(as_of)
    if as_of_line:
        lines.append(as_of_line)
    lines.append("")
    if n_at_cap:
        lines.append(
            f"⚠ {n_at_cap} mã đang chạm trần "
            f"{float(w_max) * 100:.0f}%/mã — không phải lỗi chia đều."
        )
        lines.append("")

    for item in computed:
        icon = _pnl_traffic_icon(item["pnl"])
        hold_txt = (
            f"giữ {item['hold_n']} phiên"
            if item["hold_n"] is not None
            else "giữ — phiên"
        )
        pnl_txt = _fmt_pct(item["pnl"], 1) if item["pnl"] is not None else "—"
        if detail:
            lines.extend(
                [
                    f"{icon} {item['ticker']}   {pnl_txt}  · {hold_txt} · "
                    f"tỷ trọng {item['size_txt']}",
                    f"  Giá vào: {_fmt_num(item['entry'])}  ·  "
                    f"Cắt lỗ (tham khảo): {_fmt_num(item['stop'])}",
                    f"  Mở: {_fmt_day_vi(item['row'].get('opened_at'))}",
                    "",
                ]
            )
        else:
            lines.append(
                f"{icon} {item['ticker']}   {pnl_txt}  · {hold_txt} · "
                f"tỷ trọng {item['size_txt']}"
            )

    if not detail:
        lines.extend(
            [
                "",
                "Chi tiết giá vào & cắt lỗ: bấm ▾ Xem chi tiết từng mã.",
                "So sánh gợi ý: /signals · /check <mã>",
                "",
                DISCLAIMER,
            ]
        )
    else:
        lines.extend(
            [
                "So sánh gợi ý: /signals · /check <mã>",
                "",
                DISCLAIMER,
            ]
        )
    return "\n".join(lines)


def _format_exposure_stats_line(row: Mapping[str, Any]) -> str | None:
    """Một dòng tóm tắt exposure khi có trong row (D-7).

    Chấp nhận ``exposure_stats`` (dict) hoặc field phẳng ``avg_exposure`` /
    ``pct_sessions_cash_gt_80`` từ metrics — không suy từ equity_curve.
    """
    exp: Any = row.get("exposure_stats")
    if isinstance(exp, dict):
        avg = exp.get("avg_exposure")
        cash = exp.get("pct_sessions_cash_gt_80")
        avg_n = exp.get("avg_n_positions")
    else:
        avg = row.get("avg_exposure")
        cash = row.get("pct_sessions_cash_gt_80")
        avg_n = row.get("avg_n_positions")
    if avg is None and cash is None and avg_n is None:
        return None
    bits: list[str] = []
    if avg is not None:
        bits.append(f"phơi nhiễm TB {_fmt_pct(avg, 1)}")
    if cash is not None:
        bits.append(f"~{_fmt_pct(cash, 0)} phiên gần full tiền mặt")
    if avg_n is not None:
        bits.append(f"số mã mở TB {_fmt_num(avg_n, 1)}")
    if not bits:
        return None
    return "Exposure: " + " · ".join(bits)


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

    # E-3: 1 câu mở đầu ngôn ngữ thường trước bảng số.
    try:
        s_fw = float(fw["sharpe"]) if fw.get("sharpe") is not None else None
        s_b0 = float(b0["sharpe"]) if b0.get("sharpe") is not None else None
    except (TypeError, ValueError):
        s_fw, s_b0 = None, None

    opener: str
    if s_fw is not None and s_b0 is not None:
        if s_fw < s_b0:
            opener = (
                f"🔴 Trên dữ liệu kiểm thử, chiến lược hệ thống "
                f"(Sharpe {_fmt_num(s_fw)}) đang thấp hơn nhiều so với chỉ mua "
                f"& giữ đơn giản (Sharpe {_fmt_num(s_b0)}) — đây là phát hiện hợp lệ, "
                "không phải lỗi hiển thị."
            )
        elif s_fw > s_b0:
            opener = (
                f"🟢 Trên dữ liệu kiểm thử, chiến lược hệ thống "
                f"(Sharpe {_fmt_num(s_fw)}) cao hơn mua & giữ "
                f"(Sharpe {_fmt_num(s_b0)})."
            )
        else:
            opener = (
                f"🟡 Trên dữ liệu ngoài mẫu, Sharpe khung ≈ mua & giữ "
                f"({_fmt_num(s_fw)})."
            )
    else:
        opener = (
            "Kết luận: đây là báo cáo nghiên cứu ngoài mẫu đã ghi sẵn "
            "— không phải lãi/lỗ tài khoản thật."
        )

    lines = [
        "📈 Kết quả kiểm thử chiến lược (ngoài mẫu — không phải lãi/lỗ thật)",
        "",
        opener,
        "",
        # Round2 Phần 3.1: B0 n_trades=0 vẫn có Sharpe — đúng bản chất equity daily.
        "→ B0 (mua & giữ) không có «lệnh» nào sau lần mua đầu, nên Sharpe/CAGR của B0 "
        "vẫn tính được từ biến động giá trị danh mục hàng ngày, không phụ thuộc số lệnh "
        "— không phải bịa số liệu.",
        f"Phạm vi: {scope} · mã chạy: {run_id} · ghi ngày {_fmt_day_vi(run_at)}",
        "",
        "── Chi tiết so sánh ──",
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
    if s_fw is not None and s_b0 is not None and s_fw < s_b0:
        lines.append(
            f"📌 Phát hiện hợp lệ: khung hệ thống (Sharpe OOS {_fmt_num(s_fw)}) "
            f"thua B0 ({_fmt_num(s_b0)}) trên mẫu này — "
            "giữ trong DECISIONS; không flip MC/BL."
        )
        lines.append("")

    try:
        if n_fw is not None and int(n_fw) < 30:
            # D-9: ngôn ngữ nhà đầu tư, không giống log debug.
            lines.append(
                f"⚠️ Số lệnh ngoài mẫu còn ít (~{int(n_fw)}; thường cần ≥30 "
                "để kết luận chắc hơn). "
                "Sharpe / Calmar / Sortino chỉ mang tính minh hoạ."
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
            f"Sharpe (lãi/rủi ro): {_fmt_num(row.get('sharpe'))}"
        )
        lines.append(
            f"Sụt tối đa: {_fmt_pct(row.get('max_drawdown'), 1)}  ·  "
            f"Số lệnh: {row.get('n_trades', '—')}"
        )
        # D-9: tách chỉ số học thuật — 1 câu tóm tắt trước.
        lines.append(
            "Chỉ số bổ sung (nghiên cứu): "
            f"Sortino {_fmt_num(row.get('sortino'))} · "
            f"Calmar {_fmt_num(row.get('calmar'))} · "
            f"biên an toàn ~{_fmt_num(row.get('margin_bps'))} bps · "
            f"phục hồi ~"
            f"{row.get('max_drawdown_days') if row.get('max_drawdown_days') is not None else '—'} phiên"
        )
        if row.get("turnover") is not None:
            lines.append(f"Vòng quay danh mục (ước): {_fmt_num(row.get('turnover'), 4)}")
        # D-7: thống kê bổ sung khi field có trong row (không bịa số).
        supp_bits: list[str] = []
        if row.get("win_rate") is not None:
            supp_bits.append(f"tỷ lệ thắng {_fmt_pct(row.get('win_rate'), 1)}")
        if row.get("total_return") is not None:
            supp_bits.append(f"tổng lãi {_fmt_pct(row.get('total_return'), 1)}")
        if row.get("profit_factor") is not None:
            supp_bits.append(f"hệ số lãi/lỗ {_fmt_num(row.get('profit_factor'))}")
        if supp_bits:
            lines.append("Thống kê bổ sung: " + " · ".join(supp_bits))
        exp_line = _format_exposure_stats_line(row)
        if exp_line:
            lines.append(exp_line)
        if row.get("equity_curve_json"):
            lines.append("Biểu đồ đường vốn: xem ảnh bên dưới (cùng khung OOS).")
        lines.append("")

    if checks:
        lines.append("── Kiểm tra đã đăng ký trước (✅/❌) ──")
        for chk in checks:
            mark = "✅" if int(chk.get("passed") or 0) else "❌"
            name = translate_backtest_check_name(chk.get("check_name"))
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


def unknown_share_from_sector_rows(rows: list[dict]) -> float | None:
    """Tỷ lệ mã thuộc ngành UNKNOWN trên tổng ``n_total`` của overview /sector.

    ``None`` khi không có dòng / tổng = 0.
    """
    if not rows:
        return None
    total = 0
    unknown = 0
    for row in rows:
        n = int(row.get("n_total") or 0)
        total += n
        if str(row.get("industry") or "").strip().upper() == "UNKNOWN":
            unknown += n
    if total <= 0:
        return None
    return float(unknown) / float(total)


def format_unknown_sector_warning(
    share: float | None,
    *,
    threshold: float = 0.10,
    n_unknown: int | None = None,
) -> str | None:
    """Cảnh báo khi tỷ lệ UNKNOWN > ngưỡng (mặc định 10%). Không bịa ngành."""
    if share is None:
        return None
    if share <= threshold:
        return None
    pct = share * 100.0
    if n_unknown is not None and n_unknown > 0:
        head = (
            f"⚠ Cảnh báo: dữ liệu ngành đang thiếu cho {int(n_unknown)} mã "
            f"({pct:.0f}% > {threshold * 100:.0f}%)"
        )
    else:
        head = (
            f"⚠ Cảnh báo: {pct:.0f}% mã đang ở ngành UNKNOWN "
            f"(>{threshold * 100:.0f}%)"
        )
    return (
        f"{head} — xem /tinhtrangdulieu. "
        "Chạy sector_job --universe-file data/universe/vn100.csv "
        "để populate sector_mapping — không tự gán ngành trong bot."
    )


def format_sector_overview(
    rows: list[dict],
    as_of: str | None = None,
    *,
    has_sector_mapping: bool = True,
    has_watchlist: bool = True,
    unknown_share: float | None = None,
) -> str:
    """Tổng quan /sector — top-down theo industry."""
    if not rows:
        reasons = []
        if not has_watchlist:
            reasons.append("chưa có watchlist (chạy lần rà lọc doanh nghiệp)")
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
        "Nếu cách hôm nay quá xa: cần chạy lại lần rà lọc doanh nghiệp "
        "(BCTC năm mới) — không phải lỗi /sector.",
        "",
    ]
    share = (
        unknown_share
        if unknown_share is not None
        else unknown_share_from_sector_rows(rows)
    )
    n_unknown = None
    if share is not None:
        unk = 0
        for row in rows:
            if str(row.get("industry") or "").strip().upper() == "UNKNOWN":
                unk += int(row.get("n_total") or 0)
        n_unknown = unk
    warn = format_unknown_sector_warning(share, n_unknown=n_unknown)
    if warn:
        lines.extend([warn, ""])
    for row in rows:
        ind = str(row.get("industry") or "?").strip()
        if ind.upper() == "UNKNOWN":
            lines.append(
                f"⚪ Chưa xác định ngành: {row.get('n_total', 0)} mã — "
                "dữ liệu ngành đang được bổ sung, không phải lỗi hiển thị."
            )
            continue
        n_pass = int(row.get("n_pass") or 0)
        n_watch = int(row.get("n_watch") or 0)
        n_fail = int(row.get("n_fail") or 0)
        if n_pass > 0 and n_fail == 0:
            icon = "🟢"
        elif n_pass > 0:
            icon = "🟡"
        else:
            icon = "⚪"
        lines.append(
            f"{icon} {ind}: {n_pass} đạt · {n_watch} theo dõi"
            + (f" · {n_fail} loại" if n_fail else "")
        )
    lines.extend(
        [
            "",
            "Đạt/Theo dõi = còn trong rổ · Loại = không vào rổ.",
            "Tiếp: /watchlist · /check <mã> · /signals · /tinhtrangdulieu",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_tinh_trang_du_lieu(
    *,
    latest_signal_date: str | None = None,
    watchlist_n: int = 0,
    open_positions_n: int = 0,
    unknown_sector_share: float | None = None,
    config_flags: dict[str, bool] | None = None,
    include_config_flags: bool = False,
) -> str:
    """/tinhtrangdulieu — bảng EOD vs realtime (Round2 Phần 7); bot chỉ đọc store."""
    lines = [
        "📡 Tình trạng dữ liệu",
        "",
        "Kết luận: mọi lệnh Telegram chỉ đọc dữ liệu đã tính sẵn trong store — "
        "không gọi realtime khi bạn chat.",
        "",
    ]
    as_of_line = format_as_of_session_line(latest_signal_date)
    if as_of_line:
        lines.append(as_of_line)
    else:
        lines.append("Dữ liệu tính đến phiên: (chưa có tín hiệu trong store)")
    lines.extend(
        [
            f"• Watchlist: {watchlist_n} mã  ·  Vị thế giấy mở: {open_positions_n}",
            "",
            "── EOD vs realtime (kiến trúc) ──",
            "• EOD giá đóng cửa (OHLCV): chạy 1 lần/ngày sau 15:00 "
            "(pipeline/daily_job) → ghi store.price_bars. "
            "Bot không gọi provider giá khi bạn gõ lệnh.",
            "• BCTC / Fundamental: rà lại định kỳ (~3 tháng/lần) xem có BCTC NĂM "
            "mới chưa (pipeline/quarterly_job) → store.fundamental_scores. "
            "Bot chỉ đọc điểm đã lưu.",
            "• DNSE realtime API: chỉ khi job pipeline cần valuation tức thời "
            "— không bao giờ từ bot/.",
            "• Lệnh /check · /signals · /regime · /backtest · /positions · "
            "/watchlist · /sector: 100% đọc store (EOD/đã lưu) — không realtime.",
            "",
        ]
    )
    warn = format_unknown_sector_warning(unknown_sector_share)
    if warn:
        lines.extend([warn, ""])
    if include_config_flags and config_flags is not None:
        lines.append("── Cờ mô hình (bật/tắt) ──")
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
        lines.append("")
    lines.extend(
        [
            (
                "Tiếp: /signals · /help · /tinhtrangdulieu"
                if include_config_flags
                else "Tiếp: /signals · /help · /status"
            ),
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
    unknown_sector_share: float | None = None,
) -> str:
    """/status — mirror /tinhtrangdulieu + cờ config (Round2 Phần 6)."""
    # Mirror nội dung tình trạng dữ liệu; giữ cờ mô hình cho ops.
    return format_tinh_trang_du_lieu(
        latest_signal_date=latest_signal_date,
        watchlist_n=watchlist_n,
        open_positions_n=open_positions_n,
        unknown_sector_share=unknown_sector_share,
        config_flags=config_flags,
        include_config_flags=True,
    )


# ---------------------------------------------------------------------------
# Phần C — InlineKeyboard / ReplyKeyboard (chỉ điều hướng + đọc store)
# ---------------------------------------------------------------------------

# action ∈ {price, radar, ta, pnl, detail}; callback chk:<action>:<TICKER>
# watch_add đã ẩn (Round 2) — không schema user_follows lần này.
_CHECK_ACTIONS = frozenset({"price", "radar", "ta", "pnl", "detail"})


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

    # E-1: nút thu gọn/mở chi tiết — reuse chk: (Phần C), không viết CallbackQuery mới.
    if state in (
        CHECK_FAIL,
        CHECK_WATCH,
        CHECK_PASS_NO_SIGNAL,
        CHECK_PASS,
        CHECK_POSITION,
        CHECK_INSUFFICIENT,
    ):
        _add("▾ Xem đầy đủ số liệu", "detail")

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


def build_signals_opener_keyboard(
    *,
    n_buy: int,
    n_watch: int,
    n_sell: int,
):
    """Tin đầu /signals — nút mở từng nhóm + /regime (UX Redesign collapse)."""
    InlineKeyboardButton, InlineKeyboardMarkup, _, _ = _telegram_keyboard_imports()
    row: list = []
    if n_buy > 0:
        row.append(
            InlineKeyboardButton(
                f"▾ Xem {n_buy} mã đáng mua",
                callback_data=assert_callback_data_ok("sig:BUY:0"),
            )
        )
    if n_watch > 0:
        row.append(
            InlineKeyboardButton(
                f"▾ Xem {n_watch} mã theo dõi",
                callback_data=assert_callback_data_ok("sig:WATCH:0"),
            )
        )
    if n_sell > 0:
        row.append(
            InlineKeyboardButton(
                f"▾ Xem {n_sell} mã tránh mua",
                callback_data=assert_callback_data_ok("sig:SELL:0"),
            )
        )
    rows = []
    # Telegram: tối đa ~3 nút/hàng cho dễ đọc.
    if row:
        if len(row) <= 2:
            rows.append(row)
        else:
            rows.append(row[:2])
            rows.append(row[2:])
    rows.append(
        [
            InlineKeyboardButton(
                "📊 /regime chi tiết",
                callback_data=assert_callback_data_ok("nav:regime"),
            )
        ]
    )
    return InlineKeyboardMarkup(rows)


def build_signals_keyboard(
    page: int,
    total_pages: int,
    *,
    action_filter: str | None = None,
):
    """Nút ◀ / Trang X/Y / ▶ — ``page:signals:<n>`` hoặc ``sig:<ACT>:<n>``."""
    InlineKeyboardButton, InlineKeyboardMarkup, _, _ = _telegram_keyboard_imports()
    if total_pages <= 1:
        # Vẫn cho nút quay lại opener khi đang xem 1 nhóm.
        if action_filter:
            return InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "← Tóm tắt /signals",
                            callback_data=assert_callback_data_ok("sig:summary"),
                        )
                    ]
                ]
            )
        return None
    page_i = max(0, min(int(page), total_pages - 1))
    filt = str(action_filter or "").upper() or None
    row = []
    if page_i > 0:
        if filt:
            cb = assert_callback_data_ok(f"sig:{filt}:{page_i - 1}")
        else:
            cb = assert_callback_data_ok(f"page:signals:{page_i - 1}")
        row.append(InlineKeyboardButton("◀ Trước", callback_data=cb))
    row.append(
        InlineKeyboardButton(
            f"Trang {page_i + 1}/{total_pages}",
            callback_data=assert_callback_data_ok(
                f"sig:{filt}:{page_i}" if filt else f"page:signals:{page_i}"
            ),
        )
    )
    if page_i < total_pages - 1:
        if filt:
            cb = assert_callback_data_ok(f"sig:{filt}:{page_i + 1}")
        else:
            cb = assert_callback_data_ok(f"page:signals:{page_i + 1}")
        row.append(InlineKeyboardButton("Tiếp ▶", callback_data=cb))
    rows = [row]
    if filt:
        rows.append(
            [
                InlineKeyboardButton(
                    "← Tóm tắt /signals",
                    callback_data=assert_callback_data_ok("sig:summary"),
                )
            ]
        )
    return InlineKeyboardMarkup(rows)


def build_watchlist_keyboard(*, n_pass: int, n_watch: int):
    """Nút ▾ Xem danh sách ĐẠT / THEO DÕI."""
    InlineKeyboardButton, InlineKeyboardMarkup, _, _ = _telegram_keyboard_imports()
    row = []
    if n_pass > 0:
        row.append(
            InlineKeyboardButton(
                "▾ Xem danh sách ĐẠT",
                callback_data=assert_callback_data_ok("wl:PASS"),
            )
        )
    if n_watch > 0:
        row.append(
            InlineKeyboardButton(
                "▾ Xem danh sách THEO DÕI",
                callback_data=assert_callback_data_ok("wl:WATCH"),
            )
        )
    if not row:
        return None
    return InlineKeyboardMarkup([row])


def build_positions_keyboard(*, has_rows: bool):
    """Nút ▾ Xem chi tiết từng mã (giá vào, cắt lỗ)."""
    if not has_rows:
        return None
    InlineKeyboardButton, InlineKeyboardMarkup, _, _ = _telegram_keyboard_imports()
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "▾ Xem chi tiết từng mã (giá vào, cắt lỗ)",
                    callback_data=assert_callback_data_ok("pos:detail"),
                )
            ]
        ]
    )


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
                    "Xem /signals theo mã →",
                    callback_data=assert_callback_data_ok("nav:signals"),
                )
            ]
        ]
    )


def build_start_reply_keyboard():
    """ReplyKeyboard cố định cho /start — gồm nút Tình trạng dữ liệu (Round2)."""
    _, _, KeyboardButton, ReplyKeyboardMarkup = _telegram_keyboard_imports()
    return ReplyKeyboardMarkup(
        [
            [
                KeyboardButton("/check"),
                KeyboardButton("/signals"),
                KeyboardButton("/regime"),
            ],
            [
                KeyboardButton("/positions"),
                KeyboardButton("/tinhtrangdulieu"),
            ],
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
        f"📋 Kiểm tra đã đăng ký · {scope} · {run_id}",
        "",
    ]
    if not checks:
        lines.append("Chưa có check nào trong store cho lần chạy này.")
    else:
        for chk in checks:
            mark = "✅" if int(chk.get("passed") or 0) else "❌"
            name = translate_backtest_check_name(chk.get("check_name"))
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
            f"✓ {t} đang trong rổ theo dõi hệ thống (sau lần rà lọc doanh nghiệp).\n"
            f"Xem: /watchlist · /check {t}"
        )
    else:
        body = (
            f"ℹ {t} chưa có trong rổ lọc doanh nghiệp của hệ thống.\n"
            f"Bot không thêm mã vào pipeline khi bấm nút "
            "(chỉ đọc store).\n"
            f"Tiếp: /watchlist · /check {t} · /subscribe"
        )
    return f"{body}\n\n{DISCLAIMER}"

