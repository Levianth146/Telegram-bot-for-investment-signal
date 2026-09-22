"""Build store.signals rows from prepared price series + fundamental scores.

Pure path: no network. ``pipeline/daily_job`` prepares OHLCV via ``data/`` then
calls ``generate_signals``. Shared with ``backtest/`` (ARCHITECTURE invariant #2).
"""

from __future__ import annotations

import json
from typing import Any, Mapping

import numpy as np
import pandas as pd

from quant_engine.alpha.kalman_trend import (
    alpha_effective,
    fit_kalman_trend,
    slope_tstat,
)
from quant_engine.alpha.ou_meanrev import fit_ou_process, ou_half_life
from quant_engine.portfolio.black_litterman import (
    bl_portfolio_weights,
    equal_weight_fallback,
)
from quant_engine.regime import fit_or_fallback_regime
from quant_engine.risk.garch import (
    fit_or_fallback_sigma,
    inverse_vol_normalize_weights,
    position_size,
    stop_loss_price,
)


def _log_returns(close: pd.Series) -> pd.Series:
    prices = pd.to_numeric(close, errors="coerce").dropna()
    return np.log(prices).diff().dropna()


def _compute_alpha_pack(
    close: pd.Series,
    *,
    fund: Mapping[str, Any],
    kalman_enabled: bool,
    use_ou: bool,
) -> dict[str, Any]:
    """Kalman/OU alpha + Alpha_effective for one ticker (shared BL + signal path)."""
    log_px = np.log(close)
    alpha_raw = float("nan")
    tstat = float("nan")
    half_life = None
    kalman_level_last = None
    alpha_method = "none"
    if kalman_enabled:
        level, slope, slope_var = fit_kalman_trend(log_px)
        alpha_raw = float(slope.iloc[-1])
        tstat = slope_tstat(float(slope.iloc[-1]), float(slope_var.iloc[-1]))
        alpha_method = "kalman_slope"
        try:
            kalman_level_last = float(level.iloc[-1])
        except (TypeError, ValueError, IndexError):
            kalman_level_last = None
        if use_ou:
            resid = log_px - level
            ou = fit_ou_process(resid)
            try:
                half_life = ou_half_life(ou["theta"])
            except ValueError:
                half_life = None
            if (
                not pd.isna(ou.get("mu"))
                and not pd.isna(resid.iloc[-1])
                and ou.get("theta", 0) > 0
            ):
                alpha_raw = float(ou["mu"] - resid.iloc[-1])
                alpha_method = "ou_residual"

    growth = fund.get("growth_score")
    quality = fund.get("quality_score")
    raw_for_alpha = (
        tstat
        if alpha_method == "kalman_slope" and not pd.isna(tstat)
        else alpha_raw
    )
    alpha_eff = alpha_effective(raw_for_alpha, growth, quality)
    return {
        "alpha_raw": alpha_raw,
        "tstat": tstat,
        "half_life": half_life,
        "kalman_level_last": kalman_level_last,
        "alpha_method": alpha_method,
        "alpha_eff": alpha_eff,
        "growth": growth,
        "quality": quality,
        "valuation": fund.get("valuation_score"),
    }


def _decide_action(
    *,
    p_bull: float,
    alpha_eff: float,
    tstat: float,
    bull_threshold: float,
    bear_threshold: float,
    min_tstat: float,
    fundamental_view: str | None = None,
    alpha_method: str = "kalman_slope",
    half_life: float | None = None,
    max_ou_half_life: float = 60.0,
) -> str:
    """Quyết định BUY/SELL/WATCH theo regime + alpha method (long-only V1).

    - Bull: Kalman slope + tstat → BUY/SELL
    - Neutral: OU edge dương + half-life hợp lệ → BUY; âm → SELL
    - Bear: không mở long mới (SELL nếu alpha âm, else WATCH)
    - Cap Fundamental WATCH/FAIL → không BUY
    """
    view = str(fundamental_view or "").strip().upper()
    method = str(alpha_method or "kalman_slope")

    if pd.isna(alpha_eff):
        action = "WATCH"
    elif p_bull <= bear_threshold:
        # Bear: không mở long mới
        action = "SELL" if (not pd.isna(alpha_eff) and alpha_eff < 0) else "WATCH"
    elif p_bull >= bull_threshold:
        # Bull / trending — Kalman
        if alpha_eff > 0 and (
            method != "kalman_slope" or (not pd.isna(tstat) and tstat >= min_tstat)
        ):
            action = "BUY"
        elif alpha_eff < 0 and (
            method != "kalman_slope" or (not pd.isna(tstat) and tstat <= -min_tstat)
        ):
            action = "SELL"
        else:
            action = "WATCH"
    else:
        # Neutral / sideway — OU mean-reversion
        hl_ok = (
            half_life is not None
            and not pd.isna(half_life)
            and 0 < float(half_life) <= float(max_ou_half_life)
        )
        if method == "ou_residual" and hl_ok and alpha_eff > 0:
            action = "BUY"
        elif method == "ou_residual" and (alpha_eff < 0 or not hl_ok):
            action = "SELL" if alpha_eff < 0 else "WATCH"
        elif alpha_eff > 0 and not pd.isna(tstat) and tstat >= min_tstat:
            action = "BUY"
        elif alpha_eff < 0 and not pd.isna(tstat) and tstat <= -min_tstat:
            action = "SELL"
        else:
            action = "WATCH"

    if view in {"WATCH", "FAIL"} and action == "BUY":
        return "WATCH"
    return action


def generate_signals(
    close_by_ticker: Mapping[str, pd.Series],
    *,
    as_of_date: str,
    fundamental_scores: Mapping[str, Mapping[str, Any]] | None = None,
    index_ticker: str | None = None,
    signal_tickers: list[str] | None = None,
    config: Mapping[str, Any] | None = None,
    regime_cache: dict[tuple[Any, ...], Mapping[str, Any]] | None = None,
    garch_cache: dict[tuple[Any, ...], Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Generate one signals row per ticker (schema.sql contract).

    Parameters
    ----------
    close_by_ticker:
        Prepared close series (may include benchmark series not in ``signal_tickers``).
    fundamental_scores:
        Optional ``{ticker: {growth_score, quality_score, ...}}`` for Alpha_effective.
    index_ticker:
        Benchmark for regime; must be present in ``close_by_ticker`` when possible.
    signal_tickers:
        Names that receive signal rows. Defaults to all keys in ``close_by_ticker``
        except the benchmark when ``index_ticker`` is set and distinct.
    config:
        Pipeline config fragment (reads ``quant_engine`` block).
    regime_cache:
        Optional memo ``{(as_of, benchmark, n_returns): probabilities}`` — tránh
        fit Markov trùng trong cùng experiment khi cùng cửa sổ expanding.
    garch_cache:
        Optional same-day memo ``{(as_of, ticker, n_returns): risk_pack}`` — tránh
        fit GARCH trùng cùng as_of trong một run (không đổi daily→weekly).
    """
    if not close_by_ticker:
        return []

    cfg = dict(config or {})
    qcfg = dict(cfg.get("quant_engine") or {})
    sigma_target = float(qcfg.get("sigma_target", 0.02))
    w_max = float(qcfg.get("w_max", 0.10))
    stop_k = float(qcfg.get("stop_k", 2.0))
    bull_threshold = float(qcfg.get("bull_threshold", 0.55))
    bear_threshold = float(qcfg.get("bear_threshold", 0.35))
    min_tstat = float(qcfg.get("min_slope_tstat", 1.0))
    regime_enabled = bool((qcfg.get("regime_markov") or {}).get("enabled", True))
    kalman_enabled = bool((qcfg.get("alpha_kalman_trend") or {}).get("enabled", True))
    ou_enabled = bool((qcfg.get("alpha_ou_meanreversion") or {}).get("enabled", True))
    garch_enabled = bool((qcfg.get("risk_garch") or {}).get("enabled", True))
    bl_cfg = dict(qcfg.get("portfolio_black_litterman") or {})
    bl_enabled = bool(bl_cfg.get("enabled", False))
    bl_tau = float(bl_cfg.get("tau", 0.05))
    bl_delta = float(bl_cfg.get("delta", 2.5))
    mc_cfg = dict(qcfg.get("probabilistic_monte_carlo") or {})
    mc_enabled = bool(mc_cfg.get("enabled", False))
    mc_paths = int(mc_cfg.get("n_paths", 2000))
    mc_horizon = int(mc_cfg.get("horizon_days", 10))
    mc_tp = float(mc_cfg.get("tp_pct", 0.08))
    hawkes_enabled = bool((qcfg.get("probabilistic_hawkes") or {}).get("enabled", False))

    available = {str(t).strip().upper() for t in close_by_ticker}
    scores = {
        str(k).strip().upper(): v for k, v in (fundamental_scores or {}).items()
    }
    configured_benchmark = (
        (index_ticker or qcfg.get("benchmark") or "").strip().upper() or None
    )
    # Regime series: prefer configured benchmark when present; else first series
    regime_benchmark = configured_benchmark
    if regime_benchmark and regime_benchmark not in available:
        regime_benchmark = next(iter(available)) if available else None

    if signal_tickers is not None:
        tickers = [
            str(t).strip().upper()
            for t in signal_tickers
            if str(t).strip().upper() in available
        ]
    else:
        tickers = sorted(available)

    if not tickers:
        return []

    # Regime on benchmark returns (chuỗi rỗng → p_bull=0.5, không crash)
    p_bull = 0.5
    regime_method = "disabled"
    if regime_enabled and regime_benchmark and regime_benchmark in close_by_ticker:
        index_returns = _log_returns(close_by_ticker[regime_benchmark])
        n_rets = int(len(index_returns))
        cache_key = (str(as_of_date), str(regime_benchmark), n_rets)
        probs: Mapping[str, Any] | None = None
        if regime_cache is not None and cache_key in regime_cache:
            probs = regime_cache[cache_key]
        else:
            regime_pack = fit_or_fallback_regime(index_returns)
            probs = regime_pack["probabilities"]
            if regime_cache is not None:
                regime_cache[cache_key] = probs
        p_bull = float(probs.get("bull", 0.5))
        regime_method = str(probs.get("method", "unknown"))

    use_ou = ou_enabled and p_bull < bull_threshold and p_bull > bear_threshold

    # Precompute alphas (needed for BL views; reused in emit loop)
    alpha_packs: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        close = pd.to_numeric(close_by_ticker[ticker], errors="coerce").dropna()
        if len(close) < 30:
            continue
        alpha_packs[ticker] = _compute_alpha_pack(
            close,
            fund=scores.get(ticker) or {},
            kalman_enabled=kalman_enabled,
            use_ou=use_ou,
        )

    # Portfolio weights over signal universe only
    if bl_enabled and len(alpha_packs) >= 2:
        alpha_signals = {
            t: pack["alpha_eff"]
            for t, pack in alpha_packs.items()
            if pack["alpha_eff"] is not None and not pd.isna(pack["alpha_eff"])
        }
        valuation_signals = {
            t: pack["valuation"]
            for t, pack in alpha_packs.items()
            if pack["valuation"] is not None and not pd.isna(pack["valuation"])
        }
        weights = bl_portfolio_weights(
            close_by_ticker,
            list(alpha_packs),
            alpha_signals,
            valuation_signals or None,
            tau=bl_tau,
            delta=bl_delta,
        )
        weight_method = "black_litterman"
    else:
        weights = equal_weight_fallback(tickers)
        weight_method = "equal_weight" if not bl_enabled else "equal_weight_bl_fallback"

    # Precompute sigma cho inverse-vol sizing (Option B V1)
    sigma_by_ticker: dict[str, float] = {}
    risk_by_ticker: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        close = pd.to_numeric(close_by_ticker[ticker], errors="coerce").dropna()
        if len(close) < 30:
            continue
        returns = _log_returns(close)
        n_rets = int(len(returns))
        garch_key = (str(as_of_date), str(ticker), n_rets)
        if garch_enabled:
            if garch_cache is not None and garch_key in garch_cache:
                risk = dict(garch_cache[garch_key])
            else:
                risk = fit_or_fallback_sigma(returns)
                if garch_cache is not None:
                    # Không cache object model nặng — chỉ sigma/method (same-day reuse).
                    garch_cache[garch_key] = {
                        "sigma_hat": risk.get("sigma_hat"),
                        "method": risk.get("method"),
                    }
        else:
            risk = {
                "sigma_hat": float(returns.iloc[-20:].std(ddof=1))
                if len(returns) >= 2
                else float("nan"),
                "method": "disabled_rolling",
            }
        risk_by_ticker[ticker] = risk
        sigma_hat = risk.get("sigma_hat")
        if sigma_hat is not None and not pd.isna(sigma_hat) and float(sigma_hat) > 0:
            sigma_by_ticker[ticker] = float(sigma_hat)

    if garch_enabled and sigma_by_ticker:
        risk_weights = inverse_vol_normalize_weights(
            sigma_by_ticker, w_max=w_max, target_sum=1.0
        )
        size_method = "inverse_vol_normalize"
    else:
        risk_weights = {}
        size_method = "legacy_sigma_target"

    hawkes_mult = 1.0
    if hawkes_enabled:
        # Volume-event Hawkes needs daily spikes; size overlay applied when fit works
        try:
            from quant_engine.probabilistic.hawkes import (
                crowding_size_multiplier,
                fit_hawkes_from_returns,
            )

            bench_rets = (
                _log_returns(close_by_ticker[regime_benchmark])
                if regime_benchmark and regime_benchmark in close_by_ticker
                else None
            )
            if bench_rets is not None and len(bench_rets) >= 60:
                fitted = fit_hawkes_from_returns(bench_rets)
                hawkes_mult = crowding_size_multiplier(fitted["branching_ratio"])
        except Exception:  # noqa: BLE001
            hawkes_mult = 1.0

    signals: list[dict[str, Any]] = []
    for ticker in tickers:
        close = pd.to_numeric(close_by_ticker[ticker], errors="coerce").dropna()
        if len(close) < 30:
            signals.append(
                {
                    "date": as_of_date,
                    "ticker": ticker,
                    "action": "WATCH",
                    "score": None,
                    "p_regime": p_bull,
                    "sigma_hat": None,
                    "stop": None,
                    "size": 0.0,
                    "p_tp_before_sl": None,
                    "cvar95": None,
                    "reason_json": json.dumps(
                        {"error": "insufficient_price_history", "n": len(close)},
                        ensure_ascii=False,
                    ),
                }
            )
            continue

        entry_price = float(close.iloc[-1])
        pack = alpha_packs.get(ticker) or _compute_alpha_pack(
            close,
            fund=scores.get(ticker) or {},
            kalman_enabled=kalman_enabled,
            use_ou=use_ou,
        )
        alpha_eff = pack["alpha_eff"]
        tstat = pack["tstat"]
        half_life = pack["half_life"]
        alpha_method = pack["alpha_method"]
        growth = pack["growth"]
        quality = pack["quality"]

        risk = risk_by_ticker.get(ticker) or {
            "sigma_hat": float("nan"),
            "method": "missing",
        }
        sigma_hat = risk["sigma_hat"]
        if size_method == "inverse_vol_normalize":
            size = float(risk_weights.get(ticker, 0.0))
        else:
            size = position_size(sigma_hat, sigma_target, w_max=w_max)
        # BL / equal-weight overlay: không vượt portfolio weight × hawkes
        size = min(size, float(weights.get(ticker, w_max))) * float(hawkes_mult)
        stop = stop_loss_price(entry_price, sigma_hat, k=stop_k)

        fund_row = scores.get(ticker) or {}
        fund_view = str(
            fund_row.get("fundamental_view") or fund_row.get("classification") or ""
        ).upper() or None
        tstat_for_action = (
            tstat
            if alpha_method == "kalman_slope"
            else (1.0 if (not pd.isna(alpha_eff) and alpha_eff > 0) else -1.0)
        )
        action_uncapped = _decide_action(
            p_bull=p_bull,
            alpha_eff=alpha_eff,
            tstat=tstat_for_action,
            bull_threshold=bull_threshold,
            bear_threshold=bear_threshold,
            min_tstat=min_tstat,
            fundamental_view=None,
            alpha_method=alpha_method,
            half_life=half_life,
        )
        action = _decide_action(
            p_bull=p_bull,
            alpha_eff=alpha_eff,
            tstat=tstat_for_action,
            bull_threshold=bull_threshold,
            bear_threshold=bear_threshold,
            min_tstat=min_tstat,
            fundamental_view=fund_view,
            alpha_method=alpha_method,
            half_life=half_life,
        )

        reason = {
            "regime_method": regime_method,
            "p_bull": p_bull,
            "alpha_method": alpha_method,
            "alpha_effective": None if pd.isna(alpha_eff) else float(alpha_eff),
            "slope_tstat": None if pd.isna(tstat) else float(tstat),
            "ou_half_life": half_life,
            "kalman_level_last": pack.get("kalman_level_last"),
            "sigma_method": risk.get("method"),
            "size_method": size_method,
            "weight_method": weight_method,
            "portfolio_weight": float(weights.get(ticker, 0.0)),
            "hawkes_size_mult": float(hawkes_mult),
            "growth_score": growth,
            "quality_score": quality,
            "fundamental_view": fund_view,
        }
        if action_uncapped == "BUY" and action == "WATCH":
            reason["action_policy"] = "fundamental_watch_no_buy"

        p_tp_before_sl = None
        cvar95 = None
        if (
            mc_enabled
            and sigma_hat is not None
            and not pd.isna(sigma_hat)
            and sigma_hat > 0
        ):
            from quant_engine.probabilistic.monte_carlo import monte_carlo_signal_stats

            try:
                mc = monte_carlo_signal_stats(
                    entry_price,
                    float(sigma_hat),
                    returns,
                    stop_price=None if pd.isna(stop) else float(stop),
                    tp_pct=mc_tp,
                    horizon_days=mc_horizon,
                    n_paths=mc_paths,
                )
                p_tp_before_sl = mc["p_tp_before_sl"]
                cvar95 = mc["cvar95"]
                reason["monte_carlo"] = {
                    "n_paths": mc["n_paths"],
                    "horizon_days": mc["horizon_days"],
                    "tp_pct": mc["tp_pct"],
                    "sl_pct": mc["sl_pct"],
                }
            except Exception:  # noqa: BLE001 — never block daily signals
                reason["monte_carlo_error"] = "simulation_failed"

        signals.append(
            {
                "date": as_of_date,
                "ticker": ticker,
                "action": action,
                "score": None if pd.isna(alpha_eff) else float(alpha_eff),
                "p_regime": p_bull,
                "sigma_hat": None if pd.isna(sigma_hat) else float(sigma_hat),
                "stop": None if pd.isna(stop) else float(stop),
                "size": float(size),
                "p_tp_before_sl": p_tp_before_sl,
                "cvar95": cvar95,
                "reason_json": json.dumps(reason, ensure_ascii=False),
            }
        )
    return signals
