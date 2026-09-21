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

# Giải thích tiếng người dùng cho /check (mục 9.7).
HEADLINE_VI = {
    "growth": "tăng trưởng lợi nhuận vài năm gần đây",
    "quality": "hiệu quả dùng vốn",
    "safety": "nợ so với khả năng sinh tiền",
    "valuation": "giá so với lịch sử và cùng ngành",
}

DISCLAIMER = (
    "⚠️ Sản phẩm học thuật, không phải tư vấn đầu tư, không thay thế tư vấn "
    "từ người có chứng chỉ hành nghề."
)

TA_REFERENCE_LABEL = "📊 Tham khảo thêm (không dùng để ra tín hiệu)"

_ACTION_VI = {
    "BUY": "Gợi ý mua / giữ nghiêng mua",
    "SELL": "Gợi ý giảm / tránh",
    "WATCH": "Theo dõi — chưa đủ tín hiệu rõ",
}

_ACTION_BANNER = {
    "BUY": "🟢 KHUYẾN NGHỊ: MUA",
    "SELL": "🔴 KHUYẾN NGHỊ: GIẢM / TRÁNH",
    "WATCH": "🟡 KHUYẾN NGHỊ: THEO DÕI",
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


def format_ta_reference_block(ta_indicators: dict) -> str:
    """Ghép khối 'Tham khảo thêm' từ các chỉ số TA cổ điển đã tính sẵn."""
    if not ta_indicators:
        return ""
    parts = [TA_REFERENCE_LABEL]
    if "rsi_14" in ta_indicators and ta_indicators["rsi_14"] is not None:
        parts.append(f"RSI(14): {ta_indicators['rsi_14']:.1f}")
    if ta_indicators.get("ma_trend"):
        parts.append(f"MA: {ta_indicators['ma_trend']}")
    if "volume_over_ma20" in ta_indicators and ta_indicators["volume_over_ma20"] is not None:
        parts.append(f"Vol/MA20: {ta_indicators['volume_over_ma20']:.2f}x")
    return "\n".join(parts)


def _fmt_num(value: Any, digits: int = 2) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "—"


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


def format_welcome() -> str:
    """/start và /help — hướng dẫn dùng bot (framework mục 9.7, giọng thân thiện)."""
    return "\n".join(
        [
            "Xin chào — Bot tín hiệu đầu tư (sản phẩm học thuật).",
            "",
            "Bot chỉ hiển thị kết quả đã tính sẵn sau mỗi phiên giao dịch "
            "(không tự tải lại dữ liệu khi bạn gõ lệnh).",
            "",
            "Bắt đầu nhanh:",
            "1) /subscribe — nhận tin khi có tín hiệu phiên mới",
            "2) /signals — danh sách gợi ý mua / giảm / theo dõi phiên gần nhất",
            "3) /check VNM — giải thích chi tiết một mã",
            "4) /watchlist — rổ mã qua bộ lọc doanh nghiệp",
            "5) /regime — thị trường đang nghiêng tăng hay giảm (chung cả rổ)",
            "6) /chart VNM price — biểu đồ giá gần đây",
            "",
            "Lưu ý hay gây hiểu nhầm:",
            "• “Khí hậu thị trường” trên /signals là chung cả rổ (thường theo VNINDEX) "
            "— cùng một mức cho mọi mã",
            "• Tỷ trọng gợi ý đang chia đều; khác nhau rõ khi bật tối ưu danh mục nâng cao",
            "• Khác biệt từng mã: hành động, điểm xu hướng, biến động và stop — xem /check",
            "",
            "Lệnh khác: /positions /sector /status /chart <mã> fundamental "
            "/backtest /unsubscribe /about",
            "",
            DISCLAIMER,
        ]
    )


def format_signals_list(signal_rows: list[dict]) -> str:
    """Một dòng/mã cho /signals — hiện số phân biệt từng mã + chú thích regime chung."""
    if not signal_rows:
        return (
            "Chưa có tín hiệu phiên nào.\n"
            "Thường có sau khi pipeline chạy xong phiên (khoảng sau 15:00). "
            "Nếu vẫn trống, báo admin kiểm tra lịch daily.\n\n"
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

    lines = [
        f"Tín hiệu phiên gần nhất{f' ({day})' if day else ''}:",
        "",
    ]
    if p_shared is not None:
        pct = f"{float(p_shared) * 100:.0f}%"
        lines.append(
            f"Khí hậu thị trường (chung mọi mã): nghiêng tăng khoảng {pct} "
            f"— {translate_regime(p_shared)}"
        )
        lines.append(
            "Tỷ trọng dưới đây đang chia đều. "
            "Số khác nhau theo mã: điểm xu hướng / biến động — gõ /check <mã>."
        )
        lines.append("")

    # Nhóm theo action để dễ đọc hơn liệt kê phẳng
    order = ("BUY", "SELL", "WATCH")
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
        lines.append(f"— {act} · {translate_action(act)} ({len(rows)}) —")
        for row in rows:
            size = row.get("size")
            size_pct = (
                f"{float(size) * 100:.1f}%"
                if size is not None
                else "—"
            )
            lines.append(
                f"{row.get('ticker')} | điểm={_fmt_num(row.get('score'))} | "
                f"biến động={_fmt_num(row.get('sigma_hat'), 4)} | "
                f"tỷ trọng≈{size_pct}  "
                f"→ /check {row.get('ticker')}"
            )
        lines.append("")

    for row in other:
        lines.append(
            f"{row.get('action')} — {row.get('ticker')} | "
            f"điểm={_fmt_num(row.get('score'))} → /check {row.get('ticker')}"
        )

    lines.append(DISCLAIMER)
    return "\n".join(lines)


def format_watchlist(rows: list[dict]) -> str:
    if not rows:
        return (
            "Watchlist trống.\n"
            "Đây là rổ PASS/WATCH sau bộ lọc cơ bản (Tầng 1). "
            "Cần chạy quarterly_job trước khi có danh sách.\n\n"
            + DISCLAIMER
        )
    as_of = rows[0].get("as_of_date", "")
    lines = [
        f"Watchlist Tầng 1{f' ({as_of})' if as_of else ''}:",
        "PASS = đủ điều kiện vào rổ quant; WATCH = theo dõi / chưa đủ tin cậy valuation.",
        "",
    ]
    for row in rows:
        lines.append(f"{row.get('ticker')}: {row.get('fundamental_view')}")
    lines.extend(
        ["", "Tiếp: /signals để xem tín hiệu phiên, /check <mã> để xem chi tiết.", "", DISCLAIMER]
    )
    return "\n".join(lines)


def format_regime_message(p_bull: float | None, as_of: str | None = None) -> str:
    header = f"Khí hậu thị trường{f' | {as_of}' if as_of else ''}:"
    if p_bull is None:
        body = "Chưa có dữ liệu phiên gần nhất."
    else:
        pct = f"{float(p_bull) * 100:.0f}%"
        body = (
            f"Xác suất nghiêng tăng khoảng {pct}\n"
            f"→ {translate_regime(p_bull)}"
        )
    return f"{header}\n{body}\n\n{DISCLAIMER}"


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
                f"Xác suất nghiêng tăng khoảng {pct}\n"
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
    header_bits = [str(ticker)]
    if market:
        header_bits.append(f"({market})")
    if industry and str(industry).upper() not in {"UNKNOWN", "NONE"}:
        header_bits.append(f"— {industry}")
    title = " ".join(header_bits)

    lines = [
        title,
        f"Snapshot phiên: {day}" if day else "Snapshot: (chưa có ngày)",
        "",
        _ACTION_BANNER.get(action, f"KHUYẾN NGHỊ: {action}"),
        translate_action(action),
        "",
        "① Chất lượng doanh nghiệp (bộ lọc cơ bản)",
        f"Kết luận lọc: {fundamental_row.get('fundamental_view', '—')}",
        (
            f"Điểm 0–100: tăng trưởng {_fmt_num(fundamental_row.get('growth_score'))} · "
            f"chất lượng {_fmt_num(fundamental_row.get('quality_score'))} · "
            f"an toàn {_fmt_num(fundamental_row.get('safety_score'))} · "
            f"định giá {_fmt_num(fundamental_row.get('valuation_score'))}"
        ),
        (
            "Nhìn chủ yếu vào: "
            f"{HEADLINE_VI['growth']}; {HEADLINE_VI['quality']}; "
            f"{HEADLINE_VI['safety']}; {HEADLINE_VI['valuation']}."
        ),
        "",
        "② Khí hậu thị trường (chung cả rổ — không riêng mã này)",
        p_line,
        "",
        "③ Xu hướng riêng của mã",
        f"Điểm xu hướng: {_fmt_num(signal_row.get('score'))} "
        f"(dương = nghiêng tăng, âm = nghiêng giảm)",
        f"Nhận định: {translate_kalman_trend(reason.get('slope_tstat'))}",
        f"Cách ước: {translate_alpha_method(reason.get('alpha_method'))}",
        "",
        "④ Rủi ro & tỷ trọng gợi ý",
        f"Biến động ngày ước tính: {_fmt_num(signal_row.get('sigma_hat'), 4)} "
        f"(càng lớn = giá dao động mạnh hơn)",
        f"Vùng cắt lỗ gợi ý: {_fmt_num(signal_row.get('stop'))}",
        f"Tỷ trọng gợi ý: khoảng {size_pct} danh mục "
        f"(≈ {weight_pct}, {translate_weight_method(reason.get('weight_method'))})",
    ]
    if signal_row.get("p_tp_before_sl") is not None:
        lines.append(
            "Xác suất chạm mục tiêu trước cắt lỗ: "
            f"{_fmt_num(signal_row.get('p_tp_before_sl'))}"
        )
    if signal_row.get("cvar95") is not None:
        lines.append(
            "Rủi ro đuôi ước tính (CVaR 95%): "
            f"{_fmt_num(signal_row.get('cvar95'))}"
        )

    ta_block = format_ta_reference_block(ta_indicators or {})
    if ta_block:
        lines.extend(["", ta_block])

    lines.extend(
        [
            "",
            f"📈 Biểu đồ giá: /chart {ticker} price",
            f"📊 Radar cơ bản: /chart {ticker} fundamental",
            "",
            DISCLAIMER,
        ]
    )
    return "\n".join(lines)


def format_positions(rows: list[dict]) -> str:
    """Bảng text cho /positions."""
    if not rows:
        return "Không có vị thế OPEN trong store.\n\n" + DISCLAIMER
    lines = ["Vị thế đang mở:", ""]
    for row in rows:
        lines.append(
            f"{row.get('ticker')} | entry={_fmt_num(row.get('entry_price'))} "
            f"stop={_fmt_num(row.get('stop_price'))} "
            f"size={_fmt_num(row.get('size_pct_nav'), 3)} "
            f"opened={row.get('opened_at', '—')}"
        )
    lines.extend(["", DISCLAIMER])
    return "\n".join(lines)


def format_backtest_results(rows: list[dict], scope: str) -> str:
    """Tóm tắt /backtest từ store.backtest_results (đã tính sẵn)."""
    if not rows:
        return (
            f"Chưa có kết quả backtest cho scope={scope}.\n"
            "Chờ lần chạy định kỳ (pipeline/backtest) — bot không chạy live.\n\n"
            + DISCLAIMER
        )
    run_id = rows[0].get("run_id", "?")
    run_at = rows[0].get("run_at", "")
    lines = [f"Backtest | scope={scope} | run={run_id} | {run_at}", ""]
    for row in rows:
        lines.append(
            f"[{row.get('baseline', 'framework')}] "
            f"CAGR={_fmt_num(row.get('cagr'))} "
            f"Sharpe={_fmt_num(row.get('sharpe'))} "
            f"MDD={_fmt_num(row.get('max_drawdown'))} "
            f"WR={_fmt_num(row.get('win_rate'))} "
            f"n={row.get('n_trades', '—')}"
        )
    lines.extend(["", DISCLAIMER])
    return "\n".join(lines)


def format_sector_overview(rows: list[dict], as_of: str | None = None) -> str:
    """Tổng quan /sector — top-down theo industry."""
    if not rows:
        return (
            "Chưa có sector overview (cần sector_mapping + watchlist).\n\n"
            + DISCLAIMER
        )
    header = f"Sector overview{f' | {as_of}' if as_of else ''}:"
    lines = [header, ""]
    for row in rows:
        lines.append(
            f"{row.get('industry', '?')}: "
            f"PASS={row.get('n_pass', 0)} "
            f"WATCH={row.get('n_watch', 0)} "
            f"FAIL={row.get('n_fail', 0)}"
        )
    lines.extend(["", DISCLAIMER])
    return "\n".join(lines)


def format_status(
    *,
    config_flags: dict[str, bool],
    latest_signal_date: str | None,
    watchlist_n: int,
    open_positions_n: int,
) -> str:
    """/status — cờ config + timestamp store (không fit model)."""
    lines = ["Pipeline status:", ""]
    if latest_signal_date:
        lines.append(f"signals latest date: {latest_signal_date}")
    else:
        lines.append("signals latest date: (empty)")
    lines.append(f"watchlist size: {watchlist_n}")
    lines.append(f"open positions: {open_positions_n}")
    lines.append("")
    lines.append("Config flags:")
    for key, enabled in sorted(config_flags.items()):
        lines.append(f"  {key}: {'ON' if enabled else 'off'}")
    lines.extend(["", DISCLAIMER])
    return "\n".join(lines)
