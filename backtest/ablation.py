"""Ablation study — bật/tắt từng tầng theo pipeline/config.yaml, đo đóng góp biên.

Tham chiếu: mục 4.2 (B0/B1/... -> +regime -> +alpha -> +risk) và mục 11.3
(tiêu chí giữ/cắt, ghi log vào docs/DECISIONS.md).

CLI: ``python -m backtest.ablation --tickers VNM,FPT --start-date 2019-01-01``
"""

from __future__ import annotations

import argparse
import json
from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any, Mapping

import yaml

from backtest.engine import run_backtest

# Cumulative stack: each step enables one more quant layer on top of previous.
DEFAULT_LAYERS = [
    "B0_buyhold",
    "fundamental",
    "regime",
    "alpha",
    "risk",
]

# Ngưỡng giữ tầng (docs/DECISIONS.md) — Sharpe biên vs bước trước.
SHARPE_KEEP_DELTA = 0.10


def _benchmark_ticker(config: Mapping[str, Any] | None) -> str | None:
    q = dict((config or {}).get("quant_engine") or {})
    raw = str(q.get("benchmark") or "").strip().upper()
    return raw or None


def _signal_closes(
    close_by_ticker: Mapping[str, Any],
    config: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Loại benchmark khỏi equal-weight buyhold (regime vẫn dùng full map)."""
    bench = _benchmark_ticker(config)
    if not bench:
        return dict(close_by_ticker)
    out = {
        str(t).upper(): s
        for t, s in close_by_ticker.items()
        if str(t).strip().upper() != bench
    }
    return out or dict(close_by_ticker)


def _set_quant_flags(config: dict, *, regime: bool, alpha: bool, risk: bool) -> dict:
    cfg = deepcopy(config)
    q = dict(cfg.get("quant_engine") or {})
    q["regime_markov"] = {**(q.get("regime_markov") or {}), "enabled": regime}
    q["alpha_kalman_trend"] = {**(q.get("alpha_kalman_trend") or {}), "enabled": alpha}
    q["alpha_ou_meanreversion"] = {
        **(q.get("alpha_ou_meanreversion") or {}),
        "enabled": alpha,
    }
    q["risk_garch"] = {**(q.get("risk_garch") or {}), "enabled": risk}
    # Force equal-weight / no MC for ablation fairness at P0
    q["portfolio_black_litterman"] = {
        **(q.get("portfolio_black_litterman") or {}),
        "enabled": False,
    }
    q["probabilistic_monte_carlo"] = {
        **(q.get("probabilistic_monte_carlo") or {}),
        "enabled": False,
    }
    cfg["quant_engine"] = q
    return cfg


def _buyhold_result(
    close_by_ticker: Mapping[str, Any],
    start_date: str,
    end_date: str,
    config: dict,
) -> dict:
    """Equal-weight buy-and-hold of all tickers (no signals)."""
    import pandas as pd

    from backtest.metrics import compute_metrics

    frames = []
    for ticker, series in close_by_ticker.items():
        s = pd.to_numeric(series, errors="coerce").dropna()
        s.index = s.index.astype(str)
        s = s.loc[(s.index >= start_date) & (s.index <= end_date)]
        if not s.empty:
            frames.append(s.rename(str(ticker).upper()))
    if not frames:
        empty = {"equity_curve": [], "trades": [], "metrics": compute_metrics([], [], config)}
        return empty
    prices = pd.concat(frames, axis=1).sort_index().ffill().dropna(how="all")
    rets = prices.pct_change().fillna(0.0)
    port = rets.mean(axis=1)
    equity = (1.0 + port).cumprod()
    curve = [{"date": str(d), "equity": float(v)} for d, v in equity.items()]
    return {
        "equity_curve": curve,
        "trades": [],
        "metrics": compute_metrics(curve, [], config),
        "signals": [],
    }


def _assumed_lag_days(config: Mapping[str, Any] | None) -> int:
    sources = dict((config or {}).get("data_sources") or {})
    backtest = dict(sources.get("financial_statements_backtest") or {})
    return int(backtest.get("assumed_publication_lag_days", 90))


def build_scoring_schedule(
    tickers: list[str],
    start_date: str,
    end_date: str,
    config: Mapping[str, Any] | None = None,
    *,
    lookback_years: int = 5,
    db_path: str = "store/bot.db",
    include_prior_year: bool = True,
) -> dict[str, dict[str, Any]]:
    """Build ``{assumed_filed_at: scoring_frames}`` for backtest PIT watchlist.

    Each calendar year ``Y`` pulls annual frames ``[Y-lookback+1, Y]`` via
    ``build_scoring_frames_from_providers`` and keys by ``assumed_filed_at(Y)``.
    """
    from data.ingest.pit import assumed_filed_at
    from data.ingest.scoring_frames import build_scoring_frames_from_providers

    if lookback_years < 1:
        raise ValueError("lookback_years must be >= 1")
    start_y = int(str(start_date)[:4])
    end_y = int(str(end_date)[:4])
    if start_y > end_y:
        raise ValueError("start_date year must be <= end_date year")
    lag = _assumed_lag_days(config)
    first_y = start_y - 1 if include_prior_year else start_y
    schedule: dict[str, dict[str, Any]] = {}
    for year in range(first_y, end_y + 1):
        frame_start = year - lookback_years + 1
        print(
            f"scoring_schedule: year={year} frames={frame_start}..{year} ...",
            flush=True,
        )
        frames = build_scoring_frames_from_providers(
            tickers,
            frame_start,
            year,
            config=dict(config or {}),
            db_path=db_path,
        )
        if not frames:
            print(f"scoring_schedule: skip empty frames for year={year}", flush=True)
            continue
        filed = assumed_filed_at(year, lag)
        schedule[filed] = frames
    return schedule


def run_ablation(
    config: dict,
    layers_order: list[str] | None = None,
    *,
    close_by_ticker: Mapping[str, Any],
    start_date: str,
    end_date: str,
    scoring_schedule: Mapping[str, Any] | None = None,
    signal_every_n_days: int = 5,
) -> dict:
    """Run backtest cumulatively: baseline -> +fundamental -> +regime -> +alpha -> +risk.

    Returns ``{"steps": [...], "layers_order": [...]}`` with Sharpe/CAGR/MDD per step.
    """
    from backtest.engine import _active_watchlist

    order = list(layers_order or DEFAULT_LAYERS)
    steps = []
    signal_closes = _signal_closes(close_by_ticker, config)

    for layer in order:
        print(f"ablation step: {layer} ...", flush=True)
        if layer == "B0_buyhold":
            result = _buyhold_result(signal_closes, start_date, end_date, config)
            label = "B0_buyhold"
        elif layer == "fundamental":
            # Equal-weight PASS/WATCH universe at end_date (PIT via schedule).
            if scoring_schedule:
                watchlist, _scores = _active_watchlist(
                    scoring_schedule,
                    end_date,
                    list(signal_closes),
                    config,
                )
                subset = {
                    t: close_by_ticker[t]
                    for t in watchlist
                    if t in close_by_ticker and t in signal_closes
                }
                result = _buyhold_result(
                    subset or signal_closes, start_date, end_date, config
                )
            else:
                result = _buyhold_result(signal_closes, start_date, end_date, config)
            label = "fundamental"
        elif layer == "regime":
            # Regime on; alpha off (alpha_eff NaN → WATCH-heavy — isolates regime).
            cfg = _set_quant_flags(config, regime=True, alpha=False, risk=False)
            result = run_backtest(
                cfg,
                start_date,
                end_date,
                close_by_ticker=close_by_ticker,
                scoring_schedule=scoring_schedule,
                signal_every_n_days=signal_every_n_days,
                signal_tickers=list(signal_closes),
            )
            label = "regime"
        elif layer == "alpha":
            cfg = _set_quant_flags(config, regime=True, alpha=True, risk=False)
            result = run_backtest(
                cfg,
                start_date,
                end_date,
                close_by_ticker=close_by_ticker,
                scoring_schedule=scoring_schedule,
                signal_every_n_days=signal_every_n_days,
                signal_tickers=list(signal_closes),
            )
            label = "alpha"
        elif layer == "risk":
            cfg = _set_quant_flags(config, regime=True, alpha=True, risk=True)
            result = run_backtest(
                cfg,
                start_date,
                end_date,
                close_by_ticker=close_by_ticker,
                scoring_schedule=scoring_schedule,
                signal_every_n_days=signal_every_n_days,
                signal_tickers=list(signal_closes),
            )
            label = "risk"
        else:
            raise ValueError(f"Unknown ablation layer: {layer}")

        m = result["metrics"]
        steps.append(
            {
                "layer": label,
                "cagr": m.get("cagr"),
                "sharpe": m.get("sharpe"),
                "max_drawdown": m.get("max_drawdown"),
                "win_rate": m.get("win_rate"),
                "n_trades": m.get("n_trades"),
                "metrics": m,
            }
        )

    return {"layers_order": order, "steps": steps}


def format_decisions_row(step: dict, decision: str = "pending") -> str:
    """One markdown table row for docs/DECISIONS.md ablation log."""
    return (
        f"| {{date}} | ablation `{step['layer']}` | "
        f"Sharpe={step.get('sharpe')!s} CAGR={step.get('cagr')!s} "
        f"MDD={step.get('max_drawdown')!s} | {decision} | |"
    )


def decide_keep_cut(
    steps: list[dict],
    *,
    threshold: float = SHARPE_KEEP_DELTA,
) -> list[dict]:
    """Gắn ``delta_sharpe`` và ``decision`` (giữ/cắt/baseline) theo ngưỡng biên."""
    annotated: list[dict] = []
    prev_sharpe: float | None = None
    for step in steps:
        row = dict(step)
        sharpe = row.get("sharpe")
        try:
            sharpe_f = float(sharpe) if sharpe is not None else None
        except (TypeError, ValueError):
            sharpe_f = None
        if sharpe_f is not None and sharpe_f != sharpe_f:  # NaN
            sharpe_f = None

        if row.get("layer") == "B0_buyhold":
            row["delta_sharpe"] = None
            row["decision"] = "baseline"
        elif sharpe_f is None:
            row["delta_sharpe"] = None
            row["decision"] = "pending — missing Sharpe (0 trades / flat)"
        elif prev_sharpe is None:
            row["delta_sharpe"] = None
            row["decision"] = "baseline (no prior Sharpe)"
        else:
            delta = sharpe_f - prev_sharpe
            row["delta_sharpe"] = delta
            if delta >= threshold:
                row["decision"] = f"keep (dSharpe={delta:+.3f} >= +{threshold:.2f})"
            else:
                row["decision"] = (
                    f"cut from main / keep appendix "
                    f"(dSharpe={delta:+.3f} < +{threshold:.2f})"
                )

        if sharpe_f is not None:
            prev_sharpe = sharpe_f
        annotated.append(row)
    return annotated


def append_decisions_log(
    steps: list[dict],
    decisions_path: str | Path = "docs/DECISIONS.md",
    decision: str = "pending review",
) -> None:
    """Append ablation summary lines under the decisions log section."""
    path = Path(decisions_path)
    today = date.today().isoformat()
    lines = ["\n### Ablation auto-log\n"]
    for step in steps:
        label = step.get("decision") or decision
        row = format_decisions_row(step, decision=label).replace("{date}", today)
        lines.append(row + "\n")
    with path.open("a", encoding="utf-8") as handle:
        handle.writelines(lines)


def load_close_by_ticker(
    tickers: list[str],
    start_date: str,
    end_date: str,
    config: dict,
    *,
    include_benchmark: bool = True,
) -> dict[str, Any]:
    """Nap close series qua ``data.ingest.price_history`` (provider chain)."""
    from data.ingest.price_history import fetch_universe_ohlcv, to_close_series

    wanted = [str(t).strip().upper() for t in tickers if str(t).strip()]
    bench = _benchmark_ticker(config) if include_benchmark else None
    if bench and bench not in wanted:
        wanted.append(bench)
    ohlcv = fetch_universe_ohlcv(wanted, start_date, end_date, config)
    closes = {t: to_close_series(frame) for t, frame in ohlcv.items()}
    missing = sorted(set(wanted) - set(closes))
    if missing:
        print(f"warning: missing OHLCV for {missing}", flush=True)
    return closes


def format_steps_table(steps: list[dict]) -> str:
    """Bang text Sharpe/CAGR/MDD theo layer (stdout CLI)."""
    header = (
        f"{'layer':<14} {'sharpe':>10} {'cagr':>10} {'mdd':>10} "
        f"{'n_trades':>8}  decision"
    )
    lines = [header, "-" * max(len(header), 72)]
    for step in steps:
        sharpe = step.get("sharpe")
        cagr = step.get("cagr")
        mdd = step.get("max_drawdown")
        n_trades = step.get("n_trades")
        lines.append(
            f"{str(step.get('layer')):<14} "
            f"{_fmt_metric(sharpe):>10} "
            f"{_fmt_metric(cagr):>10} "
            f"{_fmt_metric(mdd):>10} "
            f"{str(n_trades if n_trades is not None else ''):>8}  "
            f"{step.get('decision') or ''}"
        )
    return "\n".join(lines)


def _fmt_metric(value: Any) -> str:
    try:
        if value is None:
            return "-"
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _load_config(path: str | Path) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _json_safe(value: Any) -> Any:
    """JSON-friendly scalars (NaN/Inf → None)."""
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            return None
        return value
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ablation P0 stack (B0->fundamental->regime->alpha->risk)"
    )
    parser.add_argument(
        "--config",
        default="pipeline/config.yaml",
        help="Pipeline YAML (default: pipeline/config.yaml)",
    )
    parser.add_argument(
        "--tickers",
        default="VNM,FPT",
        help="Comma-separated tickers (default: VNM,FPT)",
    )
    parser.add_argument("--start-date", default=None, help="ISO start (default: config)")
    parser.add_argument("--end-date", default=None, help="ISO end (default: today)")
    parser.add_argument(
        "--signal-every",
        type=int,
        default=5,
        help="Recompute signals every N sessions (default: 5)",
    )
    parser.add_argument(
        "--out-json",
        default="store/ablation_p0.json",
        help="Write steps JSON (default: store/ablation_p0.json)",
    )
    parser.add_argument(
        "--no-benchmark",
        action="store_true",
        help="Do not fetch quant_engine.benchmark OHLCV",
    )
    parser.add_argument(
        "--with-fundamentals",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Build PIT scoring_schedule via providers (default: on)",
    )
    parser.add_argument(
        "--lookback-years",
        type=int,
        default=5,
        help="Annual BCTC lookback per schedule year (default: 5)",
    )
    parser.add_argument(
        "--db-path",
        default="store/bot.db",
        help="SQLite path for sector_mapping (default: store/bot.db)",
    )
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="Also run walk-forward OOS on full P0 stack (regime+alpha+risk)",
    )
    args = parser.parse_args(argv)

    config = _load_config(args.config)
    bt = dict(config.get("backtest") or {})
    start = args.start_date or bt.get("start_date") or "2019-01-01"
    end = args.end_date or date.today().isoformat()
    tickers = [t.strip().upper() for t in str(args.tickers).split(",") if t.strip()]
    if not tickers:
        raise SystemExit("Provide at least one ticker via --tickers")

    print(f"ablation: tickers={tickers} window={start}..{end}", flush=True)
    closes = load_close_by_ticker(
        tickers,
        start,
        end,
        config,
        include_benchmark=not args.no_benchmark,
    )
    if not closes:
        raise SystemExit("No OHLCV loaded — check providers / network")

    signal_names = sorted(_signal_closes(closes, config))
    print(
        f"loaded closes: {sorted(closes)} | signal_universe={signal_names} "
        f"| benchmark={_benchmark_ticker(config)}",
        flush=True,
    )

    scoring_schedule = None
    if args.with_fundamentals:
        scoring_schedule = build_scoring_schedule(
            tickers,
            start,
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

    raw = run_ablation(
        config,
        close_by_ticker=closes,
        start_date=start,
        end_date=end,
        scoring_schedule=scoring_schedule,
        signal_every_n_days=max(int(args.signal_every), 1),
    )
    steps = decide_keep_cut(raw["steps"])

    walk_forward_payload = None
    if args.walk_forward:
        from backtest.walk_forward import run_walk_forward

        print("walk_forward: full P0 stack ...", flush=True)
        wf_cfg = _set_quant_flags(config, regime=True, alpha=True, risk=True)
        wf = run_walk_forward(
            wf_cfg,
            start,
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
            f"cagr={walk_forward_payload['cagr']}",
            flush=True,
        )

    out_path = Path(args.out_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "start_date": start,
        "end_date": end,
        "tickers": tickers,
        "loaded": sorted(closes),
        "scoring_schedule_keys": sorted(scoring_schedule or {}),
        "with_fundamentals": bool(args.with_fundamentals),
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
            }
            for s in steps
        ],
        "walk_forward": walk_forward_payload,
        "note": (
            "P0 stack only; MC/BL forced off in ablation. "
            "Do not flip pipeline defaults until P1 ablation has numbers."
        ),
    }
    out_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )
    print(f"wrote {out_path}", flush=True)
    try:
        print(format_steps_table(steps), flush=True)
    except UnicodeEncodeError:
        # Windows cp1252 consoles — metrics already in JSON
        print(format_steps_table(steps).encode("ascii", "replace").decode("ascii"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
