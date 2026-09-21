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
from typing import Any

HEADLINE_METRICS = {
    "growth": "eps_cagr_3y",
    "quality": "roic",
    "safety": "net_debt_to_ebitda",
    "valuation": "pe_vs_history_and_peer",
}

DISCLAIMER = (
    "⚠️ Sản phẩm học thuật, không phải tư vấn đầu tư, không thay thế tư vấn "
    "từ người có chứng chỉ hành nghề."
)

TA_REFERENCE_LABEL = "📊 Tham khảo thêm (không dùng để ra tín hiệu)"


def translate_regime(p_bull: float) -> str:
    """Dịch xác suất regime sang câu dễ hiểu — mục 9.7."""
    if p_bull is None:
        return "chưa đủ dữ liệu regime"
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
            "Bot chỉ ĐỌC kết quả đã tính sẵn trong store/ (không tự crawl hay fit lại mô hình).",
            "",
            "Bắt đầu nhanh:",
            "1) /subscribe — nhận tin khi pipeline daily chạy xong",
            "2) /signals — danh sách BUY / SELL / WATCH phiên gần nhất",
            "3) /check VNM — chi tiết 4 khối cho một mã (cơ bản → regime → alpha → risk)",
            "4) /watchlist — rổ PASS/WATCH từ bộ lọc cơ bản (Tầng 1)",
            "5) /regime — xác suất thị trường nghiêng tăng (chung cả rổ)",
            "",
            "Lưu ý hay gây hiểu nhầm:",
            "• p_bull trên /signals là regime THỊ TRƯỜNG (thường từ VNINDEX) — cùng một số cho mọi mã",
            "• size mặc định equal-weight (1/N NAV); khác nhau rõ khi bật Black-Litterman hoặc σ̂ rất lớn",
            "• Khác biệt từng mã nằm ở action, score (alpha), σ̂ và stop — xem /check <mã>",
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
            "Chưa có tín hiệu trong store.\n"
            "Gợi ý: đợi pipeline daily chạy, hoặc hỏi admin chạy "
            "`python scripts/run_daily_pipeline.py`.\n\n"
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
        lines.append(
            f"Regime thị trường (chung mọi mã): P(bull)={_fmt_num(p_shared)} "
            f"— {translate_regime(p_shared)}"
        )
        lines.append(
            "Size dưới đây thường bằng equal-weight 1/N (BL đang tắt). "
            "Số khác nhau theo mã: score / σ̂ — gõ /check <mã> để xem stop & chi tiết."
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
        lines.append(f"— {act} ({len(rows)}) —")
        for row in rows:
            lines.append(
                f"{row.get('ticker')} | score={_fmt_num(row.get('score'))} | "
                f"σ̂={_fmt_num(row.get('sigma_hat'), 4)} | "
                f"size={_fmt_num(row.get('size'), 3)}  "
                f"→ /check {row.get('ticker')}"
            )
        lines.append("")

    for row in other:
        lines.append(
            f"{row.get('action')} — {row.get('ticker')} | "
            f"score={_fmt_num(row.get('score'))} → /check {row.get('ticker')}"
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
    header = f"Regime{f' | {as_of}' if as_of else ''}:"
    if p_bull is None:
        body = "Chưa có p_regime trong store."
    else:
        body = f"P(bull) = {_fmt_num(p_bull)}\n→ {translate_regime(p_bull)}"
    return f"{header}\n{body}\n\n{DISCLAIMER}"


def format_signal_message(
    signal_row: dict,
    fundamental_row: dict | None = None,
    ta_indicators: dict | None = None,
) -> str:
    """Ghép mẫu tin nhắn đầy đủ theo mục 9.7 (+ 4 khối /check)."""
    fundamental_row = fundamental_row or {}
    reason = _reason_payload(signal_row)
    ticker = signal_row.get("ticker", "?")
    action = signal_row.get("action", "WATCH")
    day = signal_row.get("date", "")

    lines = [
        f"{action} — {ticker}{f' | {day}' if day else ''}",
        "",
        "① Bộ lọc cơ bản (Tầng 1) — chất lượng doanh nghiệp",
        f"Phân loại: {fundamental_row.get('fundamental_view', '—')}",
        (
            f"Tăng trưởng={_fmt_num(fundamental_row.get('growth_score'))} | "
            f"Chất lượng={_fmt_num(fundamental_row.get('quality_score'))} | "
            f"An toàn={_fmt_num(fundamental_row.get('safety_score'))} | "
            f"Định giá={_fmt_num(fundamental_row.get('valuation_score'))}"
        ),
        "(Thang 0–100 theo module; headline metric khung chiến lược: "
        f"{HEADLINE_METRICS['growth']}, {HEADLINE_METRICS['quality']}, "
        f"{HEADLINE_METRICS['safety']}, {HEADLINE_METRICS['valuation']})",
        "",
        "② Regime thị trường — chung cả rổ (không phải riêng mã này)",
        f"P(bull) = {_fmt_num(signal_row.get('p_regime'))}",
        f"→ {translate_regime(signal_row.get('p_regime'))}",
        "",
        "③ Alpha / xu hướng riêng mã",
        f"Score (alpha hiệu dụng): {_fmt_num(signal_row.get('score'))}",
        f"Xu hướng: {translate_kalman_trend(reason.get('slope_tstat'))}",
        f"Phương pháp: {reason.get('alpha_method', '—')}",
        "",
        "④ Rủi ro & kích thước vị thế",
        f"Biến động ngày σ̂ = {_fmt_num(signal_row.get('sigma_hat'), 4)}",
        f"Stop gợi ý = {_fmt_num(signal_row.get('stop'))}",
        f"Size = {_fmt_num(signal_row.get('size'), 3)} NAV "
        f"(weight={_fmt_num(reason.get('portfolio_weight'), 3)}, "
        f"{reason.get('weight_method', '—')})",
    ]
    if signal_row.get("p_tp_before_sl") is not None:
        lines.append(f"P(TP before SL) = {_fmt_num(signal_row.get('p_tp_before_sl'))}")
    if signal_row.get("cvar95") is not None:
        lines.append(f"CVaR95 = {_fmt_num(signal_row.get('cvar95'))}")

    ta_block = format_ta_reference_block(ta_indicators or {})
    if ta_block:
        lines.extend(["", ta_block])

    lines.extend(["", DISCLAIMER])
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
