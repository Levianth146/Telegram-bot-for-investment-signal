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


def test_build_scoring_schedule_keys(monkeypatch):
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
    )
    # years 2020, 2021, 2022 (prior + window)
    assert assumed_filed_at(2020, 90) in schedule
    assert assumed_filed_at(2021, 90) in schedule
    assert assumed_filed_at(2022, 90) in schedule
    assert calls  # at least one provider build
    # lookback 3 for year 2022 → start 2020
    assert (2020, 2022) in calls


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
        {"date": "2024-06-28", "equity": 1.02},
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
    assert out["rows"] == 2
    conn = repository.get_connection(str(db))
    rows = {r["baseline"]: r for r in repository.get_backtest_results(conn, "portfolio")}
    conn.close()
    assert "B0_buyhold" in rows and "framework" in rows
    assert json.loads(rows["B0_buyhold"]["equity_curve_json"])[0]["equity"] == 1.0
    assert json.loads(rows["framework"]["equity_curve_json"])[-1]["equity"] == 1.03
    assert abs(float(rows["framework"]["sharpe"]) - 0.8) < 1e-9


def test_sharpe_unit():
    rets = pd.Series([0.01, -0.005, 0.008, 0.002])
    assert sharpe_ratio(rets) != 0
