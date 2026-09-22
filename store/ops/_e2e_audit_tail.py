"""Tail of E2E audit — UTF-8 stdout."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

c = sqlite3.connect("file:store/bot.db?mode=ro", uri=True)
print("FPT", c.execute("select industry, market from sector_mapping where ticker='FPT'").fetchall())
print("VNM", c.execute("select industry, market from sector_mapping where ticker='VNM'").fetchall())
print(
    "wl 2026-03-31",
    c.execute(
        "select fundamental_view, count(*) from watchlist where as_of_date='2026-03-31' group by 1"
    ).fetchall(),
)
print(
    "FAIL n",
    c.execute(
        "select count(*) from fundamental_scores where filed_at='2026-03-31' and upper(fundamental_view)='FAIL'"
    ).fetchone(),
)
row = c.execute(
    "select ticker, headline_json from fundamental_scores "
    "where filed_at='2026-03-31' and upper(fundamental_view)='FAIL' limit 1"
).fetchone()
if row:
    print("FAIL ticker", row[0])
    hj = row[1] or ""
    print("has value keys", '"value"' in hj, "len", len(hj))
    print("snippet", hj[:240])
print(
    "PASS sample",
    c.execute(
        "select ticker from fundamental_scores where filed_at='2026-03-31' "
        "and upper(fundamental_view)='PASS' limit 5"
    ).fetchall(),
)
print(
    "signals actions",
    c.execute(
        "select action, count(*) from signals where date=(select max(date) from signals) group by 1"
    ).fetchall(),
)
print("subs", c.execute("select count(*) from subscribers").fetchone())
print("scopes", c.execute("select scope, count(*) from backtest_results group by 1").fetchall())
cfg = yaml.safe_load(Path("pipeline/config.yaml").read_text(encoding="utf-8"))
print("BL", cfg["quant_engine"]["portfolio_black_litterman"]["enabled"])
print("MC", cfg["quant_engine"]["probabilistic_monte_carlo"]["enabled"])
print("wf", cfg["backtest"]["walk_forward"])
print("checks", cfg["backtest"]["checks"])
print(
    "cvar cal",
    cfg["backtest"]["metrics"]["cvar95_calibration"]["enabled"],
    "regime sharpe",
    cfg["backtest"]["metrics"]["regime_conditional_sharpe"]["enabled"],
)
c.close()
