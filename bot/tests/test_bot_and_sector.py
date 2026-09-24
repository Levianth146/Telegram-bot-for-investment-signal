"""Tests for sector_mapping + bot formatters (no Telegram network)."""

from __future__ import annotations

from bot import formatters
from pipeline import sector_job
from store import repository


def test_sector_mapping_upsert_and_overview(tmp_path):
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.upsert_watchlist(
        conn,
        [
            {"as_of_date": "2024-06-28", "ticker": "VNM", "fundamental_view": "PASS"},
            {"as_of_date": "2024-06-28", "ticker": "VCB", "fundamental_view": "WATCH"},
        ],
    )
    # FAIL nằm ở fundamental_scores (không vào watchlist) — /sector phải đếm được.
    repository.upsert_fundamental_scores(
        conn,
        [
            {
                "ticker": "VNM",
                "filed_at": "2024-06-28",
                "period": "2023",
                "growth_score": 70,
                "quality_score": 65,
                "safety_score": 60,
                "valuation_score": 55,
                "fundamental_view": "PASS",
                "headline_json": "{}",
            },
            {
                "ticker": "VCB",
                "filed_at": "2024-06-28",
                "period": "2023",
                "growth_score": 50,
                "quality_score": 50,
                "safety_score": 50,
                "valuation_score": 50,
                "fundamental_view": "WATCH",
                "headline_json": "{}",
            },
            {
                "ticker": "ABC",
                "filed_at": "2024-06-28",
                "period": "2023",
                "growth_score": 20,
                "quality_score": 20,
                "safety_score": 20,
                "valuation_score": 20,
                "fundamental_view": "FAIL",
                "headline_json": "{}",
            },
        ],
    )
    repository.upsert_sector_mapping(
        conn,
        [
            {
                "ticker": "VNM",
                "market": "HOSE",
                "sector": "Hàng tiêu dùng",
                "industry": "Thực phẩm",
                "subindustry": None,
                "updated_at": "2024-06-01",
            },
            {
                "ticker": "VCB",
                "market": "HOSE",
                "sector": "Tài chính",
                "industry": "Ngân hàng",
                "subindustry": None,
                "updated_at": "2024-06-01",
            },
            {
                "ticker": "ABC",
                "market": "HOSE",
                "sector": "Hàng tiêu dùng",
                "industry": "Thực phẩm",
                "subindustry": None,
                "updated_at": "2024-06-01",
            },
        ],
    )
    assert repository.get_sector_for_ticker(conn, "VNM")["industry"] == "Thực phẩm"
    overview = repository.get_sector_overview(conn, "2024-06-28")
    by_ind = {r["industry"]: r for r in overview}
    assert by_ind["Thực phẩm"]["n_pass"] == 1
    assert by_ind["Thực phẩm"]["n_fail"] == 1
    assert by_ind["Ngân hàng"]["n_watch"] == 1
    # None → ngày watchlist mới nhất (không phụ thuộc ngày tín hiệu phiên)
    assert repository.get_sector_overview(conn, None) == overview
    conn.close()


def test_sector_overrides_applied(tmp_path):
    from pipeline.sector_job import apply_sector_overrides, load_sector_overrides

    ov = load_sector_overrides()
    assert "VRE" in ov
    rows = apply_sector_overrides(
        [
            {
                "ticker": "VRE",
                "market": "HOSE",
                "sector": "Bất động sản",
                "industry": "Bất động sản",
                "subindustry": None,
                "updated_at": "2024-01-01",
            }
        ],
        updated_at="2026-09-22",
        overrides=ov,
    )
    by_t = {r["ticker"]: r for r in rows}
    assert by_t["VRE"]["industry"] == "Bán lẻ"
    assert by_t["POW"]["industry"] == "Tiện ích"
    db = tmp_path / "bot.db"
    rows = [
        sector_job.industry_to_mapping_row(
            "FPT",
            {"industry_name": "Công nghệ", "market": "HOSE"},
            updated_at="2024-07-01",
        )
    ]
    result = sector_job.run(
        {"sector_classification": {"enabled": True}},
        mapping_rows=rows,
        db_path=str(db),
    )
    assert result["rows"]
    conn = repository.get_connection(str(db))
    assert repository.get_sector_for_ticker(conn, "FPT")["industry"] == "Công nghệ"
    conn.close()


def test_formatters_regime_and_check():
    assert "tăng" in formatters.translate_regime(0.8)
    assert "giảm" in formatters.translate_regime(0.2)
    # D-3: nhãn prefix theo ngưỡng hiển thị
    assert formatters.regime_label_prefix(0.8) == "nghiêng tăng"
    assert formatters.regime_label_prefix(0.5) == "đi ngang"
    assert formatters.regime_label_prefix(0.2) == "nghiêng giảm"
    assert "rõ ràng" in formatters.translate_kalman_trend(2.5)
    # D-4: ba nhánh size
    assert "Không mở" in formatters._fmt_size_pct(0)
    assert "Không mở" in formatters._fmt_size_pct(None)
    assert "rất nhỏ" in formatters._fmt_size_pct(0.003)
    assert "6.0%" in formatters._fmt_size_pct(0.06)
    # D-6 helper
    assert "Biểu đồ giá" in formatters.format_chart_skip_note(
        "giá", ValueError("chưa đủ dữ liệu")
    )
    assert "Đạt" in formatters.translate_fundamental_view("PASS")
    msg = formatters.format_signal_message(
        {
            "ticker": "VNM",
            "date": "2024-06-28",
            "action": "BUY",
            "score": 1.2,
            "p_regime": 0.72,
            "sigma_hat": 0.02,
            "stop": 95.0,
            "size": 0.06,
            "reason_json": (
                '{"slope_tstat": 2.1, "alpha_method": "kalman_slope", '
                '"sigma_method": "gjr_garch", "weight_method": "equal_weight"}'
            ),
        },
        {
            "fundamental_view": "PASS",
            "growth_score": 70,
            "quality_score": 65,
            "safety_score": 60,
            "valuation_score": 55,
            "headline_json": (
                '{"safety_gate_status": "OK", '
                '"classification_reason": "PASS: đủ 4 trụ", '
                '"fundamental_percentile": 72}'
            ),
        },
        ta_indicators={"rsi_14": 55.0, "ma_trend": "MA20 trên MA50 (ngắn hạn nghiêng tăng)"},
        meta={"market": "HOSE", "industry": "Thực phẩm", "last_close": 68.5},
    )
    assert "VNM" in msg and "HOSE" in msg
    assert "Tín hiệu hệ thống: MUA" in msg
    assert "KHUYẾN NGHỊ" not in msg
    assert "① Doanh nghiệp" in msg
    assert "Kết luận:" in msg
    assert "→ Vì sao" in msg
    assert "── Chi tiết ──" in msg
    assert "Xếp hạng trong nhóm ngành" in msg
    # Không có value 6.1 trong fixture → fallback điểm nội bộ
    assert "Điểm nội bộ" in msg or "tăng trưởng" in msg
    assert "② Thị trường chung" in msg
    assert "③ Xu hướng mã này" in msg
    # D-5: Kalman dùng t-stat; score trên dòng riêng
    assert "t-stat" in msg.casefold()
    assert "Điểm tổng hợp" in msg
    assert "(điểm 1.2)" not in msg  # không ghép score vào câu Kalman
    assert "④ Rủi ro" in msg
    assert "Giá gần nhất" in msg
    assert "/chart VNM price" in msg
    assert "/chart VNM risk" in msg
    # D-9: ngôn ngữ sản phẩm khi MC off (không «chưa bật»)
    assert "mô phỏng xác suất" in msg.casefold()
    assert "chưa bật" not in msg.casefold()
    assert "eps_cagr_3y" not in msg
    assert "kalman_slope" not in msg
    assert "equal_weight" not in msg
    assert "gjr_garch" not in msg
    assert "PASS_THRESHOLDS" not in msg
    assert formatters.DISCLAIMER in msg

    # D-5 + D-4: score thấp ≠ t-stat; size = 0
    split_msg = formatters.format_signal_message(
        {
            "ticker": "AAA",
            "date": "2024-06-28",
            "action": "WATCH",
            "score": 0.34,
            "p_regime": 0.02,
            "sigma_hat": 0.02,
            "stop": 10.0,
            "size": 0.0,
            "reason_json": '{"slope_tstat": 0.3}',
        },
        {"fundamental_view": "PASS"},
    )
    assert "không có xu hướng rõ" in split_msg.casefold()
    assert "t-stat" in split_msg.casefold()
    assert "Điểm tổng hợp" in split_msg and "0.34" in split_msg
    assert "(điểm 0.34)" not in split_msg
    assert "Không mở vị thế" in split_msg
    # D-3: p≈0 không còn «nghiêng tăng ~0%»
    assert "nghiêng giảm" in split_msg.casefold()
    assert "nghiêng tăng (~0%" not in split_msg.casefold()
    assert "nghiêng tăng ~0%" not in split_msg

    gap_msg = formatters.format_signal_message(
        {
            "ticker": "XYZ",
            "date": "2024-06-28",
            "action": "WATCH",
            "score": None,
            "p_regime": 0.5,
            "sigma_hat": None,
            "stop": None,
            "size": 0.0,
            "reason_json": '{"error": "insufficient_price_history", "n": 5}',
        },
        {"fundamental_view": "WATCH"},
    )
    assert "Thiếu dữ liệu giá" in gap_msg

    welcome = formatters.format_welcome()
    assert "/signals" in welcome and "/positions" in welcome
    assert "Thị trường" in welcome or "cơ hội" in welcome
    assert "/check FPT" in welcome
    assert "/tinhtrangdulieu" in welcome
    assert "/subscribe" not in welcome  # E-3: đẩy xuống /help
    # UX Redesign: không lặp EOD ở /start
    assert "không realtime" not in welcome.casefold()
    assert formatters.DISCLAIMER in welcome
    help_txt = formatters.format_help()
    assert "/check <mã>" in help_txt and "Tham khảo thêm" in help_txt
    assert "Khám phá thị trường" in help_txt
    assert "Tra cứu 1 mã" in help_txt
    assert "Quản lý vị thế" in help_txt
    assert "ví dụ: /check FPT" in help_txt
    assert "/tinhtrangdulieu" in help_txt
    assert "trần %/mã" in help_txt or "trần" in help_txt
    assert "w_max" not in help_txt
    assert "chia đều" not in help_txt or "không chia đều" in help_txt

    sig_list = formatters.format_signals_list(
        [
            {
                "date": "2024-06-28",
                "ticker": "VNM",
                "action": "BUY",
                "score": 1.2,
                "p_regime": 0.59,
                "sigma_hat": 0.02,
                "size": 0.062,
            },
            {
                "date": "2024-06-28",
                "ticker": "FPT",
                "action": "SELL",
                "score": -0.5,
                "p_regime": 0.59,
                "sigma_hat": 0.018,
                "size": 0.062,
            },
            {
                "date": "2024-06-28",
                "ticker": "AAA",
                "action": "BUY",
                "score": 0.3,
                "p_regime": 0.59,
                "sigma_hat": 0.02,
                "size": 0.05,
            },
        ]
    )
    assert "Kết luận:" in sig_list
    assert "điểm" in sig_list
    # D-3 / E-1: một dòng khí hậu, nhãn động (0.59 → nghiêng tăng)
    assert "nghiêng tăng (~59%)" in sig_list or "nghiêng tăng (~59" in sig_list
    climate_line = [
        ln for ln in sig_list.splitlines() if "khí hậu" in ln.casefold()
    ][0]
    assert "—" in climate_line
    assert "σ̂" not in sig_list
    assert "VNM" in sig_list and "FPT" in sig_list
    assert "🟢 VNM" in sig_list or "🟢 AAA" in sig_list  # E-3 badge trước mã
    assert "→ Chi tiết: /check VNM" in sig_list
    assert "Tín hiệu đáng chú ý" in sig_list
    assert "Tránh mua mới" in sig_list
    assert "pipeline" in sig_list.casefold()
    assert "biến động" in sig_list.casefold() or "trần" in sig_list
    assert "w_max" not in sig_list
    assert "10.0%" in sig_list or "trần" in sig_list  # trần %/mã / size
    # Độ mạnh: VNM (1.2) trước AAA (0.3) trong nhóm BUY
    assert sig_list.index("VNM") < sig_list.index("AAA")
    # Size thật (không làm tròn mất) + chạm trần
    capped = formatters.format_signals_list(
        [
            {
                "date": "2024-06-28",
                "ticker": "GAS",
                "action": "BUY",
                "score": 1.0,
                "p_regime": 0.6,
                "sigma_hat": 0.02,
                "size": 0.10,
            }
        ],
        w_max=0.10,
    )
    assert "chạm trần" in capped
    # D-4 trên /signals: size rất nhỏ
    tiny = formatters.format_signals_list(
        [
            {
                "date": "2024-06-28",
                "ticker": "TINY",
                "action": "BUY",
                "score": 0.5,
                "p_regime": 0.4,
                "sigma_hat": 0.02,
                "size": 0.002,
            }
        ]
    )
    assert "rất nhỏ" in tiny
    assert "nghiêng giảm" in tiny or "đi ngang" in tiny
    assert formatters.format_signals_list([])
    # Round2: 0 mã đáng chú ý → giải thích (không để số trơ)
    zero_buy = formatters.format_signals_list(
        [
            {
                "date": "2024-06-28",
                "ticker": "FPT",
                "action": "WATCH",
                "score": 0.1,
                "p_regime": 0.4,
                "sigma_hat": 0.02,
                "size": 0.05,
            }
        ]
    )
    assert "đáng chú ý (0)" in zero_buy.casefold() or "đáng chú ý (0)" in zero_buy
    assert "chưa có mã đạt đủ điều kiện mua" in zero_buy.casefold()
    regime_bear = formatters.format_regime_message(0.1, "2024-06-28")
    assert "nghiêng giảm" in regime_bear.casefold()
    assert "🔴" in regime_bear  # đèn giao thông
    assert "điểm" in regime_bear.casefold()
    assert "24/06/2024" in regime_bear or "28/06/2024" in regime_bear or "2024" in regime_bear
    assert "nghiêng tăng ~" not in regime_bear
    assert "Ảnh hưởng" in regime_bear or "vì sao" in regime_bear.casefold()
    regime_cmp = formatters.format_regime_message(
        0.6, "2024-06-28", prev_p_bull=0.4
    )
    assert "So với hôm qua" in regime_cmp or "So với phiên trước" in regime_cmp
    assert "đã chuyển" in regime_cmp
    assert "🟢" in regime_cmp
    regime_same = formatters.format_regime_message(
        0.6, "2024-06-28", prev_p_bull=0.58
    )
    assert "không đổi" in regime_same
    wl = formatters.format_watchlist(
        [
            {"as_of_date": "2024-01-01", "ticker": "AAA", "fundamental_view": "PASS"},
            {"as_of_date": "2024-01-01", "ticker": "BBB", "fundamental_view": "WATCH"},
        ]
    )
    assert "ĐẠT" in wl.upper() or "Đạt" in wl
    assert "THEO DÕI" in wl.upper() or "Theo dõi" in wl
    # Opener không dump mã — mã chỉ sau view_filter
    assert "AAA" not in wl
    wl_pass = formatters.format_watchlist(
        [
            {"as_of_date": "2024-01-01", "ticker": "AAA", "fundamental_view": "PASS"},
            {"as_of_date": "2024-01-01", "ticker": "BBB", "fundamental_view": "WATCH"},
        ],
        view_filter="PASS",
    )
    assert "AAA" in wl_pass and "BBB" not in wl_pass
    # UX mới: Rổ lọc + ngày VI + ghi chú BCTC năm
    wl2 = formatters.format_watchlist(
        [
            {"as_of_date": "2025-03-31", "ticker": "AAA", "fundamental_view": "PASS"},
            {"as_of_date": "2025-03-31", "ticker": "BBB", "fundamental_view": "WATCH"},
        ]
    )
    assert "Rổ lọc doanh nghiệp" in wl2
    assert "31/03/2025" in wl2
    assert "Không phải ngày giao dịch" in wl2 or "không phải ngày giao dịch" in wl2
    assert "BCTC năm" in wl2 and "không" in wl2.casefold() and "quý" in wl2.casefold()
    empty_pos = formatters.format_positions([])
    assert "Chưa có vị thế giấy" in empty_pos
    assert "tín hiệu BÁN" in empty_pos or "BÁN" in empty_pos
    assert "tham khảo" in empty_pos.casefold()
    pos = formatters.format_positions(
        [
            {
                "ticker": "GAS",
                "entry_price": 87.5,
                "stop_price": 83.5,
                "size_pct_nav": 0.1,
                "opened_at": "2026-09-21",
            }
        ],
        last_closes={"GAS": 96.25},
        as_of="2026-09-24",
    )
    assert "Vị thế giấy" in pos
    assert "giữ 3 phiên" in pos
    assert "Dữ liệu tính đến phiên" in pos
    assert "tham khảo" in pos.casefold()
    assert "10.0%" in pos or "tỷ trọng" in pos.casefold()
    assert "chạm trần" in pos
    assert "tổng p/l" in pos.casefold()
    assert "w_max" not in pos
    # entry 87.5 → 96.25 = +10%; icon 🟢 trên opener
    assert "🟢" in pos
    assert "+10" in pos or "10.0%" in pos or "10%" in pos
    # Giá vào / cắt lỗ chỉ trong detail
    assert "Giá vào" not in pos
    pos_detail = formatters.format_positions(
        [
            {
                "ticker": "GAS",
                "entry_price": 87.5,
                "stop_price": 83.5,
                "size_pct_nav": 0.1,
                "opened_at": "2026-09-21",
            }
        ],
        last_closes={"GAS": 96.25},
        as_of="2026-09-24",
        detail=True,
    )
    assert "Giá vào" in pos_detail
    assert "21/09/2026" in pos_detail
    assert formatters.holding_sessions_from_opened_at("2026-09-21", "2026-09-21") == 0
    assert formatters.holding_sessions_from_opened_at("2026-09-21", "2026-09-24") == 3
    empty_bt = formatters.format_backtest_results([], "portfolio")
    assert "Chưa có báo cáo kiểm thử" in empty_bt or "Chưa có" in empty_bt
    assert "/signals" in empty_bt and "/watchlist" in empty_bt
    filled_bt = formatters.format_backtest_results(
        [
            {
                "run_id": "demo",
                "run_at": "2026-01-01",
                "baseline": "B0_buyhold",
                "cagr": 0.1,
                "sharpe": 0.5,
                "max_drawdown": -0.2,
                "win_rate": None,
                "n_trades": 0,
                "equity_curve_json": "[]",
                "sortino": 0.6,
                "calmar": 0.4,
                "margin_bps": 100.0,
            },
            {
                "run_id": "demo",
                "run_at": "2026-01-01",
                "baseline": "framework",
                "cagr": -0.05,
                "sharpe": -0.8,
                "max_drawdown": -0.12,
                "n_trades": 36,
                "sortino": -0.7,
                "calmar": -0.4,
                "win_rate": 0.495,
                "total_return": 0.0215,
                "profit_factor": 1.19,
                "avg_exposure": 0.321,
                "pct_sessions_cash_gt_80": 0.12,
            },
        ],
        "portfolio",
        checks=[
            {
                "check_name": "MIN_SHARPE_IMPROVEMENT_OOS",
                "threshold": 0.1,
                "actual_value": -1.3,
                "passed": 0,
                "note": "thua B0",
            }
        ],
    )
    assert "kiểm thử" in filled_bt.casefold()
    assert "Sharpe" in filled_bt and ("thấp hơn" in filled_bt or "🔴" in filled_bt)
    assert (
        "không cam kết" in filled_bt.casefold()
        or "không phải lãi" in filled_bt.casefold()
        or "ngoài mẫu" in filled_bt.casefold()
    )
    # Round2: giải thích B0 n_trades=0 vẫn có Sharpe
    assert "không có «lệnh»" in filled_bt or "không có 'lệnh'" in filled_bt or "mua đầu" in filled_bt.casefold()
    assert "hàng ngày" in filled_bt.casefold() or "không phụ thuộc số lệnh" in filled_bt.casefold()
    assert "Sortino" in filled_bt
    assert "phát hiện hợp lệ" in filled_bt.casefold()
    assert "Cải thiện Sharpe" in filled_bt or "❌" in filled_bt
    assert "MIN_SHARPE" not in filled_bt  # D-9: dịch tên check
    assert "B1" in filled_bt or "CANSLIM" in filled_bt
    # D-7: thống kê bổ sung (ngôn ngữ sản phẩm)
    assert "Thống kê bổ sung" in filled_bt
    assert "tỷ lệ thắng" in filled_bt.casefold() or "win rate" in filled_bt.casefold()
    assert "hệ số lãi/lỗ" in filled_bt.casefold() or "profit factor" in filled_bt.casefold()
    assert "tổng lãi" in filled_bt.casefold()
    assert "Exposure" in filled_bt or "phơi nhiễm" in filled_bt.casefold()
    thin_bt = formatters.format_backtest_results(
        [
            {
                "run_id": "thin",
                "run_at": "2026-01-01",
                "baseline": "framework",
                "cagr": 0.03,
                "sharpe": 0.8,
                "max_drawdown": -0.02,
                "n_trades": 3,
            }
        ],
        "portfolio",
    )
    assert "ít" in thin_bt.casefold() or "mỏng" in thin_bt.casefold() or "sơ bộ" in thin_bt.casefold()
    miss = formatters.format_check_unavailable(
        "VCB", in_watchlist=False, has_fundamental=False, in_universe_csv=False
    )
    assert "phạm vi" in miss.casefold() or "universe" in miss.casefold()
    assert "15:00" not in miss
    assert "không tự crawl" in miss.casefold() or "chỉ đọc store" in miss.casefold() or "ngoài phạm vi" in miss.casefold()
    sec_txt = formatters.format_sector_overview(
        [{"industry": "Thực phẩm", "n_pass": 1, "n_watch": 0, "n_fail": 2}],
        "2024-06-28",
    )
    assert "loại" in sec_txt and "2" in sec_txt
    assert "28/06/2024" in sec_txt
    empty_bt2 = formatters.format_backtest_results(
        [], "portfolio", available_scopes=["ablation_demo"]
    )
    assert "/backtest ablation_demo" in empty_bt2
    empty_sec = formatters.format_sector_overview(
        [], has_sector_mapping=True, has_watchlist=False
    )
    assert "watchlist" in empty_sec.casefold() or "Watchlist" in empty_sec
    assert "/signals" in empty_sec
    status = formatters.format_status(
        config_flags={"regime_markov": True, "portfolio_black_litterman": False},
        latest_signal_date="2024-06-28",
        watchlist_n=2,
        open_positions_n=0,
    )
    assert "Khí hậu thị trường: BẬT" in status
    assert "Tối ưu tỷ trọng nâng cao: tắt" in status
    assert "regime_markov: ON" not in status
    assert "Tình trạng dữ liệu" in status  # /status mirror /tinhtrangdulieu
    assert "/tinhtrangdulieu" in status
    assert "EOD" in status or "realtime" in status.casefold()
    assert "Dữ liệu tính đến phiên" in status

    tinh = formatters.format_tinh_trang_du_lieu(
        latest_signal_date="2024-06-28",
        watchlist_n=2,
        open_positions_n=1,
    )
    assert "Tình trạng dữ liệu" in tinh
    assert "chỉ đọc dữ liệu đã tính sẵn" in tinh.casefold() or "không gọi realtime" in tinh.casefold()
    assert "daily_job" in tinh or "EOD" in tinh
    assert "quarterly_job" in tinh or "BCTC" in tinh
    assert "rà lại định kỳ" in tinh.casefold() or "~3 tháng" in tinh
    assert "lịch quý" not in tinh.casefold()
    assert "Cờ mô hình" not in tinh  # lệnh riêng không nhồi cờ (status mới có)

    # UNKNOWN > 10% → cảnh báo trên /sector và /status
    high_unk = formatters.format_sector_overview(
        [
            {"industry": "UNKNOWN", "n_pass": 0, "n_watch": 0, "n_fail": 0, "n_total": 20},
            {"industry": "Thực phẩm", "n_pass": 1, "n_watch": 0, "n_fail": 0, "n_total": 5},
        ],
        "2024-06-28",
    )
    assert "Cảnh báo" in high_unk
    assert (
        "UNKNOWN" in high_unk
        or "thiếu" in high_unk.casefold()
        or "chưa xác định ngành" in high_unk.casefold()
    )
    assert "/tinhtrangdulieu" in high_unk
    assert "không phải lỗi hiển thị" in high_unk.casefold()
    status_warn = formatters.format_status(
        config_flags={"regime_markov": True},
        latest_signal_date=None,
        watchlist_n=0,
        open_positions_n=0,
        unknown_sector_share=0.25,
    )
    assert "Cảnh báo" in status_warn
    low = formatters.format_unknown_sector_warning(0.05)
    assert low is None

    # /check header có timestamp khi meta.as_of
    chk_ts = formatters.format_check_out_of_scope(
        "XYZ", meta={"as_of": "2024-06-28", "last_close": 10.0}
    )
    assert "Dữ liệu tính đến phiên" in chk_ts
    assert "28/06/2024" in chk_ts


def test_subscribe_helpers(tmp_path):
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.set_subscription(conn, 42, True)
    assert repository.get_active_subscribers(conn) == [42]
    repository.set_subscription(conn, 42, False)
    assert repository.get_active_subscribers(conn) == []
    conn.close()


def test_bot_dry_run(capsys, tmp_path, monkeypatch):
    db = tmp_path / "bot.db"
    monkeypatch.setenv("DATABASE_PATH", str(db))
    monkeypatch.setenv("BOT_TOKEN", "changeme")
    from bot import main as bot_main

    bot_main.main(["--dry-run"])
    out = capsys.readouterr().out
    assert "bot dry-run OK" in out


def test_signals_pagination_edges():
    """C-4.4 — trang đầu không ◀; trang cuối không ▶; callback ≤ 64 byte."""
    rows = []
    for i in range(25):
        rows.append(
            {
                "date": "2024-06-28",
                "ticker": f"B{i:02d}",
                "action": "BUY",
                "score": 1.0 - i * 0.01,
                "p_regime": 0.6,
                "sigma_hat": 0.02,
                "size": 0.05,
            }
        )
    for i in range(15):
        rows.append(
            {
                "date": "2024-06-28",
                "ticker": f"W{i:02d}",
                "action": "WATCH",
                "score": 0.1,
                "p_regime": 0.6,
                "sigma_hat": 0.02,
                "size": 0.03,
            }
        )
    total = formatters.signals_total_pages(rows)
    assert total >= 3

    page0 = formatters.format_signals_list(rows, page=0)
    assert "B00" in page0
    assert "B10" not in page0  # trang 0 chỉ 10 BUY đầu
    assert "Trang 1/" in page0

    kb0 = formatters.build_signals_keyboard(0, total)
    texts0 = [b.text for row in kb0.inline_keyboard for b in row]
    assert "◀ Trước" not in texts0
    assert "Tiếp ▶" in texts0

    kb_last = formatters.build_signals_keyboard(total - 1, total)
    texts_last = [b.text for row in kb_last.inline_keyboard for b in row]
    assert "◀ Trước" in texts_last
    assert "Tiếp ▶" not in texts_last

    for kb in (kb0, kb_last):
        for row in kb.inline_keyboard:
            for btn in row:
                assert len(btn.callback_data.encode("utf-8")) <= 64
                assert btn.callback_data.startswith("page:signals:")


def test_backtest_and_regime_and_start_keyboards():
    """Nút /backtest, /regime, /start — callback ngắn; ReplyKeyboard có lệnh."""
    bt = formatters.build_backtest_keyboard("run_demo_20260923")
    cbs = [b.callback_data for row in bt.inline_keyboard for b in row]
    assert any(c.startswith("bt:b0:") for c in cbs)
    assert any(c.startswith("bt:yearly:") for c in cbs)
    assert any(c.startswith("bt:checks:") for c in cbs)
    assert all(len(c.encode("utf-8")) <= 64 for c in cbs)

    rg = formatters.build_regime_keyboard()
    assert rg.inline_keyboard[0][0].callback_data == "nav:signals"

    start_kb = formatters.build_start_reply_keyboard()
    labels = [b.text for row in start_kb.keyboard for b in row]
    assert "/check" in labels and "/signals" in labels
    assert "/regime" in labels and "/positions" in labels
    assert "/tinhtrangdulieu" in labels


def test_callback_handler_answers_and_no_network(tmp_path, monkeypatch):
    """C-4.2/3 — answer() luôn gọi; bấm nút không kích hoạt network provider."""
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock, MagicMock

    db = tmp_path / "bot.db"
    monkeypatch.setenv("DATABASE_PATH", str(db))
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    conn.close()

    def _boom(*_a, **_k):
        raise RuntimeError("network/provider must not be called")

    # Nếu callback vô tình import/gọi provider → fail.
    monkeypatch.setattr(
        "data.providers.registry.get_provider", _boom, raising=False
    )

    from bot import main as bot_main

    app = bot_main.build_application("test-token-unused")
    # Lấy CallbackQueryHandler callback
    cb_handler = None
    for handlers in app.handlers.values():
        for h in handlers:
            if h.__class__.__name__ == "CallbackQueryHandler":
                cb_handler = h
                break
    assert cb_handler is not None

    answer = AsyncMock()
    reply_text = AsyncMock()
    query = SimpleNamespace(
        data="nav:signals",
        answer=answer,
        message=SimpleNamespace(
            reply_text=reply_text,
            edit_message_text=AsyncMock(),
        ),
        edit_message_text=AsyncMock(),
    )
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={}, args=None)

    async def _run():
        await cb_handler.callback(update, context)

    asyncio.run(_run())
    answer.assert_awaited()
    # nav:signals → gửi danh sách (có thể trống) qua reply hoặc edit
    assert (
        reply_text.await_count >= 1
        or query.edit_message_text.await_count >= 1
        or query.message.edit_message_text.await_count >= 1
    )


def test_watch_add_ack_copy():
    on = formatters.format_watch_add_ack("FPT", on_system_watchlist=True)
    off = formatters.format_watch_add_ack("XYZ", on_system_watchlist=False)
    assert "FPT" in on and "rổ theo dõi" in on
    assert "XYZ" in off and "chưa có" in off.casefold()


def test_check_cmd_text_only_no_auto_photo(tmp_path, monkeypatch):
    """Phần 4: /check chỉ reply_text (+ keyboard); không reply_photo."""
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    db = tmp_path / "bot.db"
    monkeypatch.setenv("DATABASE_PATH", str(db))
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    # Đủ bars + fund PASS để trước đây đã auto-send nhiều PNG.
    repository.upsert_price_bars(
        conn,
        [
            {
                "ticker": "FPT",
                "date": f"2024-01-{i:02d}",
                "open": 10.0,
                "high": 11.0,
                "low": 9.0,
                "close": 10.0 + i * 0.1,
                "volume": 1_000_000,
            }
            for i in range(1, 28)
        ],
    )
    repository.upsert_fundamental_scores(
        conn,
        [
            {
                "ticker": "FPT",
                "filed_at": "2024-03-31",
                "period": "2023",
                "growth_score": 70,
                "quality_score": 65,
                "safety_score": 60,
                "valuation_score": 55,
                "fundamental_view": "PASS",
                "headline_json": "{}",
            }
        ],
    )
    conn.close()
    monkeypatch.setattr(
        "bot.main._universe_and_finance_flags",
        lambda _t: (True, False, True),
    )

    from bot import main as bot_main

    app = bot_main.build_application("test-token-unused")
    check_handler = None
    for handlers in app.handlers.values():
        for h in handlers:
            cmds = getattr(h, "commands", None) or set()
            if "check" in cmds:
                check_handler = h
                break
        if check_handler:
            break
    assert check_handler is not None

    reply_text = AsyncMock()
    reply_photo = AsyncMock()
    update = SimpleNamespace(
        message=SimpleNamespace(reply_text=reply_text, reply_photo=reply_photo)
    )
    context = SimpleNamespace(args=["FPT"], user_data={})

    async def _run():
        await check_handler.callback(update, context)

    asyncio.run(_run())
    assert reply_text.await_count == 1
    assert reply_photo.await_count == 0
    # Keyboard vẫn đi kèm (reply_markup)
    call_kwargs = reply_text.await_args.kwargs
    assert call_kwargs.get("reply_markup") is not None


def test_bt_b0_callback_passes_framework_and_b0(tmp_path, monkeypatch):
    """Phần 5: bt:b0 gọi render với baselines=[framework, B0_buyhold]."""
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from pathlib import Path

    db = tmp_path / "bot.db"
    monkeypatch.setenv("DATABASE_PATH", str(db))
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    conn.close()

    captured: dict = {}

    def _fake_render(scope, run_id, out_path, **kwargs):
        captured["baselines"] = kwargs.get("baselines")
        captured["scope"] = scope
        captured["run_id"] = run_id
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG\r\n\x1a\nfake")
        return p

    monkeypatch.setattr(
        "bot.charts.render_backtest_equity_curve_chart", _fake_render
    )

    from bot import main as bot_main

    app = bot_main.build_application("test-token-unused")
    cb_handler = None
    for handlers in app.handlers.values():
        for h in handlers:
            if h.__class__.__name__ == "CallbackQueryHandler":
                cb_handler = h
                break
    assert cb_handler is not None

    answer = AsyncMock()
    reply_photo = AsyncMock()
    reply_text = AsyncMock()
    query = SimpleNamespace(
        data="bt:b0:run_demo",
        answer=answer,
        message=SimpleNamespace(
            reply_text=reply_text,
            reply_photo=reply_photo,
        ),
    )
    update = SimpleNamespace(callback_query=query)
    context = SimpleNamespace(user_data={"bt_scope": "portfolio"}, args=None)

    async def _run():
        await cb_handler.callback(update, context)

    asyncio.run(_run())
    answer.assert_awaited()
    assert captured.get("baselines") == ["framework", "B0_buyhold"]
    assert reply_photo.await_count == 1
