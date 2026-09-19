"""Backtest engine — GỌI LẠI đúng hàm trong fundamental_filter/ và quant_engine/,
không viết logic tính điểm/tín hiệu riêng cho backtest (nguyên tắc bất biến #2,
xem docs/ARCHITECTURE.md).
"""

from __future__ import annotations


def run_backtest(config: dict, start_date: str, end_date: str) -> dict:
    """Chạy toàn bộ pipeline (Tầng 1 + Tầng 2) trên dữ liệu lịch sử, tôn trọng
    point-in-time (BCTC theo ngày công bố, không dùng smoothed probability).

    Trả về dict {"equity_curve":.., "trades":.., "metrics":..}.
    """
    raise NotImplementedError
