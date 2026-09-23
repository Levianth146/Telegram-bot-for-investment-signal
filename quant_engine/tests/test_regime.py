"""Quant P0 unit tests — no network."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from quant_engine.alpha.kalman_trend import alpha_effective, fit_kalman_trend, slope_tstat
from quant_engine.alpha.ou_meanrev import fit_ou_process, ou_half_life
from quant_engine.portfolio.black_litterman import equal_weight_fallback
from quant_engine.regime import filtered_regime_probability, fit_or_fallback_regime
from quant_engine.risk.garch import position_size, rolling_sigma_fallback, stop_loss_price
from quant_engine.signal_engine import generate_signals


def _synthetic_close(n=120, drift=0.001, seed=0) -> pd.Series:
    rng = np.random.default_rng(seed)
    rets = drift + rng.normal(0, 0.015, size=n)
    prices = 100 * np.exp(np.cumsum(rets))
    dates = pd.bdate_range("2024-01-01", periods=n)
    return pd.Series(prices, index=dates.astype(str), name="close")


def test_alpha_effective_bounds():
    assert alpha_effective(1.0, 0, 0) == pytest.approx(0.5)
    assert alpha_effective(1.0, 100, 100) == pytest.approx(1.5)
    assert alpha_effective(2.0, 50, 50) == pytest.approx(2.0)


def test_kalman_trend_on_uptrend():
    close = _synthetic_close(drift=0.002, seed=1)
    level, slope, svar = fit_kalman_trend(np.log(close))
    assert len(level) == len(close)
    tstat = slope_tstat(float(slope.iloc[-1]), float(svar.iloc[-1]))
    assert tstat > 0


def test_kalman_incremental_matches_full():
    """P2-1: resume state theo ticker tương đương expanding filter full."""
    close = _synthetic_close(drift=0.001, seed=7)
    log_px = np.log(close)
    # Full đến n-1 rồi 1 bước → so với full n.
    n = len(log_px)
    *_, state = fit_kalman_trend(log_px.iloc[: n - 1], return_state=True)
    _l1, s1, v1 = fit_kalman_trend(log_px, init_state=state)
    _l0, s0, v0 = fit_kalman_trend(log_px)
    assert float(s1.iloc[-1]) == pytest.approx(float(s0.iloc[-1]), rel=1e-9, abs=1e-12)
    assert float(v1.iloc[-1]) == pytest.approx(float(v0.iloc[-1]), rel=1e-9, abs=1e-12)


def test_kalman_cache_keyed_by_ticker_not_n_returns():
    """P2-1: kalman_cache trong generate_signals key theo ticker."""
    from quant_engine import signal_engine as se

    idx = pd.bdate_range("2023-01-02", periods=60).strftime("%Y-%m-%d")
    aaa = pd.Series(
        100 + np.cumsum(np.random.default_rng(0).normal(0, 1, 60)),
        index=list(idx),
    )
    vni = pd.Series(
        1000 + np.cumsum(np.random.default_rng(1).normal(0, 1, 60)),
        index=list(idx),
    )
    cfg = {
        "quant_engine": {
            "benchmark": "VNINDEX",
            "regime_markov": {"enabled": False},
            "alpha_kalman_trend": {"enabled": True},
            "alpha_ou_meanreversion": {"enabled": False},
            "risk_garch": {"enabled": False},
        }
    }
    cache: dict = {}
    # Giống backtest: truncate closes ≤ as_of rồi gọi lại ngày sau.
    cut1 = { "AAA": aaa.iloc[:58], "VNINDEX": vni.iloc[:58] }
    se.generate_signals(
        cut1,
        as_of_date=idx[57],
        signal_tickers=["AAA"],
        config=cfg,
        kalman_cache=cache,
    )
    assert "AAA" in cache
    assert set(cache.keys()) == {"AAA"}
    n_before = int(cache["AAA"]["n"])
    cut2 = { "AAA": aaa.iloc[:59], "VNINDEX": vni.iloc[:59] }
    se.generate_signals(
        cut2,
        as_of_date=idx[58],
        signal_tickers=["AAA"],
        config=cfg,
        kalman_cache=cache,
    )
    # Expanding +1 quan sát; vẫn một key ticker (không nhân theo n_returns).
    assert set(cache.keys()) == {"AAA"}
    assert int(cache["AAA"]["n"]) == n_before + 1


def test_ou_half_life():
    assert ou_half_life(math.log(2)) == pytest.approx(1.0)
    with pytest.raises(ValueError):
        ou_half_life(0.0)
    # Mean-reverting residual around 0
    t = np.arange(80)
    resid = 0.5 * np.exp(-0.1 * t) + np.random.default_rng(0).normal(0, 0.05, size=80)
    params = fit_ou_process(resid)
    assert params["theta"] > 0


def test_position_size_and_stop():
    # min(w_max=0.1, 0.02/0.04=0.5) → capped at w_max
    assert position_size(0.04, 0.02, w_max=0.1) == pytest.approx(0.1)
    assert position_size(0.4, 0.02, w_max=0.1) == pytest.approx(0.05)
    assert stop_loss_price(100.0, 0.02, k=2.0) == pytest.approx(96.0)


def test_inverse_vol_normalize_monotonic():
    from quant_engine.risk.garch import inverse_vol_normalize_weights

    # w_max đủ cao để thấy thứ tự inverse-vol trước khi bão hòa cap.
    w = inverse_vol_normalize_weights(
        {"A": 0.01, "B": 0.02, "C": 0.04}, w_max=0.50, target_sum=1.0
    )
    assert w["A"] > w["B"] > w["C"]
    assert all(v <= 0.50 + 1e-9 for v in w.values())
    assert sum(w.values()) <= 1.0 + 1e-9
    # Risk-off (cap thấp) khác distribution risk-on
    capped = inverse_vol_normalize_weights(
        {"A": 0.01, "B": 0.02, "C": 0.04}, w_max=0.10, target_sum=1.0
    )
    assert capped != w
    assert all(v <= 0.10 + 1e-9 for v in capped.values())


def test_ou_neutral_buy_and_bear_no_buy():
    from quant_engine.signal_engine import _decide_action

    buy_ou = _decide_action(
        p_bull=0.45,
        alpha_eff=0.05,
        tstat=0.0,
        bull_threshold=0.55,
        bear_threshold=0.35,
        min_tstat=1.0,
        alpha_method="ou_residual",
        half_life=10.0,
    )
    assert buy_ou == "BUY"
    sell_ou = _decide_action(
        p_bull=0.45,
        alpha_eff=-0.05,
        tstat=0.0,
        bull_threshold=0.55,
        bear_threshold=0.35,
        min_tstat=1.0,
        alpha_method="ou_residual",
        half_life=10.0,
    )
    assert sell_ou == "SELL"
    bear = _decide_action(
        p_bull=0.2,
        alpha_eff=0.05,
        tstat=3.0,
        bull_threshold=0.55,
        bear_threshold=0.35,
        min_tstat=1.0,
        alpha_method="kalman_slope",
        half_life=None,
    )
    assert bear != "BUY"


def test_markov_nonconverged_fallback(monkeypatch):
    from quant_engine import regime as regime_mod

    def boom(*_a, **_k):
        raise RuntimeError("markov_mle_nonconverged")

    monkeypatch.setattr(regime_mod, "fit_markov_regime", boom)
    rets = _synthetic_close(n=300, drift=0.001).pct_change().dropna()
    pack = regime_mod.fit_or_fallback_regime(rets)
    assert pack["probabilities"]["method"] == "heuristic_nonconverged_markov"


def test_label_states_turbulent_by_variance():
    from quant_engine.regime import _label_states_by_mean_and_variance

    params = pd.Series(
        {
            "const[0]": -0.01,
            "const[1]": 0.00,
            "const[2]": 0.02,
            "sigma2[0]": 0.001,
            "sigma2[1]": 0.050,  # highest var → turbulent
            "sigma2[2]": 0.002,
        }
    )
    labels = _label_states_by_mean_and_variance(params, 3)
    assert labels[1] == "turbulent"
    assert labels[0] == "bear"
    assert labels[2] == "bull"


def test_regime_heuristic_fallback():
    rets = _synthetic_close(drift=0.002).pct_change().dropna()
    pack = fit_or_fallback_regime(rets)
    probs = pack["probabilities"]
    assert abs(sum(probs[k] for k in ("bull", "bear", "turbulent")) - 1.0) < 1e-9
    fallback = filtered_regime_probability(None, rets)
    assert "bull" in fallback


def test_regime_empty_returns_neutral():
    """Benchmark chưa có giá / 1 điểm → returns rỗng: không raise, p_bull=0.5."""
    pack = fit_or_fallback_regime(pd.Series(dtype=float))
    probs = pack["probabilities"]
    assert probs["method"] == "empty_returns_neutral"
    assert probs["bull"] == pytest.approx(0.5)
    assert pack["model"] is None


def test_equal_weight_fallback():
    weights = equal_weight_fallback(["aaa", "BBB"])
    assert weights == {"AAA": 0.5, "BBB": 0.5}


def test_generate_signals_writes_schema_fields(tmp_path):
    close_a = _synthetic_close(drift=0.002, seed=2)
    close_b = _synthetic_close(drift=-0.001, seed=3)
    signals = generate_signals(
        {"AAA": close_a, "BBB": close_b},
        as_of_date="2024-06-28",
        fundamental_scores={
            "AAA": {"growth_score": 70, "quality_score": 65},
            "BBB": {"growth_score": 40, "quality_score": 40},
        },
        config={
            "quant_engine": {
                "regime_markov": {"enabled": True},
                "alpha_kalman_trend": {"enabled": True},
                "alpha_ou_meanreversion": {"enabled": True},
                "risk_garch": {"enabled": True},
                "portfolio_black_litterman": {"enabled": False},
                "sigma_target": 0.02,
                "w_max": 0.1,
                "benchmark": "AAA",
            }
        },
    )
    assert len(signals) == 2
    for row in signals:
        assert row["date"] == "2024-06-28"
        assert row["action"] in {"BUY", "WATCH", "SELL"}
        assert 0.0 <= row["p_regime"] <= 1.0
        assert row["size"] >= 0.0
        assert row["reason_json"]


def test_rolling_sigma_fallback():
    rets = _synthetic_close().pct_change().dropna()
    sigma = rolling_sigma_fallback(rets, window=20)
    assert sigma > 0
