"""Chi phí giao dịch thực tế — bắt buộc trong mọi backtest (mục 12.2).

T+2 (không bán ngay ngày mua), không short, thuế bán 0.1%, phí round-trip
~0.3–0.5% tùy broker, biên độ ±7% (HOSE) coi như không khớp nếu chạm trần/sàn.
"""

from __future__ import annotations


def apply_transaction_costs(
    gross_return: float, tax_sell_pct: float, fee_roundtrip_pct: float
) -> float:
    """Net return after sell tax + round-trip fee (applied once per closed trade)."""
    return float(gross_return) - float(tax_sell_pct) - float(fee_roundtrip_pct)


def buy_cost_fraction(fee_roundtrip_pct: float) -> float:
    """Half of round-trip fee charged on entry (NAV haircut)."""
    return float(fee_roundtrip_pct) / 2.0


def sell_cost_fraction(tax_sell_pct: float, fee_roundtrip_pct: float) -> float:
    """Sell tax + half round-trip fee charged on exit."""
    return float(tax_sell_pct) + float(fee_roundtrip_pct) / 2.0


def is_tradable_at_price_limit(
    open_price: float, prev_close: float, limit_pct: float = 0.07
) -> bool:
    """False nếu giá đã chạm trần/sàn — coi như không khớp được lệnh."""
    if open_price is None or prev_close is None:
        return False
    if prev_close <= 0 or open_price <= 0:
        return False
    move = abs(float(open_price) / float(prev_close) - 1.0)
    return move < float(limit_pct) - 1e-12
