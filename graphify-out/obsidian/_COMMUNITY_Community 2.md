---
type: community
cohesion: 0.23
members: 12
---

# Community 2

**Cohesion:** 0.23 - loosely connected
**Members:** 12 nodes

## Members
- [[Bot dùng hàm này để trả lời signals — CHỈ ĐỌC, không tính toán gì thêm.]] - rationale - store/repository.py
- [[Connection]] - code
- [[Ghi một dòng vào bảng signals. `signal` phải khớp cột trong schema.sql.]] - rationale - store/repository.py
- [[Lớp truy cập dữ liệu cho storeschema.sql — cả pipeline lẫn bot đều đi qua đây,…]] - rationale - store/repository.py
- [[get_connection()]] - code - store/repository.py
- [[get_latest_signals()]] - code - store/repository.py
- [[get_watchlist()]] - code - store/repository.py
- [[init_schema()]] - code - store/repository.py
- [[pathlib]] - concept
- [[repository.py]] - code - store/repository.py
- [[sqlite3]] - concept
- [[upsert_signal()]] - code - store/repository.py

## Live Query (requires Dataview plugin)

```dataview
TABLE source_file, type FROM #community/Community_2
SORT file.name ASC
```
