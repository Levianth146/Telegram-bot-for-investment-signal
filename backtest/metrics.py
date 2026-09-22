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


def margin_bps(cagr_value: float, turnover_value: float) -> float:
    """WQ-style: return / turnover (bps). CAGR thập phân, turnover phân số NAV/kỳ.

    ``margin_bps = (cagr / turnover) * 10000`` khi turnover > 0.
    """
    if cagr_value is None or turnover_value is None:
        return float("nan")
    if pd.isna(cagr_value) or pd.isna(turnover_value):
        return float("nan")
    t = float(turnover_value)
    if abs(t) < 1e-12:
        return float("nan")
    return float(cagr_value) / t * 10_000.0


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
    min_obs: int = 5,
) -> dict[str, Any]:
    """Sharpe theo regime bucket; thiếu mẫu → None + display N/A (không literal None chart)."""
    empty = {
        "sharpe_bull": None,
        "sharpe_bear": None,
        "sharpe_neutral": None,
        "n_bull": 0,
        "n_bear": 0,
        "n_neutral": 0,
        "display_bull": f"N/A (n < {min_obs})",
        "display_bear": f"N/A (n < {min_obs})",
        "display_neutral": f"N/A (n < {min_obs})",
    }
    equity = _equity_series(equity_curve)
    if len(equity) < 3 or not regime_by_date:
        return empty
    rets = equity.pct_change().dropna()
    bull_rets: list[float] = []
    bear_rets: list[float] = []
    neutral_rets: list[float] = []
    for day, ret in rets.items():
        p = regime_by_date.get(str(day))
        if p is None:
            continue
        if p >= bull_threshold:
            bull_rets.append(float(ret))
        elif p <= bear_threshold:
            bear_rets.append(float(ret))
        else:
            neutral_rets.append(float(ret))

    def _pack(vals: list[float]) -> tuple[float | None, str]:
        if len(vals) < min_obs:
            return None, f"N/A (n < {min_obs})"
        s = sharpe_ratio(pd.Series(vals))
        if s is None or (isinstance(s, float) and (pd.isna(s) or s != s)):
            return None, f"N/A (n={len(vals)})"
        return float(s), f"{float(s):.2f} (n={len(vals)})"

    bull_s, bull_d = _pack(bull_rets)
    bear_s, bear_d = _pack(bear_rets)
    neu_s, neu_d = _pack(neutral_rets)
    return {
        "sharpe_bull": bull_s,
        "sharpe_bear": bear_s,
        "sharpe_neutral": neu_s,
        "n_bull": len(bull_rets),
        "n_bear": len(bear_rets),
        "n_neutral": len(neutral_rets),
        "display_bull": bull_d,
        "display_bear": bear_d,
        "display_neutral": neu_d,
    }


def exposure_stats(equity_curve: list[dict]) -> dict[str, Any]:
    """Thống kê exposure/cash từ equity_curve (nếu có field exposure)."""
    if not equity_curve:
        return {}
    exposures = [
        float(p["exposure"])
        for p in equity_curve
        if p.get("exposure") is not None and not pd.isna(p.get("exposure"))
    ]
    n_pos = [
        int(p["n_positions"])
        for p in equity_curve
        if p.get("n_positions") is not None
    ]
    if not exposures:
        return {}
    arr = np.array(exposures, dtype=float)
    cash_heavy = float(np.mean(arr < 0.20))
    return {
        "avg_exposure": float(arr.mean()),
        "median_exposure": float(np.median(arr)),
        "max_exposure": float(arr.max()),
        "pct_sessions_cash_gt_80": cash_heavy,
        "avg_n_positions": float(np.mean(n_pos)) if n_pos else None,
        "max_n_positions": int(max(n_pos)) if n_pos else None,
    }


def total_return(equity: pd.Series) -> float:
    if len(equity) < 2:
        return float("nan")
    start, end = float(equity.iloc[0]), float(equity.iloc[-1])
    if start <= 0:
        return float("nan")
    return float(end / start - 1.0)


def format_regime_sharpe_display(value: float | None, n: int, min_obs: int = 5) -> str:
    """Không render literal None trong report."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return f"N/A (n < {min_obs})" if n < min_obs else f"N/A (n={n})"
    return f"{float(value):.2f}"


def compute_metrics(
    equity_curve: list[dict],
    trades: list[dict],
    config: Mapping[str, Any] | None = None,
    *,
    signals: list[dict] | None = None,
    regime_by_date: Mapping[str, float] | None = None,
    force_research_metrics: bool = False,
) -> dict[str, Any]:
    """CORE metrics always; add-ons / P1 respect ``backtest.metrics.*.enabled``.

    ``force_research_metrics=True`` bật regime Sharpe cho report (không đổi live config).
    """
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
        "total_return": total_return(equity),
        "sharpe": sharpe_ratio(rets),
        "max_drawdown": mdd,
        "win_rate": win_rate(closed),
        "n_trades": len(closed),
    }
    metrics.update(exposure_stats(equity_curve))

    # Cost attribution từ closed trades
    if closed:
        gross_pnl = sum(float(t.get("pnl") or 0) for t in closed)
        # Approximate: cost ≈ notional * (entry fee + exit fee) — ledger already net
        metrics["net_pnl"] = gross_pnl
        metrics["avg_holding_days"] = float(
            np.mean(
                [
                    max(
                        (
                            pd.Timestamp(str(t["exit_date"]))
                            - pd.Timestamp(str(t["entry_date"]))
                        ).days,
                        0,
                    )
                    for t in closed
                    if t.get("entry_date") and t.get("exit_date")
                ]
                or [float("nan")]
            )
        )

    def _enabled(name: str, default: bool = True) -> bool:
        if force_research_metrics and name == "regime_conditional_sharpe":
            return True
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

    if _enabled("margin_bps"):
        to = metrics.get("turnover")
        if to is None:
            to = turnover(trades, equity_curve)
        metrics["margin_bps"] = margin_bps(cagr_v, to)

    if _enabled("cvar95_calibration", default=False):
        realized = cvar95_realized(rets)
        metrics["cvar95_realized"] = realized
        _, note = calibrate_cvar95(list(signals or []), realized)
        metrics["cvar95_calibration_note"] = note

    if _enabled("regime_conditional_sharpe", default=False) or force_research_metrics:
        bull_th = float(qcfg.get("bull_threshold", 0.55))
        bear_th = float(qcfg.get("bear_threshold", 0.35))
        pack = regime_conditional_sharpe(
            equity_curve,
            regime_by_date or {},
            bull_threshold=bull_th,
            bear_threshold=bear_th,
        )
        metrics["sharpe_bull_regime"] = pack["sharpe_bull"]
        metrics["sharpe_bear_regime"] = pack["sharpe_bear"]
        metrics["sharpe_neutral_regime"] = pack["sharpe_neutral"]
        metrics["n_sessions_bull"] = pack["n_bull"]
        metrics["n_sessions_bear"] = pack["n_bear"]
        metrics["n_sessions_neutral"] = pack["n_neutral"]
        metrics["sharpe_bull_display"] = pack["display_bull"]
        metrics["sharpe_bear_display"] = pack["display_bear"]
        metrics["sharpe_neutral_display"] = pack["display_neutral"]

    return metrics


def yearly_breakdown_from_equity(
    equity_curve: list[dict],
    trades: list[dict] | None = None,
    config: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Tách metrics theo năm dương lịch từ equity_curve (WQ yearly)."""
    if not equity_curve:
        return []
    by_year: dict[int, list[dict]] = {}
    for point in equity_curve:
        day = str(point.get("date") or "")
        if len(day) < 4:
            continue
        try:
            year = int(day[:4])
        except ValueError:
            continue
        by_year.setdefault(year, []).append(point)

    trades = list(trades or [])
    rows: list[dict[str, Any]] = []
    for year in sorted(by_year):
        curve = by_year[year]
        if len(curve) < 2:
            continue
        # Rebase năm về 1.0 để CAGR/Sharpe trong năm có nghĩa.
        base = float(curve[0]["equity"]) or 1.0
        rebated = [
            {"date": p["date"], "equity": float(p["equity"]) / base}
            for p in curve
        ]
        year_trades = [
            t
            for t in trades
            if str(t.get("exit_date") or t.get("entry_date") or "")[:4] == str(year)
        ]
        m = compute_metrics(rebated, year_trades, config)
        rows.append(
            {
                "year": year,
                "cagr": m.get("cagr"),
                "sharpe": m.get("sharpe"),
                "max_drawdown": m.get("max_drawdown"),
                "turnover": m.get("turnover"),
                "margin_bps": m.get("margin_bps"),
                "n_trades": m.get("n_trades"),
            }
        )
    return rows
