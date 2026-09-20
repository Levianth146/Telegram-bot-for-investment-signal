---
type: community
cohesion: 0.14
members: 14
---

# Community 1

**Cohesion:** 0.14 - loosely connected
**Members:** 14 nodes

## Members
- [[Job Tầng 1 — chạy lại mỗi khi có BCTC mới (event-driven, theo quý). Luồng…]] - rationale - pipeline/quarterly_job.py
- [[Job Tầng 2 — chạy mỗi phiên, sau giờ đóng cửa (~1500). Luồng store.watchlist…]] - rationale - pipeline/daily_job.py
- [[Sinh ra danh sách (train_start, train_end, test_start, test_end).]] - rationale - backtest/walk_forward.py
- [[Walk-forward validation — train N năm, test M tháng, trượt cửa sổ tới. Tham…]] - rationale - backtest/walk_forward.py
- [[argparse]] - concept
- [[daily_job.py]] - code - pipeline/daily_job.py
- [[main()]] - code - backtest/walk_forward.py
- [[main()_1]] - code - pipeline/daily_job.py
- [[main()_2]] - code - pipeline/quarterly_job.py
- [[quarterly_job.py]] - code - pipeline/quarterly_job.py
- [[run()]] - code - pipeline/daily_job.py
- [[run()_1]] - code - pipeline/quarterly_job.py
- [[walk_forward.py]] - code - backtest/walk_forward.py
- [[walk_forward_windows()]] - code - backtest/walk_forward.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_1
SORT file.name ASC
```
