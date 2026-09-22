"""BacktestDataBundle — share prices + PIT schedule across B0/B1/B2/framework.

Một experiment context load data **một lần**; baselines và ablation dùng chung
bundle (prompt tối ưu §15). Không đổi semantics final.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass
class BacktestDataBundle:
    """Shared prices, schedule, universe, và config cho một report/ablation run."""

    close_by_ticker: dict[str, Any]
    signal_closes: dict[str, Any]
    tickers: list[str]
    start_date: str
    end_date: str
    oos_start: str
    oos_end: str
    config: Mapping[str, Any]
    scoring_schedule: Mapping[str, Any] | None = None
    mode: str = "final"  # "fast_dev" | "final"
    no_plots: bool = False
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def n_tickers(self) -> int:
        return len(self.tickers)

    @property
    def is_fast_dev(self) -> bool:
        return self.mode == "fast_dev"


def build_data_bundle(
    *,
    tickers: list[str],
    hist_start: str,
    hist_end: str,
    oos_start: str,
    oos_end: str,
    config: Mapping[str, Any],
    with_fundamentals: bool = True,
    lookback_years: int = 5,
    db_path: str = "store/bot.db",
    refresh_fundamentals: bool = False,
    mode: str = "final",
    no_plots: bool = False,
) -> BacktestDataBundle:
    """Load OHLCV (+ optional PIT schedule) một lần cho toàn bộ report columns."""
    from backtest.ablation import (
        _signal_closes,
        build_scoring_schedule,
        load_close_by_ticker,
    )

    tickers_u = [str(t).strip().upper() for t in tickers if str(t).strip()]
    fetch_list = list(dict.fromkeys([*tickers_u, "VNINDEX", "VN30"]))
    closes = load_close_by_ticker(
        fetch_list,
        hist_start,
        hist_end,
        dict(config),
        include_benchmark=True,
    )
    if not closes:
        raise RuntimeError("No OHLCV loaded — check providers / network / cache")

    signal_closes = _signal_closes(
        {t: closes[t] for t in tickers_u if t in closes},
        config,
    )
    scoring_schedule = None
    if with_fundamentals:
        print(
            f"building scoring_schedule (PIT) refresh={refresh_fundamentals}...",
            flush=True,
        )
        scoring_schedule = build_scoring_schedule(
            list(signal_closes),
            hist_start,
            hist_end,
            config,
            lookback_years=max(int(lookback_years), 1),
            db_path=db_path,
            refresh=refresh_fundamentals,
        )
        print(f"scoring_schedule keys={sorted(scoring_schedule)}", flush=True)

    return BacktestDataBundle(
        close_by_ticker=closes,
        signal_closes=signal_closes,
        tickers=tickers_u,
        start_date=hist_start,
        end_date=hist_end,
        oos_start=oos_start,
        oos_end=oos_end,
        config=config,
        scoring_schedule=scoring_schedule,
        mode=mode,
        no_plots=bool(no_plots),
        meta={
            "n_closes": len(closes),
            "n_signal": len(signal_closes),
            "with_fundamentals": bool(with_fundamentals),
        },
    )
