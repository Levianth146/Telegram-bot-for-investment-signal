"""Controlled ticker universes for pipeline jobs (not full HOSE/HNX/UPCOM listing)."""

from __future__ import annotations

from pathlib import Path


def load_universe_tickers(path: str | Path) -> list[str]:
    """Load unique uppercase tickers from a one-column CSV (header optional).

    Accepts a ``ticker`` header or a bare list of codes (one per line).
    Blank lines and ``#`` comments are ignored.
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


def resolve_tickers(
    *,
    tickers_csv: str = "",
    universe_file: str | Path | None = None,
) -> list[str]:
    """Prefer ``--tickers`` comma list; else load ``--universe-file``."""
    from_cli = [t.strip().upper() for t in str(tickers_csv).split(",") if t.strip()]
    if from_cli:
        return list(dict.fromkeys(from_cli))
    if universe_file:
        return load_universe_tickers(universe_file)
    return []
