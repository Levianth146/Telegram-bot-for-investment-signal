"""Ops: missing sector vs overrides; n2027 hygiene check (readonly)."""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from data.universe import load_universe_tickers

vn = set(load_universe_tickers("data/universe/vn100.csv"))
c = sqlite3.connect("file:store/bot.db?mode=ro", uri=True)
sec = {r[0] for r in c.execute("select ticker from sector_mapping")}
ov: set[str] = set()
with Path("data/universe/sector_overrides.csv").open(encoding="utf-8") as handle:
    for row in csv.DictReader(handle):
        t = (row.get("ticker") or "").strip().upper()
        if t:
            ov.add(t)
missing = sorted(vn - sec)
print("missing", len(missing))
print("missing_in_overrides", sorted(set(missing) & ov))
print("missing_not_overrides_head", [t for t in missing if t not in ov][:40])
print(
    "n2027_fund",
    c.execute(
        "select count(*) from fundamental_scores where filed_at like '2027%'"
    ).fetchone()[0],
)
print(
    "n2027_wl",
    c.execute(
        "select count(*) from watchlist where as_of_date like '2027%'"
    ).fetchone()[0],
)
print(
    "filed_at_dist",
    c.execute(
        "select filed_at, count(*) from fundamental_scores group by 1 order by 1"
    ).fetchall(),
)
c.close()
