"""Điểm khởi động bot Telegram — CHỈ ĐỌC từ store/, không tính toán, không fit
mô hình (nguyên tắc bất biến #1, xem docs/ARCHITECTURE.md).

Lệnh: /start, /help, /signals, /check <ma>, /regime, /watch <ma>,
/subscribe, /unsubscribe (xem thiết kế lệnh trong tài liệu framework).
"""

from __future__ import annotations


def main():
    # TODO(P5 - bot): khởi tạo python-telegram-bot, đăng ký handlers/ ,
    # đọc BOT_TOKEN từ .env, mở kết nối store qua store/repository.py
    raise NotImplementedError


if __name__ == "__main__":
    main()
