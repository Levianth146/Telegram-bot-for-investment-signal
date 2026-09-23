"""Job Tầng 2 — chạy mỗi phiên, sau giờ đóng cửa (~15:00).

Luồng: store.watchlist (từ Tầng 1) + giá/khối lượng hằng ngày từ
``data.providers.get_price_provider`` / ``data.ingest.price_history``
  -> regime -> alpha (kalman/ou) -> risk (garch) -> portfolio (black-litterman,
     hoặc fallback equal-weight nếu tắt) -> probabilistic (monte carlo + hawkes,
     nếu bật) -> ghi vào store.signals

Universe Quant: chỉ watchlist (config ``universe.quant_from_watchlist: true``);
không kéo full VN100. Benchmark thêm ``quant_engine.benchmark`` (vd VNINDEX).

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
    db_path: str = "store/bot.db",
    as_of_date: str | None = None,
    *,
    config: dict | None = None,
) -> list[str]:
    """Đọc watchlist rồi lọc defensive theo eligibility Layer 1 (DB cũ có thể stale)."""
    from fundamental_filter.layer1_engine.eligibility import (
        is_quant_eligible_fundamental,
    )

    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        tickers = repository.get_watchlist(conn, as_of_date)
        fund_by_ticker = repository.get_latest_fundamental_scores(conn, tickers or None)
    finally:
        conn.close()

    if tickers:
        kept: list[str] = []
        dropped: list[str] = []
        for ticker in tickers:
            key = str(ticker).strip().upper()
            fund = fund_by_ticker.get(key)
            if is_quant_eligible_fundamental(fund):
                kept.append(key)
            else:
                dropped.append(key)
        if dropped:
            print(
                "daily_job: dropped "
                f"{len(dropped)} non-eligible fundamental tickers: "
                f"{', '.join(dropped)}",
                flush=True,
            )
        tickers = kept

    if not config:
        return tickers
    from data.universe import filter_tickers_for_config

    kept, dropped = filter_tickers_for_config(tickers, config, db_path=db_path)
    if dropped:
        print(
            f"daily_job: dropped {len(dropped)} watchlist by exchange: "
            f"{', '.join(dropped)}",
            flush=True,
        )
    return kept


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


def bars_from_price_inputs(price_inputs: dict[str, Any] | None) -> list[dict]:
    """Chuyển OHLCV frames (hoặc close series) → rows ``price_bars``."""
    if not price_inputs:
        return []
    bars: list[dict] = []
    ohlcv = price_inputs.get("ohlcv") or {}
    for ticker, frame in ohlcv.items():
        if frame is None:
            continue
        try:
            import pandas as pd

            df = frame if isinstance(frame, pd.DataFrame) else None
        except Exception:  # noqa: BLE001
            df = None
        if df is None or df.empty or "date" not in getattr(df, "columns", []):
            continue
        ticker_u = str(ticker).strip().upper()
        for _, row in df.iterrows():
            day = str(row.get("date") or "")[:10]
            close = row.get("close")
            if not day or close is None:
                continue
            try:
                close_f = float(close)
            except (TypeError, ValueError):
                continue
            bars.append(
                {
                    "ticker": ticker_u,
                    "date": day,
                    "open": row.get("open"),
                    "high": row.get("high"),
                    "low": row.get("low"),
                    "close": close_f,
                    "volume": row.get("volume"),
                }
            )
    if bars:
        return bars

    # Fallback: close series only
    for ticker, series in (price_inputs.get("close_series") or {}).items():
        if series is None:
            continue
        ticker_u = str(ticker).strip().upper()
        try:
            import pandas as pd

            s = pd.to_numeric(series, errors="coerce").dropna()
        except Exception:  # noqa: BLE001
            continue
        for idx, val in s.items():
            day = idx.isoformat()[:10] if hasattr(idx, "isoformat") else str(idx)[:10]
            bars.append(
                {
                    "ticker": ticker_u,
                    "date": day,
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": float(val),
                    "volume": None,
                }
            )
    return bars


def _maybe_push_signals(
    signals: list[dict],
    chat_ids: list[int],
    *,
    action_changes: list[dict] | None = None,
) -> dict[str, Any]:
    """Notify active subscribers after signals are persisted (ARCHITECTURE).

    Ưu tiên tin **đổi action** (BUY↔WATCH↔SELL) khi có; fallback danh sách đầy đủ.
    """
    from bot.formatters import format_action_changes_alert, format_signals_list

    prefer_changes = bool(action_changes)
    text = (
        format_action_changes_alert(action_changes or [])
        if prefer_changes
        else (format_signals_list(signals) if signals else "")
    )
    result: dict[str, Any] = {
        "chat_ids": list(chat_ids),
        "sent": 0,
        "failed": 0,
        "text": text,
        "mode": "action_changes" if prefer_changes else "full_list",
        "n_changes": len(action_changes or []),
    }
    if not chat_ids or not text:
        return result

    import json
    import os
    import urllib.error
    import urllib.request

    token = os.getenv("BOT_TOKEN", "")
    if not token or token == "changeme":
        result["skipped"] = "BOT_TOKEN unset"
        return result

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


def diff_signal_actions(
    previous: list[dict],
    current: list[dict],
) -> list[dict]:
    """So action theo ticker giữa hai lần signals — chỉ trả mã đổi trạng thái."""
    prev_map = {
        str(r.get("ticker", "")).upper(): str(r.get("action") or "WATCH").upper()
        for r in previous
        if r.get("ticker")
    }
    out: list[dict] = []
    for row in current:
        ticker = str(row.get("ticker") or "").upper()
        if not ticker:
            continue
        new_act = str(row.get("action") or "WATCH").upper()
        old_act = prev_map.get(ticker)
        if old_act is None or old_act == new_act:
            continue
        out.append(
            {
                "ticker": ticker,
                "from_action": old_act,
                "to_action": new_act,
                "date": row.get("date"),
                "score": row.get("score"),
            }
        )
    out.sort(key=lambda r: str(r.get("ticker")))
    return out


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
    sync_paper: bool = True,
) -> dict[str, Any]:
    """Load watchlist, prepare prices, generate signals, optionally persist + push."""
    signal_date = as_of_date or date.today().isoformat()
    universe = tickers or load_watchlist_tickers(
        db_path, as_of_date, config=config
    )
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
    price_bars_n = 0
    if persist:
        # Ghi price_bars dù không có signal (phục vụ /chart price)
        bar_rows = bars_from_price_inputs(price_inputs)
        if not bar_rows and series:
            bar_rows = bars_from_price_inputs(
                {"ohlcv": {}, "close_series": series}
            )
        conn = repository.get_connection(db_path)
        try:
            repository.init_schema(conn)
            prev_signals = repository.get_latest_signals(conn) if signals else []
            action_changes = (
                diff_signal_actions(prev_signals, signals) if signals else []
            )
            if bar_rows:
                price_bars_n = repository.upsert_price_bars(conn, bar_rows)
            if signals:
                repository.upsert_signals(conn, signals)
                chat_ids = repository.get_active_subscribers(conn)
                if sync_paper:
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
            else:
                chat_ids = []
                action_changes = []
        finally:
            conn.close()
        if push and signals:
            push_result = _maybe_push_signals(
                signals, chat_ids, action_changes=action_changes or None
            )

    return {
        "tickers": universe,
        "price_inputs": price_inputs,
        "signals": signals,
        "push": push_result,
        "paper_positions": paper_result,
        "price_bars_upserted": price_bars_n,
        "benchmark": benchmark,
        "benchmark_loaded": bool(
            benchmark and series and benchmark in series
        ),
        "note": f"generated {len(signals)} signals for {signal_date}",
    }


def _closes_from_store(
    conn,
    tickers: list[str],
    *,
    as_of: str,
    lookback_days: int = 800,
) -> dict:
    """Đọc close đã có trong ``price_bars`` tới ``as_of`` — không bịa giá."""
    import pandas as pd

    out: dict = {}
    for ticker in tickers:
        rows = repository.get_price_closes(
            conn, ticker, limit_days=lookback_days
        )
        if not rows:
            continue
        pairs = [
            (str(r["date"])[:10], float(r["close"]))
            for r in rows
            if r.get("close") is not None and str(r["date"])[:10] <= as_of
        ]
        if not pairs:
            continue
        out[str(ticker).upper()] = pd.Series(
            {d: c for d, c in pairs}, dtype=float
        ).sort_index()
    return out


def backfill_from_store(
    config: dict,
    *,
    db_path: str = "store/bot.db",
    days: int = 20,
    push: bool = False,
) -> dict[str, Any]:
    """Tích lũy ``signals`` nhiều phiên từ ``price_bars`` thật (PIT theo ngày).

    Không bịa số: mỗi phiên gọi lại ``generate_signals`` trên chuỗi close ≤ ngày đó.
    Dùng khi store mới chỉ có 1 ngày signal nhưng đã có lịch sử giá.
    """
    days = max(1, int(days))
    universe = load_watchlist_tickers(db_path, config=config)
    if not universe:
        return {
            "days_requested": days,
            "dates": [],
            "signals_upserted_days": 0,
            "note": "empty watchlist — run quarterly_job first",
        }

    qcfg = config.get("quant_engine") or {}
    benchmark = (qcfg.get("benchmark") or "").strip().upper() or None
    needed = list(universe)
    if benchmark and benchmark not in needed:
        needed.append(benchmark)

    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        cur = conn.execute(
            """
            SELECT DISTINCT date AS d
            FROM price_bars
            WHERE ticker IN ({})
            ORDER BY date DESC
            LIMIT ?
            """.format(",".join("?" for _ in universe)),
            (*universe, days),
        )
        dates = sorted(str(r["d"])[:10] for r in cur.fetchall())
    finally:
        conn.close()

    done: list[str] = []
    for day in dates:
        conn = repository.get_connection(db_path)
        try:
            series = _closes_from_store(conn, needed, as_of=day)
        finally:
            conn.close()
        if len(series) < 2:
            continue
        result = run(
            config,
            db_path=db_path,
            as_of_date=day,
            tickers=universe,
            fetch_prices=False,
            close_by_ticker=series,
            persist=True,
            push=False,
            sync_paper=False,
        )
        if result.get("signals"):
            done.append(day)

    return {
        "days_requested": days,
        "dates": dates,
        "signals_upserted_days": len(done),
        "done_dates": done,
        "note": (
            f"backfill {len(done)}/{len(dates)} phiên từ price_bars "
            f"(không fetch mạng, không bịa số)"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--db-path", default="store/bot.db")
    parser.add_argument("--as-of-date", default=None)
    parser.add_argument("--no-persist", action="store_true")
    parser.add_argument(
        "--backfill-days",
        type=int,
        default=0,
        help="Tích signals từ price_bars N phiên gần nhất (không bịa số)",
    )
    parser.add_argument("--no-push", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.dry_run:
        from data.providers import get_price_provider

        tickers = load_watchlist_tickers(args.db_path, config=config)
        price = get_price_provider(config)
        print("daily_job dry-run OK")
        print(f"  price chain: {price.name}")
        print(f"  watchlist size: {len(tickers)}")
        if tickers:
            print(f"  sample: {', '.join(tickers[:5])}")
        return

    if args.backfill_days and args.backfill_days > 0:
        bf = backfill_from_store(
            config,
            db_path=args.db_path,
            days=args.backfill_days,
            push=not args.no_push,
        )
        print(bf["note"])
        print(f"dates: {bf.get('signals_upserted_days')}/{len(bf.get('dates') or [])}")
        return

    result = run(
        config,
        db_path=args.db_path,
        as_of_date=args.as_of_date,
        fetch_prices=True,
        persist=not args.no_persist,
        push=not args.no_push,
    )
    print(result["note"])
    print(f"tickers: {len(result['tickers'])}")
    if result.get("benchmark"):
        print(
            f"benchmark: {result['benchmark']} "
            f"loaded={result.get('benchmark_loaded')}"
        )
    if result["price_inputs"]:
        loaded = len(result["price_inputs"]["ohlcv"])
        missing = result["price_inputs"]["missing"] or []
        wanted = loaded + len(missing)
        pct = (100.0 * len(missing) / wanted) if wanted else 0.0
        print(f"ohlcv loaded: {loaded}/{wanted} missing={len(missing)} ({pct:.1f}%)")
        if missing:
            print(f"missing tickers: {', '.join(missing)}")
        delay_ms = (
            (config.get("data_sources") or {}).get("price") or {}
        ).get("request_delay_ms")
        print(f"request_delay_ms: {delay_ms}")
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
