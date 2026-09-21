"""Chạy pipeline một lần: optional sector → daily (persist + push).

Ví dụ:
  python scripts/run_daily_pipeline.py
  python scripts/run_daily_pipeline.py --with-sector
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def _load_dotenv(path: Path = Path(".env")) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def main(argv: list[str] | None = None) -> int:
    # Cho phép chạy từ repo root: python scripts/run_daily_pipeline.py
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser(
        description="Ops: sector (optional) + daily_job persist/push"
    )
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--db-path", default=None, help="Mặc định DATABASE_PATH hoặc store/bot.db")
    parser.add_argument("--as-of-date", default=None)
    parser.add_argument(
        "--with-sector",
        action="store_true",
        help="Chạy sector_job (fetch_live) trước daily",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="Persist signals nhưng không gửi Telegram",
    )
    args = parser.parse_args(argv)

    _load_dotenv(root / ".env")
    db_path = args.db_path or os.getenv("DATABASE_PATH", "store/bot.db")

    from pipeline import daily_job, sector_job

    config = daily_job.load_config(args.config)

    if args.with_sector:
        sector_result = sector_job.run(
            config,
            db_path=db_path,
            fetch_live=True,
            as_of_date=args.as_of_date,
        )
        print(f"sector: {sector_result.get('note')}")

    result = daily_job.run(
        config,
        db_path=db_path,
        as_of_date=args.as_of_date,
        fetch_prices=True,
        persist=True,
        push=not args.no_push,
    )
    print(result.get("note") or "daily done")
    print(f"tickers: {len(result.get('tickers') or [])}")
    if result.get("benchmark"):
        print(
            f"benchmark: {result['benchmark']} "
            f"loaded={result.get('benchmark_loaded')}"
        )
    price_inputs = result.get("price_inputs") or {}
    if price_inputs:
        loaded = len(price_inputs.get("ohlcv") or {})
        missing = price_inputs.get("missing") or []
        wanted = loaded + len(missing)
        pct = (100.0 * len(missing) / wanted) if wanted else 0.0
        print(f"ohlcv loaded: {loaded}/{wanted} missing={len(missing)} ({pct:.1f}%)")
    push = result.get("push") or {}
    skipped = push.get("skipped") or ""
    print(
        f"push: subscribers={len(push.get('chat_ids') or [])} "
        f"sent={push.get('sent', 0)} failed={push.get('failed', 0)} "
        f"{skipped}".rstrip()
    )
    paper = result.get("paper_positions") or {}
    if paper:
        print(
            f"paper: opened={paper.get('opened', 0)} "
            f"closed={paper.get('closed', 0)} skipped={paper.get('skipped', 0)}"
        )
    for row in (result.get("signals") or [])[:10]:
        print(
            f"  {row['ticker']}: {row['action']} "
            f"p_bull={row['p_regime']:.2f} size={row['size']:.3f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
