"""GARCH/GJR-GARCH — dự báo biến động có điều kiện.

Tham chiếu: mục "Risk" trong tài liệu framework.
  sigma^2_t = omega + (alpha + gamma*1[eps<0]) * eps^2_(t-1) + beta * sigma^2_(t-1)

Dùng thư viện ``arch``. Biên độ ±7% HOSE cắt cụt return → vol có thể bị
đánh giá thấp — ghi chú khi diễn giải.

P2-1 / Phần 8.5: ``refit_every_n`` thật — MLE mỗi N phiên tín hiệu; giữa các
lần dùng multi-step forecast từ model đã fit (không rolling-window MLE).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd

_LOG = logging.getLogger(__name__)


def _as_returns(returns_series) -> pd.Series:
    series = pd.Series(returns_series, dtype=float).dropna()
    if series.empty:
        raise ValueError("returns_series is empty")
    return series


def should_refit_garch(
    *,
    days_since_fit: int | None,
    refit_every_n: int | None,
) -> bool:
    """Quyết định có chạy MLE GARCH lại không.

    - ``refit_every_n`` None/≤0 → luôn refit (hành vi V1 / N=1).
    - N>0: refit khi chưa từng fit (``days_since_fit is None``) hoặc
      ``days_since_fit >= N`` (đếm phiên tín hiệu kể từ lần MLE gần nhất).
    """
    if refit_every_n is None or int(refit_every_n) <= 0:
        return True
    if days_since_fit is None:
        return True
    return int(days_since_fit) >= int(refit_every_n)


def fit_gjr_garch(returns_series):
    """Fit GJR-GARCH(1,1). Returns arch ``ARCHModelResult`` or raises."""
    series = _as_returns(returns_series)
    if len(series) < 60:
        raise ValueError("Need at least 60 returns to fit GJR-GARCH")
    # arch ổn định hơn với return theo %
    from arch import arch_model

    scaled = series * 100.0
    model = arch_model(scaled, mean="Zero", vol="GARCH", p=1, o=1, q=1, dist="normal")
    return model.fit(disp="off")


def forecast_sigma(model, horizon: int = 1) -> float:
    """Sigma dự báo horizon phiên tới (đơn vị return thập phân — store.signals.sigma_hat)."""
    if horizon < 1:
        raise ValueError("horizon must be >= 1")
    forecast = model.forecast(horizon=horizon)
    variance = float(forecast.variance.values[-1, -1])
    # variance theo %^2 → sigma thập phân
    return float(np.sqrt(max(variance, 0.0)) / 100.0)


def rolling_sigma_fallback(returns_series, window: int = 20) -> float:
    """ponytail: rolling std khi GARCH fit thất bại."""
    series = _as_returns(returns_series)
    trail = series.iloc[-min(window, len(series)) :]
    if len(trail) < 2:
        return float("nan")
    return float(trail.std(ddof=1))


def fit_or_fallback_sigma(
    returns_series,
    window: int = 20,
    *,
    refit_every_n: int | None = None,
    days_since_fit: int | None = None,
    previous_model: Any = None,
) -> dict[str, Any]:
    """Trả ``{sigma_hat, method, model, refit, days_since_fit}``.

    Khi ``refit_every_n`` > 0 và chưa đến kỳ refit: multi-step forecast từ
    ``previous_model`` với ``horizon = days_since_fit + 1`` (roll-forward).
    """
    do_refit = should_refit_garch(
        days_since_fit=days_since_fit, refit_every_n=refit_every_n
    )

    if (
        not do_refit
        and previous_model is not None
        and days_since_fit is not None
        and int(days_since_fit) >= 0
    ):
        horizon = int(days_since_fit) + 1
        try:
            sigma = forecast_sigma(previous_model, horizon=horizon)
            return {
                "sigma_hat": sigma,
                "method": "gjr_garch_forecast",
                "model": previous_model,
                "refit": False,
                "days_since_fit": int(days_since_fit),
            }
        except Exception:  # noqa: BLE001
            _LOG.debug(
                "GARCH forecast roll-forward thất bại (h=%s) — fallback MLE",
                horizon,
                exc_info=True,
            )

    try:
        model = fit_gjr_garch(returns_series)
        sigma = forecast_sigma(model, horizon=1)
        return {
            "sigma_hat": sigma,
            "method": "gjr_garch",
            "model": model,
            "refit": True,
            "days_since_fit": 0,
        }
    except Exception:  # noqa: BLE001
        return {
            "sigma_hat": rolling_sigma_fallback(returns_series, window=window),
            "method": "rolling_std",
            "model": None,
            "refit": True,
            "days_since_fit": 0,
        }


def position_size(sigma_hat: float, sigma_target: float, w_max: float = 0.1) -> float:
    """size = min(w_max, sigma_target / sigma_hat). Legacy per-ticker (giữ tương thích)."""
    if sigma_hat is None or pd.isna(sigma_hat) or sigma_hat <= 0:
        return 0.0
    if sigma_target is None or pd.isna(sigma_target) or sigma_target <= 0:
        raise ValueError("sigma_target must be positive")
    return float(min(w_max, float(sigma_target) / float(sigma_hat)))


def inverse_vol_normalize_weights(
    sigma_by_ticker: dict[str, float],
    *,
    w_max: float = 0.10,
    target_sum: float = 1.0,
) -> dict[str, float]:
    """Inverse-vol portfolio: raw=1/σ, normalize sum≤target_sum, cap w_max.

    Cash = phần dư sau cap. σ↑ → weight↓ (monotonic trên cùng universe).
    """
    raw: dict[str, float] = {}
    for ticker, sigma in sigma_by_ticker.items():
        if sigma is None or pd.isna(sigma) or float(sigma) <= 0:
            continue
        raw[str(ticker).strip().upper()] = 1.0 / float(sigma)
    if not raw:
        return {}
    total = sum(raw.values())
    if total <= 0:
        return {t: 0.0 for t in raw}
    scale = float(target_sum) / total
    weights = {t: min(float(w_max), v * scale) for t, v in raw.items()}
    # Phân bổ residual nếu còn room dưới w_max (một vòng).
    capped_sum = sum(weights.values())
    residual = float(target_sum) - capped_sum
    if residual > 1e-12:
        room = {
            t: float(w_max) - w
            for t, w in weights.items()
            if float(w_max) - w > 1e-12
        }
        room_total = sum(room.values())
        if room_total > 0:
            for t, r in room.items():
                add = residual * (r / room_total)
                weights[t] = min(float(w_max), weights[t] + add)
    return weights


def stop_loss_price(entry_price: float, sigma_hat: float, k: float = 2.0) -> float:
    """stop = entry_price * (1 - k * sigma_hat). Long-only V1."""
    if entry_price is None or entry_price <= 0:
        raise ValueError("entry_price must be positive")
    if sigma_hat is None or pd.isna(sigma_hat):
        return float("nan")
    return float(entry_price) * (1.0 - float(k) * float(sigma_hat))
