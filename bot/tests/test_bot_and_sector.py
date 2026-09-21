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
        ],
    )
    assert repository.get_sector_for_ticker(conn, "VNM")["industry"] == "Thực phẩm"
    overview = repository.get_sector_overview(conn, "2024-06-28")
    conn.close()
    by_ind = {r["industry"]: r for r in overview}
    assert by_ind["Thực phẩm"]["n_pass"] == 1
    assert by_ind["Ngân hàng"]["n_watch"] == 1


def test_sector_job_with_prepared_rows(tmp_path):
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
            "reason_json": '{"slope_tstat": 2.1, "alpha_method": "kalman_slope"}',
        },
        {
            "fundamental_view": "PASS",
            "growth_score": 70,
            "quality_score": 65,
            "safety_score": 60,
            "valuation_score": 55,
        },
        ta_indicators={"rsi_14": 55.0, "ma_trend": "MA20 trên MA50 (ngắn hạn nghiêng tăng)"},
        meta={"market": "HOSE", "industry": "Thực phẩm"},
    )
    assert "VNM" in msg and "HOSE" in msg
    assert "KHUYẾN NGHỊ: MUA" in msg
    assert "① Chất lượng doanh nghiệp" in msg
    assert "chung cả rổ" in msg
    assert "Tham khảo thêm" in msg and "RSI(14)" in msg
    assert "/chart VNM price" in msg
    assert "eps_cagr_3y" not in msg
    assert "kalman_slope" not in msg
    assert "equal_weight" not in msg
    assert formatters.DISCLAIMER in msg
    welcome = formatters.format_welcome()
    assert "/signals" in welcome and "Khí hậu thị trường" in welcome
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
    assert "điểm=" in sig_list
    assert "σ̂" not in sig_list
    assert "VNM" in sig_list and "FPT" in sig_list
    assert formatters.format_signals_list([])
    assert "Watchlist" in formatters.format_watchlist(
        [{"as_of_date": "2024-01-01", "ticker": "AAA", "fundamental_view": "PASS"}]
    )
    assert "Không có vị thế" in formatters.format_positions([])
    assert "Chưa có kết quả" in formatters.format_backtest_results([], "portfolio")
    assert "Sector overview" in formatters.format_sector_overview(
        [{"industry": "Thực phẩm", "n_pass": 1, "n_watch": 0, "n_fail": 0}],
        "2024-06-28",
    )
    status = formatters.format_status(
        config_flags={"regime_markov": True},
        latest_signal_date="2024-06-28",
        watchlist_n=2,
        open_positions_n=0,
    )
    assert "regime_markov: ON" in status


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
