"""Monte Carlo (filtered historical simulation) — xác suất hóa tín hiệu.

Tham chiếu: mục "Monte Carlo" trong tài liệu framework.
Bootstrap residual chuẩn hóa z_t = eps_t / sigma_t từ GARCH, nhân lại với
sigma_hat dự báo, clip ±7% (biên độ HOSE), mô phỏng nhiều đường giá.

Output feed vào store.signals.p_tp_before_sl và cvar95.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _as_array(values) -> np.ndarray:
    arr = np.asarray(pd.Series(values, dtype=float).dropna(), dtype=float)
    return arr[np.isfinite(arr)]


def simulate_price_paths(
    entry_price: float,
    sigma_hat: float,
    historical_residuals,
    horizon_days: int = 10,
    n_paths: int = 10_000,
    price_limit_pct: float = 0.07,
    rng: np.random.Generator | None = None,
):
    """Return array shape (n_paths, horizon_days) of simulated prices."""
    if entry_price is None or entry_price <= 0:
        raise ValueError("entry_price must be positive")
    if sigma_hat is None or pd.isna(sigma_hat) or sigma_hat < 0:
        raise ValueError("sigma_hat must be non-negative")
    if horizon_days < 1 or n_paths < 1:
        raise ValueError("horizon_days and n_paths must be >= 1")

    generator = rng or np.random.default_rng(0)
    residuals = _as_array(historical_residuals)
    if len(residuals) >= 10:
        scale = float(np.std(residuals, ddof=1)) or 1.0
        z_pool = residuals / scale
        picks = generator.integers(0, len(z_pool), size=(n_paths, horizon_days))
        z = z_pool[picks]
    else:
        z = generator.normal(0.0, 1.0, size=(n_paths, horizon_days))

    daily = np.clip(
        float(sigma_hat) * z,
        -float(price_limit_pct),
        float(price_limit_pct),
    )
    paths = float(entry_price) * np.exp(np.cumsum(daily, axis=1))
    return paths


def probability_tp_before_sl(
    paths, entry_price: float, tp_pct: float, sl_pct: float
) -> float:
    """Fraction of paths that hit TP before SL within the horizon."""
    if entry_price <= 0:
        raise ValueError("entry_price must be positive")
    arr = np.asarray(paths, dtype=float)
    if arr.ndim != 2 or arr.size == 0:
        return float("nan")
    tp = float(entry_price) * (1.0 + abs(float(tp_pct)))
    sl = float(entry_price) * (1.0 - abs(float(sl_pct)))
    hits = 0
    for path in arr:
        for px in path:
            if px <= sl:
                break
            if px >= tp:
                hits += 1
                break
    return float(hits / arr.shape[0])


def cvar(paths, entry_price: float, alpha: float = 0.95) -> float:
    """CVaR of terminal return at level ``alpha`` (e.g. 0.95 → worst 5% mean)."""
    arr = np.asarray(paths, dtype=float)
    if arr.ndim != 2 or arr.size == 0 or entry_price <= 0:
        return float("nan")
    terminal = arr[:, -1] / float(entry_price) - 1.0
    q = float(np.quantile(terminal, 1.0 - float(alpha)))
    tail = terminal[terminal <= q]
    if tail.size == 0:
        return q
    return float(tail.mean())


def monte_carlo_signal_stats(
    entry_price: float,
    sigma_hat: float,
    returns_series,
    *,
    stop_price: float | None = None,
    tp_pct: float = 0.08,
    horizon_days: int = 10,
    n_paths: int = 2000,
    price_limit_pct: float = 0.07,
    seed: int = 0,
) -> dict:
    """Convenience wrapper → ``{p_tp_before_sl, cvar95, sl_pct}``."""
    rets = _as_array(returns_series)
    if stop_price is not None and entry_price > 0 and not pd.isna(stop_price):
        sl_pct = max(0.0, 1.0 - float(stop_price) / float(entry_price))
    else:
        sl_pct = 2.0 * float(sigma_hat) if sigma_hat else 0.05

    # Standardized residuals proxy: r_t / rolling_sigma
    if len(rets) >= 20:
        roll = pd.Series(rets).rolling(20).std().to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            resid = np.where(roll > 1e-12, rets / roll, 0.0)
        resid = resid[np.isfinite(resid)]
    else:
        resid = rets

    paths = simulate_price_paths(
        entry_price,
        sigma_hat,
        resid,
        horizon_days=horizon_days,
        n_paths=n_paths,
        price_limit_pct=price_limit_pct,
        rng=np.random.default_rng(seed),
    )
    return {
        "p_tp_before_sl": probability_tp_before_sl(paths, entry_price, tp_pct, sl_pct),
        "cvar95": cvar(paths, entry_price, alpha=0.95),
        "sl_pct": sl_pct,
        "tp_pct": tp_pct,
        "n_paths": n_paths,
        "horizon_days": horizon_days,
    }
