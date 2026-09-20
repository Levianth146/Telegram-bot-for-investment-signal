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


def open_position(conn: sqlite3.Connection, position: dict) -> None:
    """Ghi 1 vị thế mới (status='OPEN') — dùng khi paper-trading engine vào lệnh
    theo tín hiệu BUY. Bot chỉ ĐỌC bảng này qua get_open_positions, không tự mở lệnh.
    """
    raise NotImplementedError


def close_position(conn: sqlite3.Connection, ticker: str, opened_at: str, close_price: float,
                    closed_at: str) -> None:
    raise NotImplementedError


def get_open_positions(conn: sqlite3.Connection) -> list[dict]:
    """Bot dùng hàm này để trả lời /positions — CHỈ ĐỌC."""
    raise NotImplementedError


def set_subscription(conn: sqlite3.Connection, chat_id: int, is_active: bool) -> None:
    """Dùng cho /subscribe và /unsubscribe. is_active=False vẫn giữ lại dòng (lịch sử),
    không xóa — để biết ai đã từng đăng ký."""
    raise NotImplementedError


def get_active_subscribers(conn: sqlite3.Connection) -> list[int]:
    """pipeline/daily_job.py dùng hàm này để biết push tín hiệu cho chat_id nào."""
    raise NotImplementedError


def get_backtest_results(conn: sqlite3.Connection, scope: str, run_id: str | None = None) -> list[dict]:
    """Bot dùng hàm này để trả lời /backtest — CHỈ ĐỌC kết quả đã tính sẵn theo lịch
    định kỳ trong backtest_results. `run_id=None` -> lấy lần chạy mới nhất."""
    raise NotImplementedError
