"""Ablation ngắn GARCH refit_every_n: N=1 vs N=5 vs N=21.

So Sharpe / max_drawdown / n_trades trên cùng cửa sổ OOS.
Ngưỡng chấp nhận N=5: |ΔSharpe vs N=1| ≤ min_sharpe_improvement_oos (0.10).

Ví dụ::

  python scripts/ablation_garch_refit_n.py --synthetic
  python scripts/ablation_garch_refit_n.py --tickers FPT,VNM,HPG,GAS --start-date 2024-01-01 --no-fundamentals
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from copy import deepcopy
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SHARPE_KEEP_DELTA = 0.10  # đồng bộ docs/DECISIONS.md / ablation


def _synthetic_closes(n_tickers: int = 4, n_days: int = 160):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2024-01-02", periods=n_days).strftime("%Y-%m-%d").tolist()
    tickers = ["FPT", "VNM", "HPG", "GAS", "MWG", "REE"][:n_tickers]
    closes: dict = {}
    for i, t in enumerate(tickers):
        walk = 100.0 + i * 3.0 + np.cumsum(rng.normal(0.04, 1.2, size=n_days))
        closes[t] = __import__("pandas").Series(walk, index=dates, name="close")
    closes["VNINDEX"] = __import__("pandas").Series(
        1000.0 + np.cumsum(rng.normal(0.02, 0.9, size=n_days)),
        index=dates,
        name="close",
    )
    return closes, tickers, dates[0], dates[-1]


def _minimal_config(refit_every_n, *, parallel_workers=1) -> dict:
    return {
        "quant_engine": {
            "benchmark": "VNINDEX",
            "sigma_target": 0.02,
            "w_max": 0.10,
            "stop_k": 2.0,
            "bull_threshold": 0.55,
            "bear_threshold": 0.35,
            "min_slope_tstat": 1.0,
            "parallel_workers": parallel_workers,
            "regime_markov": {"enabled": True},
            "alpha_kalman_trend": {"enabled": True},
            "alpha_ou_meanreversion": {"enabled": False},
            "risk_garch": {
                "enabled": True,
                "refit_every_n": refit_every_n,
            },
            "portfolio_black_litterman": {"enabled": False},
            "probabilistic_monte_carlo": {"enabled": False},
            "probabilistic_hawkes": {"enabled": False},
        },
        "backtest": {
            "cost": {
                "tax_sell_pct": 0.001,
                "fee_roundtrip_pct": 0.003,
                "limit_pct": 0.07,
            }
        },
    }


def _metrics_row(result: dict, *, n: int | None, elapsed: float) -> dict:
    m = dict(result.get("metrics") or {})
    return {
        "refit_every_n": n,
        "sharpe": m.get("sharpe"),
        "max_drawdown": m.get("max_drawdown"),
        "n_trades": m.get("n_trades"),
        "cagr": m.get("cagr"),
        "elapsed_sec": round(float(elapsed), 2),
    }


def _decide(rows: list[dict]) -> dict:
    by_n = {r["refit_every_n"]: r for r in rows}
    base = by_n.get(1) or by_n.get(None)
    n5 = by_n.get(5)
    if base is None or n5 is None:
        return {
            "decision": "keep_null",
            "reason": "thiếu metric N=1 hoặc N=5",
            "config_refit_every_n": None,
        }
    s1 = float(base.get("sharpe") or 0.0)
    s5 = float(n5.get("sharpe") or 0.0)
    delta = s5 - s1
    ok = abs(delta) <= SHARPE_KEEP_DELTA
    if ok:
        return {
            "decision": "set_n5",
            "reason": (
                f"|dSharpe|={abs(delta):.4f} <= {SHARPE_KEEP_DELTA} "
                f"(N1={s1:.4f}, N5={s5:.4f}) — chap nhan N=5"
            ),
            "config_refit_every_n": 5,
            "delta_sharpe_n5_vs_n1": round(delta, 4),
        }
    return {
        "decision": "keep_null",
        "reason": (
            f"|dSharpe|={abs(delta):.4f} > {SHARPE_KEEP_DELTA} "
            f"(N1={s1:.4f}, N5={s5:.4f}) — giu null (N=1)"
        ),
        "config_refit_every_n": None,
        "delta_sharpe_n5_vs_n1": round(delta, 4),
    }


def main(argv: list[str] | None = None) -> int:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    parser = argparse.ArgumentParser(description="Ablation GARCH refit_every_n")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--tickers", default="FPT,VNM,HPG,GAS")
    parser.add_argument("--start-date", default="2024-01-01")
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--signal-every", type=int, default=5)
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--no-fundamentals", action="store_true", default=True)
    parser.add_argument("--parallel-workers", type=int, default=1)
    parser.add_argument(
        "--out-json",
        default="store/ablation_garch_refit_n.json",
    )
    args = parser.parse_args(argv)

    from backtest.engine import run_backtest

    ns = [1, 5, 21]
    rows: list[dict] = []

    if args.synthetic:
        closes, tickers, start, end = _synthetic_closes()
        print(
            f"garch_refit_ablation synthetic tickers={tickers} "
            f"window={start}..{end} signal_every={args.signal_every}",
            flush=True,
        )
        for n in ns:
            refit = None if n == 1 else n
            cfg = _minimal_config(
                refit, parallel_workers=args.parallel_workers
            )
            t0 = time.perf_counter()
            result = run_backtest(
                cfg,
                start,
                end,
                close_by_ticker=closes,
                scoring_schedule=None,
                signal_tickers=tickers,
                signal_every_n_days=max(int(args.signal_every), 1),
            )
            elapsed = time.perf_counter() - t0
            row = _metrics_row(result, n=n, elapsed=elapsed)
            rows.append(row)
            print(
                f"  N={n}: sharpe={row['sharpe']} mdd={row['max_drawdown']} "
                f"n_trades={row['n_trades']} elapsed={row['elapsed_sec']}s",
                flush=True,
            )
    else:
        from backtest.ablation import _load_config, load_close_by_ticker

        end = args.end_date or date.today().isoformat()
        tickers = [
            t.strip().upper()
            for t in str(args.tickers).split(",")
            if t.strip()
        ]
        base_cfg = _load_config(args.config)
        print(
            f"garch_refit_ablation tickers={tickers} "
            f"window={args.start_date}..{end}",
            flush=True,
        )
        closes = load_close_by_ticker(
            tickers,
            args.start_date,
            end,
            base_cfg,
            include_benchmark=True,
        )
        if not closes:
            print("No OHLCV loaded", flush=True)
            return 1
        signal_tickers = [
            t for t in tickers if t in closes and t != "VNINDEX"
        ]
        for n in ns:
            cfg = deepcopy(base_cfg)
            q = dict(cfg.get("quant_engine") or {})
            rg = dict(q.get("risk_garch") or {})
            rg["enabled"] = True
            rg["refit_every_n"] = None if n == 1 else n
            q["risk_garch"] = rg
            q["parallel_workers"] = int(args.parallel_workers)
            # Tắt MC/BL — chỉ đo GARCH cadence.
            for key in (
                "portfolio_black_litterman",
                "probabilistic_monte_carlo",
                "probabilistic_hawkes",
            ):
                q[key] = {**(q.get(key) or {}), "enabled": False}
            cfg["quant_engine"] = q
            t0 = time.perf_counter()
            result = run_backtest(
                cfg,
                args.start_date,
                end,
                close_by_ticker=closes,
                scoring_schedule=None,
                signal_tickers=signal_tickers,
                signal_every_n_days=max(int(args.signal_every), 1),
            )
            elapsed = time.perf_counter() - t0
            row = _metrics_row(result, n=n, elapsed=elapsed)
            rows.append(row)
            print(
                f"  N={n}: sharpe={row['sharpe']} mdd={row['max_drawdown']} "
                f"n_trades={row['n_trades']} elapsed={row['elapsed_sec']}s",
                flush=True,
            )

    decision = _decide(rows)
    out = {
        "rows": rows,
        "decision": decision,
        "threshold_abs_delta_sharpe": SHARPE_KEEP_DELTA,
        "mode": "synthetic" if args.synthetic else "ohlcv",
    }
    out_path = ROOT / args.out_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(out, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    print(json.dumps(decision, ensure_ascii=False, indent=2), flush=True)
    print(f"wrote {out_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
