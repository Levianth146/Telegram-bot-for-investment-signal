"""Readonly: remaining VN100 missing sector after overrides."""
from __future__ import annotations

import sqlite3

from data.ingest.scoring_frames import is_excluded_financial
from data.universe import load_universe_tickers

vn = set(load_universe_tickers("data/universe/vn100.csv"))
c = sqlite3.connect("file:store/bot.db?mode=ro", uri=True)
sec = {r[0] for r in c.execute("select ticker from sector_mapping")}
print("sector_mapping n", len(sec))
print("vcb", c.execute("select industry from sector_mapping where ticker='VCB'").fetchone())
print("ssi", c.execute("select industry from sector_mapping where ticker='SSI'").fetchone())
missing = sorted(vn - sec)
non_fin = [t for t in missing if not is_excluded_financial(t, None)]
print("missing total", len(missing))
print("missing non_fin", len(non_fin), non_fin)
# batch12
for i in range(0, len(non_fin), 12):
    print(f"BATCH{i//12+1}", ",".join(non_fin[i : i + 12]))
c.close()
