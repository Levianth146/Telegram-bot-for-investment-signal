"""Upsert sector_overrides vào store — không gọi network (tránh treo full VN100)."""
from __future__ import annotations

from datetime import date

from pipeline.sector_job import load_config, load_sector_overrides, run

cfg = load_config()
ov = load_sector_overrides()
updated = date.today().isoformat()
rows = [
    {
        "ticker": t,
        "market": info.get("market"),
        "sector": info.get("sector") or "UNKNOWN",
        "industry": info.get("industry") or "UNKNOWN",
        "subindustry": info.get("subindustry"),
        "updated_at": updated,
    }
    for t, info in ov.items()
]
result = run(
    cfg,
    mapping_rows=rows,
    db_path="store/bot.db",
    fetch_live=False,
)
print(result["note"], "overrides", len(ov))
