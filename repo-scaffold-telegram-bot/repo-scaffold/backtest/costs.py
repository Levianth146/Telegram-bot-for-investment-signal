"""Chi phí giao dịch thực tế — bắt buộc trong mọi backtest (mục 12.2 sai lầm cần tránh).

T+2 (không bán ngay ngày mua), không short, thuế bán 0.1%, phí round-trip
~0.3-0.5% tùy broker, biên độ +-7% (HOSE) coi như không mua/bán được nếu
giá chạm trần/sàn.
"""

from __future__ import annotations


def apply_transaction_costs(gross_return: float, tax_sell_pct: float, fee_roundtrip_pct: float) -> float:
    raise NotImplementedError


def is_tradable_at_price_limit(open_price: float, prev_close: float, limit_pct: float = 0.07) -> bool:
    """False nếu giá đã chạm trần/sàn — coi như không khớp được lệnh."""
    raise NotImplementedError
