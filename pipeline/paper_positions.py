"""Paper-trading sync — ghi/đóng ``store.positions`` từ ``store.signals``.

Bot chỉ ĐỌC positions. Job này (hoặc daily_job hook) là nơi DUY NHẤT mở/đóng
vị thế paper theo action BUY/SELL. Không fit model — chỉ đọc signals đã có.
"""

from __future__ import annotations

import argparse
from typing import Any

from store import repository


def sync_positions_from_signals(
    conn,
    signals: list[dict],
    *,
    entry_price_by_ticker: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Apply latest signal actions onto OPEN positions.

    - BUY + no OPEN → open_position (needs entry/stop/size on the signal row)
    - SELL + OPEN → close_position at provided/close price
    - WATCH → no change

    ``entry_price_by_ticker`` overrides when signal has no embedded price
    (V1 signals store stop/size but not always entry — use last close).
    """
    prices = {str(k).upper(): float(v) for k, v in (entry_price_by_ticker or {}).items()}
    opened = closed = skipped = 0
    open_rows = {
        str(r["ticker"]).upper(): r for r in repository.get_open_positions(conn)
    }

    for signal in signals:
        ticker = str(signal["ticker"]).strip().upper()
        action = str(signal.get("action") or "WATCH").upper()
        day = str(signal.get("date") or "")
        if action == "BUY" and ticker not in open_rows:
            entry = prices.get(ticker)
            stop = signal.get("stop")
            size = signal.get("size")
            if entry is None or stop is None or size is None:
                skipped += 1
                continue
            repository.open_position(
                conn,
                {
                    "ticker": ticker,
                    "opened_at": day,
                    "entry_price": float(entry),
                    "stop_price": float(stop),
                    "size_pct_nav": float(size),
                },
            )
            open_rows[ticker] = {"ticker": ticker, "opened_at": day}
            opened += 1
        elif action == "SELL" and ticker in open_rows:
            pos = open_rows[ticker]
            close_px = prices.get(ticker)
            if close_px is None:
                skipped += 1
                continue
            repository.close_position(
                conn,
                ticker,
                str(pos["opened_at"]),
                float(close_px),
                day,
            )
            del open_rows[ticker]
            closed += 1

    return {"opened": opened, "closed": closed, "skipped": skipped}


def run(
    *,
    db_path: str = "store/bot.db",
    as_of_date: str | None = None,
    entry_price_by_ticker: dict[str, float] | None = None,
) -> dict[str, Any]:
    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        signals = repository.get_latest_signals(conn, as_of_date)
        result = sync_positions_from_signals(
            conn, signals, entry_price_by_ticker=entry_price_by_ticker
        )
        result["signals"] = len(signals)
        return result
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync paper positions from signals")
    parser.add_argument("--db-path", default="store/bot.db")
    parser.add_argument("--as-of-date", default=None)
    args = parser.parse_args()
    result = run(db_path=args.db_path, as_of_date=args.as_of_date)
    print(
        f"paper_positions: signals={result['signals']} "
        f"opened={result['opened']} closed={result['closed']} "
        f"skipped={result['skipped']}"
    )


if __name__ == "__main__":
    main()
