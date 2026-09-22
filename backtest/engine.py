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
    """Cắt closes ≤ as_of (ISO date sort = chronological)."""
    if series.empty:
        return series
    # searchsorted + iloc: tránh boolean mask copy mỗi ngày.
    end = series.index.searchsorted(as_of, side="right")
    return series.iloc[:end]


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


# Risk override: không cho Quant ghi đè cho đến khi SELL khớp.
_RISK_OVERRIDE_REASONS = frozenset({"stop_hit", "fundamental_fail_exit"})

# Kiểu cache FF: filed_at → (watchlist PASS/WATCH, scores dict).
_FFState = tuple[list[str], dict[str, dict]]


def _score_frames_to_watchlist(
    frames: Mapping[str, pd.DataFrame],
    filed_at: str,
) -> _FFState:
    """Chạy ``score_current_universe`` một lần trên frames của một filed_at.

    Schema canonical: ``fundamental_view`` (PASS|WATCH|FAIL) — alias
    ``classification`` giữ tương thích ngược.
    """
    if not frames:
        return [], {}

    sample = next(iter(frames.values()))
    if sample is None or getattr(sample, "empty", True):
        return [], {}

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
        view = str(row.get("classification") or "").strip().upper()
        scores[ticker] = {
            "growth_score": row.get("growth_score"),
            "quality_score": row.get("quality_score"),
            "safety_score": row.get("safety_score"),
            "valuation_score": row.get("valuation_score"),
            "fundamental_score": row.get("fundamental_score"),
            # Canonical cho quant_engine; classification = alias.
            "fundamental_view": view,
            "classification": view,
        }
    return tickers, scores


def precompute_fundamental_states(
    scoring_schedule: Mapping[str, Mapping[str, pd.DataFrame]] | None,
) -> dict[str, _FFState]:
    """Precompute ``filed_at → (watchlist, scores)`` — event-driven, không rescore mỗi ngày.

    Mỗi key trong ``scoring_schedule`` chỉ gọi ``score_current_universe`` một lần.
    Daily loop chỉ lookup latest filed_at ≤ day (tương đương semantics cũ).
    """
    if not scoring_schedule:
        return {}
    states: dict[str, _FFState] = {}
    for filed_at in sorted(scoring_schedule.keys()):
        frames = scoring_schedule[filed_at] or {}
        states[str(filed_at)] = _score_frames_to_watchlist(frames, str(filed_at))
    return states


def _lookup_ff_state(
    ff_states: Mapping[str, _FFState],
    as_of: str,
    fallback_tickers: list[str],
) -> _FFState:
    """Latest precomputed state với filed_at ≤ as_of."""
    if not ff_states:
        return list(fallback_tickers), {}
    eligible = [d for d in ff_states if d <= as_of]
    if not eligible:
        return [], {}
    return ff_states[max(eligible)]


def _active_watchlist(
    scoring_schedule: Mapping[str, Mapping[str, pd.DataFrame]] | None,
    as_of: str,
    fallback_tickers: list[str],
    config: dict,
    *,
    ff_states: Mapping[str, _FFState] | None = None,
) -> tuple[list[str], dict[str, dict]]:
    """Latest fundamental run with filed_at <= as_of → PASS/WATCH + scores.

    Nếu ``ff_states`` đã precompute → chỉ lookup (O(events)); ngược lại score
    on-the-fly (tương thích test/call cũ).
    """
    if ff_states is not None:
        return _lookup_ff_state(ff_states, as_of, fallback_tickers)

    if not scoring_schedule:
        return list(fallback_tickers), {}

    eligible = sorted(d for d in scoring_schedule if d <= as_of)
    if not eligible:
        return [], {}

    filed_at = eligible[-1]
    return _score_frames_to_watchlist(scoring_schedule[filed_at] or {}, filed_at)


def _price_on(series: pd.Series, day: str) -> float | None:
    if day not in series.index:
        return None
    value = series.loc[day]
    if pd.isna(value):
        return None
    return float(value)


def _prev_price(
    series: pd.Series,
    day: str,
    calendar: list[str],
    *,
    day_pos: Mapping[str, int] | None = None,
) -> float | None:
    """Giá phiên trước trên calendar (có mặt trong series)."""
    if day_pos is not None:
        i = day_pos.get(day)
        if i is None:
            return None
        for j in range(i - 1, -1, -1):
            prev_d = calendar[j]
            if prev_d in series.index:
                return _price_on(series, prev_d)
        return None
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

    Tín hiệu dùng closes ≤ ngày T; khớp lệnh từ phiên T+1 (tránh look-ahead
    fill cùng close đã dùng để tính signal). Stop-loss khớp cùng phiên chạm.

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

    # Precompute FF states một lần / filed_at (event-driven; daily chỉ lookup).
    ff_states = (
        precompute_fundamental_states(scoring_schedule)
        if scoring_schedule is not None
        else None
    )
    # Map ngày → vị trí trên calendar (prev_price O(1) thay vì scan list).
    day_pos = {d: i for i, d in enumerate(calendar)}
    # Regime memo trong một run: cùng as_of + cùng benchmark end → không fit lại.
    regime_memo: dict[tuple[str, str, int], dict[str, Any]] = {}

    cash = float(initial_equity)
    # ticker -> {qty_value at entry, entry_price, stop, entry_date, shares}
    positions: dict[str, dict[str, Any]] = {}
    equity_curve: list[dict] = []
    trades: list[dict] = []
    all_signals: list[dict] = []
    watchlist: list[str] = list(closes.keys())
    fund_scores: dict[str, dict] = {}
    last_signals: dict[str, dict] = {}
    # Ngày tín hiệu được sinh; khớp lệnh chỉ từ phiên kế tiếp (T+1 fill).
    # None = khớp ngay (dùng cho stop_hit cùng phiên).
    signal_asof: dict[str, str | None] = {}

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

    def _signal_actionable(ticker: str, day: str) -> bool:
        """True nếu tín hiệu đã sẵn sàng khớp (T+1 hoặc stop cùng ngày)."""
        if ticker not in last_signals:
            return False
        asof = signal_asof.get(ticker)
        if asof is None:
            return True  # stop_hit: khớp ngay phiên chạm stop
        return day > asof

    for i, day in enumerate(calendar):
        # --- Fundamental refresh (point-in-time filed_at) ---
        watchlist, fund_scores = _active_watchlist(
            scoring_schedule,
            day,
            list(closes.keys()),
            cfg,
            ff_states=ff_states,
        )
        # Held + FAIL/excluded → schedule forced EXIT (T+1), không kẹt vô hạn.
        if scoring_schedule is not None:
            for ticker in list(positions):
                if ticker in watchlist:
                    continue
                existing = last_signals.get(ticker) or {}
                if str(existing.get("reason") or "") in _RISK_OVERRIDE_REASONS:
                    continue
                last_signals[ticker] = {
                    "action": "SELL",
                    "size": 0.0,
                    "stop": positions[ticker].get("stop"),
                    "reason": "fundamental_fail_exit",
                }
                signal_asof[ticker] = day  # khớp Close T+1

        # --- Stops (khớp cùng phiên khi close ≤ stop; không chờ T+1) ---
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
                signal_asof[ticker] = None

        # --- Execute (trước khi sinh tín hiệu mới — tránh fill cùng close dùng tính signal) ---
        equity_before = mark_equity(day)
        for ticker in list(dict.fromkeys([*watchlist, *positions.keys()])):
            if ticker not in closes:
                continue
            if not _signal_actionable(ticker, day):
                continue
            px = _price_on(closes[ticker], day)
            prev = _prev_price(
                closes[ticker], day, calendar, day_pos=day_pos
            )
            if px is None:
                continue
            signal = last_signals.get(ticker) or {}
            action = str(signal.get("action") or "WATCH").upper()

            tradable = is_tradable_at_price_limit(px, prev, limit_pct=limit_pct)

            # Close — long-only: SELL đóng vị thế mua (direction +1 trong PnL)
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
                # Xóa risk override sau khi khớp SELL.
                last_signals.pop(ticker, None)
                signal_asof.pop(ticker, None)
                continue

            # Open — BUY = long (không short); FAIL/excluded không mở mới.
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

        # --- Quant signals (closes ≤ day); khớp lệnh từ phiên T+1 ---
        if i % max(int(signal_every_n_days), 1) == 0 and watchlist:
            # Truncate một lần / ticker (tránh double _truncate + boolean copy).
            truncated: dict[str, pd.Series] = {}
            for t, series in closes.items():
                cut = _truncate(series, day)
                if not cut.empty:
                    truncated[t] = cut
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
                    regime_cache=regime_memo,
                )
                all_signals.extend(day_signals)
                for row in day_signals:
                    tkr = str(row["ticker"]).upper()
                    # Hard risk override: stop / FAIL exit không bị Quant ghi đè.
                    existing_reason = str(
                        (last_signals.get(tkr) or {}).get("reason") or ""
                    )
                    if existing_reason in _RISK_OVERRIDE_REASONS:
                        continue
                    last_signals[tkr] = row
                    signal_asof[tkr] = day

        invested = sum(float(p.get("market_value") or 0.0) for p in positions.values())
        eq = mark_equity(day)
        equity_curve.append(
            {
                "date": day,
                "equity": eq,
                "cash": cash,
                "exposure": (invested / eq) if eq > 0 else 0.0,
                "n_positions": len(positions),
            }
        )

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
        force_research_metrics=True,
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
