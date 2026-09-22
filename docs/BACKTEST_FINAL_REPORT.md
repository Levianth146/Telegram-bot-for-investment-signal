# BACKTEST FINAL REPORT — VN100 Framework Fix

**Date:** 2026-09-22  
**Status:** Correctness fixes shipped; smoke run documented; full VN100 daily+fund may be long-running.

## A. Research setup

| Item | Value |
|---|---|
| Universe | `data/universe/vn100.csv` (CLI `--universe vn100`) |
| Survivorship | **Fixed/current VN100** — not historical constituents |
| Exclusions | Financials via FF industry gate (framework V1) when fundamentals on |
| OOS window | ~6 months (`--oos-start` / `--oos-end`) |
| Warm-up | `--warmup-years` (default 3) before OOS for Markov/GARCH/Kalman |
| Quant cadence | `signal_every=1` (daily) for final; smoke may use 5/21 |
| Execution | **Close T+1** (policy locked) |
| Risk sizing | **Inverse-vol normalize → `w_max` cap** (Option B); config `sigma_target`/`w_max` **unchanged** |
| Costs | buy half RT fee; sell tax + half RT; B0/B1/B2 same ledger |
| T+2 | Sell blocked until ≥2 sessions held |
| Price limit | HOSE ±7% (config `limit_pct`) |
| PIT lag | Assumed filing lag **90d** if no real `filed_at` |
| Price type | Provider `close` series (cache under `data/cache/`) |

## B. Bugs found → fixed

| Issue | File | Root cause | Fix | Test | Impact |
|---|---|---|---|---|---|
| I3 Schema | `backtest/engine.py` `_active_watchlist` | Only `classification`; Quant reads `fundamental_view` | Alias both + module scores | `test_fundamental_view_schema_in_watchlist` | WATCH capped correctly in BT |
| I1 Stop | `backtest/engine.py` | Quant could overwrite stop | `_RISK_OVERRIDE_REASONS` hard guard | `test_stop_overrides_*` | Stop sticks |
| I11 FAIL hold | `backtest/engine.py` | “keep until SELL” stuck | `fundamental_fail_exit` T+1 | `test_fundamental_fail_exit_while_holding` | Forced exit |
| I4 Ablation FF | `backtest/ablation.py` | Watchlist @ `end_date` BH | `_dynamic_fundamental_result` PIT daily | `test_dynamic_fundamental_no_end_date_leak` | No look-ahead FF layer |
| I12 B1/B2 costs | `backtest/ablation.py` | Vectorized gross only | Same fee + T+1 cost on Δpos | `test_b1_b2_*` net≤gross | Fair baselines |
| I8 OU | `quant_engine/signal_engine.py` | BUY needed bull while OU is neutral | Regime-aware `_decide_action` | `test_ou_neutral_buy_and_bear_no_buy` | OU can BUY in neutral |
| I7 Risk | `quant_engine/risk/garch.py` | `min(w_max, σ_t/σ̂)` saturates | `inverse_vol_normalize_weights` | `test_inverse_vol_normalize_monotonic` | σ↑→weight↓ |
| I9/I10 Markov | `quant_engine/regime.py` | Non-converge used; turbulent=middle mean | Reject MLE; turbulent=max σ² | `test_markov_nonconverged_*`, `test_label_states_*` | Semantic regime |
| I14 Regime Sharpe | `backtest/metrics.py` | Flag off → `None` | Research force + `N/A (n < min)` display | existing + display keys | No literal None |

**Not changed (locked):** `bull_threshold`, `sigma_target`, `w_max`, denser Sharpe **−0.84** log in DECISIONS.

## C. Metrics (smoke subset — not full VN100)

Artifact: `store/backtest_final_vn100_smoke.json`  
Setup: FPT,VNM,GAS · OOS 2025-06-01→2025-09-01 · warmup from 2024-06 · `signal_every=5` · **no-fundamentals** · Close T+1.

| Strategy | Total Return | CAGR | Sharpe | Max DD | n_trades | Avg exposure | Cost drag |
|---|---:|---:|---:|---:|---:|---:|---:|
| B0 | +5.2% | +22.1% | +1.28 | −6.8% | 0 | — | 0.42% |
| B1 | −1.1% | −4.4% | −0.40 | −5.2% | 7 | — | 0.76% |
| B2 | ~0% | ~0% | — | 0% | 0 | — | 0% |
| Framework | +2.0% | +8.1% | +2.45 | −1.3% | 7 | 15% | — |
| VN-Index | +25.6% | — | +5.28 | −4.4% | — | — | — |

Regime Sharpe displays: `bull=N/A (n < 5)` / `bear=N/A (n < 5)` / `neutral=N/A (n < 5)` — **no literal None**.

**Honest caveat:** Framework smoke Sharpe positive on 3 names / 3 months / no FF / every-5-days is **not** evidence of VN100 daily+fundamental edge. Ablation on the same OOS calendar without long warmup still shows **alpha→risk drag** (risk step Sharpe ≈ −0.50). Denser prior OOS Sharpe **−0.84** remains the documented full-protocol stress log.

## D. Charts

Generate under `outputs/backtest/` or `store/charts/` when plotting helpers available. Required set:

1. Equity B0/B1/B2/Framework (aligned OOS, rebase 1.0)  
2. Framework drawdown  
3. Rolling Sharpe 126 (note if OOS short)  
4. Regime-conditional (display N/A not None)  
5. Exposure / cash  
6. Ablation bar Sharpe/CAGR/MDD  

## E. Ablation

Dynamic PIT Fundamental → Regime → Alpha → Risk (see JSON `ablation_steps`).

## F. Interpretation

Post-fix OOS numbers are **not** cooked. If Framework Total Return / Sharpe remain negative while MDD stays relatively controlled:

> Strategy controls downside but does not yet demonstrate positive out-of-sample alpha.

Denser historical log Sharpe **−0.84** (12 tickers, no-fund, `signal_every=21`) remains in `docs/DECISIONS.md` as a valid prior finding — not deleted.

## G. Limitations

- Fixed current VN100 → survivorship bias  
- Assumed 90d filing lag  
- Community OHLCV ~8y cap may truncate warm-up  
- Daily Markov MLE per session is CPU-heavy; non-converge → heuristic  
- Smoke ≠ full VN100 + fundamentals proof  
- Corporate-action audit (I13) deferred P2  

## Reproduce

### Smoke (CLI + metrics proof)

```powershell
cd d:\Projects\Telegram-bot-for-investment-signal
python scripts/run_backtest_report.py `
  --tickers FPT,VNM,GAS `
  --oos-start 2025-03-01 --oos-end 2025-09-01 `
  --warmup-years 2 --signal-every 5 `
  --no-fundamentals --no-walk-forward --no-persist-store `
  --out-json store/backtest_final_vn100_smoke.json `
  --out-xlsx store/backtest_final_vn100_smoke.xlsx
```

### Full VN100 final (long; daily + fundamentals)

```powershell
cd d:\Projects\Telegram-bot-for-investment-signal
python scripts/run_backtest_report.py `
  --universe vn100 --with-fundamentals `
  --signal-every 1 `
  --oos-start 2025-03-22 --oos-end 2025-09-22 `
  --warmup-years 3 --no-walk-forward `
  --out-json store/backtest_final_vn100_20260922.json `
  --out-xlsx store/backtest_final_vn100_20260922.xlsx
```

Lần 2 (warm): cùng lệnh — OHLCV CSV + `data/cache/scoring_schedule/{key}/year_*.pkl` hit → skip API fund theo năm đã có. Force rebuild: thêm `--refresh-fundamentals` hoặc `--refresh-data`.

**Speed note (2026-09-22):** FF event-driven precompute + year schedule cache + truncate/regime memo — **không** đổi logic/trades; denser Sharpe **−0.84** trong DECISIONS giữ nguyên. Profile: `scripts/profile_backtest_smoke.py` → `outputs/performance/profile_*.txt`.

### Unit tests

```powershell
python -m pytest backtest/tests/test_backtest.py quant_engine/tests/test_regime.py quant_engine/tests/test_signal_watch_cap.py -q
```
