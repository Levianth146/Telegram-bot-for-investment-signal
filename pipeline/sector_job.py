"""Job refresh ``store.sector_mapping`` (monthly cadence — config sector_classification).

Pure path accepts prepared mapping rows; live path pulls via ``data.providers``
sector chain (network).
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from data.providers import get_sector_provider
from store import repository


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else Path("pipeline/config.yaml")
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_sector_overrides(
    path: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Đọc ``data/universe/sector_overrides.csv`` — ưu tiên hơn nhãn provider UNKNOWN."""
    import csv

    csv_path = Path(path) if path else Path("data/universe/sector_overrides.csv")
    if not csv_path.is_file():
        return {}
    out: dict[str, dict[str, Any]] = {}
    with csv_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            ticker = str(row.get("ticker") or "").strip().upper()
            if not ticker:
                continue
            out[ticker] = {
                "ticker": ticker,
                "market": (row.get("market") or "").strip() or None,
                "sector": (row.get("sector") or row.get("industry") or "UNKNOWN").strip(),
                "industry": (row.get("industry") or "UNKNOWN").strip(),
                "subindustry": (row.get("subindustry") or "").strip() or None,
            }
    return out


def apply_sector_overrides(
    rows: list[dict[str, Any]],
    *,
    updated_at: str,
    overrides: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Ghi đè / bổ sung ngành từ CSV overrides (tránh UNKNOWN lâu dài)."""
    ov = overrides if overrides is not None else load_sector_overrides()
    if not ov:
        return rows
    by_ticker = {str(r.get("ticker", "")).upper(): dict(r) for r in rows}
    for ticker, info in ov.items():
        by_ticker[ticker] = {
            "ticker": ticker,
            "market": info.get("market"),
            "sector": info.get("sector") or "UNKNOWN",
            "industry": info.get("industry") or "UNKNOWN",
            "subindustry": info.get("subindustry"),
            "updated_at": updated_at,
        }
    return list(by_ticker.values())


def industry_to_mapping_row(
    ticker: str, info: dict[str, Any] | None, *, updated_at: str
) -> dict[str, Any] | None:
    """Normalize provider industry payload → sector_mapping row."""
    if not info:
        return None
    industry = info.get("industry_name") or info.get("industry")
    if not industry:
        return None
    from data.universe import normalize_exchange

    market = normalize_exchange(
        info.get("market") or info.get("exchange") or info.get("board")
    )
    return {
        "ticker": ticker.strip().upper(),
        # Chỉ ghi HOSE/HNX/UPCOM khi nhận diện được — tránh "VN" mơ hồ
        "market": market or None,
        # V1: KBS often only has industry_name — reuse as sector until ICB levels land
        "sector": info.get("sector") or industry,
        "industry": industry,
        "subindustry": info.get("sub_industry") or info.get("subindustry"),
        "updated_at": updated_at,
    }


def run(
    config: dict,
    *,
    tickers: list[str] | None = None,
    mapping_rows: list[dict] | None = None,
    db_path: str = "store/bot.db",
    fetch_live: bool = False,
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Upsert sector_mapping for tickers (from args, watchlist, or prepared rows)."""
    sc = config.get("sector_classification") or {}
    if sc.get("enabled") is False:
        return {"rows": [], "note": "sector_classification.enabled=false"}

    updated_at = as_of_date or date.today().isoformat()
    rows = list(mapping_rows or [])

    if not rows:
        universe = [t.strip().upper() for t in (tickers or []) if t.strip()]
        if not universe:
            conn = repository.get_connection(db_path)
            try:
                repository.init_schema(conn)
                universe = repository.get_watchlist(conn)
            finally:
                conn.close()
        if not universe:
            return {"rows": [], "note": "empty ticker universe"}

        if fetch_live:
            from data.universe.exchanges import (
                enrich_industry_info_with_exchange,
                load_symbol_exchange_map,
            )

            exchange_map = load_symbol_exchange_map()
            sector = get_sector_provider(config)
            for ticker in universe:
                try:
                    info = sector.get_industry(ticker)
                except Exception:  # noqa: BLE001
                    info = None
                info = enrich_industry_info_with_exchange(
                    ticker, info, exchange_map=exchange_map
                )
                # Industry thiếu nhưng đã biết sàn → vẫn ghi market để filter exchange
                if info is None and ticker in exchange_map:
                    info = {
                        "industry_name": "UNKNOWN",
                        "market": exchange_map[ticker],
                        "exchange": exchange_map[ticker],
                    }
                mapped = industry_to_mapping_row(ticker, info, updated_at=updated_at)
                if mapped:
                    rows.append(mapped)
        else:
            raise NotImplementedError(
                "Pass mapping_rows=... or set fetch_live=True (network)."
            )

    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        rows = apply_sector_overrides(rows, updated_at=updated_at)
        repository.upsert_sector_mapping(conn, rows)
    finally:
        conn.close()

    return {"rows": rows, "note": f"upserted {len(rows)} sector_mapping rows"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--db-path", default="store/bot.db")
    parser.add_argument("--tickers", default="", help="Comma-separated; default=watchlist")
    parser.add_argument(
        "--universe-file",
        default="",
        help=(
            "CSV of tickers (when --tickers empty; else "
            "config universe.fundamental_file / universe.file)"
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    if args.dry_run:
        sector = get_sector_provider(config)
        print("sector_job dry-run OK")
        print(f"  sector provider: {sector.name}")
        print(f"  enabled: {(config.get('sector_classification') or {}).get('enabled', True)}")
        return

    from data.universe import (
        filter_tickers_for_config,
        fundamental_universe_file,
        resolve_tickers,
    )

    universe_file = args.universe_file or fundamental_universe_file(config)
    tickers = resolve_tickers(
        tickers_csv=args.tickers,
        universe_file=universe_file or None,
    )
    if tickers:
        tickers, dropped = filter_tickers_for_config(
            tickers, config, db_path=args.db_path
        )
        if dropped:
            print(
                f"sector_job: dropped {len(dropped)} by exchange: "
                f"{', '.join(dropped)}",
                flush=True,
            )
    result = run(
        config,
        tickers=tickers or None,
        db_path=args.db_path,
        fetch_live=True,
    )
    print(result["note"])


if __name__ == "__main__":
    main()
