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
    assert "rõ ràng" in formatters.translate_kalman_trend(2.5)
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
    assert "KHUYẾN NGHỊ: MUA" in msg
    assert "① Doanh nghiệp" in msg
    assert "Xếp hạng trong nhóm ngành" in msg
    # Không có value 6.1 trong fixture → fallback điểm nội bộ
    assert "Điểm nội bộ" in msg or "tăng trưởng" in msg
    assert "② Thị trường chung" in msg
    assert "③ Xu hướng mã này" in msg
    assert "④ Rủi ro" in msg
    assert "Giá gần nhất" in msg
    assert "/chart VNM price" in msg
    assert "/chart VNM risk" in msg
    assert "Mô phỏng xác suất" in msg
    assert "eps_cagr_3y" not in msg
    assert "kalman_slope" not in msg
    assert "equal_weight" not in msg
    assert "gjr_garch" not in msg
    assert "PASS_THRESHOLDS" not in msg
    assert formatters.DISCLAIMER in msg

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
    assert "/signals" in welcome and "Bắt đầu nhanh" in welcome
    help_txt = formatters.format_help()
    assert "/check <mã>" in help_txt and "Tham khảo thêm" in help_txt
    assert "/chart <mã> ta" in help_txt

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
        ]
    )
    assert "Khí hậu thị trường" in sig_list
    assert "điểm" in sig_list
    assert "σ̂" not in sig_list
    assert "VNM" in sig_list and "FPT" in sig_list
    assert "→ Chi tiết: /check VNM" in sig_list
    assert formatters.format_signals_list([])
    wl = formatters.format_watchlist(
        [
            {"as_of_date": "2024-01-01", "ticker": "AAA", "fundamental_view": "PASS"},
            {"as_of_date": "2024-01-01", "ticker": "BBB", "fundamental_view": "WATCH"},
        ]
    )
    assert "Đạt" in wl and "Theo dõi" in wl and "AAA" in wl
    # UX mới: Rổ lọc + ngày VI
    wl2 = formatters.format_watchlist(
        [
            {"as_of_date": "2025-03-31", "ticker": "AAA", "fundamental_view": "PASS"},
            {"as_of_date": "2025-03-31", "ticker": "BBB", "fundamental_view": "WATCH"},
        ]
    )
    assert "Rổ lọc doanh nghiệp" in wl2
    assert "31/03/2025" in wl2
    assert "Không phải ngày giao dịch" in wl2 or "không phải ngày giao dịch" in wl2
    assert "Chưa có vị thế giấy" in formatters.format_positions([])
    pos = formatters.format_positions(
        [
            {
                "ticker": "GAS",
                "entry_price": 87.5,
                "stop_price": 83.5,
                "size_pct_nav": 0.1,
                "opened_at": "2026-09-21",
            }
        ]
    )
    assert "Vị thế giấy" in pos
    assert "21/09/2026" in pos
    assert "10.0%" in pos or "Tỷ trọng" in pos
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
            }
        ],
        "portfolio",
    )
    assert "Báo cáo kiểm thử" in filled_bt
    assert "không phải lãi/lỗ tài khoản thật" in filled_bt.casefold() or "không phải" in filled_bt
    assert "Sortino" in filled_bt
    assert "B1" in filled_bt or "CANSLIM" in filled_bt
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
    assert "mỏng" in thin_bt.casefold() or "sơ bộ" in thin_bt.casefold()
    miss = formatters.format_check_unavailable(
        "VCB", in_watchlist=False, has_fundamental=False, in_universe_csv=False
    )
    assert "universe" in miss.casefold() or "hose_liquid" in miss.casefold()
    assert "không tự crawl" in miss.casefold() or "chỉ đọc store" in miss.casefold()
    sec_txt = formatters.format_sector_overview(
        [{"industry": "Thực phẩm", "n_pass": 1, "n_watch": 0, "n_fail": 2}],
        "2024-06-28",
    )
    assert "loại 2" in sec_txt
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
