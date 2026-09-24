"""Tests for bot charts (matplotlib Agg, no Telegram)."""

from __future__ import annotations

from bot.charts import (
    ChartDataError,
    render_backtest_equity_curve_chart,
    render_fundamental_radar_chart,
    render_monte_carlo_distribution_chart,
    render_price_chart,
    render_sector_overview_chart,
)
from store import repository


def test_fundamental_radar(tmp_path):
    out = tmp_path / "radar.png"
    path = render_fundamental_radar_chart("VNM", 70, 65, 60, 55, out)
    assert path.is_file()
    assert path.stat().st_size > 100


def test_price_chart_from_closes(tmp_path):
    out = tmp_path / "price.png"
    closes = [
        {"date": f"2024-01-{i:02d}", "close": 50.0 + i} for i in range(1, 15)
    ]
    path = render_price_chart("VNM", closes, out)
    assert path.is_file()
    assert path.stat().st_size > 100


def test_price_bars_store_roundtrip_and_chart(tmp_path):
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    n = repository.upsert_price_bars(
        conn,
        [
            {"ticker": "VNM", "date": f"2024-02-{i:02d}", "close": 60.0 + i}
            for i in range(1, 12)
        ],
    )
    assert n == 11
    closes = repository.get_price_closes(conn, "VNM", limit_days=500)
    conn.close()
    assert len(closes) == 11
    assert closes[0]["date"] <= closes[-1]["date"]
    path = render_price_chart("VNM", closes, tmp_path / "vnm_price.png")
    assert path.is_file()


def test_monte_carlo_hist(tmp_path):
    out = tmp_path / "mc.png"
    path = render_monte_carlo_distribution_chart(
        "AAA", [0.01, -0.02, 0.05, 0.03, -0.01] * 20, 0.08, 0.05, out
    )
    assert path.is_file()


def test_radar_missing_raises():
    try:
        render_fundamental_radar_chart("X", float("nan"), 1, 1, 1, "x.png")
        assert False, "expected ChartDataError"
    except ChartDataError:
        pass


def test_backtest_and_sector_charts(tmp_path):
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    import json

    curve = [{"date": f"2024-01-{i:02d}", "equity": 1.0 + i * 0.01} for i in range(1, 20)]
    repository.upsert_backtest_results(
        conn,
        [
            {
                "run_id": "r1",
                "run_at": "2024-06-01T00:00:00",
                "scope": "portfolio",
                "baseline": "framework",
                "cagr": 0.1,
                "sharpe": 1.0,
                "max_drawdown": -0.1,
                "win_rate": 0.5,
                "n_trades": 3,
                "equity_curve_json": json.dumps(curve),
                "turnover": 0.1,
                "sortino": 1.1,
                "calmar": 1.0,
                "profit_factor": 1.2,
                "max_drawdown_days": 5,
                "cvar95_realized": None,
                "cvar95_calibration_note": None,
                "sharpe_bull_regime": None,
                "sharpe_bear_regime": None,
            }
        ],
    )
    repository.upsert_watchlist(
        conn,
        [{"as_of_date": "2024-06-28", "ticker": "VNM", "fundamental_view": "PASS"}],
    )
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
                "ticker": "ZZZ",
                "filed_at": "2024-06-28",
                "period": "2023",
                "growth_score": 10,
                "quality_score": 10,
                "safety_score": 10,
                "valuation_score": 10,
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
                "sector": "Consumer",
                "industry": "Thực phẩm",
                "subindustry": None,
                "updated_at": "2024-01-01",
            },
            {
                "ticker": "ZZZ",
                "market": "HOSE",
                "sector": "Consumer",
                "industry": "Thực phẩm",
                "subindustry": None,
                "updated_at": "2024-01-01",
            },
        ],
    )
    conn.close()

    eq = render_backtest_equity_curve_chart(
        "portfolio", "r1", tmp_path / "eq.png", db_path=str(db)
    )
    assert eq.is_file()
    sec = render_sector_overview_chart(
        "2024-06-28", tmp_path / "sec.png", db_path=str(db)
    )
    assert sec.is_file()


def test_equity_align_oos_window(tmp_path):
    """Baseline dài hơn phải cắt về cùng khung OOS framework khi align."""
    import json

    from bot.charts import render_backtest_equity_curve_chart

    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    long_curve = [
        {"date": f"2023-{m:02d}-15", "equity": 1.0 + m * 0.01} for m in range(1, 13)
    ] + [{"date": f"2024-01-{i:02d}", "equity": 1.12 + i * 0.01} for i in range(1, 10)]
    oos_curve = [
        {"date": f"2024-01-{i:02d}", "equity": 1.0 + i * 0.02} for i in range(1, 10)
    ]
    common = {
        "run_id": "align1",
        "run_at": "2024-06-01T00:00:00",
        "scope": "portfolio",
        "cagr": 0.1,
        "sharpe": 0.5,
        "max_drawdown": -0.1,
        "win_rate": None,
        "n_trades": 5,
        "turnover": None,
        "sortino": None,
        "calmar": None,
        "profit_factor": None,
        "max_drawdown_days": None,
        "margin_bps": None,
        "cvar95_realized": None,
        "cvar95_calibration_note": None,
        "sharpe_bull_regime": None,
        "sharpe_bear_regime": None,
    }
    repository.upsert_backtest_results(
        conn,
        [
            {
                **common,
                "baseline": "B0_buyhold",
                "equity_curve_json": json.dumps(long_curve),
            },
            {
                **common,
                "baseline": "framework",
                "sharpe": -0.5,
                "equity_curve_json": json.dumps(oos_curve),
            },
        ],
    )
    conn.close()
    path = render_backtest_equity_curve_chart(
        "portfolio",
        "align1",
        tmp_path / "eq_oos.png",
        db_path=str(db),
        align_to_oos=True,
    )
    assert path.is_file()
    assert path.stat().st_size > 100


def test_equity_baselines_filter_b0_only(tmp_path, monkeypatch):
    """Phần 5: baselines=['framework','B0_buyhold'] chỉ plot 2 series đó."""
    import json

    import pytest

    from bot.charts import ChartDataError, render_backtest_equity_curve_chart

    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    curve = [{"date": f"2024-02-{i:02d}", "equity": 1.0 + i * 0.01} for i in range(1, 12)]
    common = {
        "run_id": "filt1",
        "run_at": "2024-06-01T00:00:00",
        "scope": "portfolio",
        "cagr": 0.1,
        "sharpe": 0.5,
        "max_drawdown": -0.1,
        "win_rate": None,
        "n_trades": 5,
        "turnover": None,
        "sortino": None,
        "calmar": None,
        "profit_factor": None,
        "max_drawdown_days": None,
        "margin_bps": None,
        "cvar95_realized": None,
        "cvar95_calibration_note": None,
        "sharpe_bull_regime": None,
        "sharpe_bear_regime": None,
        "equity_curve_json": json.dumps(curve),
    }
    repository.upsert_backtest_results(
        conn,
        [
            {**common, "baseline": "framework"},
            {**common, "baseline": "B0_buyhold"},
            {**common, "baseline": "B1_ta"},
            {**common, "baseline": "B2_canslim"},
        ],
    )
    conn.close()

    plotted: list[str] = []
    real_subplots = __import__("matplotlib.pyplot", fromlist=["plt"]).subplots

    def _wrap_subplots(*a, **k):
        fig, ax = real_subplots(*a, **k)
        real_plot = ax.plot

        def _plot(*pa, **pk):
            if "label" in pk:
                plotted.append(str(pk["label"]))
            return real_plot(*pa, **pk)

        ax.plot = _plot
        return fig, ax

    monkeypatch.setattr("bot.charts.plt.subplots", _wrap_subplots)

    path = render_backtest_equity_curve_chart(
        "portfolio",
        "filt1",
        tmp_path / "eq_b0.png",
        db_path=str(db),
        baselines=["framework", "B0_buyhold"],
    )
    assert path.is_file()
    assert set(plotted) == {"framework", "B0_buyhold"}
    assert "B1_ta" not in plotted and "B2_canslim" not in plotted

    with pytest.raises(ChartDataError):
        render_backtest_equity_curve_chart(
            "portfolio",
            "filt1",
            tmp_path / "eq_none.png",
            db_path=str(db),
            baselines=["no_such_baseline"],
        )
