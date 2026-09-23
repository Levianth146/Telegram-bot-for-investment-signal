"""P1-1 diagnose: gán nhãn Markov bull/bear/turbulent trên VNINDEX (không đổi code).

In params + state_labels; so sánh với hướng giá thực tế trên cửa sổ OOS.
Chạy::

    python scripts/diagnose_regime_labels.py
    python scripts/diagnose_regime_labels.py --start 2022-03-22 --end 2025-09-22
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data.ingest.price_history import fetch_ohlcv, to_close_series  # noqa: E402
from quant_engine.regime import (  # noqa: E402
    _label_states_by_mean_and_variance,
    fit_markov_regime,
    fit_or_fallback_regime,
)


def _log_returns(close: pd.Series) -> pd.Series:
    prices = pd.to_numeric(close, errors="coerce").dropna().sort_index()
    return np.log(prices).diff().dropna()


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnose Markov regime state labels")
    parser.add_argument("--ticker", default="VNINDEX")
    parser.add_argument("--start", default="2022-03-22")
    parser.add_argument("--end", default="2025-09-22")
    parser.add_argument(
        "--oos-start",
        default="2025-03-22",
        help="In filtered P(bull) trên cửa sổ OOS (cuối series)",
    )
    args = parser.parse_args()

    print(f"fetch OHLCV {args.ticker} {args.start}..{args.end} ...", flush=True)
    frame = fetch_ohlcv(args.ticker, args.start, args.end)
    if frame is None or frame.empty:
        print("ERROR: empty OHLCV", file=sys.stderr)
        return 1
    close = to_close_series(frame)
    rets = _log_returns(close)
    print(f"closes={len(close)} returns={len(rets)}", flush=True)

    pack = fit_or_fallback_regime(rets)
    probs = pack["probabilities"]
    print(
        f"fit_or_fallback: method={probs.get('method')} "
        f"p_bull={probs.get('bull'):.4f} p_bear={probs.get('bear'):.4f} "
        f"p_turb={probs.get('turbulent'):.4f}",
        flush=True,
    )

    try:
        fitted = fit_markov_regime(rets)
    except Exception as exc:  # noqa: BLE001
        print(f"fit_markov_regime failed: {exc}", flush=True)
        return 0

    labels = fitted.get("state_labels") or {}
    result = fitted.get("result")
    params = getattr(result, "params", None) if result is not None else None
    print("state_labels:", labels, flush=True)
    if params is not None:
        print("params:\n", params, flush=True)
        # Recompute labels explicitly for audit
        recomputed = _label_states_by_mean_and_variance(params, n_states=3)
        print("recomputed_labels:", recomputed, flush=True)

    # Price direction OOS vs last filtered probs
    oos = close.loc[str(args.oos_start) :] if args.oos_start in close.index else close
    if len(oos) >= 2:
        ret_oos = float(oos.iloc[-1] / oos.iloc[0] - 1.0)
        print(
            f"OOS price change {args.oos_start}..{args.end}: {ret_oos:.2%} "
            f"(positive rally + low p_bull → nghi P1-1 label)",
            flush=True,
        )
    print(
        "NOTE: Không đổi _label_states_by_mean_and_variance trong PR P0. "
        "Nếu rally bị gán turbulent → bàn nhóm trước khi sửa nhãn.",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
