"""Backtest engine — GỌI LẠI đúng hàm trong fundamental_filter/ và quant_engine/,
không viết logic tính điểm/tín hiệu riêng cho backtest (nguyên tắc bất biến #2,
xem docs/ARCHITECTURE.md).
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Mapping

import pandas as pd

from backtest.costs import (
    buy_cost_fraction,
    is_tradable_at_price_limit,
    sell_cost_fraction,
)
from backtest.metrics import compute_metrics
from data.ingest.pit import assumed_filed_at
from fundamental_filter import score_current_universe
from quant_engine.signal_engine import generate_signals


def _as_date_index(series: pd.Series) -> pd.Series:
    out = pd.to_numeric(series, errors="coerce").dropna()
    out.index = out.index.astype(str)
    return out.sort_index()


def _truncate(series: pd.Series, as_of: str) -> pd.Series:
    return series.loc[series.index <= as_of]


def _trading_days(
    close_by_ticker: Mapping[str, pd.Series], start_date: str, end_date: str
) -> list[str]:
    days: set[str] = set()
    for series in close_by_ticker.values():
        idx = _as_date_index(series).index
        days.update(d for d in idx if start_date <= d <= end_date)
    return sorted(days)


def _business_days_between(start: str, end: str, calendar: list[str]) -> int:
    """Count sessions strictly after start up to and including end."""
    return sum(1 for d in calendar if start < d <= end)


def _active_watchlist(
    scoring_schedule: Mapping[str, Mapping[str, pd.DataFrame]] | None,
    as_of: str,
    fallback_tickers: list[str],
    config: dict,
) -> tuple[list[str], dict[str, dict]]:
    """Latest fundamental run with filed_at <= as_of → PASS/WATCH + scores."""
    if not scoring_schedule:
        return list(fallback_tickers), {}

    eligible = sorted(d for d in scoring_schedule if d <= as_of)
    if not eligible:
        return [], {}

    filed_at = eligible[-1]
    frames = scoring_schedule[filed_at]
    if not frames:
        return [], {}

    # Infer year window from frame rows
    sample = next(iter(frames.values()))
    years = pd.to_numeric(sample.get("year"), errors="coerce").dropna()
    end_year = int(years.max()) if not years.empty else int(filed_at[:4])
    start_year = int(years.min()) if not years.empty else end_year

    results, _, _ = score_current_universe(
        frames, start_year, end_year, config=None
    )
    keep = results.loc[
        results["classification"].astype(str).str.upper().isin({"PASS", "WATCH"})
    ]
    tickers = [str(t).strip().upper() for t in keep["ticker"].tolist()]
    scores: dict[str, dict] = {}
    for _, row in keep.iterrows():
        ticker = str(row["ticker"]).strip().upper()
        scores[ticker] = {
            "growth_score": row.get("growth_score"),
            "quality_score": row.get("quality_score"),
            "safety_score": row.get("safety_score"),
            "valuation_score": row.get("valuation_score"),
            "classification": row.get("classification"),
        }
    return tickers, scores


def _price_on(series: pd.Series, day: str) -> float | None:
    if day not in series.index:
        return None
    value = series.loc[day]
    if pd.isna(value):
        return None
    return float(value)


def _prev_price(series: pd.Series, day: str, calendar: list[str]) -> float | None:
    earlier = [d for d in calendar if d < day and d in series.index]
    if not earlier:
        return None
    return _price_on(series, earlier[-1])


def run_backtest(
    config: dict,
    start_date: str,
    end_date: str,
    *,
    close_by_ticker: Mapping[str, pd.Series],
    scoring_schedule: Mapping[str, Mapping[str, pd.DataFrame]] | None = None,
    initial_equity: float = 1.0,
    signal_every_n_days: int = 1,
    signal_tickers: list[str] | None = None,
) -> dict:
    """Run Tầng 1 + Tầng 2 over history with point-in-time closes.

    Parameters
    ----------
    close_by_ticker:
        Full close histories (will be truncated to ≤ t each day — no look-ahead).
    scoring_schedule:
        ``{assumed_filed_at: scoring_frames}`` for ``score_current_universe``.
        If omitted, all price tickers stay on the watchlist (quant-only path).
    signal_tickers:
        Subset that may receive BUY/SELL (e.g. exclude VNINDEX). Default: watchlist.
    """
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")
    if not close_by_ticker:
        raise ValueError("close_by_ticker is required")

    cfg = deepcopy(config) if config else {}
    bt_cfg = dict(cfg.get("backtest") or {})
    cost_cfg = dict(bt_cfg.get("cost") or {})
    tax_sell = float(cost_cfg.get("tax_sell_pct", 0.001))
    fee_rt = float(cost_cfg.get("fee_roundtrip_pct", 0.003))
    limit_pct = float(cost_cfg.get("limit_pct", 0.07))
    buy_fee = buy_cost_fraction(fee_rt)
    sell_fee = sell_cost_fraction(tax_sell, fee_rt)

    closes = {
        str(t).strip().upper(): _as_date_index(s) for t, s in close_by_ticker.items()
    }
    calendar = _trading_days(closes, start_date, end_date)
    if not calendar:
        return {
            "equity_curve": [],
            "trades": [],
            "metrics": compute_metrics([], [], cfg),
            "signals": [],
        }

    cash = float(initial_equity)
    # ticker -> {qty_value at entry, entry_price, stop, entry_date, shares}
    positions: dict[str, dict[str, Any]] = {}
    equity_curve: list[dict] = []
    trades: list[dict] = []
    all_signals: list[dict] = []
    watchlist: list[str] = list(closes.keys())
    fund_scores: dict[str, dict] = {}
    last_signals: dict[str, dict] = {}

    def mark_equity(day: str) -> float:
        total = cash
        for ticker, pos in positions.items():
            px = _price_on(closes[ticker], day)
            if px is None:
                total += float(pos["market_value"])
            else:
                pos["market_value"] = float(pos["shares"]) * px
                total += pos["market_value"]
        return total

    for i, day in enumerate(calendar):
        # --- Fundamental refresh (point-in-time filed_at) ---
        watchlist, fund_scores = _active_watchlist(
            scoring_schedule, day, list(closes.keys()), cfg
        )
        # Drop positions no longer on watchlist via forced review (keep until SELL)

        # --- Stops ---
        for ticker in list(positions):
            pos = positions[ticker]
            px = _price_on(closes[ticker], day)
            stop = pos.get("stop")
            if px is None or stop is None or pd.isna(stop):
                continue
            if px <= float(stop):
                last_signals[ticker] = {
                    "action": "SELL",
                    "size": 0.0,
                    "stop": stop,
                    "reason": "stop_hit",
                }

        # --- Quant signals (filtered closes ≤ day) ---
        if i % max(int(signal_every_n_days), 1) == 0 and watchlist:
            truncated = {
                t: _truncate(closes[t], day)
                for t in closes
                if not _truncate(closes[t], day).empty
            }
            emit = [
                t
                for t in (signal_tickers if signal_tickers is not None else watchlist)
                if str(t).strip().upper() in truncated
            ]
            if truncated and emit:
                day_signals = generate_signals(
                    truncated,
                    as_of_date=day,
                    fundamental_scores=fund_scores,
                    config=cfg,
                    signal_tickers=emit,
                )
                all_signals.extend(day_signals)
                for row in day_signals:
                    last_signals[str(row["ticker"]).upper()] = row

        # --- Execute ---
        equity_before = mark_equity(day)
        for ticker in list(dict.fromkeys([*watchlist, *positions.keys()])):
            if ticker not in closes:
                continue
            px = _price_on(closes[ticker], day)
            prev = _prev_price(closes[ticker], day, calendar)
            if px is None:
                continue
            signal = last_signals.get(ticker) or {}
            action = str(signal.get("action") or "WATCH").upper()

            tradable = is_tradable_at_price_limit(px, prev, limit_pct=limit_pct)

            # Close
            if ticker in positions and action == "SELL":
                pos = positions[ticker]
                held_days = _business_days_between(pos["entry_date"], day, calendar)
                if held_days < 2:
                    continue  # T+2
                if not tradable:
                    continue
                gross = (px / float(pos["entry_price"])) - 1.0
                proceeds = float(pos["shares"]) * px
                net_proceeds = proceeds * (1.0 - sell_fee)
                pnl = net_proceeds - float(pos["cost_basis"])
                cash += net_proceeds
                trades.append(
                    {
                        "ticker": ticker,
                        "entry_date": pos["entry_date"],
                        "exit_date": day,
                        "entry_price": pos["entry_price"],
                        "exit_price": px,
                        "pnl": pnl,
                        "gross_return": gross,
                        "notional": proceeds,
                        "reason": signal.get("reason") or "signal_sell",
                    }
                )
                del positions[ticker]
                continue

            # Open
            if (
                ticker not in positions
                and action == "BUY"
                and ticker in watchlist
                and tradable
            ):
                size = float(signal.get("size") or 0.0)
                if size <= 0 or equity_before <= 0:
                    continue
                alloc = min(size, 1.0) * equity_before
                if alloc > cash:
                    alloc = cash
                if alloc <= 0:
                    continue
                spent = alloc * (1.0 + buy_fee)
                if spent > cash:
                    alloc = cash / (1.0 + buy_fee)
                    spent = cash
                shares = alloc / px
                cash -= spent
                stop = signal.get("stop")
                positions[ticker] = {
                    "shares": shares,
                    "entry_price": px,
                    "entry_date": day,
                    "stop": stop,
                    "cost_basis": spent,
                    "market_value": alloc,
                }
                trades.append(
                    {
                        "ticker": ticker,
                        "entry_date": day,
                        "exit_date": None,
                        "entry_price": px,
                        "exit_price": None,
                        "pnl": None,
                        "gross_return": None,
                        "notional": alloc,
                        "reason": "signal_buy",
                    }
                )

        equity_curve.append({"date": day, "equity": mark_equity(day)})

    regime_by_date: dict[str, float] = {}
    for sig in all_signals:
        day = str(sig.get("date") or "")
        p = sig.get("p_regime")
        if day and p is not None and day not in regime_by_date:
            try:
                regime_by_date[day] = float(p)
            except (TypeError, ValueError):
                continue

    metrics = compute_metrics(
        equity_curve,
        trades,
        cfg,
        signals=all_signals,
        regime_by_date=regime_by_date,
    )
    return {
        "equity_curve": equity_curve,
        "trades": trades,
        "metrics": metrics,
        "signals": all_signals,
        "start_date": start_date,
        "end_date": end_date,
    }


def default_scoring_dates(
    years: list[int], lag_days: int = 90
) -> list[str]:
    """Assumed filing dates for annual fundamental refreshes."""
    return [assumed_filed_at(year, lag_days) for year in years]


def run_id_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
