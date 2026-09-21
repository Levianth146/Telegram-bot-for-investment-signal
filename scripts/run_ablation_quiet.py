"""Ablation + walk-forward với stdout im lặng (tránh dump fundamental hàng MB).

Ví dụ:
  python scripts/run_ablation_quiet.py --tickers FPT,VNM,HPG,GAS --walk-forward
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from datetime import date
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser(description="Quiet ablation + optional walk-forward")
    parser.add_argument("--config", default="pipeline/config.yaml")
    parser.add_argument("--tickers", default="FPT,VNM,HPG,GAS")
    parser.add_argument("--start-date", default="2022-01-01")
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--signal-every", type=int, default=42)
    parser.add_argument("--lookback-years", type=int, default=5)
    parser.add_argument("--db-path", default="store/bot.db")
    parser.add_argument("--out-json", default="store/ablation_vn30_scale.json")
    parser.add_argument("--walk-forward", action="store_true")
    parser.add_argument("--no-fundamentals", action="store_true")
    args = parser.parse_args(argv)

    from backtest import ablation as abl
    from backtest.ablation import (
        SHARPE_KEEP_DELTA,
        _benchmark_ticker,
        _json_safe,
        _load_config,
        _set_quant_flags,
        _signal_closes,
        build_scoring_schedule,
        decide_keep_cut,
        load_close_by_ticker,
        run_ablation,
    )

    end = args.end_date or date.today().isoformat()
    tickers = [t.strip().upper() for t in str(args.tickers).split(",") if t.strip()]
    config = _load_config(args.config)
    print(f"quiet_ablation: tickers={tickers} window={args.start_date}..{end}", flush=True)

    sink = io.StringIO()
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        closes = load_close_by_ticker(
            tickers, args.start_date, end, config, include_benchmark=True
        )
    if not closes:
        print("No OHLCV loaded", flush=True)
        return 1
    signal_names = sorted(_signal_closes(closes, config))
    print(
        f"loaded closes={sorted(closes)} signal_universe={signal_names} "
        f"benchmark={_benchmark_ticker(config)}",
        flush=True,
    )

    scoring_schedule = None
    if not args.no_fundamentals:
        print("building scoring_schedule (stdout suppressed)…", flush=True)
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            scoring_schedule = build_scoring_schedule(
                tickers,
                args.start_date,
                end,
                config,
                lookback_years=max(int(args.lookback_years), 1),
                db_path=args.db_path,
            )
        print(
            f"scoring_schedule keys={sorted(scoring_schedule)} "
            f"n_years={len(scoring_schedule)}",
            flush=True,
        )

    print("run_ablation layers…", flush=True)
    with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        raw = run_ablation(
            config,
            close_by_ticker=closes,
            start_date=args.start_date,
            end_date=end,
            scoring_schedule=scoring_schedule,
            signal_every_n_days=max(int(args.signal_every), 1),
        )
    steps = decide_keep_cut(raw["steps"])
    for s in steps:
        print(
            f"  {s['layer']}: sharpe={_json_safe(s.get('sharpe'))} "
            f"delta={_json_safe(s.get('delta_sharpe'))} "
            f"n_trades={s.get('n_trades')} decision={s.get('decision')}",
            flush=True,
        )

    walk_forward_payload = None
    if args.walk_forward:
        from backtest.walk_forward import run_walk_forward

        print("walk_forward…", flush=True)
        wf_cfg = _set_quant_flags(config, regime=True, alpha=True, risk=True)
        with contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            wf = run_walk_forward(
                wf_cfg,
                args.start_date,
                end,
                close_by_ticker=closes,
                scoring_schedule=scoring_schedule,
                signal_every_n_days=max(int(args.signal_every), 1),
                signal_tickers=list(signal_names),
            )
        wm = wf.get("metrics") or {}
        walk_forward_payload = {
            "n_folds": len(wf.get("folds") or []),
            "cagr": _json_safe(wm.get("cagr")),
            "sharpe": _json_safe(wm.get("sharpe")),
            "max_drawdown": _json_safe(wm.get("max_drawdown")),
            "n_trades": wm.get("n_trades"),
            "equity_curve": list(wf.get("equity_curve") or []),
            "folds": [
                {
                    "test_start": f.get("test_start"),
                    "test_end": f.get("test_end"),
                    "sharpe": _json_safe((f.get("metrics") or {}).get("sharpe")),
                    "cagr": _json_safe((f.get("metrics") or {}).get("cagr")),
                    "n_trades": (f.get("metrics") or {}).get("n_trades"),
                }
                for f in (wf.get("folds") or [])
            ],
        }
        print(
            f"walk_forward: folds={walk_forward_payload['n_folds']} "
            f"sharpe={walk_forward_payload['sharpe']} "
            f"n_trades={walk_forward_payload['n_trades']}",
            flush=True,
        )

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "start_date": args.start_date,
        "end_date": end,
        "tickers": tickers,
        "loaded": sorted(closes),
        "scoring_schedule_keys": sorted(scoring_schedule or {}),
        "with_fundamentals": not args.no_fundamentals,
        "signal_every": int(args.signal_every),
        "layers_order": raw["layers_order"],
        "sharpe_keep_delta": SHARPE_KEEP_DELTA,
        "steps": [
            {
                "layer": s["layer"],
                "cagr": _json_safe(s.get("cagr")),
                "sharpe": _json_safe(s.get("sharpe")),
                "max_drawdown": _json_safe(s.get("max_drawdown")),
                "win_rate": _json_safe(s.get("win_rate")),
                "n_trades": s.get("n_trades"),
                "delta_sharpe": _json_safe(s.get("delta_sharpe")),
                "decision": s.get("decision"),
                "equity_curve": list(s.get("equity_curve") or []),
            }
            for s in steps
        ],
        "walk_forward": walk_forward_payload,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"wrote {out_path}", flush=True)
    from backtest.ablation import persist_ablation_to_store

    persisted = persist_ablation_to_store(
        payload, db_path=args.db_path, run_id=out_path.stem, scope="portfolio"
    )
    print(f"store: {persisted.get('note')}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
