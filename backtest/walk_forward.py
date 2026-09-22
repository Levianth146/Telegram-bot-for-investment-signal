"""Walk-forward validation — train N năm, test M tháng, trượt cửa sổ tới.

Tham chiếu: mục 11.3 — tiêu chí giữ/cắt một tầng phải dựa trên Sharpe NGOÀI MẪU
(out-of-sample), không phải Sharpe trên chính tập đã fit.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping

import yaml

from backtest.engine import run_backtest
from backtest.metrics import compute_metrics


def _parse(d: str) -> date:
    return datetime.strptime(d, "%Y-%m-%d").date()


def _fmt(d: date) -> str:
    return d.isoformat()


def _add_months(d: date, months: int) -> date:
    year = d.year + (d.month - 1 + months) // 12
    month = (d.month - 1 + months) % 12 + 1
    leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
    dim = [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(d.day, dim))


def walk_forward_windows(
    start_date: str, end_date: str, train_years: int, test_months: int
) -> list[tuple[str, str, str, str]]:
    """Yield (train_start, train_end, test_start, test_end) ISO dates."""
    if train_years < 1:
        raise ValueError("train_years must be >= 1")
    if test_months < 1:
        raise ValueError("test_months must be >= 1")

    start = _parse(start_date)
    end = _parse(end_date)
    if start >= end:
        raise ValueError("start_date must be before end_date")

    windows: list[tuple[str, str, str, str]] = []
    train_start = start
    while True:
        train_end = _add_months(train_start, train_years * 12) - timedelta(days=1)
        test_start = train_end + timedelta(days=1)
        test_end = _add_months(test_start, test_months) - timedelta(days=1)
        if test_start > end:
            break
        if test_end > end:
            test_end = end
        if train_end < train_start or test_end < test_start:
            break
        windows.append(
            (_fmt(train_start), _fmt(train_end), _fmt(test_start), _fmt(test_end))
        )
        train_start = _add_months(train_start, test_months)
        if train_start >= end:
            break
    return windows


def run_walk_forward(
    config: dict,
    start_date: str,
    end_date: str,
    *,
    close_by_ticker: Mapping[str, Any],
    scoring_schedule: Mapping[str, Any] | None = None,
    signal_every_n_days: int = 5,
    signal_tickers: list[str] | None = None,
) -> dict:
    """Run OOS folds; concatenate test equity and report fold + pooled metrics."""
    bt = dict(config.get("backtest") or {})
    wf = dict(bt.get("walk_forward") or {})
    train_years = int(wf.get("train_years", 3))
    test_months = int(wf.get("test_months", 6))

    windows = walk_forward_windows(start_date, end_date, train_years, test_months)
    folds = []
    oos_equity: list[dict] = []
    oos_trades: list[dict] = []

    for train_start, train_end, test_start, test_end in windows:
        result = run_backtest(
            config,
            test_start,
            test_end,
            close_by_ticker=close_by_ticker,
            scoring_schedule=scoring_schedule,
            signal_every_n_days=signal_every_n_days,
            signal_tickers=signal_tickers,
        )
        folds.append(
            {
                "train_start": train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
                "metrics": result["metrics"],
            }
        )
        curve = result["equity_curve"]
        if not curve:
            continue
        base = oos_equity[-1]["equity"] if oos_equity else 1.0
        first_eq = float(curve[0]["equity"]) or 1.0
        scale = base / first_eq
        for point in curve:
            oos_equity.append(
                {"date": point["date"], "equity": float(point["equity"]) * scale}
            )
        oos_trades.extend(result["trades"])

    pooled = compute_metrics(oos_equity, oos_trades, config)
    fold_sharpes: list[float] = []
    for fold in folds:
        raw = (fold.get("metrics") or {}).get("sharpe")
        if raw is None:
            continue
        try:
            val = float(raw)
        except (TypeError, ValueError):
            continue
        if val == val:  # not NaN
            fold_sharpes.append(val)
    n_folds = len(folds)
    if fold_sharpes:
        mean_fs = float(sum(fold_sharpes) / len(fold_sharpes))
        if len(fold_sharpes) >= 2:
            var = sum((x - mean_fs) ** 2 for x in fold_sharpes) / (
                len(fold_sharpes) - 1
            )
            std_fs = float(var**0.5)
        else:
            std_fs = 0.0
    else:
        mean_fs = None
        std_fs = None
    pooled = dict(pooled)
    pooled["n_folds"] = n_folds
    pooled["fold_sharpes"] = fold_sharpes
    pooled["fold_sharpe_mean"] = mean_fs
    pooled["fold_sharpe_std"] = std_fs
    return {
        "windows": windows,
        "folds": folds,
        "equity_curve": oos_equity,
        "trades": oos_trades,
        "metrics": pooled,
        "n_folds": n_folds,
        "fold_sharpes": fold_sharpes,
        "fold_sharpe_mean": mean_fs,
        "fold_sharpe_std": std_fs,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward backtest")
    parser.add_argument("--config", required=True)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    args = parser.parse_args()
    path = Path(args.config)
    with path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    bt = config.get("backtest") or {}
    start = args.start_date or bt.get("start_date")
    end = args.end_date or date.today().isoformat()
    if not start:
        raise SystemExit("Provide --start-date or backtest.start_date in config")
    windows = walk_forward_windows(
        start,
        end,
        int((bt.get("walk_forward") or {}).get("train_years", 3)),
        int((bt.get("walk_forward") or {}).get("test_months", 6)),
    )
    print(f"walk_forward windows: {len(windows)}")
    for row in windows:
        print("  train {}..{} | test {}..{}".format(*row))
    print(
        "Note: pass prepared close_by_ticker via run_walk_forward() for full OOS run "
        "(CLI listing only — no network)."
    )


if __name__ == "__main__":
    main()
