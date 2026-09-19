# Nhật ký quyết định giữ/cắt một tầng (ablation log)

Nguyên tắc: một tầng chỉ được giữ trong bản cuối nếu nó cải thiện Sharpe ngoài mẫu
(out-of-sample, walk-forward) tối thiểu ngưỡng đã thống nhất. Nếu không đạt, ghi lại đây
là phát hiện hợp lệ — không xóa khỏi báo cáo.

Ngưỡng thống nhất trước khi chạy ablation lần đầu: **+0.10 Sharpe** (điền lại nếu nhóm chốt
số khác) — điền ngày chốt: __________

## Mẫu ghi log

| Ngày | Tầng thử nghiệm | Kết quả (Sharpe/CAGR/MDD trước–sau) | Quyết định | Người chốt |
|---|---|---|---|---|
| VD: 2026-10-15 | Hawkes crowding filter | Sharpe 1.12 → 1.14 (không đạt ngưỡng +0.10) | Cắt khỏi bản chính, giữ làm phụ lục nghiên cứu | @tên |

## Log thực tế của nhóm

(điền dần trong quá trình backtest/ablation — xem `backtest/ablation.py`)
