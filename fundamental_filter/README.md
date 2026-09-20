# `fundamental_filter/` — Tầng 1 (Fundamental Filter)

Hai lớp có chủ đích, không phải hai hệ scoring song song.

## Facade vs engine

| Lớp | File | Vai trò |
|---|---|---|
| **Facade (public API)** | `growth.py`, `quality.py`, `safety.py`, `valuation.py`, `scoring.py` | Công thức/docstring theo framework (mục 2–5, 10); smoke tests; Merton stub P2 ở `safety.py` |
| **Engine** | `layer1_engine/` | Chấm điểm thật: metric → module → fundamental → PASS/WATCH/FAIL → `to_store_records` |

**Production path (universe):**

```text
DataFrames đã chuẩn bị (từ data/)
  → score_current_universe
  → classify PASS/WATCH/FAIL
  → to_store_records
  → store.fundamental_scores + store.watchlist
```

Import gợi ý:

```python
from fundamental_filter import growth, scoring
from fundamental_filter import score_current_universe, to_store_records

# Single-ticker absolute fallback (không thay universe path):
scoring.aggregate_fundamental_view(growth_d, quality_d, safety_d, valuation_d, config)
```

`*_score()` ở facade chỉ bọc dict/float đã tính — **không** thay `score_current_universe`.

## Network / I/O

CONTRIBUTING: không gọi network trong `fundamental_filter/` khi production.

- **Pure path:** `score_current_universe` — không mạng.
- **Live path (transitional):** `layer1_engine.analyze_fundamental_universe` và các helper I/O — đang được bọc dần bởi `data/providers/`. Pipeline mới phải gọi `data/`, không import DNSE/vnstock trực tiếp từ filter.

Chi tiết engine: [`layer1_engine/README.md`](layer1_engine/README.md).
