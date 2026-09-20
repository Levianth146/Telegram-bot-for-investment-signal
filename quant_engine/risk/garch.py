"""GARCH/GJR-GARCH — dự báo biến động có điều kiện.

Tham chiếu: mục "Risk" trong tài liệu framework.
  sigma^2_t = omega + (alpha + gamma*1[eps<0]) * eps^2_(t-1) + beta * sigma^2_(t-1)

Dùng thư viện ``arch``. Biên độ ±7% HOSE cắt cụt return → vol có thể bị
đánh giá thấp — ghi chú khi diễn giải.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def _as_returns(returns_series) -> pd.Series:
    series = pd.Series(returns_series, dtype=float).dropna()
    if series.empty:
        raise ValueError("returns_series is empty")
    return series


def fit_gjr_garch(returns_series):
    """Fit GJR-GARCH(1,1). Returns arch ``ARCHModelResult`` or raises."""
    series = _as_returns(returns_series)
    if len(series) < 60:
        raise ValueError("Need at least 60 returns to fit GJR-GARCH")
    # arch is more stable with percent returns
    from arch import arch_model

    scaled = series * 100.0
    model = arch_model(scaled, mean="Zero", vol="GARCH", p=1, o=1, q=1, dist="normal")
    return model.fit(disp="off")


def forecast_sigma(model, horizon: int = 1) -> float:
    """Next-session sigma_hat in decimal return units (store.signals.sigma_hat)."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    forecast = model.forecast(horizon=horizon)
    variance = float(forecast.variance.values[-1, -1])
    # variance is in percent^2 → sigma in decimal
    return float(np.sqrt(max(variance, 0.0)) / 100.0)


def rolling_sigma_fallback(returns_series, window: int = 20) -> float:
    """ponytail: rolling std when GARCH fit fails."""
    series = _as_returns(returns_series)
    trail = series.iloc[-min(window, len(series)) :]
    if len(trail) < 2:
        return float("nan")
    return float(trail.std(ddof=1))


def fit_or_fallback_sigma(returns_series, window: int = 20) -> dict:
    """Return ``{sigma_hat, method, model}`` with GARCH preferred."""
    try:
        model = fit_gjr_garch(returns_series)
        sigma = forecast_sigma(model, horizon=1)
        return {"sigma_hat": sigma, "method": "gjr_garch", "model": model}
    except Exception:  # noqa: BLE001
        return {
            "sigma_hat": rolling_sigma_fallback(returns_series, window=window),
            "method": "rolling_std",
            "model": None,
        }


def position_size(sigma_hat: float, sigma_target: float, w_max: float = 0.1) -> float:
    """size = min(w_max, sigma_target / sigma_hat). Framework mục Risk."""
    if sigma_hat is None or pd.isna(sigma_hat) or sigma_hat <= 0:
        return 0.0
    if sigma_target is None or pd.isna(sigma_target) or sigma_target <= 0:
        raise ValueError("sigma_target must be positive")
    return float(min(w_max, float(sigma_target) / float(sigma_hat)))


def stop_loss_price(entry_price: float, sigma_hat: float, k: float = 2.0) -> float:
    """stop = entry_price * (1 - k * sigma_hat). Long-only V1."""
    if entry_price is None or entry_price <= 0:
        raise ValueError("entry_price must be positive")
    if sigma_hat is None or pd.isna(sigma_hat):
        return float("nan")
    return float(entry_price) * (1.0 - float(k) * float(sigma_hat))
