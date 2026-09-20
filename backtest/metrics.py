"""Backtest performance metrics (CORE + config-flagged add-ons)."""

from __future__ import annotations

from typing import Any, Mapping

import numpy as np
import pandas as pd


def _equity_series(equity_curve: list[dict]) -> pd.Series:
    if not equity_curve:
        return pd.Series(dtype=float)
    frame = pd.DataFrame(equity_curve)
    series = pd.to_numeric(frame["equity"], errors="coerce")
    series.index = frame["date"].astype(str)
    return series.dropna()


def cagr(equity: pd.Series, periods_per_year: float = 252.0) -> float:
    if len(equity) < 2:
        return float("nan")
    start, end = float(equity.iloc[0]), float(equity.iloc[-1])
    if start <= 0 or end <= 0:
        return float("nan")
    years = (len(equity) - 1) / periods_per_year
    if years <= 0:
        return float("nan")
    return float((end / start) ** (1.0 / years) - 1.0)


def sharpe_ratio(returns: pd.Series, periods_per_year: float = 252.0) -> float:
    clean = returns.dropna()
    if len(clean) < 2:
        return float("nan")
    mu = float(clean.mean())
    sigma = float(clean.std(ddof=1))
    if sigma <= 0:
        return float("nan")
    return float(np.sqrt(periods_per_year) * mu / sigma)


def sortino_ratio(returns: pd.Series, periods_per_year: float = 252.0) -> float:
    clean = returns.dropna()
    if len(clean) < 2:
        return float("nan")
    downside = clean[clean < 0]
    if downside.empty:
        return float("nan")
    dd = float(downside.std(ddof=1))
    if dd <= 0:
        return float("nan")
    return float(np.sqrt(periods_per_year) * float(clean.mean()) / dd)


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return float("nan")
    peak = equity.cummax()
    dd = equity / peak - 1.0
    return float(dd.min())


def max_drawdown_days(equity: pd.Series) -> int | float:
    """Longest peak-to-recovery duration in sessions (or to end if unrecovered)."""
    if len(equity) < 2:
        return float("nan")
    peak = equity.cummax()
    underwater = equity < peak
    longest = 0
    current = 0
    for flag in underwater.tolist():
        if flag:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return int(longest)


def calmar_ratio(cagr_value: float, mdd: float) -> float:
    if cagr_value is None or mdd is None or pd.isna(cagr_value) or pd.isna(mdd):
        return float("nan")
    if abs(mdd) < 1e-12:
        return float("nan")
    return float(cagr_value) / abs(float(mdd))


def profit_factor(trades: list[dict]) -> float:
    gains = sum(float(t["pnl"]) for t in trades if float(t.get("pnl", 0)) > 0)
    losses = sum(-float(t["pnl"]) for t in trades if float(t.get("pnl", 0)) < 0)
    if losses <= 0:
        return float("nan") if gains <= 0 else float("inf")
    return float(gains / losses)


def win_rate(trades: list[dict]) -> float:
    closed = [t for t in trades if t.get("pnl") is not None]
    if not closed:
        return float("nan")
    wins = sum(1 for t in closed if float(t["pnl"]) > 0)
    return float(wins / len(closed))


def turnover(trades: list[dict], equity_curve: list[dict]) -> float:
    """Average absolute trade notional / NAV per session (approx)."""
    if not equity_curve or not trades:
        return 0.0
    n_days = max(len(equity_curve) - 1, 1)
    notionals = [abs(float(t.get("notional", 0.0))) for t in trades]
    avg_equity = float(np.mean([float(p["equity"]) for p in equity_curve]))
    if avg_equity <= 0:
        return float("nan")
    return float(sum(notionals) / avg_equity / n_days)


def cvar95_realized(returns: pd.Series, alpha: float = 0.05) -> float:
    """Empirical CVaR (expected shortfall) of daily returns at level ``alpha``."""
    clean = returns.dropna()
    if len(clean) < 20:
        return float("nan")
    cutoff = float(np.quantile(clean, alpha))
    tail = clean[clean <= cutoff]
    if tail.empty:
        return float("nan")
    return float(tail.mean())


def calibrate_cvar95(
    signals: list[dict],
    realized: float,
) -> tuple[float | None, str]:
    """Compare mean forecast ``cvar95`` on signals vs realized equity CVaR.

    Returns (mean_forecast_or_None, note).
    """
    forecasts = [
        float(s["cvar95"])
        for s in signals
        if s.get("cvar95") is not None and not pd.isna(s.get("cvar95"))
    ]
    if not forecasts or realized is None or pd.isna(realized):
        return None, "insufficient forecast or realized CVaR"
    mean_f = float(np.mean(forecasts))
    gap = mean_f - float(realized)
    note = (
        f"mean_forecast={mean_f:.4f} realized={float(realized):.4f} "
        f"gap={gap:.4f} (forecast−realized)"
    )
    return mean_f, note


def regime_conditional_sharpe(
    equity_curve: list[dict],
    regime_by_date: Mapping[str, float],
    *,
    bull_threshold: float = 0.55,
    bear_threshold: float = 0.35,
) -> tuple[float, float]:
    """Sharpe of equity returns split by P(bull) regime buckets."""
    equity = _equity_series(equity_curve)
    if len(equity) < 3 or not regime_by_date:
        return float("nan"), float("nan")
    rets = equity.pct_change().dropna()
    bull_rets = []
    bear_rets = []
    for day, ret in rets.items():
        p = regime_by_date.get(str(day))
        if p is None:
            continue
        if p >= bull_threshold:
            bull_rets.append(float(ret))
        elif p <= bear_threshold:
            bear_rets.append(float(ret))
    bull = sharpe_ratio(pd.Series(bull_rets)) if len(bull_rets) >= 5 else float("nan")
    bear = sharpe_ratio(pd.Series(bear_rets)) if len(bear_rets) >= 5 else float("nan")
    return bull, bear


def compute_metrics(
    equity_curve: list[dict],
    trades: list[dict],
    config: Mapping[str, Any] | None = None,
    *,
    signals: list[dict] | None = None,
    regime_by_date: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """CORE metrics always; add-ons / P1 respect ``backtest.metrics.*.enabled``."""
    cfg = dict(config or {})
    bt = dict(cfg.get("backtest") or {})
    flags = dict(bt.get("metrics") or {})
    qcfg = dict(cfg.get("quant_engine") or {})

    equity = _equity_series(equity_curve)
    rets = equity.pct_change().dropna()
    cagr_v = cagr(equity)
    mdd = max_drawdown(equity)
    closed = [t for t in trades if t.get("pnl") is not None]

    metrics: dict[str, Any] = {
        "cagr": cagr_v,
        "sharpe": sharpe_ratio(rets),
        "max_drawdown": mdd,
        "win_rate": win_rate(closed),
        "n_trades": len(closed),
    }

    def _enabled(name: str, default: bool = True) -> bool:
        block = flags.get(name) or {}
        if isinstance(block, dict):
            return bool(block.get("enabled", default))
        return bool(block) if block is not None else default

    if _enabled("turnover"):
        metrics["turnover"] = turnover(trades, equity_curve)
    if _enabled("sortino"):
        metrics["sortino"] = sortino_ratio(rets)
    if _enabled("calmar"):
        metrics["calmar"] = calmar_ratio(cagr_v, mdd)
    if _enabled("profit_factor"):
        metrics["profit_factor"] = profit_factor(closed)
    if _enabled("max_drawdown_days"):
        metrics["max_drawdown_days"] = max_drawdown_days(equity)

    if _enabled("cvar95_calibration", default=False):
        realized = cvar95_realized(rets)
        metrics["cvar95_realized"] = realized
        _, note = calibrate_cvar95(list(signals or []), realized)
        metrics["cvar95_calibration_note"] = note

    if _enabled("regime_conditional_sharpe", default=False):
        bull_th = float(qcfg.get("bull_threshold", 0.55))
        bear_th = float(qcfg.get("bear_threshold", 0.35))
        bull_s, bear_s = regime_conditional_sharpe(
            equity_curve,
            regime_by_date or {},
            bull_threshold=bull_th,
            bear_threshold=bear_th,
        )
        metrics["sharpe_bull_regime"] = bull_s
        metrics["sharpe_bear_regime"] = bear_s

    return metrics
