"""Job Tầng 2 — chạy mỗi phiên, sau giờ đóng cửa (~15:00).

Luồng: store.watchlist (từ Tầng 1) + giá/khối lượng hằng ngày
  -> regime -> alpha (kalman/ou) -> risk (garch) -> portfolio (black-litterman,
     hoặc fallback equal-weight nếu tắt) -> probabilistic (monte carlo + hawkes,
     nếu bật) -> ghi vào store.signals

QUAN TRỌNG: đây là nơi DUY NHẤT được fit/chạy các mô hình Tầng 2. bot/ không
bao giờ được gọi các hàm trong quant_engine/ trực tiếp.
"""

from __future__ import annotations
import argparse


def run(config: dict) -> None:
    # TODO(P2/P3/P4 - quant): với mỗi mã trong watchlist:
    #   1. filtered_regime_probability
    #   2. alpha_effective (kalman trend x growth/quality, hoặc ou nếu đi ngang)
    #   3. garch sigma_hat -> stop, size
    #   4. black_litterman (nếu enabled) hoặc equal_weight_fallback
    #   5. monte_carlo (nếu enabled) -> p_tp_before_sl, cvar95
    #   6. hawkes (nếu enabled) -> crowding_size_multiplier
    #   7. upsert_signal vào store
    raise NotImplementedError


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.dry_run:
        print("daily_job dry-run OK (stub)")
        return
    raise NotImplementedError


if __name__ == "__main__":
    main()
