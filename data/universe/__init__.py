"""Controlled ticker universes for pipeline jobs (not full HOSE/HNX/UPCOM listing)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

# Fallback smoke khi config thiếu smoke_file
_DEFAULT_SMOKE_FILE = "data/universe/hose_liquid_35.csv"


def load_universe_tickers(path: str | Path) -> list[str]:
    """Đọc ticker duy nhất (uppercase) từ CSV một cột (header tuỳ chọn).

    Chấp nhận header ``ticker`` hoặc danh sách mã trần (một dòng một mã).
    Bỏ dòng trống và comment ``#``.
    """
    file_path = Path(path)
    if not file_path.is_file():
        raise FileNotFoundError(f"universe file not found: {file_path}")

    tickers: list[str] = []
    seen: set[str] = set()
    with file_path.open(encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            # CSV may be "ticker" header or "FPT" / "FPT,..."
            cell = line.split(",")[0].strip().strip('"').strip("'")
            if not cell or cell.lower() == "ticker":
                continue
            key = cell.upper()
            if key in seen:
                continue
            seen.add(key)
            tickers.append(key)
    return tickers


def fundamental_universe_file(config: Mapping[str, Any] | None) -> str | None:
    """Đường dẫn CSV Tier1 (Fundamental / OUT_OF_SCOPE).

    Ưu tiên ``universe.fundamental_file``, fallback ``universe.file``.
    """
    block = dict((config or {}).get("universe") or {})
    path = block.get("fundamental_file") or block.get("file")
    if not path:
        return None
    return str(path)


def smoke_universe_file(config: Mapping[str, Any] | None) -> str:
    """CSV smoke / ablation / fallback nhanh (mặc định hose_liquid_35)."""
    block = dict((config or {}).get("universe") or {})
    path = block.get("smoke_file") or _DEFAULT_SMOKE_FILE
    return str(path)


def quant_from_watchlist(config: Mapping[str, Any] | None) -> bool:
    """True nếu daily Quant chỉ lấy mã từ watchlist (không kéo full Tier1)."""
    block = dict((config or {}).get("universe") or {})
    # Mặc định True — khớp framework hai tầng
    if "quant_from_watchlist" not in block:
        return True
    return bool(block.get("quant_from_watchlist"))


def load_fundamental_universe(config: Mapping[str, Any] | None) -> list[str]:
    """Load danh sách ticker Tier1 từ config (fundamental_file / file)."""
    path = fundamental_universe_file(config)
    if not path:
        return []
    return load_universe_tickers(path)


def resolve_tickers(
    *,
    tickers_csv: str = "",
    universe_file: str | Path | None = None,
) -> list[str]:
    """Ưu tiên ``--tickers`` CSV; không có thì load ``--universe-file``."""
    from_cli = [t.strip().upper() for t in str(tickers_csv).split(",") if t.strip()]
    if from_cli:
        return list(dict.fromkeys(from_cli))
    if universe_file:
        return load_universe_tickers(universe_file)
    return []


def normalize_exchange(raw: str | None) -> str | None:
    """Chuẩn hoá mã sàn về HOSE / HNX / UPCOM; không nhận diện → None (giữ ticker)."""
    if raw is None:
        return None
    text = str(raw).strip().upper()
    if not text:
        return None
    aliases = {
        "HOSE": "HOSE",
        "HSX": "HOSE",
        "HCM": "HOSE",
        "HNX": "HNX",
        "UPCOM": "UPCOM",
        "UPC": "UPCOM",
    }
    if text in aliases:
        return aliases[text]
    if "UPCOM" in text:
        return "UPCOM"
    if text in {"HOSE", "HNX"}:
        return text
    # "VN", industry labels, v.v. → coi như chưa biết sàn
    return None


def allowed_exchanges_from_config(config: Mapping[str, Any] | None) -> list[str]:
    """Đọc ``universe.allowed_exchanges``; mặc định HOSE+HNX (loại UPCOM)."""
    block = dict((config or {}).get("universe") or {})
    raw = block.get("allowed_exchanges")
    if not raw:
        return ["HOSE", "HNX"]
    out: list[str] = []
    for item in raw:
        norm = normalize_exchange(str(item))
        if norm and norm not in out:
            out.append(norm)
    return out or ["HOSE", "HNX"]


def filter_tickers_by_exchange(
    tickers: list[str],
    *,
    market_by_ticker: Mapping[str, str | None],
    allowed_exchanges: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Lọc theo sàn đã map.

    - Không có mapping / market không nhận diện (vd ``VN``) → **giữ** (CSV curated).
    - Mapping = UPCOM hoặc sàn ngoài allow-list → **loại**.
    - Mapping HOSE/HNX (trong allow-list) → **giữ**.
    """
    allowed: set[str] = set()
    for item in allowed_exchanges or ["HOSE", "HNX"]:
        norm = normalize_exchange(str(item))
        if norm:
            allowed.add(norm)
    if not allowed:
        allowed = {"HOSE", "HNX"}
    kept: list[str] = []
    dropped: list[str] = []
    for raw in tickers:
        ticker = str(raw).strip().upper()
        if not ticker:
            continue
        exch = normalize_exchange(market_by_ticker.get(ticker))
        if exch is None:
            kept.append(ticker)
        elif exch in allowed:
            kept.append(ticker)
        else:
            dropped.append(ticker)
    return kept, dropped


def filter_tickers_for_config(
    tickers: list[str],
    config: Mapping[str, Any] | None,
    *,
    db_path: str = "store/bot.db",
) -> tuple[list[str], list[str]]:
    """Load ``sector_mapping.market`` rồi áp ``allowed_exchanges`` từ config."""
    from store import repository

    allowed = allowed_exchanges_from_config(config)
    cleaned = [str(t).strip().upper() for t in tickers if str(t).strip()]
    if not cleaned:
        return [], []

    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        markets = repository.get_markets_for_tickers(conn, cleaned)
    finally:
        conn.close()

    return filter_tickers_by_exchange(
        cleaned,
        market_by_ticker=markets,
        allowed_exchanges=allowed,
    )
