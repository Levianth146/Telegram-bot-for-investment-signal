"""Walk-forward validation — train N năm, test M tháng, trượt cửa sổ tới.

Tham chiếu: mục 11.3 — tiêu chí giữ/cắt một tầng phải dựa trên Sharpe NGOÀI MẪU
(out-of-sample), không phải Sharpe trên chính tập đã fit.
"""

from __future__ import annotations
import argparse


def walk_forward_windows(start_date: str, end_date: str, train_years: int, test_months: int):
    """Sinh ra danh sách (train_start, train_end, test_start, test_end)."""
    raise NotImplementedError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    # TODO(P4 - backtest): đọc config, chạy walk-forward, in bảng Sharpe/CAGR/MDD
    raise NotImplementedError


if __name__ == "__main__":
    main()
