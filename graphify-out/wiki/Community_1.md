# Community 1

> 14 nodes · cohesion 0.14

## Key Concepts

- **walk_forward.py** (4 connections) — `backtest/walk_forward.py`
- **daily_job.py** (4 connections) — `pipeline/daily_job.py`
- **quarterly_job.py** (4 connections) — `pipeline/quarterly_job.py`
- **argparse** (3 connections)
- **walk_forward_windows()** (2 connections) — `backtest/walk_forward.py`
- **main()** (1 connections) — `backtest/walk_forward.py`
- **Walk-forward validation — train N năm, test M tháng, trượt cửa sổ tới. Tham…** (1 connections) — `backtest/walk_forward.py`
- **Sinh ra danh sách (train_start, train_end, test_start, test_end).** (1 connections) — `backtest/walk_forward.py`
- **main()** (1 connections) — `pipeline/daily_job.py`
- **Job Tầng 2 — chạy mỗi phiên, sau giờ đóng cửa (~15:00). Luồng: store.watchlist…** (1 connections) — `pipeline/daily_job.py`
- **run()** (1 connections) — `pipeline/daily_job.py`
- **main()** (1 connections) — `pipeline/quarterly_job.py`
- **Job Tầng 1 — chạy lại mỗi khi có BCTC mới (event-driven, theo quý). Luồng:…** (1 connections) — `pipeline/quarterly_job.py`
- **run()** (1 connections) — `pipeline/quarterly_job.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `backtest/walk_forward.py`
- `pipeline/daily_job.py`
- `pipeline/quarterly_job.py`

## Audit Trail

- EXTRACTED: 13 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*