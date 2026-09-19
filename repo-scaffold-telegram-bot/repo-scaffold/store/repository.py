"""Lớp truy cập dữ liệu cho store/schema.sql — cả pipeline lẫn bot đều đi qua đây,
không viết SQL rải rác ở nơi khác.
"""

from __future__ import annotations
import sqlite3
from pathlib import Path


def get_connection(db_path: str = "store/bot.db") -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection, schema_path: str = "store/schema.sql") -> None:
    sql = Path(schema_path).read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def upsert_signal(conn: sqlite3.Connection, signal: dict) -> None:
    """Ghi một dòng vào bảng signals. `signal` phải khớp cột trong schema.sql."""
    raise NotImplementedError


def get_latest_signals(conn: sqlite3.Connection, as_of_date: str | None = None) -> list[dict]:
    """Bot dùng hàm này để trả lời /signals — CHỈ ĐỌC, không tính toán gì thêm."""
    raise NotImplementedError


def get_watchlist(conn: sqlite3.Connection, as_of_date: str | None = None) -> list[str]:
    raise NotImplementedError
