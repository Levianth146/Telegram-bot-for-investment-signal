"""Job Tầng 1 — chạy lại mỗi khi có BCTC mới (event-driven, theo quý).

Luồng duy nhất (production):

  data/providers (BCTC point-in-time)
    → data.ingest.build_scoring_frames[_from_providers]
    → fundamental_filter.score_current_universe  # pure path
    → to_store_records
    → store.fundamental_scores + store.watchlist
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

from data.ingest.pit import assumed_filed_at
from data.ingest.scoring_frames import build_scoring_frames_from_providers
from fundamental_filter import score_current_universe, to_store_records
from store import repository


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else Path("pipeline/config.yaml")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _assumed_lag_days(config: dict) -> int:
    sources = config.get("data_sources") or {}
    backtest = sources.get("financial_statements_backtest") or {}
    return int(backtest.get("assumed_publication_lag_days", 90))


def run(
    config: dict,
    *,
    tickers: list[str] | None = None,
    scoring_frames: dict | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    db_path: str = "store/bot.db",
    persist: bool = True,
    fetch_live: bool = False,
) -> dict[str, Any]:
    """Score universe and optionally persist store-shaped records.

    Provide either ``scoring_frames`` (pure) or ``tickers`` + years.
    With ``fetch_live=True`` and tickers, pulls BCTC via ``data.providers``.
    """
    if start_year is None or end_year is None:
        raise ValueError("start_year and end_year are required")

    if scoring_frames is None:
        if not tickers:
            raise ValueError(
                "Provide tickers=... (and fetch_live=True for provider pull) "
                "or scoring_frames=..."
            )
        if fetch_live:
            scoring_frames = build_scoring_frames_from_providers(
                tickers, start_year, end_year, config=config, db_path=db_path
            )
        else:
            raise NotImplementedError(
                "Pass scoring_frames, or set fetch_live=True to build frames "
                "from data.providers (network)."
            )

    results, metrics, stages = score_current_universe(
        scoring_frames, start_year, end_year
    )
    filed = assumed_filed_at(end_year, _assumed_lag_days(config))
    records = to_store_records(results, filed_at=filed, as_of_date=filed)

    if persist:
        conn = repository.get_connection(db_path)
        try:
            repository.init_schema(conn)
            repository.upsert_fundamental_scores(conn, records["fundamental_scores"])
            repository.upsert_watchlist(conn, records["watchlist"])
        finally:
            conn.close()

    return {
        "results": results,
        "metrics": metrics,
        "records": records,
        "stages": stages,
        "scoring_frames": scoring_frames,
        "filed_at": filed,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument(
        "--tickers",
        default="",
        help="Comma-separated tickers for live fetch (requires network)",
    )
    parser.add_argument(
        "--universe-file",
        default="",
        help="CSV of tickers (used when --tickers empty; else config universe.file)",
    )
    parser.add_argument("--start-year", type=int, default=None)
    parser.add_argument("--end-year", type=int, default=None)
    parser.add_argument("--db-path", default="store/bot.db")
    parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Score only; do not write SQLite",
    )
    args = parser.parse_args()
    config = load_config(args.config)
    if args.dry_run:
        from data.providers import (
            get_financial_statement_provider,
            get_price_provider,
            get_sector_provider,
        )

        price = get_price_provider(config)
        fs = get_financial_statement_provider(config)
        sector = get_sector_provider(config)
        print("quarterly_job dry-run OK")
        print(f"  price chain: {price.name}")
        print(f"  financials chain: {fs.name}")
        print(f"  sector: {sector.name}")
        return

    from data.universe import resolve_tickers

    universe_file = args.universe_file or (config.get("universe") or {}).get("file")
    tickers = resolve_tickers(
        tickers_csv=args.tickers,
        universe_file=universe_file or None,
    )
    if not tickers:
        raise SystemExit(
            "Provide --tickers VNM,FPT or --universe-file data/universe/vn30_sample.csv "
            "(plus --start-year / --end-year)."
        )
    if args.start_year is None or args.end_year is None:
        raise SystemExit("--start-year and --end-year are required")

    print(f"quarterly_job: {len(tickers)} tickers", flush=True)
    result = run(
        config,
        tickers=tickers,
        start_year=args.start_year,
        end_year=args.end_year,
        db_path=args.db_path,
        persist=not args.no_persist,
        fetch_live=True,
    )
    print(result["results"].to_string(index=False))


if __name__ == "__main__":
    main()
