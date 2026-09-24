"""Backtest P0 tests — synthetic prices, no network."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from backtest.ablation import run_ablation
from backtest.costs import (
    apply_transaction_costs,
    is_tradable_at_price_limit,
)
from backtest.engine import run_backtest
from backtest.metrics import compute_metrics, sharpe_ratio
from backtest.walk_forward import run_walk_forward, walk_forward_windows
from store import repository


def _close(n=80, drift=0.001, seed=0, start="2023-01-02") -> pd.Series:
    rng = np.random.default_rng(seed)
    rets = drift + rng.normal(0, 0.012, size=n)
    prices = 100 * np.exp(np.cumsum(rets))
    dates = pd.bdate_range(start, periods=n)
    return pd.Series(prices, index=dates.strftime("%Y-%m-%d"), name="close")


def _config(**overrides):
    cfg = {
        "quant_engine": {
            "regime_markov": {"enabled": True},
            "alpha_kalman_trend": {"enabled": True},
            "alpha_ou_meanreversion": {"enabled": True},
            "risk_garch": {"enabled": True},
            "portfolio_black_litterman": {"enabled": False},
            "probabilistic_monte_carlo": {"enabled": False},
            "benchmark": "AAA",
            "sigma_target": 0.02,
            "w_max": 0.2,
            "bull_threshold": 0.4,
            "bear_threshold": 0.3,
            "min_slope_tstat": 0.5,
        },
        "backtest": {
            "cost": {"tax_sell_pct": 0.001, "fee_roundtrip_pct": 0.003},
            "walk_forward": {"train_years": 1, "test_months": 3},
            "metrics": {
                "turnover": {"enabled": True},
                "sortino": {"enabled": True},
                "calmar": {"enabled": True},
                "profit_factor": {"enabled": True},
                "max_drawdown_days": {"enabled": True},
            },
        },
    }
    cfg.update(overrides)
    return cfg


def test_costs_and_limit():
    net = apply_transaction_costs(0.10, 0.001, 0.003)
    assert net == pytest.approx(0.096)
    assert is_tradable_at_price_limit(105.0, 100.0, 0.07) is True
    assert is_tradable_at_price_limit(107.0, 100.0, 0.07) is False


def test_run_backtest_finite_metrics():
    closes = {
        "AAA": _close(drift=0.002, seed=1),
        "BBB": _close(drift=0.0005, seed=2),
    }
    start, end = closes["AAA"].index[10], closes["AAA"].index[-1]
    result = run_backtest(
        _config(),
        start,
        end,
        close_by_ticker=closes,
        scoring_schedule=None,
        signal_every_n_days=5,
    )
    assert result["equity_curve"]
    assert result["equity_curve"][0]["date"] >= start
    assert result["equity_curve"][-1]["date"] <= end
    m = result["metrics"]
    assert m["n_trades"] >= 0
    for key in ("cagr", "sharpe", "max_drawdown", "sortino", "calmar", "turnover"):
        assert key in m
        val = m[key]
        if val is not None and not (isinstance(val, float) and np.isnan(val)):
            assert np.isfinite(val) or val == float("inf")


def test_pit_no_future_closes(monkeypatch):
    """generate_signals must only see closes on or before as_of_date."""
    closes = {"AAA": _close(n=60, seed=3)}
    seen_max = {}

    from quant_engine import signal_engine

    real = signal_engine.generate_signals

    def wrapped(close_by_ticker, *, as_of_date, **kwargs):
        for ticker, series in close_by_ticker.items():
            if len(series):
                seen_max[as_of_date] = max(
                    seen_max.get(as_of_date, ""), str(series.index.max())
                )
                assert str(series.index.max()) <= as_of_date
        return real(close_by_ticker, as_of_date=as_of_date, **kwargs)

    monkeypatch.setattr("backtest.engine.generate_signals", wrapped)
    start, end = closes["AAA"].index[5], closes["AAA"].index[-1]
    run_backtest(
        _config(),
        start,
        end,
        close_by_ticker=closes,
        signal_every_n_days=10,
    )
    assert seen_max


def test_signal_fill_is_t_plus_1(monkeypatch):
    """BUY/SELL từ quant không khớp cùng close đã dùng để tính tín hiệu."""
    closes = {
        "AAA": _close(n=80, drift=0.002, seed=11),
        "BBB": _close(n=80, drift=0.001, seed=12),
    }
    signal_days: dict[str, str] = {}

    def fake_generate(close_by_ticker, *, as_of_date, **kwargs):
        emit = kwargs.get("signal_tickers") or list(close_by_ticker)
        rows = []
        for ticker in emit:
            t = str(ticker).upper()
            if t in signal_days:
                continue
            signal_days[t] = as_of_date
            rows.append(
                {
                    "date": as_of_date,
                    "ticker": t,
                    "action": "BUY",
                    "size": 0.2,
                    "stop": None,
                    "reason": "unit_test_buy",
                }
            )
        return rows

    monkeypatch.setattr("backtest.engine.generate_signals", fake_generate)
    start, end = closes["AAA"].index[5], closes["AAA"].index[-1]
    result = run_backtest(
        _config(),
        start,
        end,
        close_by_ticker=closes,
        signal_every_n_days=5,
    )
    buys = [
        t
        for t in result["trades"]
        if t.get("reason") == "signal_buy" and t.get("entry_date")
    ]
    assert buys, "expected at least one BUY fill"
    for trade in buys:
        ticker = trade["ticker"]
        gen = signal_days[ticker]
        assert trade["entry_date"] > gen, (
            f"{ticker}: fill {trade['entry_date']} must be after signal {gen}"
        )


def test_buy_opens_long_positive_pnl_on_rise(monkeypatch):
    """BUY = long: giá tăng → pnl đóng lệnh > 0 (sau phí nhỏ)."""
    dates = pd.bdate_range("2023-01-02", periods=40).strftime("%Y-%m-%d")
    # Giá tăng mạnh sau ngày tín hiệu để PnL long dương rõ.
    prices = [100.0] * 10 + [100.0 + i for i in range(30)]
    closes = {"AAA": pd.Series(prices, index=list(dates), name="close")}
    fired = {"n": 0}

    def fake_generate(close_by_ticker, *, as_of_date, **kwargs):
        if fired["n"] > 0:
            # Sau khi đã BUY: SELL khi đã cầm đủ lâu (engine T+2).
            if as_of_date >= dates[20]:
                return [
                    {
                        "date": as_of_date,
                        "ticker": "AAA",
                        "action": "SELL",
                        "size": 0.0,
                        "stop": None,
                        "reason": "unit_test_sell",
                    }
                ]
            return []
        fired["n"] += 1
        return [
            {
                "date": as_of_date,
                "ticker": "AAA",
                "action": "BUY",
                "size": 0.5,
                "stop": None,
                "reason": "unit_test_buy",
            }
        ]

    monkeypatch.setattr("backtest.engine.generate_signals", fake_generate)
    result = run_backtest(
        {
            "quant_engine": {"benchmark": "AAA"},
            "backtest": {
                "cost": {"tax_sell_pct": 0.0, "fee_roundtrip_pct": 0.0, "limit_pct": 0.5},
            },
        },
        dates[5],
        dates[-1],
        close_by_ticker=closes,
        signal_every_n_days=3,
    )
    closed = [t for t in result["trades"] if t.get("exit_date") and t.get("pnl") is not None]
    assert closed, "expected a closed long trade"
    assert closed[0]["pnl"] > 0


def test_costs_reduce_closed_trade_pnl():
    gross = 0.05
    cheap = apply_transaction_costs(gross, 0.0, 0.0)
    costly = apply_transaction_costs(gross, 0.001, 0.003)
    assert costly < cheap


def test_walk_forward_windows():
    windows = walk_forward_windows("2020-01-01", "2023-12-31", 1, 6)
    assert len(windows) >= 2
    for train_start, train_end, test_start, test_end in windows:
        assert train_start < train_end < test_start <= test_end


def test_run_walk_forward_synthetic():
    closes = {
        "AAA": _close(n=320, drift=0.001, seed=4, start="2021-06-01"),
        "BBB": _close(n=320, drift=0.0008, seed=5, start="2021-06-01"),
    }
    start, end = closes["AAA"].index[0], closes["AAA"].index[-1]
    cfg = _config()
    cfg["quant_engine"]["risk_garch"] = {"enabled": False}  # faster OOS folds
    out = run_walk_forward(
        cfg,
        start,
        end,
        close_by_ticker=closes,
        signal_every_n_days=20,
    )
    assert out["folds"]
    assert "sharpe" in out["metrics"]
    assert out["n_folds"] == len(out["folds"])
    assert "fold_sharpe_mean" in out
    assert "fold_sharpe_std" in out
    assert out["metrics"].get("n_folds") == out["n_folds"]


def test_ablation_decide_keep_cut():
    from backtest.ablation import decide_keep_cut

    steps = [
        {"layer": "B0_buyhold", "sharpe": 0.50},
        {"layer": "regime", "sharpe": 0.55},  # +0.05 < 0.10 → cắt
        {"layer": "risk", "sharpe": 0.70},  # +0.15 ≥ 0.10 → giữ
    ]
    out = decide_keep_cut(steps)
    assert out[0]["decision"] == "baseline"
    assert out[1]["delta_sharpe"] == pytest.approx(0.05)
    assert "cut" in out[1]["decision"]
    assert out[2]["delta_sharpe"] == pytest.approx(0.15)
    assert "keep" in out[2]["decision"]


def test_ablation_signal_closes_excludes_benchmark():
    from backtest.ablation import _signal_closes

    closes = {"VNM": _close(n=10, seed=1), "VNINDEX": _close(n=10, seed=2)}
    cfg = {"quant_engine": {"benchmark": "VNINDEX"}}
    subset = _signal_closes(closes, cfg)
    assert "VNM" in subset
    assert "VNINDEX" not in subset


def test_build_scoring_schedule_keys(monkeypatch, tmp_path):
    from backtest import ablation as ablation_mod
    from data.ingest.pit import assumed_filed_at

    calls: list[tuple[int, int]] = []

    def fake_build(tickers, start_year, end_year, config=None, db_path="store/bot.db"):
        calls.append((start_year, end_year))
        import pandas as pd

        return {
            "VNM": pd.DataFrame(
                {"year": [end_year], "ticker": ["VNM"], "revenue": [1.0]}
            )
        }

    monkeypatch.setattr(
        "data.ingest.scoring_frames.build_scoring_frames_from_providers",
        fake_build,
    )
    cfg = {
        "data_sources": {
            "financial_statements_backtest": {"assumed_publication_lag_days": 90}
        }
    }
    schedule = ablation_mod.build_scoring_schedule(
        ["VNM"],
        "2021-01-01",
        "2022-12-31",
        cfg,
        lookback_years=3,
        include_prior_year=True,
        cache_dir=tmp_path,
        refresh=True,
    )
    # years 2020, 2021, 2022 (prior + window)
    assert assumed_filed_at(2020, 90) in schedule
    assert assumed_filed_at(2021, 90) in schedule
    assert assumed_filed_at(2022, 90) in schedule
    assert calls  # at least one provider build
    # lookback 3 for year 2022 → start 2020
    assert (2020, 2022) in calls

    # Cache hit: cùng key → 0 provider calls bổ sung; frames keys giống.
    calls.clear()
    schedule2 = ablation_mod.build_scoring_schedule(
        ["VNM"],
        "2021-01-01",
        "2022-12-31",
        cfg,
        lookback_years=3,
        include_prior_year=True,
        cache_dir=tmp_path,
        refresh=False,
    )
    assert calls == []
    assert set(schedule2.keys()) == set(schedule.keys())
    for k in schedule:
        assert set(schedule2[k].keys()) == set(schedule[k].keys())


def test_ablation_regime_alpha_flags_differ(monkeypatch):
    """regime layer must disable alpha; alpha/risk enable it."""
    from backtest import ablation as ablation_mod

    seen: list[tuple[bool, bool, bool]] = []

    def fake_set(config, *, regime, alpha, risk):
        seen.append((regime, alpha, risk))
        return config

    monkeypatch.setattr(ablation_mod, "_set_quant_flags", fake_set)

    def fake_backtest(*_a, **_k):
        return {
            "metrics": {
                "cagr": 0.0,
                "sharpe": 0.0,
                "max_drawdown": 0.0,
                "win_rate": 0.0,
                "n_trades": 0,
            }
        }

    monkeypatch.setattr(ablation_mod, "run_backtest", fake_backtest)
    closes = {"AAA": _close(n=40, seed=9)}
    ablation_mod.run_ablation(
        _config(),
        ["regime", "alpha", "risk"],
        close_by_ticker=closes,
        start_date=closes["AAA"].index[5],
        end_date=closes["AAA"].index[-1],
        signal_every_n_days=20,
    )
    assert seen[0] == (True, False, False)
    assert seen[1] == (True, True, False)
    assert seen[2] == (True, True, True)


def test_p1_cvar_and_regime_sharpe_metrics():
    from backtest.metrics import compute_metrics

    curve = [
        {"date": f"2024-03-{(i % 28) + 1:02d}", "equity": 1.0 + 0.002 * i * ((-1) ** i)}
        for i in range(60)
    ]
    # unique-ish dates by prefixing with week index
    curve = [
        {"date": f"2024-{(1 + i // 28):02d}-{(i % 28) + 1:02d}", "equity": 1.0 + 0.001 * i}
        for i in range(60)
    ]
    regime = {row["date"]: (0.7 if i % 2 == 0 else 0.2) for i, row in enumerate(curve)}
    cfg = {
        "backtest": {
            "metrics": {
                "cvar95_calibration": {"enabled": True},
                "regime_conditional_sharpe": {"enabled": True},
                "turnover": {"enabled": False},
                "sortino": {"enabled": False},
                "calmar": {"enabled": False},
                "profit_factor": {"enabled": False},
                "max_drawdown_days": {"enabled": False},
            }
        },
        "quant_engine": {"bull_threshold": 0.55, "bear_threshold": 0.35},
    }
    metrics = compute_metrics(
        curve,
        [],
        cfg,
        signals=[{"cvar95": -0.03}, {"cvar95": -0.025}],
        regime_by_date=regime,
    )
    assert "cvar95_realized" in metrics
    assert "cvar95_calibration_note" in metrics
    assert "sharpe_bull_regime" in metrics
    assert "sharpe_bear_regime" in metrics


def test_upsert_backtest_results(tmp_path):
    db = tmp_path / "bot.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    curve = [{"date": "2024-01-02", "equity": 1.0}, {"date": "2024-01-03", "equity": 1.01}]
    metrics = compute_metrics(curve, [], _config())
    repository.upsert_backtest_results(
        conn,
        [
            {
                "run_id": "test_run",
                "run_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "scope": "portfolio",
                "baseline": "framework",
                "cagr": metrics.get("cagr"),
                "sharpe": metrics.get("sharpe"),
                "max_drawdown": metrics.get("max_drawdown"),
                "win_rate": metrics.get("win_rate"),
                "n_trades": metrics.get("n_trades"),
                "equity_curve_json": json.dumps(curve),
                "turnover": metrics.get("turnover"),
                "sortino": metrics.get("sortino"),
                "calmar": metrics.get("calmar"),
                "profit_factor": metrics.get("profit_factor"),
                "max_drawdown_days": metrics.get("max_drawdown_days"),
            }
        ],
    )
    rows = repository.get_backtest_results(conn, "portfolio")
    assert repository.list_backtest_scopes(conn) == ["portfolio"]
    conn.close()
    assert len(rows) == 1
    assert rows[0]["run_id"] == "test_run"


def test_ablation_persist_to_store(tmp_path):
    from backtest.ablation import persist_ablation_to_store

    db = tmp_path / "bot.db"
    curve_b0 = [
        {"date": "2021-01-04", "equity": 1.0},
        {"date": "2021-06-01", "equity": 1.05},
        {"date": "2021-12-31", "equity": 1.12},
    ]
    curve_wf = [
        {"date": "2024-01-02", "equity": 1.0},
        {"date": "2024-03-01", "equity": 0.98},
        {"date": "2024-06-28", "equity": 1.02},
        {"date": "2024-09-30", "equity": 0.99},
        {"date": "2024-12-31", "equity": 1.03},
    ]
    payload = {
        "steps": [
            {
                "layer": "B0_buyhold",
                "cagr": 0.12,
                "sharpe": 0.65,
                "max_drawdown": -0.3,
                "win_rate": None,
                "n_trades": 0,
                "equity_curve": curve_b0,
            },
            {
                "layer": "B1_ta",
                "cagr": 0.05,
                "sharpe": 0.4,
                "max_drawdown": -0.2,
                "n_trades": 12,
                "equity_curve": curve_b0,
            },
            {
                "layer": "B2_canslim",
                "cagr": 0.07,
                "sharpe": 0.5,
                "max_drawdown": -0.22,
                "n_trades": 8,
                "equity_curve": curve_b0,
            },
            {
                "layer": "risk",
                "cagr": -0.02,
                "sharpe": -0.9,
                "max_drawdown": -0.08,
                "win_rate": 0.13,
                "n_trades": 23,
            },
        ],
        "walk_forward": {
            "cagr": 0.03,
            "sharpe": 0.8,
            "max_drawdown": -0.02,
            "n_trades": 3,
            "equity_curve": curve_wf,
        },
    }
    out = persist_ablation_to_store(
        payload, db_path=str(db), run_id="ablation_test", scope="portfolio"
    )
    assert out["rows"] == 4
    assert out.get("checks", 0) >= 4
    conn = repository.get_connection(str(db))
    rows = {r["baseline"]: r for r in repository.get_backtest_results(conn, "portfolio")}
    checks = repository.get_backtest_checks(
        conn, "portfolio", "framework", "ablation_test"
    )
    yearly = repository.get_yearly_breakdown(
        conn, "portfolio", "framework", "ablation_test"
    )
    conn.close()
    assert "B0_buyhold" in rows and "framework" in rows
    assert "B1_ta" in rows and "B2_canslim" in rows
    assert json.loads(rows["B0_buyhold"]["equity_curve_json"])[0]["equity"] == 1.0
    assert json.loads(rows["framework"]["equity_curve_json"])[-1]["equity"] == 1.03
    assert abs(float(rows["framework"]["sharpe"]) - 0.8) < 1e-9
    # Enrich Sortino/Calmar từ equity khi artifact thiếu
    assert rows["framework"].get("sortino") is not None
    assert rows["framework"].get("calmar") is not None
    names = {c["check_name"] for c in checks}
    assert "CONCENTRATED_WEIGHT" in names
    assert "MIN_SHARPE_IMPROVEMENT_OOS" in names
    assert yearly  # có năm từ curve_wf 2024


def test_margin_bps_and_yearly():
    from backtest.metrics import margin_bps, yearly_breakdown_from_equity

    assert margin_bps(0.10, 0.05) == pytest.approx(20_000.0)
    curve = [
        {"date": "2023-01-03", "equity": 1.0},
        {"date": "2023-06-01", "equity": 1.05},
        {"date": "2023-12-29", "equity": 1.10},
        {"date": "2024-01-02", "equity": 1.10},
        {"date": "2024-06-28", "equity": 1.12},
        {"date": "2024-12-31", "equity": 1.15},
    ]
    yearly = yearly_breakdown_from_equity(curve, [], _config())
    assert [y["year"] for y in yearly] == [2023, 2024]
    assert yearly[0]["sharpe"] is not None or yearly[0]["cagr"] is not None


def test_build_backtest_checks_concentrated():
    from backtest.ablation import build_backtest_checks

    cfg = {
        "backtest": {
            "checks": {
                "min_sharpe_improvement_oos": 0.10,
                "min_trades_for_significance": 30,
                "max_turnover_pct": 200,
                "max_position_weight_pct": 0.10,
            }
        },
        "quant_engine": {"w_max": 0.10},
    }
    rows = {
        "framework": {"sharpe": -0.8, "n_trades": 36, "turnover": None},
        "B0_buyhold": {"sharpe": 0.2},
    }
    checks = build_backtest_checks(
        rows, run_id="t", scope="portfolio", config=cfg
    )
    by = {c["check_name"]: c for c in checks}
    assert by["CONCENTRATED_WEIGHT"]["passed"] == 1
    assert by["MIN_SHARPE_IMPROVEMENT_OOS"]["passed"] == 0
    assert by["MIN_TRADES_FOR_SIGNIFICANCE"]["passed"] == 1


def test_b1_b2_baseline_runners_finite():
    import numpy as np

    from backtest.ablation import _b1_ta_result, _b2_canslim_result

    rng = np.random.default_rng(0)
    dates = pd.bdate_range("2022-01-01", periods=300).astype(str)
    closes = {
        "AAA": pd.Series(
            50 * np.exp(np.cumsum(rng.normal(0.0005, 0.02, 300))), index=dates
        ),
        "BBB": pd.Series(
            40 * np.exp(np.cumsum(rng.normal(0.0003, 0.018, 300))), index=dates
        ),
        "CCC": pd.Series(
            30 * np.exp(np.cumsum(rng.normal(0.0004, 0.022, 300))), index=dates
        ),
    }
    cfg = {
        "quant_engine": {"sigma_target": 0.02},
        "backtest": {"cost": {"tax_sell_pct": 0.001, "fee_roundtrip_pct": 0.003}},
    }
    b1 = _b1_ta_result(closes, "2022-01-01", "2023-12-31", cfg)
    b2 = _b2_canslim_result(closes, "2022-01-01", "2023-12-31", cfg)
    assert len(b1["equity_curve"]) > 50
    assert len(b2["equity_curve"]) > 50
    # Net <= gross after costs
    assert b1["metrics"]["net_total_return"] <= b1["metrics"]["gross_total_return"] + 1e-9
    assert b2["metrics"]["net_total_return"] <= b2["metrics"]["gross_total_return"] + 1e-9


def test_stop_overrides_quant_buy(monkeypatch):
    """Stop hit + Quant BUY cùng ngày → final order vẫn SELL."""
    dates = pd.bdate_range("2023-01-02", periods=40).strftime("%Y-%m-%d")
    # Giá giảm dần để chạm stop sau khi vào lệnh.
    prices = [100.0] * 8 + [100.0 - i * 2 for i in range(32)]
    closes = {"AAA": pd.Series(prices, index=list(dates), name="close")}
    phase = {"n": 0}

    def fake_generate(close_by_ticker, *, as_of_date, **kwargs):
        phase["n"] += 1
        if phase["n"] == 1:
            return [
                {
                    "date": as_of_date,
                    "ticker": "AAA",
                    "action": "BUY",
                    "size": 0.5,
                    "stop": 95.0,
                    "reason": "unit_buy",
                }
            ]
        # Sau khi đã hold: cố BUY lại khi stop có thể đã hit
        return [
            {
                "date": as_of_date,
                "ticker": "AAA",
                "action": "BUY",
                "size": 0.5,
                "stop": 95.0,
                "reason": "unit_buy_override_attempt",
            }
        ]

    monkeypatch.setattr("backtest.engine.generate_signals", fake_generate)
    result = run_backtest(
        {
            "quant_engine": {"benchmark": "AAA"},
            "backtest": {
                "cost": {"tax_sell_pct": 0.0, "fee_roundtrip_pct": 0.0, "limit_pct": 0.5},
            },
        },
        dates[2],
        dates[-1],
        close_by_ticker=closes,
        signal_every_n_days=1,
    )
    stop_exits = [t for t in result["trades"] if t.get("reason") == "stop_hit"]
    assert stop_exits, "expected stop_hit exit"


def test_stop_overrides_quant_watch(monkeypatch):
    """Stop hit + Quant WATCH → vẫn SELL."""
    dates = pd.bdate_range("2023-01-02", periods=40).strftime("%Y-%m-%d")
    prices = [100.0] * 8 + [100.0 - i * 2 for i in range(32)]
    closes = {"AAA": pd.Series(prices, index=list(dates), name="close")}
    phase = {"n": 0}

    def fake_generate(close_by_ticker, *, as_of_date, **kwargs):
        phase["n"] += 1
        if phase["n"] == 1:
            return [
                {
                    "date": as_of_date,
                    "ticker": "AAA",
                    "action": "BUY",
                    "size": 0.5,
                    "stop": 95.0,
                    "reason": "unit_buy",
                }
            ]
        return [
            {
                "date": as_of_date,
                "ticker": "AAA",
                "action": "WATCH",
                "size": 0.0,
                "stop": 95.0,
                "reason": "unit_watch",
            }
        ]

    monkeypatch.setattr("backtest.engine.generate_signals", fake_generate)
    result = run_backtest(
        {
            "quant_engine": {"benchmark": "AAA"},
            "backtest": {
                "cost": {"tax_sell_pct": 0.0, "fee_roundtrip_pct": 0.0, "limit_pct": 0.5},
            },
        },
        dates[2],
        dates[-1],
        close_by_ticker=closes,
        signal_every_n_days=1,
    )
    assert any(t.get("reason") == "stop_hit" for t in result["trades"])


def test_no_stop_model_signal_normal(monkeypatch):
    """Không stop → model BUY bình thường (T+1)."""
    dates = pd.bdate_range("2023-01-02", periods=30).strftime("%Y-%m-%d")
    prices = [100.0 + i * 0.5 for i in range(30)]
    closes = {"AAA": pd.Series(prices, index=list(dates), name="close")}
    fired = {"n": 0}

    def fake_generate(close_by_ticker, *, as_of_date, **kwargs):
        if fired["n"] > 0:
            return []
        fired["n"] += 1
        return [
            {
                "date": as_of_date,
                "ticker": "AAA",
                "action": "BUY",
                "size": 0.4,
                "stop": None,
                "reason": "unit_buy",
            }
        ]

    monkeypatch.setattr("backtest.engine.generate_signals", fake_generate)
    result = run_backtest(
        {
            "quant_engine": {"benchmark": "AAA"},
            "backtest": {
                "cost": {"tax_sell_pct": 0.0, "fee_roundtrip_pct": 0.0, "limit_pct": 0.5},
            },
        },
        dates[2],
        dates[-1],
        close_by_ticker=closes,
        signal_every_n_days=5,
    )
    buys = [t for t in result["trades"] if t.get("reason") == "signal_buy"]
    assert buys


def test_fundamental_view_schema_in_watchlist(monkeypatch):
    """_active_watchlist phải truyền fundamental_view cho Quant."""
    from backtest.engine import _active_watchlist

    frames = {
        "AAA": pd.DataFrame(
            {
                "year": [2022, 2023],
                "ticker": ["AAA", "AAA"],
                "revenue": [1.0, 1.1],
            }
        )
    }
    schedule = {"2024-03-31": frames}
    seen = {}

    def fake_score(frames_in, start_year, end_year, config=None):
        df = pd.DataFrame(
            [
                {
                    "ticker": "AAA",
                    "growth_score": 70,
                    "quality_score": 65,
                    "safety_score": 60,
                    "valuation_score": 55,
                    "fundamental_score": 62,
                    "classification": "WATCH",
                }
            ]
        )
        return df, None, None

    monkeypatch.setattr("backtest.engine.score_current_universe", fake_score)
    tickers, scores = _active_watchlist(schedule, "2024-06-01", ["AAA"], {})
    assert "AAA" in tickers
    assert scores["AAA"]["fundamental_view"] == "WATCH"
    assert scores["AAA"]["classification"] == "WATCH"


def test_fundamental_fail_exit_while_holding(monkeypatch):
    """PASS→FAIL khi đang hold → schedule fundamental_fail_exit (T+1)."""
    dates = pd.bdate_range("2023-01-02", periods=50).strftime("%Y-%m-%d")
    prices = [100.0 + i * 0.2 for i in range(50)]
    closes = {"AAA": pd.Series(prices, index=list(dates), name="close")}

    # scoring_schedule: early PASS, later empty keep → FAIL/excluded
    call_day = {"d": None}

    def fake_watchlist(scoring_schedule, as_of, fallback, config, **_kwargs):
        call_day["d"] = as_of
        # Before mid: on watchlist; after: empty (FAIL)
        if as_of < dates[25]:
            return ["AAA"], {
                "AAA": {
                    "fundamental_view": "PASS",
                    "classification": "PASS",
                    "growth_score": 70,
                    "quality_score": 70,
                }
            }
        return [], {}

    phase = {"n": 0}

    def fake_generate(close_by_ticker, *, as_of_date, **kwargs):
        phase["n"] += 1
        if phase["n"] == 1:
            return [
                {
                    "date": as_of_date,
                    "ticker": "AAA",
                    "action": "BUY",
                    "size": 0.5,
                    "stop": None,
                    "reason": "unit_buy",
                }
            ]
        return []

    monkeypatch.setattr("backtest.engine._active_watchlist", fake_watchlist)
    monkeypatch.setattr("backtest.engine.generate_signals", fake_generate)
    result = run_backtest(
        {
            "quant_engine": {"benchmark": "AAA"},
            "backtest": {
                "cost": {"tax_sell_pct": 0.0, "fee_roundtrip_pct": 0.0, "limit_pct": 0.5},
            },
        },
        dates[5],
        dates[-1],
        close_by_ticker=closes,
        scoring_schedule={"2023-01-01": {"dummy": pd.DataFrame()}},
        signal_every_n_days=3,
    )
    fail_exits = [
        t for t in result["trades"] if t.get("reason") == "fundamental_fail_exit"
    ]
    assert fail_exits, "expected fundamental_fail_exit after FAIL refresh"


def test_dynamic_fundamental_no_end_date_leak(monkeypatch):
    """Ablation fundamental không dùng watchlist end_date cho cả kỳ."""
    from backtest import ablation as ablation_mod

    dates = pd.bdate_range("2023-01-02", periods=40).strftime("%Y-%m-%d")
    closes = {
        "AAA": pd.Series([100.0 + i for i in range(40)], index=list(dates)),
        "BBB": pd.Series([50.0 + i * 0.5 for i in range(40)], index=list(dates)),
    }
    seen_asof: list[str] = []

    def fake_wl(schedule, as_of, fallback, config, **_kwargs):
        seen_asof.append(as_of)
        # Early: only AAA; late: AAA+BBB — nếu leak end_date thì luôn cả hai
        if as_of < dates[20]:
            return ["AAA"], {"AAA": {"fundamental_view": "PASS", "classification": "PASS"}}
        return ["AAA", "BBB"], {
            "AAA": {"fundamental_view": "PASS", "classification": "PASS"},
            "BBB": {"fundamental_view": "WATCH", "classification": "WATCH"},
        }

    monkeypatch.setattr("backtest.engine._active_watchlist", fake_wl)
    result = ablation_mod._dynamic_fundamental_result(
        closes,
        dates[0],
        dates[-1],
        {"backtest": {"cost": {"tax_sell_pct": 0.0, "fee_roundtrip_pct": 0.0}}},
        scoring_schedule={"2023-01-01": {}},
    )
    assert result["equity_curve"]
    assert any(d < dates[20] for d in seen_asof)
    assert any(d >= dates[20] for d in seen_asof)
    # Phải gọi nhiều ngày, không chỉ end_date
    assert len(set(seen_asof)) > 5


def test_ff_precompute_matches_daily_rescore(monkeypatch):
    """Precompute filed_at → state phải giống rescore mỗi ngày (cùng frames)."""
    from backtest.engine import (
        _active_watchlist,
        precompute_fundamental_states,
    )

    frames = {
        "AAA": pd.DataFrame(
            {
                "year": [2022, 2023],
                "ticker": ["AAA", "AAA"],
                "revenue": [1.0, 1.1],
            }
        ),
        "BBB": pd.DataFrame(
            {
                "year": [2022, 2023],
                "ticker": ["BBB", "BBB"],
                "revenue": [2.0, 2.2],
            }
        ),
    }
    schedule = {
        "2024-03-31": frames,
        "2025-03-31": {
            "AAA": pd.DataFrame(
                {
                    "year": [2023, 2024],
                    "ticker": ["AAA", "AAA"],
                    "revenue": [1.1, 1.2],
                }
            )
        },
    }
    score_calls = {"n": 0}

    def fake_score(frames_in, start_year, end_year, config=None):
        score_calls["n"] += 1
        rows = []
        for t in frames_in:
            rows.append(
                {
                    "ticker": t,
                    "growth_score": 70,
                    "quality_score": 65,
                    "safety_score": 60,
                    "valuation_score": 55,
                    "fundamental_score": 62,
                    "classification": "WATCH" if t == "AAA" else "PASS",
                }
            )
        return pd.DataFrame(rows), None, None

    monkeypatch.setattr("backtest.engine.score_current_universe", fake_score)
    states = precompute_fundamental_states(schedule)
    assert score_calls["n"] == len(schedule)

    days = ["2024-01-01", "2024-06-01", "2025-06-01"]
    for day in days:
        cached = _active_watchlist(
            schedule, day, ["AAA", "BBB"], {}, ff_states=states
        )
        daily = _active_watchlist(schedule, day, ["AAA", "BBB"], {})
        assert cached[0] == daily[0]
        assert set(cached[1].keys()) == set(daily[1].keys())
        for t in cached[1]:
            assert cached[1][t]["classification"] == daily[1][t]["classification"]


def test_run_backtest_precompute_equiv_daily_path(monkeypatch):
    """run_backtest với FF precompute ≡ daily rescore (trades + equity cuối)."""
    dates = pd.bdate_range("2024-01-02", periods=60).strftime("%Y-%m-%d").tolist()
    closes = {
        "AAA": pd.Series(
            [100.0 + i * 0.3 for i in range(60)], index=dates, name="close"
        ),
        "VNINDEX": pd.Series(
            [1000.0 + i * 0.1 for i in range(60)], index=dates, name="close"
        ),
    }
    frames = {
        "AAA": pd.DataFrame(
            {"year": [2022, 2023], "ticker": ["AAA", "AAA"], "revenue": [1.0, 1.1]}
        )
    }
    schedule = {dates[10]: frames, dates[35]: frames}

    def fake_score(frames_in, start_year, end_year, config=None):
        return (
            pd.DataFrame(
                [
                    {
                        "ticker": "AAA",
                        "growth_score": 70,
                        "quality_score": 65,
                        "safety_score": 60,
                        "valuation_score": 55,
                        "fundamental_score": 62,
                        "classification": "WATCH",
                    }
                ]
            ),
            None,
            None,
        )

    def fake_generate(close_by_ticker, *, as_of_date, **kwargs):
        # Tín hiệu đơn giản deterministic — không phụ thuộc regime/GARCH.
        if "AAA" not in close_by_ticker:
            return []
        return [
            {
                "date": as_of_date,
                "ticker": "AAA",
                "action": "BUY" if as_of_date < dates[40] else "SELL",
                "size": 0.4,
                "stop": None,
                "reason": "unit_signal",
                "p_regime": 0.6,
            }
        ]

    monkeypatch.setattr("backtest.engine.score_current_universe", fake_score)
    monkeypatch.setattr("backtest.engine.generate_signals", fake_generate)
    cfg = {
        "quant_engine": {"benchmark": "VNINDEX"},
        "backtest": {
            "cost": {"tax_sell_pct": 0.0, "fee_roundtrip_pct": 0.0, "limit_pct": 0.5},
        },
    }
    opt = run_backtest(
        cfg,
        dates[0],
        dates[-1],
        close_by_ticker=closes,
        scoring_schedule=schedule,
        signal_every_n_days=5,
        signal_tickers=["AAA"],
    )
    # Ép daily rescore: precompute trả None → _active_watchlist score mỗi ngày.
    monkeypatch.setattr(
        "backtest.engine.precompute_fundamental_states", lambda _s: None
    )
    daily = run_backtest(
        cfg,
        dates[0],
        dates[-1],
        close_by_ticker=closes,
        scoring_schedule=schedule,
        signal_every_n_days=5,
        signal_tickers=["AAA"],
    )
    assert opt["metrics"]["n_trades"] == daily["metrics"]["n_trades"]
    assert len(opt["trades"]) == len(daily["trades"])
    for a, b in zip(opt["trades"], daily["trades"]):
        assert a.get("entry_date") == b.get("entry_date")
        assert a.get("exit_date") == b.get("exit_date")
        assert a.get("ticker") == b.get("ticker")
        assert a.get("reason") == b.get("reason")
    assert opt["equity_curve"] and daily["equity_curve"]
    assert abs(
        float(opt["equity_curve"][-1]["equity"])
        - float(daily["equity_curve"][-1]["equity"])
    ) < 1e-9


def test_truncate_searchsorted_matches_loc():
    """_truncate searchsorted ≡ loc mask (ISO date index)."""
    from backtest.engine import _truncate

    idx = pd.bdate_range("2024-01-02", periods=20).strftime("%Y-%m-%d")
    s = pd.Series(range(20), index=list(idx), dtype=float)
    as_of = idx[10]
    legacy = s.loc[s.index <= as_of]
    got = _truncate(s, as_of)
    assert list(got.index) == list(legacy.index)
    assert list(got.values) == list(legacy.values)


def test_fast_dev_cli_preset_and_banner():
    """--fast-dev constants: banner + mini 12-ticker fallback (plan A3)."""
    import scripts.run_backtest_report as rpt

    assert rpt.FAST_DEV_BANNER == "FAST DEV MODE — NOT FOR FINAL RESEARCH METRICS"
    assert len(rpt.FAST_DEV_MINI_TICKERS) == 12
    for t in (
        "FPT",
        "VNM",
        "GAS",
        "MWG",
        "REE",
        "PNJ",
        "PLX",
        "GVR",
        "VHM",
        "VHC",
        "DCM",
        "SAB",
    ):
        assert t in rpt.FAST_DEV_MINI_TICKERS


def test_build_scoring_schedule_cache_hit_log(monkeypatch, tmp_path, capsys):
    """CACHE HIT log rõ khi year_*.pkl đã có."""
    from backtest import ablation as ablation_mod

    calls: list[tuple[int, int]] = []

    def fake_build(tickers, start_year, end_year, config=None, db_path="store/bot.db"):
        calls.append((start_year, end_year))
        import pandas as pd

        return {
            "VNM": pd.DataFrame(
                {"year": [end_year], "ticker": ["VNM"], "revenue": [1.0]}
            )
        }

    monkeypatch.setattr(
        "data.ingest.scoring_frames.build_scoring_frames_from_providers",
        fake_build,
    )
    cfg = {
        "data_sources": {
            "financial_statements_backtest": {"assumed_publication_lag_days": 90}
        }
    }
    ablation_mod.build_scoring_schedule(
        ["VNM"],
        "2021-01-01",
        "2021-12-31",
        cfg,
        lookback_years=2,
        include_prior_year=False,
        cache_dir=tmp_path,
        refresh=True,
    )
    calls.clear()
    ablation_mod.build_scoring_schedule(
        ["VNM"],
        "2021-01-01",
        "2021-12-31",
        cfg,
        lookback_years=2,
        include_prior_year=False,
        cache_dir=tmp_path,
        refresh=False,
    )
    out = capsys.readouterr().out
    assert "CACHE HIT" in out
    assert calls == []


def test_garch_same_day_memo(monkeypatch):
    """garch_cache: cùng (as_of, ticker, n) → không fit lại."""
    from quant_engine import signal_engine as se

    fits = {"n": 0}
    real = se.fit_or_fallback_sigma

    def counting(returns, window=20, **kwargs):
        fits["n"] += 1
        return real(returns, window=window, **kwargs)

    monkeypatch.setattr(se, "fit_or_fallback_sigma", counting)

    idx = pd.bdate_range("2023-01-02", periods=120).strftime("%Y-%m-%d")
    closes = {
        "AAA": pd.Series(100 + np.cumsum(np.random.default_rng(0).normal(0, 1, 120)), index=list(idx)),
        "VNINDEX": pd.Series(
            1000 + np.cumsum(np.random.default_rng(1).normal(0, 1, 120)), index=list(idx)
        ),
    }
    cfg = {
        "quant_engine": {
            "benchmark": "VNINDEX",
            "regime_markov": {"enabled": False},
            "alpha_kalman_trend": {"enabled": False},
            "alpha_ou_meanreversion": {"enabled": False},
            "risk_garch": {"enabled": True},
        }
    }
    cache: dict = {}
    as_of = idx[-1]
    se.generate_signals(
        closes,
        as_of_date=as_of,
        signal_tickers=["AAA"],
        config=cfg,
        garch_cache=cache,
    )
    n1 = fits["n"]
    assert n1 >= 1
    se.generate_signals(
        closes,
        as_of_date=as_of,
        signal_tickers=["AAA"],
        config=cfg,
        garch_cache=cache,
    )
    assert fits["n"] == n1  # same-day memo hit


def test_garch_refit_every_n_should_refit_cadence():
    """Phần 8.5: should_refit_garch — None/≤0 luôn True; N>0 theo days_since_fit."""
    from quant_engine.risk.garch import should_refit_garch

    assert should_refit_garch(days_since_fit=0, refit_every_n=None) is True
    assert should_refit_garch(days_since_fit=100, refit_every_n=None) is True
    assert should_refit_garch(days_since_fit=0, refit_every_n=0) is True
    assert should_refit_garch(days_since_fit=None, refit_every_n=5) is True
    assert should_refit_garch(days_since_fit=0, refit_every_n=5) is False
    assert should_refit_garch(days_since_fit=4, refit_every_n=5) is False
    assert should_refit_garch(days_since_fit=5, refit_every_n=5) is True
    assert should_refit_garch(days_since_fit=21, refit_every_n=21) is True


def test_garch_refit_every_n_forecast_skips_mle(monkeypatch):
    """Giữa các kỳ refit: dùng forecast roll-forward, không gọi fit_gjr_garch."""
    from quant_engine.risk import garch as garch_mod

    fits = {"n": 0}
    real_fit = garch_mod.fit_gjr_garch

    def counting(returns):
        fits["n"] += 1
        return real_fit(returns)

    monkeypatch.setattr(garch_mod, "fit_gjr_garch", counting)

    rng = np.random.default_rng(7)
    rets = pd.Series(rng.normal(0, 0.01, 120))

    first = garch_mod.fit_or_fallback_sigma(
        rets, refit_every_n=5, days_since_fit=None, previous_model=None
    )
    assert first["refit"] is True
    assert first["method"] == "gjr_garch"
    assert fits["n"] == 1
    model = first["model"]
    assert model is not None

    mid = garch_mod.fit_or_fallback_sigma(
        rets, refit_every_n=5, days_since_fit=2, previous_model=model
    )
    assert mid["refit"] is False
    assert mid["method"] == "gjr_garch_forecast"
    assert fits["n"] == 1  # không MLE thêm
    assert mid["model"] is model

    again = garch_mod.fit_or_fallback_sigma(
        rets, refit_every_n=5, days_since_fit=5, previous_model=model
    )
    assert again["refit"] is True
    assert fits["n"] == 2


def test_garch_state_cache_refit_across_sessions(monkeypatch):
    """garch_state_cache: N=5 → MLE phiên 1 và 6; giữa đó forecast."""
    from quant_engine import signal_engine as se
    from quant_engine.risk import garch as garch_mod

    fits = {"n": 0}
    real_fit = garch_mod.fit_gjr_garch

    def counting(returns):
        fits["n"] += 1
        return real_fit(returns)

    monkeypatch.setattr(garch_mod, "fit_gjr_garch", counting)

    idx = pd.bdate_range("2023-01-02", periods=130).strftime("%Y-%m-%d")
    closes = {
        "AAA": pd.Series(
            100 + np.cumsum(np.random.default_rng(0).normal(0, 1, 130)),
            index=list(idx),
        ),
        "VNINDEX": pd.Series(
            1000 + np.cumsum(np.random.default_rng(1).normal(0, 1, 130)),
            index=list(idx),
        ),
    }
    cfg = {
        "quant_engine": {
            "benchmark": "VNINDEX",
            "parallel_workers": 1,
            "regime_markov": {"enabled": False},
            "alpha_kalman_trend": {"enabled": False},
            "alpha_ou_meanreversion": {"enabled": False},
            "risk_garch": {"enabled": True, "refit_every_n": 5},
        }
    }
    state: dict = {}
    day_cache: dict = {}
    # 6 phiên tín hiệu cách nhau → days_since_fit 0..5; MLE ở phiên 1 và 6.
    as_ofs = [idx[80], idx[90], idx[100], idx[110], idx[120], idx[129]]
    methods = []
    for as_of in as_ofs:
        day_cache.clear()  # mỗi as_of mới — không dùng same-day memo xuyên phiên
        se.generate_signals(
            closes,
            as_of_date=as_of,
            signal_tickers=["AAA"],
            config=cfg,
            garch_cache=day_cache,
            garch_state_cache=state,
        )
        methods.append(state["AAA"].get("days_since_fit"))

    assert fits["n"] == 2
    assert methods[0] == 0
    assert methods[-1] == 0
    assert state["AAA"]["model"] is not None
