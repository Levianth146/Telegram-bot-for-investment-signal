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
    assert "Tín hiệu hệ thống: MUA" in msg
    assert "KHUYẾN NGHỊ" not in msg
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
    assert "/signals" in welcome and "/positions" in welcome
    assert "Xem thị trường" in welcome or "cơ hội" in welcome
    assert "/check FPT" in welcome
    help_txt = formatters.format_help()
    assert "/check <mã>" in help_txt and "Tham khảo thêm" in help_txt
    assert "/chart <mã> ta" in help_txt
    assert "GARCH" in help_txt or "biến động" in help_txt
    assert "chia đều" not in help_txt or "không phải chia đều" in help_txt

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
    assert "Khí hậu thị trường" in sig_list
    assert "điểm" in sig_list
    assert "σ̂" not in sig_list
    assert "VNM" in sig_list and "FPT" in sig_list
    assert "→ Chi tiết: /check VNM" in sig_list
    assert "Tín hiệu đáng chú ý" in sig_list
    assert "Tránh mua mới" in sig_list
    assert "strategy pipeline" in sig_list.casefold() or "pipeline" in sig_list.casefold()
    assert "GARCH" in sig_list or "sizing" in sig_list.casefold()
    assert "10.0%" in sig_list or "trần" in sig_list  # w_max tip / size
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
    assert "∑" in pos or "trần" in pos
    assert "chạm trần" in pos
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
    assert "Báo cáo kiểm thử" in filled_bt
    assert "không phải lãi/lỗ tài khoản thật" in filled_bt.casefold() or "không cam kết" in filled_bt.casefold()
    assert "Sortino" in filled_bt
    assert "phát hiện hợp lệ" in filled_bt.casefold()
    assert "MIN_SHARPE" in filled_bt or "❌" in filled_bt
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
    assert "phạm vi" in miss.casefold() or "universe" in miss.casefold()
    assert "15:00" not in miss
    assert "không tự crawl" in miss.casefold() or "chỉ đọc store" in miss.casefold() or "ngoài phạm vi" in miss.casefold()
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
    assert labels == ["/check", "/signals", "/regime", "/positions"]


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
