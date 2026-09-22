"""Readonly E2E audit spot-check — không ghi store."""
from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml
from data.universe import load_universe_tickers

DB = Path("store/bot.db")
c = sqlite3.connect(f"file:{DB.as_posix()}?mode=ro", uri=True)


def show(label: str, sql: str) -> None:
    rows = c.execute(sql).fetchall()
    print(f"{label}: {rows}")


print("=== A Data/PIT ===")
show(
    "fund filed_at",
    "select filed_at, count(*) n from fundamental_scores group by 1 order by 1",
)
show(
    "wl as_of",
    "select as_of_date, count(*) n from watchlist group by 1 order by 1",
)
show("sector_mapping n", "select count(*) n from sector_mapping")
show(
    "signals max",
    "select max(date) d, count(distinct ticker) n from signals",
)
show(
    "n2027 fund",
    "select count(*) n from fundamental_scores where filed_at like '2027%'",
)
show(
    "n2027 wl",
    "select count(*) n from watchlist where as_of_date like '2027%'",
)

vn = set(load_universe_tickers("data/universe/vn100.csv"))
max_filed = c.execute("select max(filed_at) from fundamental_scores").fetchone()[0]
fund = {
    r[0]
    for r in c.execute(
        "select distinct ticker from fundamental_scores where filed_at=?",
        (max_filed,),
    )
}
sec = {r[0] for r in c.execute("select distinct ticker from sector_mapping")}
print(f"max_filed={max_filed} vn100={len(vn)} fund={len(fund)} overlap={len(vn & fund)}")
print(f"missing_fund ({len(vn - fund)}): {sorted(vn - fund)}")
print(
    f"sector cover vn100={len(vn & sec)} missing_sector ({len(vn - sec)}): "
    f"{sorted(vn - sec)}"
)
print(
    "VCB fund",
    c.execute(
        "select filed_at, fundamental_view from fundamental_scores where ticker='VCB'"
    ).fetchall(),
)
print(
    "VCB sector",
    c.execute(
        "select industry, market from sector_mapping where ticker='VCB'"
    ).fetchall(),
)
print(
    "SSI sector",
    c.execute(
        "select industry, market from sector_mapping where ticker='SSI'"
    ).fetchall(),
)
print(
    "FPT sector",
    c.execute(
        "select industry, market from sector_mapping where ticker='FPT'"
    ).fetchall(),
)
show("wl views", "select fundamental_view, count(*) n from watchlist group by 1")

cols = [r[1] for r in c.execute("pragma table_info(fundamental_scores)")]
print("fund columns:", cols)

fail = c.execute(
    """
    select ticker, fundamental_view, substr(coalesce(headline_json,''),1,220)
    from fundamental_scores
    where filed_at=? and upper(fundamental_view)='FAIL'
    limit 3
    """,
    (max_filed,),
).fetchall()
print("FAIL samples", fail)

pass_n = c.execute(
    "select count(*) from fundamental_scores where filed_at=? and upper(fundamental_view)='PASS'",
    (max_filed,),
).fetchone()[0]
print("PASS@max", pass_n)

for t in ("FPT", "VCB", "SSI", "VNM"):
    n = c.execute("select count(*) from price_bars where ticker=?", (t,)).fetchone()[0]
    print(f"price_bars {t}", n)

print("=== Config ===")
cfg = yaml.safe_load(Path("pipeline/config.yaml").read_text(encoding="utf-8"))
qe = cfg.get("quant_engine") or {}
ff = cfg.get("fundamental_filter") or {}
bt = cfg.get("backtest") or {}
for k in [
    "regime_markov",
    "alpha_kalman_trend",
    "risk_garch",
    "portfolio_black_litterman",
    "probabilistic_monte_carlo",
    "probabilistic_hawkes",
]:
    b = qe.get(k) or {}
    print(k, "enabled=", b.get("enabled") if isinstance(b, dict) else b)
print("exclude_financials", ff.get("exclude_financials"))
print("merton", (ff.get("safety_merton_dd") or {}).get("enabled"))
print("wf", bt.get("walk_forward"))
print("checks", bt.get("checks"))
print(
    "metrics cvar/regime",
    {
        k: (bt.get("metrics") or {}).get(k)
        for k in ("cvar95_calibration", "regime_conditional_sharpe")
    },
)
print("universe", cfg.get("universe"))
print("min_industry_peers", ff.get("min_industry_peers"))
show("subscribers", "select count(*) n from subscribers")
show(
    "backtest scopes",
    "select scope, count(*) n from backtest_results group by 1",
)

c.close()
print("DONE")
