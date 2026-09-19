"""Ablation study — bật/tắt từng tầng theo pipeline/config.yaml, đo đóng góp biên.

Tham chiếu: mục 4.2 (bảng B0/B1/B2 -> +regime -> +quality -> +vol-sizing -> +BL)
và mục 11.3 (tiêu chí giữ/cắt, ghi log vào docs/DECISIONS.md).
"""

from __future__ import annotations


def run_ablation(config: dict, layers_order: list[str]) -> dict:
    """Chạy backtest lần lượt: baseline -> +layer1 -> +layer1+layer2 -> ...

    Trả về bảng Sharpe/CAGR/MDD tại mỗi bước, để so sánh đóng góp biên của
    từng tầng trước khi quyết định giữ/cắt (ghi kết quả vào docs/DECISIONS.md).
    """
    raise NotImplementedError
