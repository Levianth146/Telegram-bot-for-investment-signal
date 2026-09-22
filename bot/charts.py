"""Vẽ chart để bot gửi qua Telegram (ảnh PNG, gửi qua sendPhoto).

QUAN TRỌNG — cùng ranh giới với formatters.py: các hàm ở đây CHỈ ĐỌC dữ liệu đã
tính sẵn trong store/ (hoặc backtest_results), KHÔNG được tự tính lại mô hình.
Nếu số liệu cần cho 1 chart chưa có trong DB, hàm phải raise lỗi rõ ràng thay vì
tự ước tính.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


class ChartDataError(ValueError):
    """Raised when required store/input series are missing (do not invent numbers)."""


def _ensure_out(out_path: str | Path) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _save(fig, out_path: Path) -> Path:
    fig.tight_layout()
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return out_path


def _dates_values(rows: Sequence[Mapping[str, Any]], value_key: str) -> tuple[list[str], list[float]]:
    dates: list[str] = []
    values: list[float] = []
    for row in rows:
        if row.get(value_key) is None:
            continue
        dates.append(str(row.get("date") or row.get("time") or ""))
        values.append(float(row[value_key]))
    return dates, values


def render_price_regime_chart(
    ticker: str,
    price_history: list[dict],
    kalman_trend: list[dict],
    regime_history: list[dict],
    out_path: str | Path,
) -> Path:
    """Giá + đường trend Kalman + nền tô theo regime (bull/bear)."""
    if not price_history:
        raise ChartDataError(f"No price_history for {ticker}")
    out = _ensure_out(out_path)
    dates, prices = _dates_values(price_history, "close")
    if len(prices) < 2:
        raise ChartDataError(f"Insufficient price points for {ticker}")

    fig, ax = plt.subplots(figsize=(9, 4.5))
    # Regime background from regime_history [{date, p_bull}]
    if regime_history:
        regime_map = {
            str(r.get("date")): float(r["p_bull"])
            for r in regime_history
            if r.get("p_bull") is not None
        }
        for i in range(len(dates) - 1):
            p = regime_map.get(dates[i])
            if p is None:
                continue
            color = "#c6efce" if p >= 0.55 else ("#ffc7ce" if p <= 0.35 else "#ffeb9c")
            ax.axvspan(i, i + 1, color=color, alpha=0.35, lw=0)

    ax.plot(range(len(prices)), prices, color="#1f4e79", lw=1.4, label="Close")
    if kalman_trend:
        _, levels = _dates_values(kalman_trend, "level")
        if levels:
            ax.plot(
                range(min(len(levels), len(prices))),
                levels[: len(prices)],
                color="#c45911",
                lw=1.2,
                label="Kalman level",
            )
    ax.set_title(f"{ticker} — price + regime")
    ax.set_xlabel("session")
    ax.set_ylabel("price")
    ax.legend(loc="best", fontsize=8)
    n = len(dates)
    step = max(n // 6, 1)
    ax.set_xticks(range(0, n, step))
    ax.set_xticklabels([dates[i] for i in range(0, n, step)], rotation=30, ha="right")
    return _save(fig, out)


def render_price_chart(
    ticker: str,
    closes: Sequence[Mapping[str, Any]],
    out_path: str | Path,
) -> Path:
    """Close-only chart từ ``store.price_bars`` (không Kalman/regime — bot V1)."""
    return render_price_regime_chart(
        ticker,
        list(closes),
        kalman_trend=[],
        regime_history=[],
        out_path=out_path,
    )


def render_garch_risk_band_chart(
    ticker: str,
    price_history: list[dict],
    sigma_hat_history: list[dict],
    out_path: str | Path,
) -> Path:
    """Dải biến động dự báo GARCH quanh giá."""
    if not price_history or not sigma_hat_history:
        raise ChartDataError(f"Need price_history + sigma_hat_history for {ticker}")
    out = _ensure_out(out_path)
    dates, prices = _dates_values(price_history, "close")
    sigma_map = {
        str(r.get("date")): float(r["sigma_hat"])
        for r in sigma_hat_history
        if r.get("sigma_hat") is not None
    }
    upper, lower = [], []
    for i, date in enumerate(dates):
        px = prices[i]
        sig = sigma_map.get(date, float("nan"))
        if math.isnan(sig):
            upper.append(float("nan"))
            lower.append(float("nan"))
        else:
            upper.append(px * (1.0 + 2.0 * sig))
            lower.append(px * (1.0 - 2.0 * sig))

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(prices))
    ax.plot(x, prices, color="#1f4e79", lw=1.3, label="Close")
    ax.fill_between(x, lower, upper, color="#5b9bd5", alpha=0.25, label="±2σ̂ band")
    ax.set_title(f"{ticker} — GARCH risk band")
    ax.legend(loc="best", fontsize=8)
    return _save(fig, out)


def render_realized_vol_band_chart(
    ticker: str,
    price_history: list[dict],
    out_path: str | Path,
    *,
    window: int = 20,
    latest_sigma_hat: float | None = None,
) -> Path:
    """Dải ±2σ từ biến động thực tế (rolling) — khi chưa có lịch sử GARCH trong store.

    Không thay thế GARCH forecast; dùng cho /chart risk V1 khi chỉ có price_bars.
    """
    if len(price_history) < max(window + 2, 30):
        raise ChartDataError(
            f"Chưa đủ lịch sử giá để vẽ risk cho {ticker} "
            f"(cần ≥{max(window + 2, 30)} phiên)."
        )
    out = _ensure_out(out_path)
    _dates, prices = _dates_values(price_history, "close")
    px = np.asarray(prices, dtype=float)
    rets = np.diff(np.log(px))
    # Rolling std of returns → band around price
    upper: list[float] = [float("nan")]
    lower: list[float] = [float("nan")]
    for i in range(1, len(px)):
        start = max(0, i - window)
        window_rets = rets[start:i]
        if len(window_rets) < 5:
            upper.append(float("nan"))
            lower.append(float("nan"))
            continue
        sig = float(np.std(window_rets, ddof=1))
        upper.append(px[i] * (1.0 + 2.0 * sig))
        lower.append(px[i] * (1.0 - 2.0 * sig))

    fig, ax = plt.subplots(figsize=(9, 4.5))
    x = range(len(px))
    ax.plot(x, px, color="#1f4e79", lw=1.3, label="Giá đóng cửa")
    ax.fill_between(
        x, lower, upper, color="#5b9bd5", alpha=0.25, label=f"±2σ rolling {window}đ"
    )
    if latest_sigma_hat is not None and latest_sigma_hat > 0:
        last = float(px[-1])
        ax.axhline(
            last * (1.0 + 2.0 * float(latest_sigma_hat)),
            color="#ed7d31",
            ls="--",
            lw=1.0,
            label="GARCH σ̂ phiên gần nhất (±2)",
        )
        ax.axhline(
            last * (1.0 - 2.0 * float(latest_sigma_hat)),
            color="#ed7d31",
            ls="--",
            lw=1.0,
        )
    ax.set_title(f"{ticker} — Biến động thực tế (rolling)")
    ax.legend(loc="best", fontsize=8)
    fig.text(
        0.5,
        0.01,
        "Tham khảo — dải rolling từ giá; σ̂ GARCH đầy đủ khi có lịch sử store",
        ha="center",
        fontsize=8,
    )
    return _save(fig, out)


def render_monte_carlo_distribution_chart(
    ticker: str,
    mc_outcomes: list[float],
    tp_pct: float,
    sl_pct: float,
    out_path: str | Path,
) -> Path:
    """Histogram phân phối kết quả mô phỏng Monte Carlo."""
    if not mc_outcomes:
        raise ChartDataError(f"No Monte Carlo outcomes for {ticker}")
    out = _ensure_out(out_path)
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(mc_outcomes, bins=40, color="#5b9bd5", edgecolor="white", alpha=0.9)
    ax.axvline(tp_pct, color="#548235", lw=1.5, label=f"TP {tp_pct:.1%}")
    ax.axvline(-abs(sl_pct), color="#c00000", lw=1.5, label=f"SL {-abs(sl_pct):.1%}")
    ax.set_title(f"{ticker} — Monte Carlo return distribution")
    ax.set_xlabel("horizon return")
    ax.legend(fontsize=8)
    return _save(fig, out)


def render_fundamental_radar_chart(
    ticker: str,
    growth_score: float,
    quality_score: float,
    safety_score: float,
    valuation_score: float,
    out_path: str | Path,
) -> Path:
    """Radar 4 trục Growth/Quality/Safety/Valuation."""
    scores = [growth_score, quality_score, safety_score, valuation_score]
    if any(s is None or (isinstance(s, float) and math.isnan(s)) for s in scores):
        raise ChartDataError(f"Incomplete fundamental scores for {ticker}")
    out = _ensure_out(out_path)
    labels = ["Growth", "Quality", "Safety", "Valuation"]
    values = [float(s) for s in scores]
    values += values[:1]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5.5, 5.5), subplot_kw={"polar": True})
    ax.plot(angles, values, color="#1f4e79", lw=1.5)
    ax.fill(angles, values, color="#5b9bd5", alpha=0.35)
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 100)
    ax.set_title(f"{ticker} — fundamental radar", pad=16)
    return _save(fig, out)


def render_ta_reference_chart(
    ticker: str,
    price_history: list[dict],
    ta_indicators: dict,
    out_path: str | Path,
) -> Path:
    """RSI/EMA/Volume — chỉ khi user xin /chart <mã> ta."""
    if not price_history:
        raise ChartDataError(f"No price_history for TA chart {ticker}")
    out = _ensure_out(out_path)
    dates, prices = _dates_values(price_history, "close")
    volumes = [float(r.get("volume") or 0) for r in price_history]

    fig, (ax_p, ax_v) = plt.subplots(
        2, 1, figsize=(9, 5.5), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )
    ax_p.plot(range(len(prices)), prices, color="#1f4e79", lw=1.2, label="Close")
    ema = ta_indicators.get("ema_20") or ta_indicators.get("ema")
    if isinstance(ema, list) and ema:
        ax_p.plot(range(min(len(ema), len(prices))), ema[: len(prices)], color="#ed7d31", label="EMA")
    ax_p.set_title(f"{ticker} — Tham khảo TA (không ra tín hiệu)")
    ax_p.legend(fontsize=8)
    ax_v.bar(range(len(volumes)), volumes, color="#a5a5a5", width=1.0)
    ax_v.set_ylabel("KL")
    fig.text(0.5, 0.01, "Tham khảo thêm — không dùng để ra tín hiệu", ha="center", fontsize=9)
    return _save(fig, out)


def _load_backtest_curves(
    scope: str, run_id: str, db_path: str = "store/bot.db"
) -> list[dict]:
    from store import repository

    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        rows = repository.get_backtest_results(conn, scope, run_id)
    finally:
        conn.close()
    if not rows:
        raise ChartDataError(
            f"chưa có kết quả backtest scope={scope} run_id={run_id}, "
            "chờ lần chạy định kỳ tiếp theo"
        )
    return rows


def _parse_equity(row: Mapping[str, Any]) -> list[dict]:
    raw = row.get("equity_curve_json")
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    try:
        data = json.loads(str(raw))
    except json.JSONDecodeError as exc:
        raise ChartDataError("equity_curve_json is not valid JSON") from exc
    return data if isinstance(data, list) else []


def render_backtest_equity_curve_chart(
    scope: str,
    run_id: str,
    out_path: str | Path,
    *,
    db_path: str = "store/bot.db",
) -> Path:
    """Equity curve framework + baselines từ backtest_results."""
    rows = _load_backtest_curves(scope, run_id, db_path=db_path)
    out = _ensure_out(out_path)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    plotted = 0
    for row in rows:
        curve = _parse_equity(row)
        if not curve:
            continue
        dates, equity = _dates_values(curve, "equity")
        if not equity:
            continue
        ax.plot(range(len(equity)), equity, lw=1.3, label=str(row.get("baseline", "?")))
        plotted += 1
    if plotted == 0:
        raise ChartDataError("backtest_results rows have empty equity_curve_json")
    ax.set_title(f"Backtest equity | {scope} | {run_id}")
    ax.legend(fontsize=8)
    ax.set_ylabel("equity")
    return _save(fig, out)


def render_drawdown_chart(
    scope: str,
    run_id: str,
    out_path: str | Path,
    *,
    db_path: str = "store/bot.db",
) -> Path:
    """Underwater/drawdown chart từ equity_curve_json (framework baseline ưu tiên)."""
    rows = _load_backtest_curves(scope, run_id, db_path=db_path)
    out = _ensure_out(out_path)
    preferred = next((r for r in rows if r.get("baseline") == "framework"), rows[0])
    curve = _parse_equity(preferred)
    if not curve:
        raise ChartDataError("no equity_curve_json for drawdown chart")
    _, equity = _dates_values(curve, "equity")
    series = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(series)
    dd = series / peak - 1.0

    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.fill_between(range(len(dd)), dd, 0, color="#c00000", alpha=0.45)
    ax.set_title(f"Drawdown | {scope} | {run_id}")
    ax.set_ylabel("drawdown")
    return _save(fig, out)


def render_rolling_sharpe_chart(
    scope: str,
    run_id: str,
    window_days: int = 126,
    out_path: str | Path | None = None,
    *,
    db_path: str = "store/bot.db",
) -> Path:
    """Sharpe cửa sổ trượt từ equity curve."""
    if out_path is None:
        raise ChartDataError("out_path is required")
    rows = _load_backtest_curves(scope, run_id, db_path=db_path)
    out = _ensure_out(out_path)
    preferred = next((r for r in rows if r.get("baseline") == "framework"), rows[0])
    curve = _parse_equity(preferred)
    _, equity = _dates_values(curve, "equity")
    if len(equity) < window_days + 2:
        raise ChartDataError("equity curve too short for rolling Sharpe")
    rets = np.diff(np.log(np.asarray(equity, dtype=float)))
    roll = []
    for i in range(window_days, len(rets) + 1):
        window = rets[i - window_days : i]
        sigma = float(np.std(window, ddof=1))
        if sigma <= 0:
            roll.append(float("nan"))
        else:
            roll.append(float(np.sqrt(252) * np.mean(window) / sigma))

    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(range(len(roll)), roll, color="#1f4e79", lw=1.2)
    ax.axhline(0, color="#888", lw=0.8)
    ax.set_title(f"Rolling Sharpe ({window_days}d) | {scope}")
    return _save(fig, out)


def render_trade_pnl_histogram(
    scope: str,
    run_id: str,
    out_path: str | Path,
    *,
    closed_trades: list[dict] | None = None,
    db_path: str = "store/bot.db",
) -> Path:
    """Histogram PnL% lệnh đã đóng (truyền closed_trades hoặc đọc positions CLOSED)."""
    out = _ensure_out(out_path)
    trades = closed_trades
    if trades is None:
        from store import repository

        conn = repository.get_connection(db_path)
        try:
            repository.init_schema(conn)
            cur = conn.execute(
                """
                SELECT pnl_pct FROM positions
                WHERE status = 'CLOSED' AND pnl_pct IS NOT NULL
                """
            )
            trades = [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
    pnls = [float(t["pnl_pct"]) for t in trades if t.get("pnl_pct") is not None]
    if not pnls:
        raise ChartDataError(
            f"No closed-trade PnL for histogram (scope={scope}, run_id={run_id})"
        )
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(pnls, bins=30, color="#70ad47", edgecolor="white")
    ax.set_title(f"Closed trade PnL% | {scope}")
    ax.set_xlabel("pnl_pct")
    return _save(fig, out)


def render_regime_conditional_equity_chart(
    scope: str,
    run_id: str,
    out_path: str | Path,
    *,
    db_path: str = "store/bot.db",
    regime_history: list[dict] | None = None,
) -> Path:
    """Equity curve tô màu theo regime (cần regime_history [{date,p_bull}] kèm theo)."""
    rows = _load_backtest_curves(scope, run_id, db_path=db_path)
    out = _ensure_out(out_path)
    preferred = next((r for r in rows if r.get("baseline") == "framework"), rows[0])
    curve = _parse_equity(preferred)
    if not curve:
        raise ChartDataError("no equity curve for regime-conditional chart")
    dates, equity = _dates_values(curve, "equity")
    regime_map = {}
    if regime_history:
        regime_map = {
            str(r.get("date")): float(r["p_bull"])
            for r in regime_history
            if r.get("p_bull") is not None
        }

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(range(len(equity)), equity, color="#1f4e79", lw=1.3)
    for i in range(len(dates) - 1):
        p = regime_map.get(dates[i])
        if p is None:
            continue
        color = "#c6efce" if p >= 0.55 else ("#ffc7ce" if p <= 0.35 else "#ffeb9c")
        ax.axvspan(i, i + 1, color=color, alpha=0.3, lw=0)
    ax.set_title(f"Regime-conditional equity | {scope}")
    note = preferred.get("sharpe_bull_regime"), preferred.get("sharpe_bear_regime")
    ax.text(
        0.01,
        0.02,
        f"sharpe_bull={note[0]} sharpe_bear={note[1]}",
        transform=ax.transAxes,
        fontsize=8,
    )
    return _save(fig, out)


def render_sector_overview_chart(
    as_of_date: str,
    out_path: str | Path,
    *,
    db_path: str = "store/bot.db",
) -> Path:
    """PASS/WATCH/FAIL counts theo ngành từ store."""
    from store import repository

    out = _ensure_out(out_path)
    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        rows = repository.get_sector_overview(conn, as_of_date)
    finally:
        conn.close()
    if not rows:
        raise ChartDataError(f"No sector overview for {as_of_date}")

    industries = [str(r["industry"]) for r in rows]
    n_pass = [int(r["n_pass"]) for r in rows]
    n_watch = [int(r["n_watch"]) for r in rows]
    n_fail = [int(r["n_fail"]) for r in rows]
    x = np.arange(len(industries))
    width = 0.25

    fig, ax = plt.subplots(figsize=(max(8, len(industries) * 0.9), 4.5))
    ax.bar(x - width, n_pass, width, label="PASS", color="#548235")
    ax.bar(x, n_watch, width, label="WATCH", color="#bf8f00")
    ax.bar(x + width, n_fail, width, label="FAIL", color="#c00000")
    ax.set_xticks(x)
    ax.set_xticklabels(industries, rotation=30, ha="right")
    ax.set_title(f"Sector overview | {as_of_date}")
    ax.legend(fontsize=8)
    return _save(fig, out)


def render_pnl_is_os_chart(
    scope: str, run_id: str, split_date: str, out_path: str | Path
) -> Path:
    """Equity curve tô 2 màu in-sample / out-of-sample theo ranh giới walk_forward.

    ``split_date`` lấy từ ``pipeline/config.yaml:backtest.walk_forward``, không tự chọn.
    """
    raise NotImplementedError


def render_yearly_stats_chart(
    scope: str, baseline: str, run_id: str, out_path: str | Path
) -> Path:
    """Bar chart Sharpe/CAGR theo năm từ ``backtest_yearly_breakdown``."""
    raise NotImplementedError


def render_turnover_chart(scope: str, run_id: str, out_path: str | Path) -> Path:
    """Turnover trượt theo thời gian (không gộp thành 1 số duy nhất)."""
    raise NotImplementedError
