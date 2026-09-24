"""Pytest 8 tình huống ban_phac §11 — /check state machine + /signals + vị thế.

Chỉ kiểm formatter/state (store-shaped fixtures) — không gọi Telegram/network.
"""

from __future__ import annotations

from bot import formatters


def test_s1_out_of_scope_no_wait_message():
    """§11.1 — ngoài phạm vi; không bảo chỉ cần đợi."""
    msg = formatters.format_check_by_state(
        formatters.CHECK_OUT_OF_SCOPE, "ZZZ", meta={"last_close": 10.0}
    )
    assert "phạm vi" in msg.casefold() or "ngoài" in msg.casefold()
    assert "15:00" not in msg
    assert "đợi" not in msg.casefold() or "không" in msg.casefold()
    assert "dữ liệu tham khảo giá" in msg.casefold()
    assert "không phải vì thiếu dữ liệu" in msg.casefold()


def test_s2_insufficient_no_signal():
    """§11.2 — thiếu BCTC: không score hoàn chỉnh / không Quant / không signal."""
    msg = formatters.format_check_by_state(
        formatters.CHECK_INSUFFICIENT,
        "ABC",
        fund=None,
        meta={"last_close": 12.5, "industry": "Thép"},
        ta_indicators={"rsi_14": 48.0},
    )
    assert "Chưa đủ dữ liệu" in msg or "thiếu dữ liệu" in msg.casefold()
    assert "Tín hiệu hệ thống: MUA" not in msg
    assert "KHUYẾN NGHỊ" not in msg
    assert "Tham khảo thêm" in msg


def test_s3_fundamental_fail_shows_pillars():
    """§11.3 — FAIL: 4 trụ + lý do; không Quant/recommendation."""
    fund = {
        "fundamental_view": "FAIL",
        "growth_score": 40,
        "quality_score": 35,
        "safety_score": 30,
        "valuation_score": 25,
        "filed_at": "2025-03-31",
        "headline_json": (
            '{"classification_reason": "MODULE_FLOOR_NOT_MET", '
            '"headline": {"growth": {"metric": "eps_cagr_3y", "value": 0.05}, '
            '"quality": {"metric": "roic", "value": 0.08}, '
            '"safety": {"metric": "net_debt_to_ebitda", "value": 3.2}, '
            '"valuation": {"metric": "pe", "value": 22}}}'
        ),
    }
    msg = formatters.format_check_by_state(
        formatters.CHECK_FAIL, "FAIL1", fund=fund, meta={"last_close": 10.0}
    )
    assert "Không vượt bộ lọc Fundamental" in msg
    assert "MODULE_FLOOR_NOT_MET" in msg
    assert "4 trụ" in msg or "EPS CAGR" in msg or "ROIC" in msg
    assert "Tín hiệu hệ thống: MUA" not in msg
    assert "KHUYẾN NGHỊ" not in msg


def test_s4_watch_no_official_buy():
    """§11.4 — WATCH có thể hiện Quant tham khảo; không BUY chính thức."""
    signal = {
        "ticker": "WTC",
        "date": "2024-06-28",
        "action": "BUY",  # engine cũ / lỗi — display phải cap
        "score": 1.5,
        "p_regime": 0.8,
        "sigma_hat": 0.02,
        "stop": 90.0,
        "size": 0.05,
        "reason_json": '{"slope_tstat": 2.5}',
    }
    fund = {"fundamental_view": "WATCH", "growth_score": 60, "quality_score": 55,
            "safety_score": 50, "valuation_score": 45, "headline_json": "{}"}
    msg = formatters.format_signal_message(signal, fund)
    assert "Tín hiệu hệ thống: THEO DÕI" in msg
    assert "Tín hiệu hệ thống: MUA" not in msg
    assert "không nâng thành MUA" in msg.casefold() or "WATCH" in msg
    assert formatters.cap_action_for_fundamental("BUY", "WATCH") == "WATCH"


def test_s5_pass_with_cached_signal():
    """§11.5 — PASS + Quant cache → tín hiệu hệ thống từ DB."""
    signal = {
        "ticker": "FPT",
        "date": "2024-06-28",
        "action": "BUY",
        "score": 1.1,
        "p_regime": 0.7,
        "sigma_hat": 0.015,
        "stop": 100.0,
        "size": 0.08,
        "reason_json": '{"slope_tstat": 2.0}',
    }
    fund = {
        "fundamental_view": "PASS",
        "growth_score": 70,
        "quality_score": 65,
        "safety_score": 60,
        "valuation_score": 55,
        "headline_json": "{}",
    }
    state = formatters.resolve_check_state(
        in_universe=True,
        is_financial=False,
        exclude_financials=True,
        fund=fund,
        signal=signal,
        has_open_position=False,
    )
    assert state == formatters.CHECK_PASS
    msg = formatters.format_check_by_state(
        state, "FPT", fund=fund, signal=signal, meta={"last_close": 110.0}
    )
    assert "Tín hiệu hệ thống: MUA" in msg
    assert "Kết luận" in msg or "FPT —" in msg
    assert "→ Vì sao" in msg
    assert "── Chi tiết ──" in msg
    assert "① Doanh nghiệp" in msg
    assert "④ Rủi ro" in msg
    assert "chưa bật" not in msg.casefold()
    assert "Khuyến nghị mua" not in msg  # E-4: không đổi nhãn


def test_s6_pass_without_quant_no_ondemand():
    """§11.6 — PASS thiếu Quant: hiện Fundamental; nói rõ cần daily_job."""
    fund = {
        "fundamental_view": "PASS",
        "growth_score": 70,
        "quality_score": 65,
        "safety_score": 60,
        "valuation_score": 55,
        "headline_json": "{}",
    }
    state = formatters.resolve_check_state(
        in_universe=True,
        is_financial=False,
        exclude_financials=True,
        fund=fund,
        signal=None,
        has_open_position=False,
    )
    assert state == formatters.CHECK_PASS_NO_SIGNAL
    msg = formatters.format_check_by_state(state, "GAS", fund=fund)
    assert "PASS" in msg
    assert "Kết luận:" in msg
    assert "daily_job" in msg or "on-demand" in msg.casefold()
    assert "Tín hiệu hệ thống: MUA" not in msg
    assert "── Chi tiết ──" in msg


def test_s7_signals_pipeline_only_and_strength_order():
    """§11.7 — /signals chỉ strategy pipeline; nhóm theo độ mạnh."""
    rows = [
        {"date": "2024-06-28", "ticker": "LOW", "action": "BUY", "score": 0.2,
         "p_regime": 0.6, "sigma_hat": 0.02, "size": 0.05},
        {"date": "2024-06-28", "ticker": "HIGH", "action": "BUY", "score": 1.8,
         "p_regime": 0.6, "sigma_hat": 0.02, "size": 0.05},
        {"date": "2024-06-28", "ticker": "AVOID", "action": "SELL", "score": -1.0,
         "p_regime": 0.6, "sigma_hat": 0.02, "size": 0.05},
    ]
    txt = formatters.format_signals_list(rows)
    assert "pipeline" in txt.casefold() or "chiến lược" in txt.casefold()
    assert txt.index("HIGH") < txt.index("LOW")
    assert "Tránh mua mới" in txt
    assert "Tín hiệu đáng chú ý" in txt


def test_s8_open_position_hold_reduce_exit():
    """§11.8 — OPEN paper → ưu tiên P/L, HOLD/REDUCE/EXIT, stop."""
    position = {
        "ticker": "VNM",
        "opened_at": "2024-06-01",
        "entry_price": 100.0,
        "stop_price": 92.0,
        "size_pct_nav": 0.1,
        "status": "OPEN",
    }
    signal = {
        "ticker": "VNM",
        "date": "2024-06-28",
        "action": "SELL",
        "score": -0.8,
        "p_regime": 0.3,
        "sigma_hat": 0.02,
        "stop": 91.0,
        "size": 0.0,
        "reason_json": "{}",
    }
    fund = {"fundamental_view": "PASS", "headline_json": "{}"}
    state = formatters.resolve_check_state(
        in_universe=True,
        is_financial=False,
        exclude_financials=True,
        fund=fund,
        signal=signal,
        has_open_position=True,
    )
    assert state == formatters.CHECK_POSITION
    msg = formatters.format_check_by_state(
        state,
        "VNM",
        fund=fund,
        signal=signal,
        position=position,
        meta={"last_close": 105.0},
    )
    assert "ĐANG NẮM GIỮ" in msg
    assert "EXIT" in msg or "THOÁT" in msg
    assert "P/L" in msg
    assert "Stop" in msg or "stop" in msg.casefold()
    assert "5.0%" in msg or "P/L ước tính" in msg


def test_excluded_financial_state():
    state = formatters.resolve_check_state(
        in_universe=True,
        is_financial=True,
        exclude_financials=True,
        fund=None,
        signal=None,
        has_open_position=False,
    )
    assert state == formatters.CHECK_EXCLUDED_FINANCIAL
    msg = formatters.format_check_by_state(
        state,
        "VCB",
        meta={"industry": "Ngân hàng", "last_close": 95.5},
        ta_indicators={"rsi_14": 52.0, "ma_trend": "Giá trên MA20"},
    )
    assert "tài chính" in msg.casefold()
    assert "Giá gần nhất" in msg
    assert "Tham khảo thêm" in msg
    assert "Chưa đủ dữ liệu" not in msg
    assert "Câu chuyện ngắn" in msg or "phạm vi" in msg.casefold()
    assert "dữ liệu tham khảo giá" in msg.casefold()
    assert "không phải vì thiếu dữ liệu" in msg.casefold()


def test_excluded_financial_not_insufficient_even_with_fund_row():
    """VCB = EXCLUDED, không nhầm INSUFFICIENT dù store có hàng fund lệch."""
    fund = {
        "fundamental_view": "WATCH",
        "headline_json": '{"classification_reason": "INSUFFICIENT_DATA"}',
    }
    state = formatters.resolve_check_state(
        in_universe=True,
        is_financial=True,
        exclude_financials=True,
        fund=fund,
        signal=None,
        has_open_position=False,
    )
    assert state == formatters.CHECK_EXCLUDED_FINANCIAL


def test_watchlist_as_of_copy_says_annual_bctc_not_quarter():
    """UX: as_of = BCTC năm + lag; không gọi «quý lịch»."""
    wl = formatters.format_watchlist(
        [
            {"as_of_date": "2026-03-31", "ticker": "FPT", "fundamental_view": "PASS"},
            {"as_of_date": "2026-03-31", "ticker": "VNM", "fundamental_view": "WATCH"},
        ]
    )
    assert "BCTC năm" in wl
    assert "31/03/2026" in wl
    assert "quý" in wl.casefold()  # phủ định «theo quý», không nhầm BCTC quý
    assert "FPT" not in wl  # opener collapse — mã sau nút
    wl_pass = formatters.format_watchlist(
        [
            {"as_of_date": "2026-03-31", "ticker": "FPT", "fundamental_view": "PASS"},
            {"as_of_date": "2026-03-31", "ticker": "VNM", "fundamental_view": "WATCH"},
        ],
        view_filter="PASS",
    )
    assert "FPT" in wl_pass and "VNM" not in wl_pass
    sec = formatters.format_sector_overview(
        [{"industry": "Công nghệ", "n_pass": 1, "n_watch": 0, "n_fail": 0}],
        as_of="2026-03-31",
    )
    assert "BCTC năm" in sec
    assert "quý lịch" in sec.casefold()


def test_ux_check_summary_hides_raw_metrics():
    """UX Redesign: tin đầu /check không chứa t-stat/EPS thô; detail có."""
    signal = {
        "ticker": "FPT",
        "date": "2024-06-28",
        "action": "WATCH",
        "score": -0.67,
        "p_regime": 0.2,
        "sigma_hat": 0.02,
        "stop": 100.0,
        "size": 0.0,
        "reason_json": '{"slope_tstat": -0.56}',
    }
    fund = {
        "fundamental_view": "PASS",
        "growth_score": 70,
        "quality_score": 65,
        "safety_score": 60,
        "valuation_score": 55,
        "headline_json": (
            '{"headline": {"growth": {"metric": "eps_cagr_3y", "value": 0.12}, '
            '"quality": {"metric": "roic", "value": 0.18}, '
            '"safety": {"metric": "net_debt_to_ebitda", "value": 0.5}, '
            '"valuation": {"metric": "pe", "value": 15}}}'
        ),
    }
    full = formatters.format_signal_message(signal, fund)
    summary = formatters.check_summary_text(full)
    detail = formatters.check_detail_text(full, ticker="FPT")
    assert "t-stat" not in summary.casefold()
    assert "EPS CAGR" not in summary
    assert "Điểm tổng hợp" not in summary
    assert formatters.DISCLAIMER in summary
    assert "t-stat" in detail.casefold()
    assert "Điểm tổng hợp" in detail or "EPS" in detail


def test_ux_signals_summary_no_ticker_dump():
    """Tin đầu /signals chỉ đếm + khí hậu; danh sách sau action_filter."""
    rows = [
        {
            "date": "2024-06-28",
            "ticker": "VNM",
            "action": "BUY",
            "score": 1.2,
            "p_regime": 0.2,
            "sigma_hat": 0.02,
            "size": 0.05,
        },
        {
            "date": "2024-06-28",
            "ticker": "FPT",
            "action": "WATCH",
            "score": 0.1,
            "p_regime": 0.2,
            "sigma_hat": 0.02,
            "size": 0.05,
        },
    ]
    opener = formatters.format_signals_summary(rows)
    assert "VNM" not in opener and "điểm 1.2" not in opener
    assert "theo dõi" in opener.casefold()
    assert formatters.DISCLAIMER in opener
    assert "lọc quý" not in opener.casefold()
    listed = formatters.format_signals_list(rows, action_filter="BUY", page=0)
    assert "VNM" in listed and "điểm" in listed


def test_ux_short_disclaimer_constant():
    assert formatters.DISCLAIMER == "⚠ Học thuật · không phải tư vấn đầu tư."
    assert "chứng chỉ hành nghề" not in formatters.DISCLAIMER


def test_action_changes_alert_format():
    msg = formatters.format_action_changes_alert(
        [
            {"ticker": "FPT", "from_action": "WATCH", "to_action": "BUY"},
            {"ticker": "GAS", "from_action": "BUY", "to_action": "SELL"},
        ]
    )
    assert "Đổi trạng thái" in msg
    assert "FPT" in msg and "GAS" in msg
    assert "WATCH → BUY" in msg


def test_pass_message_has_subscribe_cta():
    signal = {
        "ticker": "FPT",
        "date": "2024-06-28",
        "action": "BUY",
        "score": 1.1,
        "p_regime": 0.7,
        "sigma_hat": 0.015,
        "stop": 100.0,
        "size": 0.08,
        "reason_json": "{}",
    }
    fund = {"fundamental_view": "PASS", "headline_json": "{}"}
    msg = formatters.format_signal_message(signal, fund)
    assert "/subscribe" in msg


def test_c4_insufficient_watch_reason_not_check_watch():
    """C4 — WATCH + INSUFFICIENT_DATA → INSUFFICIENT, không CHECK_WATCH."""
    fund = {
        "fundamental_view": "WATCH",
        "growth_score": 40,
        "quality_score": 40,
        "safety_score": 40,
        "valuation_score": 40,
        "headline_json": '{"classification_reason": "INSUFFICIENT_DATA"}',
    }
    state = formatters.resolve_check_state(
        in_universe=True,
        is_financial=False,
        exclude_financials=True,
        fund=fund,
        signal=None,
        has_open_position=False,
    )
    assert state == formatters.CHECK_INSUFFICIENT
    assert state != formatters.CHECK_WATCH


def test_c5_critical_flag_without_insufficient_word():
    """C5 — critical_data_quality_flag=true, reason không chứa INSUFFICIENT."""
    fund = {
        "fundamental_view": "WATCH",
        "growth_score": 50,
        "quality_score": 50,
        "safety_score": 50,
        "valuation_score": 50,
        "headline_json": (
            '{"classification_reason": "MIDDLE_PERCENTILE", '
            '"data_quality": {"critical_data_quality_flag": true}}'
        ),
    }
    assert formatters.is_insufficient_fundamental(fund) is True
    state = formatters.resolve_check_state(
        in_universe=True,
        is_financial=False,
        exclude_financials=True,
        fund=fund,
        signal=None,
        has_open_position=False,
    )
    assert state == formatters.CHECK_INSUFFICIENT


def test_c5b_missing_pillar_score_resolves_insufficient():
    """C5 structural — growth_score=None + reason trống → INSUFFICIENT."""
    fund = {
        "fundamental_view": "WATCH",
        "growth_score": None,
        "quality_score": 50,
        "safety_score": 50,
        "valuation_score": 50,
        "headline_json": "{}",
    }
    state = formatters.resolve_check_state(
        in_universe=True,
        is_financial=False,
        exclude_financials=True,
        fund=fund,
        signal=None,
        has_open_position=False,
    )
    assert state == formatters.CHECK_INSUFFICIENT


def test_fail_not_on_watchlist_still_checkable():
    """C10 — FAIL không trong watchlist vẫn resolve FAIL (không phụ thuộc watchlist)."""
    fund = {
        "fundamental_view": "FAIL",
        "growth_score": 30,
        "quality_score": 28,
        "safety_score": 25,
        "valuation_score": 20,
        "headline_json": '{"classification_reason": "BELOW_WATCH_PERCENTILE"}',
    }
    state = formatters.resolve_check_state(
        in_universe=True,
        is_financial=False,
        exclude_financials=True,
        fund=fund,
        signal={"ticker": "HPG", "action": "BUY", "score": 1.0},  # stale — bỏ qua
        has_open_position=False,
    )
    assert state == formatters.CHECK_FAIL
    msg = formatters.format_check_by_state(
        state, "HPG", fund=fund, meta={"last_close": 22.0}
    )
    assert "Không vượt bộ lọc Fundamental" in msg
    assert "Tín hiệu hệ thống: MUA" not in msg


def test_out_of_scope_appends_ta_when_present():
    msg = formatters.format_check_by_state(
        formatters.CHECK_OUT_OF_SCOPE,
        "ZZZ",
        meta={"last_close": 10.0},
        ta_indicators={"rsi_14": 45.0},
    )
    assert "Tham khảo thêm" in msg
    assert "phạm vi" in msg.casefold() or "ngoài" in msg.casefold()


def _actions_from_rows(rows: list[list[tuple[str, str]]]) -> set[str]:
    """Lấy tập action từ callback_data chk:<action>:<TICKER>."""
    out: set[str] = set()
    for row in rows:
        for _lab, cb in row:
            parts = cb.split(":")
            assert parts[0] == "chk"
            out.add(parts[1])
            assert len(cb.encode("utf-8")) <= 64
    return out


def test_check_keyboard_by_state_c2():
    """C-4.1 — đúng bộ nút theo từng state (có giá); E-1 ▾ Xem đầy đủ số liệu."""
    t = "MWG"
    # OUT / EXCLUDED → chỉ TA khi có giá (không detail — message đã ngắn)
    for st in (
        formatters.CHECK_OUT_OF_SCOPE,
        formatters.CHECK_EXCLUDED_FINANCIAL,
    ):
        acts = _actions_from_rows(
            formatters.check_keyboard_rows(st, t, has_price_bars=True)
        )
        assert acts == {"ta"}
        assert (
            formatters.check_keyboard_rows(st, t, has_price_bars=False) == []
        )

    insuf_acts = _actions_from_rows(
        formatters.check_keyboard_rows(
            formatters.CHECK_INSUFFICIENT, t, has_price_bars=True
        )
    )
    assert insuf_acts == {"detail", "ta"}

    fail_acts = _actions_from_rows(
        formatters.check_keyboard_rows(
            formatters.CHECK_FAIL, t, has_price_bars=True
        )
    )
    assert fail_acts == {"detail", "radar", "ta"}

    for st in (
        formatters.CHECK_WATCH,
        formatters.CHECK_PASS_NO_SIGNAL,
        formatters.CHECK_PASS,
    ):
        acts = _actions_from_rows(
            formatters.check_keyboard_rows(st, t, has_price_bars=True)
        )
        assert acts == {"detail", "price", "radar", "ta"}

    pos_acts = _actions_from_rows(
        formatters.check_keyboard_rows(
            formatters.CHECK_POSITION, t, has_price_bars=True
        )
    )
    assert pos_acts == {"detail", "pnl", "price", "radar", "ta"}
    # watch_add đã ẩn (Round 2 Phase 2)
    assert "watch_add" not in pos_acts
    # detail đứng trước các nút base
    flat = [
        a
        for row in formatters.check_keyboard_rows(
            formatters.CHECK_POSITION, t, has_price_bars=True
        )
        for a in row
    ]
    assert flat[0][1].startswith("chk:detail:")
    assert any(cb.startswith("chk:pnl:") for _lab, cb in flat)
    assert not any("Theo dõi" in lab for lab, _cb in flat)


def test_check_keyboard_callback_len_and_build():
    """C-4.2 — callback_data ≤ 64 byte; build_* trả InlineKeyboardMarkup."""
    kb = formatters.build_check_keyboard(
        formatters.CHECK_PASS, "FPT", has_price_bars=True
    )
    assert kb is not None
    for row in kb.inline_keyboard:
        for btn in row:
            assert len(btn.callback_data.encode("utf-8")) <= 64
