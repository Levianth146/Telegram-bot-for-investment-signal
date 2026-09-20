"""Job Tầng 2 — chạy mỗi phiên, sau giờ đóng cửa (~15:00).

Luồng: store.watchlist (từ Tầng 1) + giá/khối lượng hằng ngày từ
``data.providers.get_price_provider`` / ``data.ingest.price_history``
  -> regime -> alpha (kalman/ou) -> risk (garch) -> portfolio (black-litterman,
     hoặc fallback equal-weight nếu tắt) -> probabilistic (monte carlo + hawkes,
     nếu bật) -> ghi vào store.signals

QUAN TRỌNG: đây là nơi DUY NHẤT được fit/chạy các mô hình Tầng 2. bot/ không
bao giờ được gọi các hàm trong quant_engine/ trực tiếp.
"""

from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import yaml

from data.ingest.price_history import fetch_universe_ohlcv, to_close_series
from quant_engine.signal_engine import generate_signals
from store import repository


def _pd_to_last_close(close) -> float:
    """Last finite close from a Series-like."""
    import pandas as pd

    series = pd.to_numeric(close, errors="coerce").dropna()
    if series.empty:
        raise ValueError("empty close series")
    return float(series.iloc[-1])


# alias used in run()
pd_to_last_close = _pd_to_last_close


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else Path("pipeline/config.yaml")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_watchlist_tickers(
    db_path: str = "store/bot.db", as_of_date: str | None = None
) -> list[str]:
    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        return repository.get_watchlist(conn, as_of_date)
    finally:
        conn.close()


def prepare_price_inputs(
    tickers: list[str],
    config: dict,
    *,
    lookback_days: int = 365 * 3,
    end: str | None = None,
    extra_tickers: list[str] | None = None,
) -> dict[str, Any]:
    """Fetch OHLCV + close series for Quant (via data/providers — no fit here).

    ``extra_tickers`` (e.g. VNINDEX benchmark) are fetched for regime but may
    be omitted from signal generation by the caller.
    """
    end_date = end or date.today().isoformat()
    start_date = (
        date.fromisoformat(end_date) - timedelta(days=lookback_days)
    ).isoformat()
    wanted = []
    seen: set[str] = set()
    for ticker in list(tickers) + list(extra_tickers or []):
        key = str(ticker).strip().upper()
        if key and key not in seen:
            wanted.append(key)
            seen.add(key)
    ohlcv_by_ticker = fetch_universe_ohlcv(wanted, start_date, end_date, config)
    close_by_ticker = {
        ticker: to_close_series(frame) for ticker, frame in ohlcv_by_ticker.items()
    }
    return {
        "start": start_date,
        "end": end_date,
        "ohlcv": ohlcv_by_ticker,
        "close_series": close_by_ticker,
        "missing": sorted(set(wanted) - set(ohlcv_by_ticker)),
        "fetched": wanted,
    }


def _maybe_push_signals(signals: list[dict], chat_ids: list[int]) -> dict[str, Any]:
    """Notify active subscribers after signals are persisted (ARCHITECTURE)."""
    from bot.formatters import format_signals_list

    result: dict[str, Any] = {
        "chat_ids": list(chat_ids),
        "sent": 0,
        "failed": 0,
        "text": format_signals_list(signals) if signals else "",
    }
    if not chat_ids or not signals:
        return result

    import os
    import json
    import urllib.error
    import urllib.request

    token = os.getenv("BOT_TOKEN", "")
    if not token or token == "changeme":
        result["skipped"] = "BOT_TOKEN unset"
        return result

    text = result["text"]
    for chat_id in chat_ids:
        payload = json.dumps(
            {"chat_id": chat_id, "text": text[:4000]}
        ).encode("utf-8")
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                if 200 <= resp.status < 300:
                    result["sent"] += 1
                else:
                    result["failed"] += 1
        except (urllib.error.URLError, TimeoutError, OSError):
            result["failed"] += 1
    return result


def run(
    config: dict,
    *,
    db_path: str = "store/bot.db",
    as_of_date: str | None = None,
    tickers: list[str] | None = None,
    fetch_prices: bool = True,
    close_by_ticker: dict | None = None,
    persist: bool = True,
    push: bool = True,
) -> dict[str, Any]:
    """Load watchlist, prepare prices, generate signals, optionally persist + push."""
    signal_date = as_of_date or date.today().isoformat()
    universe = tickers or load_watchlist_tickers(db_path, as_of_date)
    if not universe:
        return {
            "tickers": [],
            "price_inputs": None,
            "signals": [],
            "push": {"chat_ids": [], "sent": 0},
            "note": "empty watchlist — run quarterly_job first",
        }

    qcfg = config.get("quant_engine") or {}
    benchmark = (qcfg.get("benchmark") or "").strip().upper() or None

    price_inputs = None
    series = close_by_ticker
    if series is None and fetch_prices:
        extras = [benchmark] if benchmark else None
        price_inputs = prepare_price_inputs(
            universe, config, end=signal_date, extra_tickers=extras
        )
        series = price_inputs["close_series"]
    elif series is None:
        series = {}

    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        fund_scores = repository.get_latest_fundamental_scores(conn, universe)
    finally:
        conn.close()

    signals = generate_signals(
        series,
        as_of_date=signal_date,
        fundamental_scores=fund_scores,
        index_ticker=benchmark,
        signal_tickers=universe,
        config=config,
    )

    push_result: dict[str, Any] = {"chat_ids": [], "sent": 0}
    paper_result: dict[str, Any] = {"opened": 0, "closed": 0, "skipped": 0}
    if persist and signals:
        conn = repository.get_connection(db_path)
        try:
            repository.init_schema(conn)
            repository.upsert_signals(conn, signals)
            chat_ids = repository.get_active_subscribers(conn)
            # Paper positions from last close (no model fit)
            entry_prices = {}
            for ticker, close in (series or {}).items():
                if close is None or len(close) == 0:
                    continue
                try:
                    entry_prices[str(ticker).upper()] = float(
                        pd_to_last_close(close)
                    )
                except (TypeError, ValueError):
                    continue
            from pipeline.paper_positions import sync_positions_from_signals

            paper_result = sync_positions_from_signals(
                conn, signals, entry_price_by_ticker=entry_prices
            )
        finally:
            conn.close()
        if push:
            push_result = _maybe_push_signals(signals, chat_ids)

    return {
        "tickers": universe,
        "price_inputs": price_inputs,
        "signals": signals,
        "push": push_result,
        "paper_positions": paper_result,
        "benchmark": benchmark,
        "benchmark_loaded": bool(
            benchmark and series and benchmark in series
        ),
        "note": f"generated {len(signals)} signals for {signal_date}",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--db-path", default="store/bot.db")
    parser.add_argument("--as-of-date", default=None)
    parser.add_argument("--no-persist", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.dry_run:
        from data.providers import get_price_provider

        tickers = load_watchlist_tickers(args.db_path)
        price = get_price_provider(config)
        print("daily_job dry-run OK")
        print(f"  price chain: {price.name}")
        print(f"  watchlist size: {len(tickers)}")
        if tickers:
            print(f"  sample: {', '.join(tickers[:5])}")
        return

    result = run(
        config,
        db_path=args.db_path,
        as_of_date=args.as_of_date,
        fetch_prices=True,
        persist=not args.no_persist,
    )
    print(result["note"])
    print(f"tickers: {len(result['tickers'])}")
    if result.get("benchmark"):
        print(
            f"benchmark: {result['benchmark']} "
            f"loaded={result.get('benchmark_loaded')}"
        )
    if result["price_inputs"]:
        print(f"ohlcv loaded: {len(result['price_inputs']['ohlcv'])}")
        print(f"missing: {result['price_inputs']['missing']}")
    push = result.get("push") or {}
    if push.get("chat_ids") is not None:
        print(
            f"push: subscribers={len(push.get('chat_ids') or [])} "
            f"sent={push.get('sent', 0)} "
            f"{push.get('skipped') or ''}"
        )
    for row in result["signals"][:10]:
        print(
            f"  {row['ticker']}: {row['action']} "
            f"p_bull={row['p_regime']:.2f} size={row['size']:.3f}"
        )


if __name__ == "__main__":
    main()
