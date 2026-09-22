"""Tests cắt tin Telegram (>4096) và danh sách /signals dài."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot import formatters
from bot.main import TELEGRAM_TEXT_LIMIT, chunk_telegram_text, reply_text_safe


def test_chunk_telegram_text_over_4096():
    """Chuỗi giả >4096 → ≥2 phần, mỗi phần ≤ limit mặc định (4000)."""
    # Nhiều dòng ngắn để ưu tiên cắt tại \\n.
    lines = [f"dòng-{i:04d} " + ("x" * 60) for i in range(80)]
    text = "\n".join(lines)
    assert len(text) > 4096

    parts = chunk_telegram_text(text)
    assert len(parts) >= 2
    assert all(len(p) <= TELEGRAM_TEXT_LIMIT for p in parts)
    # Ghép lại (có thể mất đúng 1 \\n tại điểm cắt) vẫn chứa đủ nội dung dòng.
    joined = "\n".join(parts)
    for line in lines:
        assert line in joined


def test_chunk_telegram_text_hard_split_long_line():
    """Một dòng dài hơn limit → cắt cứng theo ký tự."""
    text = "A" * 8500
    parts = chunk_telegram_text(text, limit=4000)
    assert len(parts) == 3
    assert all(len(p) <= 4000 for p in parts)
    assert "".join(parts) == text


def test_format_signals_list_long_then_chunk():
    """Danh sách tín hiệu nhiều mã (>~40) vượt 4096 → chunk an toàn."""
    rows = [
        {
            "date": "2026-09-22",
            "ticker": f"T{i:02d}",
            "action": ("BUY", "WATCH", "SELL")[i % 3],
            "score": 1.0 - (i * 0.01),
            "p_regime": 0.62,
            "sigma_hat": 0.02,
            "size": 0.05,
            "fundamental_view": "PASS",
        }
        for i in range(48)
    ]
    text = formatters.format_signals_list(rows)
    assert len(text) > 4096
    assert "T00" in text and "T47" in text

    parts = chunk_telegram_text(text)
    assert len(parts) >= 2
    assert all(len(p) <= TELEGRAM_TEXT_LIMIT for p in parts)
    assert all(len(p) <= 4096 for p in parts)


def test_reply_text_safe_skips_when_message_none():
    """update.message is None → không raise, không gọi reply."""
    update = SimpleNamespace(message=None)

    async def _run():
        await reply_text_safe(update, "hello")

    asyncio.run(_run())


def test_reply_text_safe_sends_chunks():
    """Gửi từng chunk qua reply_text khi message có sẵn."""
    reply = AsyncMock()
    update = SimpleNamespace(message=SimpleNamespace(reply_text=reply))
    text = "\n".join([f"line-{i}" + ("y" * 100) for i in range(50)])
    assert len(text) > TELEGRAM_TEXT_LIMIT

    async def _run():
        await reply_text_safe(update, text)

    asyncio.run(_run())
    assert reply.await_count >= 2
    for call in reply.await_args_list:
        sent = call.args[0]
        assert len(sent) <= TELEGRAM_TEXT_LIMIT
