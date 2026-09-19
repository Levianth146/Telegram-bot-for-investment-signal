"""Job Tầng 1 — chạy lại mỗi khi có BCTC mới (event-driven, theo quý).

Luồng: data/ (BCTC point-in-time) -> fundamental_filter/ (Growth/Quality/
Safety/Valuation) -> scoring.aggregate_fundamental_view -> ghi vào
store.fundamental_scores + store.watchlist.
"""

from __future__ import annotations
import argparse


def run(config: dict) -> None:
    # TODO(P6 - fundamental): với mỗi mã có BCTC mới công bố:
    #   1. Lấy dữ liệu point-in-time từ data/
    #   2. Tính growth_score, quality_score, safety_score, valuation_score
    #   3. aggregate_fundamental_view -> ghi store.fundamental_scores
    #   4. Cập nhật store.watchlist = universe giao PASS/WATCH
    raise NotImplementedError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print("quarterly_job dry-run OK (stub)")
        return
    raise NotImplementedError


if __name__ == "__main__":
    main()
