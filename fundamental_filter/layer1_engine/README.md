# Fintech Stock Bot — Fundamental Layer engine (`layer1_engine/`)

Implementation package behind the public facade in
`fundamental_filter/{growth,quality,safety,valuation,scoring}.py`.

**Contract:** read [`../README.md`](../README.md) first (facade vs engine).

Follows the framework: Growth → Quality → Safety → Valuation →
Fundamental Score → PASS/WATCH/FAIL watchlist (mục 9.2).

## Pure path vs I/O path

| Path | Entry | Network |
|---|---|---|
| **Pure (repo contract)** | `score_current_universe`, `classify_fundamental_universe`, `to_store_records`, `load_scoring_config` | No — callers pass prepared DataFrames |
| **Live / transitional** | `analyze_fundamental_universe` | Yes — DNSE/vnstock still here until `data/` providers land |

CONTRIBUTING: production pipeline must feed the pure path from `data/`.
The live path is diagnostic / bootstrap only.

## Architecture (repo)

```text
data/ (point-in-time BCTC)  --or--  layer1 I/O transitional
  -> scoring DataFrames
  -> score_current_universe   # metric / module / fundamental
  -> classify PASS/WATCH/FAIL # thresholds from pipeline/config.yaml
  -> to_store_records         # shape for store.fundamental_scores + watchlist
  -> store/ (via repository; upserts still TODO)
```

Classification thresholds sync with `pipeline/config.yaml`
(`scoring.pass_percentile` / `scoring.fail_percentile`).

## Setup — Windows PowerShell (from repo root)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
# Optional live I/O deps:
pip install -r fundamental_filter/layer1_engine/requirements.txt
Copy-Item fundamental_filter/layer1_engine/.env.example fundamental_filter/layer1_engine/.env
```

## Run

Prefer package entry (repo root):

```powershell
python -m fundamental_filter.layer1_engine VNM,FPT,VHE 2021 2025
python -m fundamental_filter.layer1_engine VNM,FPT,VHE 2021 2025 --debug
```

Public formulas (no network):

```powershell
python -c "from fundamental_filter import growth; print(growth.revenue_growth_yoy(120, 100))"
```

## Tests

From repo root:

```powershell
python -m pytest fundamental_filter/tests -q
python -m unittest fundamental_filter.layer1_engine.test_safety_scoring `
  fundamental_filter.layer1_engine.test_systemic_fundamental `
  fundamental_filter.layer1_engine.test_fundamental_refactor -v
```

Regression fixtures: `tests/fixtures/fundamental_baseline.json` plus optional
`scoring_input_*.csv` (refactor suite skips if CSVs were not merged).
Valuation PIT tests need `fundamental_filter/layer1_engine/requirements.txt`
deps and run via:
`python -m unittest fundamental_filter.layer1_engine.test_valuation_point_in_time`.

Regression / systemic / safety tests use frozen inputs and do not call network.

## Outputs

Production default CSVs (live/diagnostic runs):

- `outputs/fundamental_results.csv`
- `outputs/fundamental_metrics.csv`

Store-shaped records (for pipeline):

```python
from fundamental_filter.layer1_engine import to_store_records
records = to_store_records(results_df)
# records["fundamental_scores"], records["watchlist"]
```

## Data limitations

- Sub-industry may be missing → peer selector industry fallback.
- Publication date / historical shares incomplete for many tickers.
- Historical valuation never fabricated; marked unavailable when not PIT-safe.
- Network vendors affect live runs only; pure-path tests do not.
