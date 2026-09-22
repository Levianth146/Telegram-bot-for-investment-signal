"""cProfile smoke cho backtest — ghi top cumtime vào outputs/performance/.

Dùng series tổng hợp (không API) để đo hotspot sim: FF rescore, truncate, regime.

Ví dụ::

  python scripts/profile_backtest_smoke.py --out outputs/performance/profile_before.txt
  python scripts/profile_backtest_smoke.py --out outputs/performance/profile_after.txt
"""

from __future__ import annotations

import argparse
import cProfile
import pstats
import sys
import time
from io import StringIO
from pathlib import Path


def _synthetic_closes(n_tickers: int = 4, n_days: int = 80):
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(42)
    dates = pd.bdate_range("2024-01-02", periods=n_days).strftime("%Y-%m-%d").tolist()
    closes: dict[str, pd.Series] = {}
    tickers = ["AAA", "BBB", "CCC", "DDD", "EEE", "FFF"][:n_tickers]
    for i, t in enumerate(tickers):
        walk = 100.0 + i * 5.0 + np.cumsum(rng.normal(0.05, 1.0, size=n_days))
        closes[t] = pd.Series(walk, index=dates, name="close")
    # Benchmark cho regime
    walk_b = 1000.0 + np.cumsum(rng.normal(0.02, 0.8, size=n_days))
    closes["VNINDEX"] = pd.Series(walk_b, index=dates, name="close")
    return closes, tickers, dates


def _synthetic_schedule(tickers: list[str], dates: list[str]):
    import pandas as pd

    mid = dates[len(dates) // 3]
    late = dates[(2 * len(dates)) // 3]
    frames_a = {
        t: pd.DataFrame(
            {
                "year": [2022, 2023],
                "ticker": [t, t],
                "revenue": [1.0, 1.1],
                "npat": [0.1, 0.12],
            }
        )
        for t in tickers
    }
    frames_b = {
        t: pd.DataFrame(
            {
                "year": [2022, 2023, 2024],
                "ticker": [t, t, t],
                "revenue": [1.0, 1.1, 1.2],
                "npat": [0.1, 0.12, 0.13],
            }
        )
        for t in tickers
    }
    return {mid: frames_a, late: frames_b}


def _minimal_config() -> dict:
    return {
        "quant_engine": {
            "benchmark": "VNINDEX",
            "sigma_target": 0.02,
            "w_max": 0.10,
            "stop_k": 2.0,
            "bull_threshold": 0.55,
            "bear_threshold": 0.35,
            "min_slope_tstat": 1.0,
            "regime_markov": {"enabled": True},
            "alpha_kalman_trend": {"enabled": True},
            "alpha_ou_meanreversion": {"enabled": True},
            "risk_garch": {"enabled": True},
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


def run_smoke(*, with_fundamentals: bool, signal_every: int) -> dict:
    from backtest.engine import run_backtest

    closes, tickers, dates = _synthetic_closes()
    schedule = _synthetic_schedule(tickers, dates) if with_fundamentals else None
    cfg = _minimal_config()

    # Monkeypatch score_current_universe nếu fund on — tránh phụ thuộc frames đầy đủ.
    if with_fundamentals:
        import pandas as pd
        import backtest.engine as eng

        def fake_score(frames, start_year, end_year, config=None):
            rows = []
            for t in frames:
                rows.append(
                    {
                        "ticker": t,
                        "growth_score": 70.0,
                        "quality_score": 65.0,
                        "safety_score": 60.0,
                        "valuation_score": 55.0,
                        "fundamental_score": 62.0,
                        "classification": "WATCH",
                    }
                )
            return pd.DataFrame(rows), None, None

        eng.score_current_universe = fake_score  # type: ignore[assignment]

    return run_backtest(
        cfg,
        dates[0],
        dates[-1],
        close_by_ticker=closes,
        scoring_schedule=schedule,
        signal_every_n_days=signal_every,
        signal_tickers=tickers,
    )


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    parser = argparse.ArgumentParser(description="Profile backtest smoke (cProfile)")
    parser.add_argument(
        "--out",
        default="outputs/performance/profile_smoke.txt",
        help="Đường dẫn file báo cáo pstats",
    )
    parser.add_argument("--signal-every", type=int, default=1)
    parser.add_argument(
        "--no-fundamentals",
        action="store_true",
        help="Bỏ scoring_schedule (đo quant-only)",
    )
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args(argv)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    profiler = cProfile.Profile()
    t0 = time.perf_counter()
    profiler.enable()
    result = run_smoke(
        with_fundamentals=not args.no_fundamentals,
        signal_every=max(int(args.signal_every), 1),
    )
    profiler.disable()
    elapsed = time.perf_counter() - t0

    stream = StringIO()
    stats = pstats.Stats(profiler, stream=stream)
    stats.strip_dirs().sort_stats("cumtime")
    print(f"=== BACKTEST SMOKE PROFILE ===", file=stream)
    print(f"elapsed_sec={elapsed:.4f}", file=stream)
    print(f"n_trades={(result.get('metrics') or {}).get('n_trades')}", file=stream)
    print(f"equity_points={len(result.get('equity_curve') or [])}", file=stream)
    print(f"with_fundamentals={not args.no_fundamentals}", file=stream)
    print(f"signal_every={args.signal_every}", file=stream)
    print("", file=stream)
    print(f"--- top {args.top} by cumtime ---", file=stream)
    stats.print_stats(args.top)
    print("", file=stream)
    print(f"--- top {args.top} by ncalls ---", file=stream)
    stats.sort_stats("ncalls").print_stats(args.top)

    text = stream.getvalue()
    out_path.write_text(text, encoding="utf-8")
    print(f"wrote {out_path} elapsed_sec={elapsed:.4f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
