"""Build store.signals rows from prepared price series + fundamental scores.

Pure path: no network. ``pipeline/daily_job`` prepares OHLCV via ``data/`` then
calls ``generate_signals``. Shared with ``backtest/`` (ARCHITECTURE invariant #2).
"""

from __future__ import annotations

import atexit
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor
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


def _perf_add(perf: dict[str, float] | None, key: str, dt: float) -> None:
    if perf is None:
        return
    perf[key] = float(perf.get(key, 0.0)) + float(dt)


def _resolve_parallel_workers(
    parallel_workers: Any, n_tickers: int
) -> int:
    """Số worker ProcessPool cho hot path per-ticker.

    - ``null`` / thiếu: auto ``min(cpu_count, n_tickers)``
    - ``1`` (hoặc ≤1): tuần tự — regression / live nhỏ
    - ``N>1``: ``min(N, n_tickers)``
    """
    n = max(int(n_tickers), 0)
    if n <= 1:
        return 1
    if parallel_workers is None:
        cpu = int(os.cpu_count() or 1)
        return max(1, min(cpu, n))
    try:
        requested = int(parallel_workers)
    except (TypeError, ValueError):
        cpu = int(os.cpu_count() or 1)
        return max(1, min(cpu, n))
    if requested <= 1:
        return 1
    return max(1, min(requested, n))


def _days_since_fit_for_session(
    garch_prev: Mapping[str, Any] | None,
    *,
    as_of_date: str,
) -> tuple[int | None, Any]:
    """Tính ``days_since_fit`` + previous_model cho phiên tín hiệu hiện tại.

    Đếm theo phiên gọi ``generate_signals`` (không phải ngày lịch). Cùng
    ``as_of`` → không tăng đếm (tránh double-bump nếu gọi lại trong ngày).
    """
    if not garch_prev:
        return None, None
    previous_model = garch_prev.get("model")
    prev_days = garch_prev.get("days_since_fit")
    last_as_of = str(garch_prev.get("last_as_of") or "")
    if last_as_of == str(as_of_date):
        if prev_days is None:
            return None, previous_model
        return int(prev_days), previous_model
    if prev_days is None:
        return None, previous_model
    return int(prev_days) + 1, previous_model


def _ticker_hotpath_worker(payload: dict[str, Any]) -> dict[str, Any]:
    """Worker module-level — picklable trên Windows ``spawn``.

    Nhận close + flags + kalman_init / garch_prev / cached_risk; trả alpha_pack
    + risk + state Kalman/GARCH mới. Không đụng mutable cache cha.
    """
    ticker = str(payload["ticker"]).strip().upper()
    close = pd.Series(
        payload["close_values"],
        index=payload["close_index"],
        dtype=float,
        name="close",
    )
    close = pd.to_numeric(close, errors="coerce").dropna()
    if len(close) < 30:
        return {
            "ticker": ticker,
            "skip": True,
            "n": int(len(close)),
            "kalman_sec": 0.0,
            "garch_sec": 0.0,
        }

    fund = dict(payload.get("fund") or {})
    kalman_enabled = bool(payload.get("kalman_enabled", True))
    use_ou = bool(payload.get("use_ou", False))
    garch_enabled = bool(payload.get("garch_enabled", True))
    garch_refit_every_n = payload.get("garch_refit_every_n")
    track_garch_state = (
        garch_refit_every_n is not None and int(garch_refit_every_n) > 0
    )
    kalman_init = payload.get("kalman_init")
    cached_risk = payload.get("cached_risk")
    garch_prev = payload.get("garch_prev")
    as_of_date = str(payload.get("as_of_date") or "")

    # Cache cục bộ 1 key — tương đương truyền init_state, không share giữa workers.
    # OU vẫn full-fit (không dùng init) nhưng vẫn ghi state cuối như path tuần tự.
    local_kalman: dict[str, Any] | None = None
    if kalman_enabled:
        local_kalman = {}
        if not use_ou and kalman_init is not None:
            local_kalman[ticker] = kalman_init

    t_kal = time.perf_counter()
    pack = _compute_alpha_pack(
        close,
        fund=fund,
        kalman_enabled=kalman_enabled,
        use_ou=use_ou,
        ticker=ticker,
        kalman_cache=local_kalman,
    )
    kalman_sec = time.perf_counter() - t_kal
    kalman_state = (
        local_kalman.get(ticker) if local_kalman is not None else None
    )

    t_garch = time.perf_counter()
    returns = _log_returns(close)
    n_returns = int(len(returns))
    garch_state: dict[str, Any] | None = None
    if cached_risk is not None:
        risk = dict(cached_risk)
        # Same-day memo: giữ state cũ (không bump days_since_fit).
        if track_garch_state and garch_prev is not None:
            garch_state = dict(garch_prev)
    elif garch_enabled:
        days_since_fit, previous_model = _days_since_fit_for_session(
            garch_prev if track_garch_state else None,
            as_of_date=as_of_date,
        )
        fitted = fit_or_fallback_sigma(
            returns,
            refit_every_n=garch_refit_every_n if track_garch_state else None,
            days_since_fit=days_since_fit,
            previous_model=previous_model if track_garch_state else None,
        )
        risk = {
            "sigma_hat": fitted.get("sigma_hat"),
            "method": fitted.get("method"),
            "refit": fitted.get("refit"),
            "days_since_fit": fitted.get("days_since_fit"),
        }
        if track_garch_state:
            garch_state = {
                "model": fitted.get("model"),
                "days_since_fit": int(fitted.get("days_since_fit") or 0),
                "last_as_of": as_of_date,
            }
    else:
        risk = {
            "sigma_hat": float(returns.iloc[-20:].std(ddof=1))
            if len(returns) >= 2
            else float("nan"),
            "method": "disabled_rolling",
        }
    garch_sec = time.perf_counter() - t_garch

    return {
        "ticker": ticker,
        "skip": False,
        "alpha_pack": pack,
        "risk": risk,
        "kalman_state": kalman_state,
        "garch_state": garch_state,
        "n_returns": n_returns,
        "kalman_sec": float(kalman_sec),
        "garch_sec": float(garch_sec),
    }


# Pool tái sử dụng giữa các lần generate_signals (tránh spawn lại mỗi ngày trên Windows).
_HOTPATH_POOL: ProcessPoolExecutor | None = None
_HOTPATH_POOL_WORKERS: int | None = None


def shutdown_hotpath_pool() -> None:
    """Đóng ProcessPool hot path (atexit / test teardown)."""
    global _HOTPATH_POOL, _HOTPATH_POOL_WORKERS
    if _HOTPATH_POOL is not None:
        _HOTPATH_POOL.shutdown(wait=True)
        _HOTPATH_POOL = None
        _HOTPATH_POOL_WORKERS = None


atexit.register(shutdown_hotpath_pool)


def _get_hotpath_pool(n_workers: int) -> ProcessPoolExecutor:
    """Lấy/ tạo ProcessPool module-level (spawn-safe, không tạo mỗi ngày)."""
    global _HOTPATH_POOL, _HOTPATH_POOL_WORKERS
    if (
        _HOTPATH_POOL is not None
        and _HOTPATH_POOL_WORKERS == int(n_workers)
    ):
        return _HOTPATH_POOL
    shutdown_hotpath_pool()
    _HOTPATH_POOL = ProcessPoolExecutor(max_workers=int(n_workers))
    _HOTPATH_POOL_WORKERS = int(n_workers)
    return _HOTPATH_POOL


def _run_ticker_hotpaths(
    payloads: list[dict[str, Any]],
    *,
    n_workers: int,
) -> list[dict[str, Any]]:
    """Chạy hot path per-ticker; merge deterministic (sort theo ticker)."""
    if not payloads:
        return []
    if n_workers <= 1 or len(payloads) <= 1:
        results = [_ticker_hotpath_worker(p) for p in payloads]
    else:
        # Tái sử dụng pool — Windows spawn đắt nếu tạo mới mỗi as_of.
        pool = _get_hotpath_pool(n_workers)
        results = list(pool.map(_ticker_hotpath_worker, payloads))
    results.sort(key=lambda r: str(r.get("ticker") or ""))
    return results


def _compute_alpha_pack(
    close: pd.Series,
    *,
    fund: Mapping[str, Any],
    kalman_enabled: bool,
    use_ou: bool,
    ticker: str | None = None,
    kalman_cache: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Kalman/OU alpha + Alpha_effective for one ticker (shared BL + signal path).

    P2-1: ``kalman_cache`` key theo ticker (không theo n_returns). Khi không OU,
    resume state từ lần trước — tương đương expanding filter. OU cần full level
    → bỏ init_state, fit lại từ đầu rồi cập nhật cache.
    """
    log_px = np.log(close)
    alpha_raw = float("nan")
    tstat = float("nan")
    half_life = None
    kalman_level_last = None
    alpha_method = "none"
    if kalman_enabled:
        key = str(ticker or "").strip().upper() or None
        init = None
        if (
            not use_ou
            and kalman_cache is not None
            and key
            and key in kalman_cache
        ):
            init = kalman_cache[key]
        level, slope, slope_var, state = fit_kalman_trend(
            log_px, init_state=init, return_state=True
        )
        if kalman_cache is not None and key:
            kalman_cache[key] = state
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
    garch_state_cache: dict[str, Any] | None = None,
    kalman_cache: dict[str, Any] | None = None,
    perf_timings: dict[str, float] | None = None,
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
    garch_state_cache:
        Optional memo theo ``ticker`` lưu model GARCH + ``days_since_fit``
        (Phần 8.5 ``refit_every_n`` — roll-forward giữa các lần MLE).
    kalman_cache:
        Optional memo theo ``ticker`` lưu state Kalman cuối (P2-1 incremental).
    perf_timings:
        Optional dict cộng dồn giây cho ``regime`` / ``kalman`` / ``garch``
        (bật khi ``BACKTEST_PROFILE=1``).
    config quant_engine.parallel_workers:
        ``null`` = auto ``min(cpu, n_tickers)``; ``1`` = tuần tự; ``N>1`` ProcessPool.
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
    garch_cfg = dict(qcfg.get("risk_garch") or {})
    garch_enabled = bool(garch_cfg.get("enabled", True))
    # None/≤0 = refit mỗi phiên (V1 / N=1). N>0 = MLE mỗi N phiên + forecast roll-forward.
    _raw_refit_n = garch_cfg.get("refit_every_n", None)
    garch_refit_every_n: int | None
    try:
        garch_refit_every_n = (
            None if _raw_refit_n is None else int(_raw_refit_n)
        )
    except (TypeError, ValueError):
        garch_refit_every_n = None
    if garch_refit_every_n is not None and garch_refit_every_n <= 0:
        garch_refit_every_n = None
    track_garch_state = garch_refit_every_n is not None
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
    # null = auto min(cpu, n_tickers); 1 = tuần tự (regression / live nhỏ).
    parallel_workers_cfg = qcfg.get("parallel_workers", None)

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
        t_reg = time.perf_counter()
        if regime_cache is not None and cache_key in regime_cache:
            probs = regime_cache[cache_key]
        else:
            regime_pack = fit_or_fallback_regime(index_returns)
            probs = regime_pack["probabilities"]
            if regime_cache is not None:
                regime_cache[cache_key] = probs
        _perf_add(perf_timings, "regime", time.perf_counter() - t_reg)
        p_bull = float(probs.get("bull", 0.5))
        regime_method = str(probs.get("method", "unknown"))

    use_ou = ou_enabled and p_bull < bull_threshold and p_bull > bear_threshold

    # Hot path per-ticker (Kalman/OU + GARCH) — song song khi parallel_workers>1.
    # Regime giữ tuần tự (shared). Cache mutable chỉ cập nhật trên orchestrator.
    alpha_packs: dict[str, dict[str, Any]] = {}
    sigma_by_ticker: dict[str, float] = {}
    risk_by_ticker: dict[str, dict[str, Any]] = {}
    payloads: list[dict[str, Any]] = []
    for ticker in tickers:
        close = pd.to_numeric(close_by_ticker[ticker], errors="coerce").dropna()
        if len(close) < 30:
            continue
        returns = _log_returns(close)
        n_rets = int(len(returns))
        garch_key = (str(as_of_date), str(ticker), n_rets)
        cached_risk = None
        if (
            garch_enabled
            and garch_cache is not None
            and garch_key in garch_cache
        ):
            cached_risk = dict(garch_cache[garch_key])
        kalman_init = None
        if (
            kalman_enabled
            and not use_ou
            and kalman_cache is not None
            and ticker in kalman_cache
        ):
            kalman_init = kalman_cache[ticker]
        garch_prev = None
        if (
            track_garch_state
            and garch_state_cache is not None
            and ticker in garch_state_cache
        ):
            garch_prev = garch_state_cache[ticker]
        payloads.append(
            {
                "ticker": ticker,
                "as_of_date": str(as_of_date),
                "close_values": close.to_numpy(dtype=float),
                "close_index": [str(x) for x in close.index.tolist()],
                "fund": dict(scores.get(ticker) or {}),
                "kalman_enabled": kalman_enabled,
                "use_ou": use_ou,
                "kalman_init": kalman_init,
                "garch_enabled": garch_enabled,
                "garch_refit_every_n": garch_refit_every_n,
                "cached_risk": cached_risk,
                "garch_prev": garch_prev,
            }
        )

    n_workers = _resolve_parallel_workers(parallel_workers_cfg, len(payloads))
    t_hot = time.perf_counter()
    hot_results = _run_ticker_hotpaths(payloads, n_workers=n_workers)
    wall_hot = time.perf_counter() - t_hot
    kalman_cpu = sum(float(r.get("kalman_sec") or 0.0) for r in hot_results)
    garch_cpu = sum(float(r.get("garch_sec") or 0.0) for r in hot_results)
    if n_workers <= 1:
        # Tuần tự: CPU ≈ wall theo từng ticker.
        _perf_add(perf_timings, "kalman", kalman_cpu)
        _perf_add(perf_timings, "garch", garch_cpu)
    else:
        # Song song: ghi wall-clock phân bổ theo tỷ lệ CPU (không cộng thêm hotpath_wall).
        cpu_sum = kalman_cpu + garch_cpu
        if cpu_sum > 0:
            _perf_add(perf_timings, "kalman", wall_hot * (kalman_cpu / cpu_sum))
            _perf_add(perf_timings, "garch", wall_hot * (garch_cpu / cpu_sum))
        else:
            _perf_add(perf_timings, "garch", wall_hot)

    for result in hot_results:
        ticker = str(result["ticker"])
        if result.get("skip"):
            continue
        pack = result["alpha_pack"]
        risk = dict(result["risk"])
        alpha_packs[ticker] = pack
        risk_by_ticker[ticker] = risk
        if kalman_cache is not None and result.get("kalman_state") is not None:
            kalman_cache[ticker] = result["kalman_state"]
        if (
            track_garch_state
            and garch_state_cache is not None
            and result.get("garch_state") is not None
        ):
            garch_state_cache[ticker] = result["garch_state"]
        if garch_enabled and garch_cache is not None:
            n_rets = int(result.get("n_returns") or 0)
            garch_key = (str(as_of_date), str(ticker), n_rets)
            if garch_key not in garch_cache:
                garch_cache[garch_key] = {
                    "sigma_hat": risk.get("sigma_hat"),
                    "method": risk.get("method"),
                }
        sigma_hat = risk.get("sigma_hat")
        if sigma_hat is not None and not pd.isna(sigma_hat) and float(sigma_hat) > 0:
            sigma_by_ticker[ticker] = float(sigma_hat)

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

    # Vòng 1: quyết định action trước — sizing chỉ trên tập BUY (P0-1).
    decided: dict[str, dict[str, Any]] = {}
    for ticker in tickers:
        close = pd.to_numeric(close_by_ticker[ticker], errors="coerce").dropna()
        if len(close) < 30:
            decided[ticker] = {
                "skip": True,
                "n": len(close),
                "action": "WATCH",
                "action_uncapped": "WATCH",
            }
            continue
        pack = alpha_packs.get(ticker) or _compute_alpha_pack(
            close,
            fund=scores.get(ticker) or {},
            kalman_enabled=kalman_enabled,
            use_ou=use_ou,
            ticker=ticker,
            kalman_cache=kalman_cache,
        )
        alpha_eff = pack["alpha_eff"]
        tstat = pack["tstat"]
        half_life = pack["half_life"]
        alpha_method = pack["alpha_method"]
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
        decided[ticker] = {
            "skip": False,
            "close": close,
            "pack": pack,
            "alpha_eff": alpha_eff,
            "tstat": tstat,
            "half_life": half_life,
            "alpha_method": alpha_method,
            "growth": pack["growth"],
            "quality": pack["quality"],
            "fund_view": fund_view,
            "action": action,
            "action_uncapped": action_uncapped,
            "entry_price": float(close.iloc[-1]),
        }

    buy_tickers = [
        t for t, d in decided.items() if not d.get("skip") and d.get("action") == "BUY"
    ]

    # Portfolio weights: BL chỉ trên BUY; equal-weight KHÔNG dùng làm trần size (P0-1).
    weights: dict[str, float] = {}
    if bl_enabled and len(buy_tickers) >= 2:
        buy_packs = {t: alpha_packs[t] for t in buy_tickers if t in alpha_packs}
        alpha_signals = {
            t: pack["alpha_eff"]
            for t, pack in buy_packs.items()
            if pack["alpha_eff"] is not None and not pd.isna(pack["alpha_eff"])
        }
        valuation_signals = {
            t: pack["valuation"]
            for t, pack in buy_packs.items()
            if pack["valuation"] is not None and not pd.isna(pack["valuation"])
        }
        weights = bl_portfolio_weights(
            close_by_ticker,
            list(buy_packs),
            alpha_signals,
            valuation_signals or None,
            tau=bl_tau,
            delta=bl_delta,
        )
        weight_method = "black_litterman"
    elif bl_enabled and len(buy_tickers) == 1:
        weights = {buy_tickers[0]: float(w_max)}
        weight_method = "black_litterman_single_buy"
    elif bl_enabled:
        weights = equal_weight_fallback(tickers)
        weight_method = "equal_weight_bl_fallback"
    else:
        # BL off: không pha loãng 1/N watchlist — trần duy nhất là w_max.
        weights = {}
        weight_method = "w_max_only"

    buy_sigmas = {
        t: sigma_by_ticker[t] for t in buy_tickers if t in sigma_by_ticker
    }
    if garch_enabled and buy_sigmas:
        risk_weights = inverse_vol_normalize_weights(
            buy_sigmas, w_max=w_max, target_sum=1.0
        )
        size_method = "inverse_vol_normalize"
    else:
        risk_weights = {}
        size_method = "legacy_sigma_target"

    signals: list[dict[str, Any]] = []
    for ticker in tickers:
        meta = decided.get(ticker) or {"skip": True, "n": 0, "action": "WATCH"}
        if meta.get("skip"):
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
                        {
                            "error": "insufficient_price_history",
                            "n": int(meta.get("n") or 0),
                        },
                        ensure_ascii=False,
                    ),
                }
            )
            continue

        close = meta["close"]
        entry_price = float(meta["entry_price"])
        pack = meta["pack"]
        alpha_eff = meta["alpha_eff"]
        tstat = meta["tstat"]
        half_life = meta["half_life"]
        alpha_method = meta["alpha_method"]
        growth = meta["growth"]
        quality = meta["quality"]
        fund_view = meta["fund_view"]
        action = meta["action"]
        action_uncapped = meta["action_uncapped"]

        risk = risk_by_ticker.get(ticker) or {
            "sigma_hat": float("nan"),
            "method": "missing",
        }
        sigma_hat = risk["sigma_hat"]
        stop = stop_loss_price(entry_price, sigma_hat, k=stop_k)

        # Non-BUY: size = 0 (không giữ weight ảo trên WATCH/SELL).
        if action != "BUY":
            size = 0.0
        else:
            if size_method == "inverse_vol_normalize":
                size = float(risk_weights.get(ticker, 0.0))
            else:
                size = position_size(sigma_hat, sigma_target, w_max=w_max)
            # Trần: w_max luôn; BL overlay chỉ khi enabled.
            caps = [float(w_max)]
            if bl_enabled and ticker in weights:
                caps.append(float(weights[ticker]))
            size = min([size] + caps) * float(hawkes_mult)

        portfolio_weight = (
            float(weights.get(ticker, 0.0))
            if bl_enabled
            else (float(w_max) if action == "BUY" else 0.0)
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
            "portfolio_weight": portfolio_weight,
            "n_buy_universe": len(buy_tickers),
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
                returns = _log_returns(close)
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
