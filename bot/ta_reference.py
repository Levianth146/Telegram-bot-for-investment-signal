"""Chỉ số TA cổ điển cho khối «Tham khảo thêm» (§9.7) — CHỈ HIỂN THỊ.

Không dùng để chấm điểm, sizing, hay quyết định BUY/SELL (chống double-count).
Tính từ chuỗi close đã có trong store.price_bars; không gọi vendor.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def ta_indicators_from_closes(
    closes: Sequence[Mapping[str, Any]],
    *,
    rsi_period: int = 14,
    ma_fast: int = 20,
    ma_slow: int = 50,
    vol_ma: int = 20,
) -> dict[str, Any]:
    """Trả dict cho ``format_ta_reference_block`` từ rows ``{date, close, volume?}``."""
    if not closes:
        return {}
    prices: list[float] = []
    volumes: list[float] = []
    for row in closes:
        c = row.get("close")
        if c is None:
            continue
        try:
            prices.append(float(c))
        except (TypeError, ValueError):
            continue
        v = row.get("volume")
        try:
            volumes.append(float(v) if v is not None else float("nan"))
        except (TypeError, ValueError):
            volumes.append(float("nan"))
    if len(prices) < rsi_period + 2:
        return {}

    out: dict[str, Any] = {}
    rsi = _rsi(prices, rsi_period)
    if rsi is not None:
        out["rsi_14"] = rsi

    if len(prices) >= ma_slow:
        ma20 = sum(prices[-ma_fast:]) / ma_fast
        ma50 = sum(prices[-ma_slow:]) / ma_slow
        if ma20 > ma50 * 1.002:
            out["ma_trend"] = "MA20 trên MA50 (ngắn hạn nghiêng tăng)"
        elif ma20 < ma50 * 0.998:
            out["ma_trend"] = "MA20 dưới MA50 (ngắn hạn nghiêng giảm)"
        else:
            out["ma_trend"] = "MA20 ≈ MA50 (đi ngang)"

    finite_vol = [v for v in volumes if v == v and v > 0]  # not NaN
    if len(finite_vol) >= vol_ma:
        latest = finite_vol[-1]
        avg = sum(finite_vol[-vol_ma:]) / vol_ma
        if avg > 0:
            out["volume_over_ma20"] = latest / avg
    return out


def _rsi(prices: list[float], period: int) -> float | None:
    if len(prices) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        delta = prices[i] - prices[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss <= 1e-12:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
