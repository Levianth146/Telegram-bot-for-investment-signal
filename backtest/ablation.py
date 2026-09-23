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


def _safe_print(text: str) -> None:
    """Print an toàn trên console Windows cp1252 (tránh crash vì mũi tên Unicode)."""
    try:
        print(text, flush=True)
    except UnicodeEncodeError:
        enc = getattr(getattr(__import__("sys"), "stdout"), "encoding", None) or "ascii"
        print(text.encode(enc, errors="replace").decode(enc, errors="replace"), flush=True)


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


def _cost_fractions(config: Mapping[str, Any] | None) -> tuple[float, float]:
    """(buy_fee, sell_fee) từ backtest.cost — cùng ledger với engine."""
    bt = dict((config or {}).get("backtest") or {})
    cost = dict(bt.get("cost") or {})
    tax_sell = float(cost.get("tax_sell_pct", 0.001))
    fee_rt = float(cost.get("fee_roundtrip_pct", 0.003))
    from backtest.costs import buy_cost_fraction, sell_cost_fraction

    return buy_cost_fraction(fee_rt), sell_cost_fraction(tax_sell, fee_rt)


def _buyhold_result(
    close_by_ticker: Mapping[str, Any],
    start_date: str,
    end_date: str,
    config: dict,
) -> dict:
    """Equal-weight buy-and-hold; entry cost một lần + exit cuối kỳ (fair vs engine)."""
    import pandas as pd

    from backtest.metrics import compute_metrics

    buy_fee, sell_fee = _cost_fractions(config)
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
    # Gross equity rồi haircut entry/exit một lần (nhất quán mọi baseline BH).
    equity_gross = (1.0 + port).cumprod()
    if len(equity_gross) == 0:
        return {
            "equity_curve": [],
            "trades": [],
            "metrics": compute_metrics([], [], config),
            "signals": [],
        }
    equity = equity_gross.copy()
    equity.iloc[0] = float(equity.iloc[0]) * (1.0 - buy_fee)
    # Rebase sau entry haircut rồi apply path
    if float(equity_gross.iloc[0]) > 0:
        path = equity_gross / float(equity_gross.iloc[0])
        equity = path * (1.0 - buy_fee)
    equity.iloc[-1] = float(equity.iloc[-1]) * (1.0 - sell_fee)
    curve = [{"date": str(d), "equity": float(v)} for d, v in equity.items()]
    gross_end = float(equity_gross.iloc[-1] / equity_gross.iloc[0]) - 1.0 if float(equity_gross.iloc[0]) else 0.0
    net_end = float(equity.iloc[-1]) - 1.0
    metrics = compute_metrics(curve, [], config)
    metrics = {
        **metrics,
        "gross_total_return": gross_end,
        "net_total_return": net_end,
        "cost_drag": gross_end - net_end,
        "total_fees_tax": float(buy_fee + sell_fee),
    }
    return {
        "equity_curve": curve,
        "trades": [],
        "metrics": metrics,
        "signals": [],
    }


def _apply_position_costs(
    pos: "pd.Series",
    gross_rets: "pd.Series",
    buy_fee: float,
    sell_fee: float,
) -> "pd.Series":
    """Trừ phí khi vị thế đổi hiệu lực (đã shift T+1 cùng gross_rets)."""
    import pandas as pd

    pos_lag = pos.shift(1).fillna(0.0)
    pos_lag2 = pos.shift(2).fillna(0.0)
    delta = pos_lag - pos_lag2
    cost = delta.clip(lower=0.0) * buy_fee + (-delta.clip(upper=0.0)) * sell_fee
    return gross_rets - cost.fillna(0.0)


def _rsi(series, period: int = 14):
    import pandas as pd

    delta = series.diff()
    gain = delta.clip(lower=0.0).rolling(period, min_periods=period).mean()
    loss = (-delta.clip(upper=0.0)).rolling(period, min_periods=period).mean()
    rs = gain / loss.replace(0.0, pd.NA)
    return 100.0 - (100.0 / (1.0 + rs))


def _b1_ta_result(
    close_by_ticker: Mapping[str, Any],
    start_date: str,
    end_date: str,
    config: dict,
) -> dict:
    """Baseline B1 — TA thuần + cùng cost/T+1 lag như framework."""
    import pandas as pd

    from backtest.metrics import compute_metrics

    buy_fee, sell_fee = _cost_fractions(config)
    frames = []
    gross_frames = []
    for ticker, series in close_by_ticker.items():
        s = pd.to_numeric(series, errors="coerce").dropna()
        s.index = s.index.astype(str)
        s = s.loc[(s.index >= start_date) & (s.index <= end_date)]
        if len(s) < 60:
            continue
        ema_fast = s.ewm(span=20, adjust=False).mean()
        ema_slow = s.ewm(span=50, adjust=False).mean()
        rsi = _rsi(s, 14)
        long_mask = (ema_fast > ema_slow) & (rsi < 70)
        pos = long_mask.astype(float).fillna(0.0)
        pct = s.pct_change().fillna(0.0)
        gross = pct * pos.shift(1).fillna(0.0)
        net = _apply_position_costs(pos, gross, buy_fee, sell_fee)
        frames.append(net.rename(str(ticker).upper()))
        gross_frames.append(gross.rename(str(ticker).upper()))
    if not frames:
        return {
            "equity_curve": [],
            "trades": [],
            "metrics": compute_metrics([], [], config),
            "signals": [],
        }
    port = pd.concat(frames, axis=1).sort_index().fillna(0.0).mean(axis=1)
    port_gross = pd.concat(gross_frames, axis=1).sort_index().fillna(0.0).mean(axis=1)
    equity = (1.0 + port).cumprod()
    equity_gross = (1.0 + port_gross).cumprod()
    curve = [{"date": str(d), "equity": float(v)} for d, v in equity.items()]
    flips = sum(
        int((f.fillna(0.0) != 0).astype(int).diff().fillna(0).abs().sum() // 2)
        for f in frames
    )
    metrics = compute_metrics(curve, [], config)
    g_ret = float(equity_gross.iloc[-1] / equity_gross.iloc[0] - 1.0) if len(equity_gross) else 0.0
    n_ret = float(equity.iloc[-1] / equity.iloc[0] - 1.0) if len(equity) else 0.0
    metrics = {
        **metrics,
        "n_trades": int(flips),
        "gross_total_return": g_ret,
        "net_total_return": n_ret,
        "cost_drag": g_ret - n_ret,
    }
    return {"equity_curve": curve, "trades": [], "metrics": metrics, "signals": []}


def _b2_canslim_result(
    close_by_ticker: Mapping[str, Any],
    start_date: str,
    end_date: str,
    config: dict,
) -> dict:
    """Baseline B2 — CANSLIM rút gọn + cost khi rebalance (T+1 lag)."""
    import pandas as pd

    from backtest.metrics import compute_metrics

    buy_fee, sell_fee = _cost_fractions(config)
    frames = []
    for ticker, series in close_by_ticker.items():
        s = pd.to_numeric(series, errors="coerce").dropna()
        s.index = s.index.astype(str)
        s = s.loc[(s.index >= start_date) & (s.index <= end_date)]
        if not s.empty:
            frames.append(s.rename(str(ticker).upper()))
    if not frames:
        return {
            "equity_curve": [],
            "trades": [],
            "metrics": compute_metrics([], [], config),
            "signals": [],
        }
    prices = pd.concat(frames, axis=1).sort_index().ffill()
    rs = prices / prices.shift(126) - 1.0
    month_ends = list(prices.groupby(prices.index.str[:7]).tail(1).index)
    weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    n_trades = 0
    prev_set: set[str] = set()
    for i, day in enumerate(month_ends):
        row = rs.loc[day].dropna()
        if row.empty:
            continue
        k = max(1, len(row) // 2)
        chosen = set(str(x) for x in row.nlargest(k).index)
        w = 1.0 / len(chosen)
        next_day = month_ends[i + 1] if i + 1 < len(month_ends) else prices.index[-1]
        slice_idx = prices.index[(prices.index >= day) & (prices.index <= next_day)]
        weights.loc[slice_idx, :] = 0.0
        for col in chosen:
            if col in weights.columns:
                weights.loc[slice_idx, col] = w
        if chosen != prev_set:
            n_trades += len(chosen.symmetric_difference(prev_set))
            prev_set = chosen
    rets = prices.pct_change().fillna(0.0)
    w_lag = weights.shift(1).fillna(0.0)
    port_gross = (rets * w_lag).sum(axis=1)
    # Cost trên thay đổi trọng số hiệu lực (turnover / 2 * fees)
    w_lag2 = weights.shift(2).fillna(0.0)
    delta_w = (w_lag - w_lag2).abs().sum(axis=1)
    # Mua tăng + bán giảm ≈ turnover; chia đôi buy/sell fee xấp xỉ
    cost = delta_w * ((buy_fee + sell_fee) / 2.0)
    port = port_gross - cost.fillna(0.0)
    equity = (1.0 + port).cumprod()
    equity_gross = (1.0 + port_gross).cumprod()
    curve = [{"date": str(d), "equity": float(v)} for d, v in equity.items()]
    metrics = compute_metrics(curve, [], config)
    g_ret = float(equity_gross.iloc[-1] / equity_gross.iloc[0] - 1.0) if len(equity_gross) else 0.0
    n_ret = float(equity.iloc[-1] / equity.iloc[0] - 1.0) if len(equity) else 0.0
    metrics = {
        **metrics,
        "n_trades": int(n_trades),
        "gross_total_return": g_ret,
        "net_total_return": n_ret,
        "cost_drag": g_ret - n_ret,
    }
    return {"equity_curve": curve, "trades": [], "metrics": metrics, "signals": []}


def _dynamic_fundamental_result(
    close_by_ticker: Mapping[str, Any],
    start_date: str,
    end_date: str,
    config: dict,
    scoring_schedule: Mapping[str, Any] | None,
) -> dict:
    """Fundamental-only: equal-weight PASS/WATCH rebalance theo PIT ngày (không look-ahead).

    Trọng số ngày T áp dụng return ngày T+1. Không dùng watchlist ``end_date``.
    """
    import pandas as pd

    from backtest.engine import (
        _active_watchlist,
        _as_date_index,
        _trading_days,
        precompute_fundamental_states,
    )
    from backtest.metrics import compute_metrics

    buy_fee, sell_fee = _cost_fractions(config)
    if not scoring_schedule:
        return _buyhold_result(close_by_ticker, start_date, end_date, config)

    closes = {
        str(t).strip().upper(): _as_date_index(s) for t, s in close_by_ticker.items()
    }
    calendar = _trading_days(closes, start_date, end_date)
    if not calendar:
        return {
            "equity_curve": [],
            "trades": [],
            "metrics": compute_metrics([], [], config),
            "signals": [],
        }

    ff_states = precompute_fundamental_states(scoring_schedule)
    prev_weights: dict[str, float] = {}
    equity = 1.0
    equity_gross = 1.0
    curve: list[dict] = []
    total_cost = 0.0

    for i, day in enumerate(calendar):
        if i > 0 and prev_weights:
            day_ret = 0.0
            n_ok = 0
            prev_day = calendar[i - 1]
            for tkr, w in prev_weights.items():
                series = closes.get(tkr)
                if series is None:
                    continue
                if day not in series.index or prev_day not in series.index:
                    continue
                px0 = float(series.loc[prev_day])
                px1 = float(series.loc[day])
                if px0 <= 0 or pd.isna(px0) or pd.isna(px1):
                    continue
                day_ret += float(w) * (px1 / px0 - 1.0)
                n_ok += 1
            if n_ok == 0:
                day_ret = 0.0
            equity_gross *= 1.0 + day_ret
            equity *= 1.0 + day_ret

        curve.append({"date": day, "equity": float(equity)})

        watchlist, _scores = _active_watchlist(
            scoring_schedule,
            day,
            list(closes),
            config,
            ff_states=ff_states,
        )
        eligible = [
            t
            for t in watchlist
            if t in closes and day in closes[t].index and not pd.isna(closes[t].loc[day])
        ]
        if eligible:
            w = 1.0 / len(eligible)
            new_weights = {t: w for t in eligible}
        else:
            new_weights = {}

        # Cost trên thay đổi weight (hiệu lực T+1 — trừ vào equity hiện tại xấp xỉ)
        all_tickers = set(prev_weights) | set(new_weights)
        turnover = sum(
            abs(new_weights.get(t, 0.0) - prev_weights.get(t, 0.0)) for t in all_tickers
        )
        step_cost = turnover * ((buy_fee + sell_fee) / 2.0)
        if step_cost > 0 and i + 1 < len(calendar):
            # Haircut sẽ phản ánh khi weight mới bắt đầu earn (ngày sau)
            total_cost += step_cost
            equity *= 1.0 - step_cost
        prev_weights = new_weights

    metrics = compute_metrics(curve, [], config)
    g_ret = equity_gross - 1.0
    n_ret = equity - 1.0
    metrics = {
        **metrics,
        "gross_total_return": g_ret,
        "net_total_return": n_ret,
        "cost_drag": g_ret - n_ret,
        "total_fees_tax": total_cost,
    }
    return {"equity_curve": curve, "trades": [], "metrics": metrics, "signals": []}


def _assumed_lag_days(config: Mapping[str, Any] | None) -> int:
    sources = dict((config or {}).get("data_sources") or {})
    backtest = dict(sources.get("financial_statements_backtest") or {})
    return int(backtest.get("assumed_publication_lag_days", 90))


# Schema version disk cache scoring_schedule — bump khi đổi format pickle/frames.
_SCORING_SCHEDULE_CACHE_SCHEMA = 1


def _scoring_schedule_cache_key(
    tickers: list[str],
    *,
    lookback_years: int,
    lag_days: int,
    include_prior_year: bool,
    config: Mapping[str, Any] | None,
) -> str:
    """Hash ổn định (sha256) cho thư mục cache theo năm."""
    import hashlib
    import json

    sources = dict((config or {}).get("data_sources") or {})
    fund_bt = dict(sources.get("financial_statements_backtest") or {})
    fund_live = dict(sources.get("financial_statements") or {})
    payload = {
        "schema": _SCORING_SCHEDULE_CACHE_SCHEMA,
        "tickers": sorted({str(t).strip().upper() for t in tickers if str(t).strip()}),
        "lookback_years": int(lookback_years),
        "lag_days": int(lag_days),
        "include_prior_year": bool(include_prior_year),
        "fund_bt_provider": fund_bt.get("provider"),
        "fund_live_provider": fund_live.get("provider"),
        "assumed_publication_lag_days": fund_bt.get("assumed_publication_lag_days", 90),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _default_scoring_cache_dir(config: Mapping[str, Any] | None) -> Path:
    sources = dict((config or {}).get("data_sources") or {})
    price = dict(sources.get("price") or {})
    base = Path(str(price.get("cache_dir") or "data/cache"))
    return base / "scoring_schedule"


def build_scoring_schedule(
    tickers: list[str],
    start_date: str,
    end_date: str,
    config: Mapping[str, Any] | None = None,
    *,
    lookback_years: int = 5,
    db_path: str = "store/bot.db",
    include_prior_year: bool = True,
    refresh: bool = False,
    cache_dir: str | Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Build ``{assumed_filed_at: scoring_frames}`` for backtest PIT watchlist.

    Each calendar year ``Y`` pulls annual frames ``[Y-lookback+1, Y]`` via
    ``build_scoring_frames_from_providers`` and keys by ``assumed_filed_at(Y)``.

    Disk cache theo năm (ghi ngay sau mỗi năm → resume nếu Ctrl+C)::

        data/cache/scoring_schedule/{key}/year_{Y}.pkl

    ``refresh=True`` (hoặc ``--refresh-data`` / ``--refresh-fundamentals``) bỏ qua
    cache và ghi đè. Cache hit → 0 API call cho năm đó.
    """
    import pickle

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
    tickers_u = [str(t).strip().upper() for t in tickers if str(t).strip()]

    cache_key = _scoring_schedule_cache_key(
        tickers_u,
        lookback_years=lookback_years,
        lag_days=lag,
        include_prior_year=include_prior_year,
        config=config,
    )
    root = Path(cache_dir) if cache_dir is not None else _default_scoring_cache_dir(config)
    year_dir = root / cache_key
    year_dir.mkdir(parents=True, exist_ok=True)
    meta_path = year_dir / "meta.json"
    if not meta_path.exists():
        meta_path.write_text(
            json.dumps(
                {
                    "schema_version": _SCORING_SCHEDULE_CACHE_SCHEMA,
                    "cache_key": cache_key,
                    "tickers": tickers_u,
                    "lookback_years": lookback_years,
                    "lag_days": lag,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    schedule: dict[str, dict[str, Any]] = {}
    hits = 0
    misses = 0
    years = list(range(first_y, end_y + 1))
    n_years = len(years)
    miss_secs: list[float] = []
    import time as _time

    for yi, year in enumerate(years):
        frame_start = year - lookback_years + 1
        year_path = year_dir / f"year_{year}.pkl"
        filed = assumed_filed_at(year, lag)

        if not refresh and year_path.is_file():
            try:
                with year_path.open("rb") as fh:
                    frames = pickle.load(fh)
                if isinstance(frames, dict) and frames:
                    schedule[filed] = frames
                    hits += 1
                    _safe_print(
                        f"scoring_schedule: year={year} CACHE HIT -> {year_path.name} "
                        f"({year_path})"
                    )
                    continue
            except Exception as exc:  # noqa: BLE001
                _safe_print(
                    f"scoring_schedule: year={year} cache corrupt ({exc}); rebuild"
                )

        remaining = n_years - yi
        if miss_secs:
            eta_s = float(sum(miss_secs) / len(miss_secs)) * remaining
            eta_msg = f" ETA~{eta_s / 60.0:.1f}min ({remaining} years left @ avg miss)"
        else:
            eta_msg = f" (CACHE MISS - cold year; {remaining} years in window)"
        _safe_print(
            f"scoring_schedule: year={year} CACHE MISS -> fetch frames={frame_start}..{year}"
            f"{eta_msg}"
        )
        t0 = _time.perf_counter()
        frames = build_scoring_frames_from_providers(
            tickers_u,
            frame_start,
            year,
            config=dict(config or {}),
            db_path=db_path,
        )
        elapsed = _time.perf_counter() - t0
        miss_secs.append(elapsed)
        misses += 1
        if not frames:
            print(
                f"scoring_schedule: skip empty frames for year={year} "
                f"({elapsed:.1f}s)",
                flush=True,
            )
            continue
        schedule[filed] = frames
        # Ghi ngay sau mỗi năm (resume-friendly).
        try:
            with year_path.open("wb") as fh:
                pickle.dump(frames, fh, protocol=pickle.HIGHEST_PROTOCOL)
            print(
                f"scoring_schedule: year={year} wrote {year_path} ({elapsed:.1f}s)",
                flush=True,
            )
        except Exception as exc:  # noqa: BLE001
            print(
                f"scoring_schedule: year={year} cache write failed ({exc})",
                flush=True,
            )

    print(
        f"scoring_schedule: done cache_key={cache_key} hits={hits} misses={misses} "
        f"keys={len(schedule)} refresh={refresh} dir={year_dir}",
        flush=True,
    )
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
    order = list(layers_order or DEFAULT_LAYERS)
    steps = []
    signal_closes = _signal_closes(close_by_ticker, config)

    for layer in order:
        print(f"ablation step: {layer} ...", flush=True)
        if layer == "B0_buyhold":
            result = _buyhold_result(signal_closes, start_date, end_date, config)
            label = "B0_buyhold"
        elif layer == "fundamental":
            # Dynamic PIT equal-weight PASS/WATCH (không look-ahead end_date).
            result = _dynamic_fundamental_result(
                signal_closes,
                start_date,
                end_date,
                config,
                scoring_schedule,
            )
            label = "fundamental"
        elif layer == "regime":
            # Regime on; alpha off (alpha_eff NaN → WATCH-heavy — isolates regime).
            # P2-2: signal_tickers=None → engine dùng watchlist Tầng 1 động (khớp live).
            cfg = _set_quant_flags(config, regime=True, alpha=False, risk=False)
            result = run_backtest(
                cfg,
                start_date,
                end_date,
                close_by_ticker=close_by_ticker,
                scoring_schedule=scoring_schedule,
                signal_every_n_days=signal_every_n_days,
                signal_tickers=None,
            )
            label = "regime"
        elif layer == "alpha":
            # P2-2: signal_tickers=None → engine dùng watchlist Tầng 1 động (khớp live).
            cfg = _set_quant_flags(config, regime=True, alpha=True, risk=False)
            result = run_backtest(
                cfg,
                start_date,
                end_date,
                close_by_ticker=close_by_ticker,
                scoring_schedule=scoring_schedule,
                signal_every_n_days=signal_every_n_days,
                signal_tickers=None,
            )
            label = "alpha"
        elif layer == "risk":
            # P2-2: signal_tickers=None → engine dùng watchlist Tầng 1 động (khớp live).
            cfg = _set_quant_flags(config, regime=True, alpha=True, risk=True)
            result = run_backtest(
                cfg,
                start_date,
                end_date,
                close_by_ticker=close_by_ticker,
                scoring_schedule=scoring_schedule,
                signal_every_n_days=signal_every_n_days,
                signal_tickers=None,
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
                # Giữ curve để persist store → bot /backtest vẽ equity/DD.
                "equity_curve": list(result.get("equity_curve") or []),
            }
        )

    # Baseline song song B1/B2 (mục 10/11.3) — không nằm trong stack keep/cut.
    for label, runner in (
        ("B1_ta", _b1_ta_result),
        ("B2_canslim", _b2_canslim_result),
    ):
        print(f"ablation step: {label} ...", flush=True)
        result = runner(signal_closes, start_date, end_date, config)
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
                "equity_curve": list(result.get("equity_curve") or []),
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
        elif row.get("layer") in {"B1_ta", "B2_canslim"}:
            row["delta_sharpe"] = None
            row["decision"] = "baseline (parallel)"
            annotated.append(row)
            continue
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


_VALID_BASELINES = frozenset({"framework", "B0_buyhold", "B1_ta", "B2_canslim"})


def _equity_curve_json(source: Mapping[str, Any] | None) -> str | None:
    """Serialize ``equity_curve`` list → JSON text cho ``backtest_results``."""
    if not source:
        return None
    curve = source.get("equity_curve")
    if not isinstance(curve, list) or not curve:
        return None
    try:
        return json.dumps(curve, ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError):
        return None


def _metrics_from_step(step: Mapping[str, Any]) -> dict:
    """CORE + ADD-ON từ bước ablation / metrics dict lồng nhau."""
    nested = step.get("metrics") if isinstance(step.get("metrics"), Mapping) else {}
    src = {**dict(nested), **dict(step)}
    keys = (
        "cagr",
        "sharpe",
        "max_drawdown",
        "win_rate",
        "n_trades",
        "turnover",
        "sortino",
        "calmar",
        "profit_factor",
        "max_drawdown_days",
        "margin_bps",
        "cvar95_realized",
        "cvar95_calibration_note",
        "sharpe_bull_regime",
        "sharpe_bear_regime",
    )
    return {k: _json_safe(src.get(k)) for k in keys}


def _enrich_metrics_from_equity(
    source: Mapping[str, Any],
    config: Mapping[str, Any] | None = None,
) -> dict:
    """Bổ sung Sortino/Calmar/margin_bps từ equity_curve nếu artifact cũ thiếu."""
    from backtest.metrics import compute_metrics

    base = _metrics_from_step(source)
    curve = source.get("equity_curve")
    if not isinstance(curve, list) or len(curve) < 2:
        return base
    need = any(
        base.get(k) is None for k in ("sortino", "calmar", "turnover", "margin_bps")
    )
    if not need:
        return base
    computed = compute_metrics(curve, list(source.get("trades") or []), config)
    out = dict(base)
    has_trades = bool(source.get("trades"))
    for key in (
        "turnover",
        "sortino",
        "calmar",
        "profit_factor",
        "max_drawdown_days",
        "margin_bps",
    ):
        if out.get(key) is not None:
            continue
        val = computed.get(key)
        if val is None:
            continue
        # Không gán turnover=0 giả khi artifact không có trades (tránh MAX_TURNOVER ảo).
        if key in {"turnover", "margin_bps"} and not has_trades:
            continue
        safe = _json_safe(val)
        if safe is None:
            continue
        out[key] = safe
    return out


def build_backtest_checks(
    rows_by_baseline: Mapping[str, Mapping[str, Any]],
    *,
    run_id: str,
    scope: str,
    config: Mapping[str, Any] | None = None,
    max_position_weight: float | None = None,
) -> list[dict]:
    """Đối chiếu ngưỡng đã đăng ký trong ``backtest.checks`` → rows store.

    Gồm MIN_SHARPE_IMPROVEMENT_OOS, MIN_TRADES_FOR_SIGNIFICANCE, MAX_TURNOVER,
    CONCENTRATED_WEIGHT (max_position_weight_pct).
    """
    cfg = dict(config or {})
    checks_cfg = dict((cfg.get("backtest") or {}).get("checks") or {})
    min_delta = float(checks_cfg.get("min_sharpe_improvement_oos", 0.10))
    min_trades = int(checks_cfg.get("min_trades_for_significance", 30))
    max_to = float(checks_cfg.get("max_turnover_pct", 200))
    max_w = float(
        checks_cfg.get(
            "max_position_weight_pct",
            (cfg.get("quant_engine") or {}).get("w_max", 0.10),
        )
    )

    fw = dict(rows_by_baseline.get("framework") or {})
    b0 = dict(rows_by_baseline.get("B0_buyhold") or {})
    out: list[dict] = []

    def _row(
        name: str,
        threshold: float,
        actual: float | None,
        passed: bool,
        note: str,
        baseline: str = "framework",
    ) -> dict:
        return {
            "run_id": run_id,
            "scope": scope,
            "baseline": baseline,
            "check_name": name,
            "threshold": threshold,
            "actual_value": _json_safe(actual),
            "passed": 1 if passed else 0,
            "note": note,
        }

    n_trades = fw.get("n_trades")
    try:
        n_i = int(n_trades) if n_trades is not None else 0
    except (TypeError, ValueError):
        n_i = 0
    out.append(
        _row(
            "MIN_TRADES_FOR_SIGNIFICANCE",
            float(min_trades),
            float(n_i),
            n_i >= min_trades,
            f"n_trades={n_i}; dưới ngưỡng thì Sharpe chỉ minh hoạ",
        )
    )

    try:
        s_fw = float(fw["sharpe"]) if fw.get("sharpe") is not None else None
    except (TypeError, ValueError):
        s_fw = None
    try:
        s_b0 = float(b0["sharpe"]) if b0.get("sharpe") is not None else None
    except (TypeError, ValueError):
        s_b0 = None
    delta = (s_fw - s_b0) if s_fw is not None and s_b0 is not None else None
    out.append(
        _row(
            "MIN_SHARPE_IMPROVEMENT_OOS",
            min_delta,
            delta,
            bool(delta is not None and delta >= min_delta),
            (
                f"ΔSharpe OOS framework−B0={delta}"
                if delta is not None
                else "thiếu Sharpe framework hoặc B0"
            ),
        )
    )

    to = fw.get("turnover")
    try:
        to_f = float(to) if to is not None else None
    except (TypeError, ValueError):
        to_f = None
    to_pct_year = (to_f * 252.0 * 100.0) if to_f is not None else None
    out.append(
        _row(
            "MAX_TURNOVER",
            max_to,
            to_pct_year,
            bool(to_pct_year is not None and to_pct_year <= max_to),
            (
                f"turnover≈{to_pct_year:.1f}%/năm (ước từ daily)"
                if to_pct_year is not None
                else "thiếu turnover — không kết luận"
            ),
        )
    )

    actual_w = max_position_weight
    if actual_w is None:
        actual_w = float((cfg.get("quant_engine") or {}).get("w_max", max_w))
        note_w = (
            f"design_cap=w_max={actual_w}; "
            "không có max weight quan sát trong artifact"
        )
    else:
        note_w = f"max_position_weight quan sát={actual_w}"
    out.append(
        _row(
            "CONCENTRATED_WEIGHT",
            max_w,
            float(actual_w),
            float(actual_w) <= max_w + 1e-12,
            note_w,
        )
    )
    return out


def ablation_payload_to_store_rows(
    payload: Mapping[str, Any],
    *,
    run_id: str | None = None,
    run_at: str | None = None,
    scope: str = "portfolio",
    config: Mapping[str, Any] | None = None,
) -> list[dict]:
    """Map ablation JSON → rows cho ``store.backtest_results``.

    Ghi baseline: B0_buyhold, B1_ta, B2_canslim + framework (walk-forward hoặc
    bước stack cuối). Các tầng ablation trung gian giữ trong JSON.
    """
    from datetime import datetime, timezone

    rid = run_id or f"ablation_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    rat = run_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows: list[dict] = []

    steps = list(payload.get("steps") or [])
    by_layer = {str(s.get("layer")): s for s in steps if isinstance(s, dict)}

    for layer_key in ("B0_buyhold", "B1_ta", "B2_canslim"):
        step = by_layer.get(layer_key)
        if not step:
            continue
        metrics = _enrich_metrics_from_equity(step, config)
        rows.append(
            {
                "run_id": rid,
                "run_at": rat,
                "scope": scope,
                "baseline": layer_key,
                **metrics,
                "equity_curve_json": _equity_curve_json(step),
            }
        )

    fw: Mapping[str, Any] | None = None
    wf = payload.get("walk_forward")
    if isinstance(wf, dict) and (
        wf.get("sharpe") is not None or wf.get("cagr") is not None
    ):
        fw = wf
    else:
        for layer in ("risk", "alpha", "regime", "fundamental"):
            step = by_layer.get(layer)
            if step and (
                step.get("sharpe") is not None or step.get("n_trades")
            ):
                fw = step
                break

    if fw:
        metrics = _enrich_metrics_from_equity(fw, config)
        rows.append(
            {
                "run_id": rid,
                "run_at": rat,
                "scope": scope,
                "baseline": "framework",
                **metrics,
                "equity_curve_json": _equity_curve_json(fw),
            }
        )

    # Lọc an toàn — tránh vi phạm CHECK baseline
    return [r for r in rows if r.get("baseline") in _VALID_BASELINES]


def ablation_payload_to_yearly_rows(
    payload: Mapping[str, Any],
    *,
    run_id: str,
    scope: str = "portfolio",
    config: Mapping[str, Any] | None = None,
) -> list[dict]:
    """Sinh ``backtest_yearly_breakdown`` từ equity_curve framework (OOS ưu tiên)."""
    from backtest.metrics import yearly_breakdown_from_equity

    source: Mapping[str, Any] | None = None
    wf = payload.get("walk_forward")
    if isinstance(wf, dict) and wf.get("equity_curve"):
        source = wf
    else:
        for step in payload.get("steps") or []:
            if isinstance(step, dict) and step.get("layer") == "risk":
                source = step
                break
    if not source:
        return []
    curve = list(source.get("equity_curve") or [])
    yearly = yearly_breakdown_from_equity(
        curve, list(source.get("trades") or []), config
    )
    return [
        {
            "run_id": run_id,
            "scope": scope,
            "baseline": "framework",
            **{
                k: _json_safe(y.get(k))
                for k in (
                    "year",
                    "cagr",
                    "sharpe",
                    "max_drawdown",
                    "turnover",
                    "margin_bps",
                    "n_trades",
                )
            },
        }
        for y in yearly
    ]


def persist_ablation_to_store(
    payload: Mapping[str, Any],
    *,
    db_path: str = "store/bot.db",
    run_id: str | None = None,
    scope: str = "portfolio",
    config: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Ghi kết quả ablation vào store để bot /backtest đọc được.

    Gồm ``backtest_results`` + ``backtest_checks`` (+ yearly nếu có curve).
    """
    from store import repository

    cfg = config
    if cfg is None:
        try:
            cfg = _load_config("pipeline/config.yaml")
        except OSError:
            cfg = {}

    rows = ablation_payload_to_store_rows(
        payload, run_id=run_id, scope=scope, config=cfg
    )
    if not rows:
        return {"rows": 0, "note": "no persistable baselines in payload"}
    rid = str(rows[0]["run_id"])
    by_base = {str(r["baseline"]): r for r in rows}
    max_w_obs = None
    for key in ("max_position_weight", "max_size"):
        if payload.get(key) is not None:
            try:
                max_w_obs = float(payload[key])
            except (TypeError, ValueError):
                max_w_obs = None
            break
    checks = build_backtest_checks(
        by_base,
        run_id=rid,
        scope=scope,
        config=cfg,
        max_position_weight=max_w_obs,
    )
    yearly = ablation_payload_to_yearly_rows(
        payload, run_id=rid, scope=scope, config=cfg
    )

    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        repository.upsert_backtest_results(conn, rows)
        if checks:
            repository.upsert_backtest_checks(conn, checks)
        if yearly:
            repository.upsert_yearly_breakdown(conn, yearly)
    finally:
        conn.close()
    return {
        "rows": len(rows),
        "run_id": rid,
        "baselines": [r["baseline"] for r in rows],
        "checks": len(checks),
        "yearly": len(yearly),
        "note": (
            f"upserted {len(rows)} backtest_results, "
            f"{len(checks)} checks, {len(yearly)} yearly"
        ),
    }


def persist_ablation_json(
    json_path: str | Path,
    *,
    db_path: str = "store/bot.db",
    scope: str = "portfolio",
) -> dict[str, Any]:
    """Đọc file ablation JSON đã có → ghi store (dùng lại artifact cũ)."""
    path = Path(json_path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    run_id = path.stem
    return persist_ablation_to_store(
        payload, db_path=db_path, run_id=run_id, scope=scope
    )


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
        help="SQLite path for sector_mapping + backtest_results (default: store/bot.db)",
    )
    parser.add_argument(
        "--no-persist-store",
        action="store_true",
        help="Không ghi backtest_results (mặc định: có ghi để /backtest đọc được)",
    )
    parser.add_argument(
        "--walk-forward",
        action="store_true",
        help="Also run walk-forward OOS on full P0 stack (regime+alpha+risk)",
    )
    parser.add_argument(
        "--refresh-fundamentals",
        action="store_true",
        help="Bỏ qua disk cache scoring_schedule theo năm",
    )
    parser.add_argument(
        "--refresh-data",
        action="store_true",
        help="Refresh fund cache + tắt OHLCV cache lần chạy này",
    )
    args = parser.parse_args(argv)

    config = _load_config(args.config)
    refresh_fund = bool(args.refresh_fundamentals or args.refresh_data)
    if args.refresh_data:
        from copy import deepcopy as _deepcopy

        config = _deepcopy(config)
        sources = dict(config.get("data_sources") or {})
        price = dict(sources.get("price") or {})
        price["cache_ohlcv"] = False
        sources["price"] = price
        config["data_sources"] = sources
        print("refresh-data: OHLCV cache disabled for this run", flush=True)
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
            refresh=refresh_fund,
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
        # P2-2: signal_tickers=None → watchlist Tầng 1 động (khớp live daily_job).
        wf = run_walk_forward(
            wf_cfg,
            start,
            end,
            close_by_ticker=closes,
            scoring_schedule=scoring_schedule,
            signal_every_n_days=max(int(args.signal_every), 1),
            signal_tickers=None,
        )
        wm = wf.get("metrics") or {}
        walk_forward_payload = {
            "n_folds": int(wf.get("n_folds") or len(wf.get("folds") or [])),
            "cagr": _json_safe(wm.get("cagr")),
            "sharpe": _json_safe(wm.get("sharpe")),
            "max_drawdown": _json_safe(wm.get("max_drawdown")),
            "win_rate": _json_safe(wm.get("win_rate")),
            "n_trades": wm.get("n_trades"),
            "turnover": _json_safe(wm.get("turnover")),
            "sortino": _json_safe(wm.get("sortino")),
            "calmar": _json_safe(wm.get("calmar")),
            "profit_factor": _json_safe(wm.get("profit_factor")),
            "max_drawdown_days": _json_safe(wm.get("max_drawdown_days")),
            "margin_bps": _json_safe(wm.get("margin_bps")),
            "fold_sharpes": [
                _json_safe(x) for x in (wf.get("fold_sharpes") or [])
            ],
            "fold_sharpe_mean": _json_safe(wf.get("fold_sharpe_mean")),
            "fold_sharpe_std": _json_safe(wf.get("fold_sharpe_std")),
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
            f"cagr={walk_forward_payload['cagr']} "
            f"fold_sharpe_mean={walk_forward_payload['fold_sharpe_mean']} "
            f"fold_sharpe_std={walk_forward_payload['fold_sharpe_std']}",
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
                "turnover": _json_safe((s.get("metrics") or {}).get("turnover")),
                "sortino": _json_safe((s.get("metrics") or {}).get("sortino")),
                "calmar": _json_safe((s.get("metrics") or {}).get("calmar")),
                "margin_bps": _json_safe((s.get("metrics") or {}).get("margin_bps")),
                "delta_sharpe": _json_safe(s.get("delta_sharpe")),
                "decision": s.get("decision"),
                "equity_curve": list(s.get("equity_curve") or []),
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
    if not args.no_persist_store:
        persisted = persist_ablation_to_store(
            payload,
            db_path=args.db_path,
            run_id=out_path.stem,
            scope="portfolio",
        )
        print(f"store: {persisted.get('note')}", flush=True)
    try:
        print(format_steps_table(steps), flush=True)
    except UnicodeEncodeError:
        # Windows cp1252 consoles — metrics already in JSON
        print(format_steps_table(steps).encode("ascii", "replace").decode("ascii"), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
