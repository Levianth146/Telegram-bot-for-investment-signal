# Community 2

> 12 nodes · cohesion 0.23

## Key Concepts

- **repository.py** (8 connections) — `store/repository.py`
- **Connection** (5 connections)
- **get_latest_signals()** (3 connections) — `store/repository.py`
- **upsert_signal()** (3 connections) — `store/repository.py`
- **get_connection()** (2 connections) — `store/repository.py`
- **get_watchlist()** (2 connections) — `store/repository.py`
- **init_schema()** (2 connections) — `store/repository.py`
- **pathlib** (1 connections)
- **sqlite3** (1 connections)
- **Lớp truy cập dữ liệu cho store/schema.sql — cả pipeline lẫn bot đều đi qua đây,…** (1 connections) — `store/repository.py`
- **Ghi một dòng vào bảng signals. `signal` phải khớp cột trong schema.sql.** (1 connections) — `store/repository.py`
- **Bot dùng hàm này để trả lời /signals — CHỈ ĐỌC, không tính toán gì thêm.** (1 connections) — `store/repository.py`

## Relationships

- No strong cross-community connections detected

## Source Files

- `store/repository.py`

## Audit Trail

- EXTRACTED: 15 (100%)
- INFERRED: 0 (0%)
- AMBIGUOUS: 0 (0%)

---

*Part of the graphify knowledge wiki. See [index](index.md) to navigate.*