"""Phase F — Button-first navigation: menu, Home, awaiting_ticker, risk/prob, sub, rổ Fund."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot import formatters
from store import repository


def _all_cbs(kb) -> list[str]:
    return [b.callback_data for row in kb.inline_keyboard for b in row]


def _has_home(kb) -> bool:
    return "nav:home" in _all_cbs(kb)


def test_main_menu_eight_buttons_and_callback_len():
    kb = formatters.build_main_menu_keyboard()
    cbs = _all_cbs(kb)
    assert len(cbs) == 8
    expected = {
        "nav:signals",
        "nav:check_prompt",
        "nav:regime",
        "nav:watchlist",
        "nav:positions",
        "nav:backtest",
        "nav:notifications",
        "nav:help",
    }
    assert set(cbs) == expected
    assert all(len(c.encode("utf-8")) <= 64 for c in cbs)


def test_major_keyboards_include_nav_home():
    """Mọi keyboard chính có hàng 🏠 Menu chính."""
    assert _has_home(
        formatters.build_signals_opener_keyboard(n_buy=1, n_watch=1, n_sell=0)
    )
    assert _has_home(formatters.build_signals_keyboard(0, 3))
    assert _has_home(formatters.build_signals_keyboard(0, 1))
    assert _has_home(formatters.build_watchlist_keyboard(n_pass=1, n_watch=0))
    assert _has_home(formatters.build_positions_keyboard(has_rows=True))
    assert _has_home(formatters.build_positions_keyboard(has_rows=False))
    assert _has_home(formatters.build_backtest_keyboard("run_x"))
    assert _has_home(formatters.build_regime_keyboard())
    assert _has_home(
        formatters.build_check_keyboard(
            formatters.CHECK_PASS, "FPT", has_price_bars=True
        )
    )
    assert _has_home(
        formatters.build_check_keyboard(
            formatters.CHECK_OUT_OF_SCOPE, "XYZ", has_price_bars=False
        )
    )
    assert _has_home(
        formatters.build_fund_basket_opener_keyboard(
            {"PASS": 1, "WATCH": 0, "FAIL": 2, "INSUFFICIENT": 0}
        )
    )
    assert _has_home(formatters.build_notifications_keyboard(is_active=False))


def test_chk_risk_prob_hidden_without_data():
    rows = formatters.check_keyboard_rows(
        formatters.CHECK_PASS,
        "FPT",
        has_price_bars=True,
        has_risk_chart=False,
        has_prob_chart=False,
    )
    acts = {cb.split(":")[1] for r in rows for _l, cb in r}
    assert "risk" not in acts and "prob" not in acts

    rows2 = formatters.check_keyboard_rows(
        formatters.CHECK_PASS,
        "FPT",
        has_price_bars=True,
        has_risk_chart=True,
        has_prob_chart=True,
    )
    acts2 = {cb.split(":")[1] for r in rows2 for _l, cb in r}
    assert "risk" in acts2 and "prob" in acts2
    for r in rows2:
        for _l, cb in r:
            assert len(cb.encode("utf-8")) <= 64


def test_fund_basket_four_groups_from_scores(tmp_path):
    db = tmp_path / "fund.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    repository.upsert_fundamental_scores(
        conn,
        [
            {
                "ticker": "AAA",
                "filed_at": "2024-12-31",
                "period": "2024",
                "growth_score": 70,
                "quality_score": 70,
                "safety_score": 70,
                "valuation_score": 70,
                "fundamental_view": "PASS",
                "headline_json": "{}",
            },
            {
                "ticker": "BBB",
                "filed_at": "2024-12-31",
                "period": "2024",
                "growth_score": 50,
                "quality_score": 50,
                "safety_score": 50,
                "valuation_score": 50,
                "fundamental_view": "WATCH",
                "headline_json": "{}",
            },
            {
                "ticker": "CCC",
                "filed_at": "2024-12-31",
                "period": "2024",
                "growth_score": 20,
                "quality_score": 20,
                "safety_score": 20,
                "valuation_score": 20,
                "fundamental_view": "FAIL",
                "headline_json": "{}",
            },
            {
                "ticker": "DDD",
                "filed_at": "2024-12-31",
                "period": "2024",
                "growth_score": None,
                "quality_score": None,
                "safety_score": None,
                "valuation_score": None,
                "fundamental_view": "WATCH",
                "headline_json": '{"classification_reason": "INSUFFICIENT_DATA"}',
            },
        ],
    )
    scores = repository.get_latest_fundamental_scores(conn)
    conn.close()
    groups = formatters.group_fundamental_scores(scores)
    counts = formatters.fund_basket_counts(groups)
    assert counts["PASS"] == 1
    assert counts["WATCH"] == 1
    assert counts["FAIL"] == 1
    assert counts["INSUFFICIENT"] == 1
    summary = formatters.format_fund_basket_summary(counts, as_of="2024-12-31")
    assert "Rổ lọc doanh nghiệp" in summary
    assert "watchlist của tôi" not in summary.casefold()
    assert "1 mã ĐẠT" in summary and "1 mã KHÔNG ĐẠT" in summary
    kb = formatters.build_fund_basket_opener_keyboard(counts)
    cbs = _all_cbs(kb)
    assert any(c.startswith("fund:PASS:") for c in cbs)
    assert any(c.startswith("fund:FAIL:") for c in cbs)
    assert "nav:home" in cbs


def test_notifications_toggle_copy_and_keyboard():
    on_txt = formatters.format_notifications_text(is_active=True)
    off_txt = formatters.format_notifications_text(is_active=False)
    assert "ĐANG BẬT" in on_txt and "ĐANG TẮT" in off_txt
    on_kb = formatters.build_notifications_keyboard(is_active=True)
    off_kb = formatters.build_notifications_keyboard(is_active=False)
    assert "sub:off" in _all_cbs(on_kb)
    assert "sub:on" in _all_cbs(off_kb)
    assert _has_home(on_kb) and _has_home(off_kb)


def test_subscription_toggle_persists(tmp_path):
    db = tmp_path / "sub.db"
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    assert repository.is_subscriber_active(conn, 99) is False
    repository.set_subscription(conn, 99, True)
    assert repository.is_subscriber_active(conn, 99) is True
    repository.set_subscription(conn, 99, False)
    assert repository.is_subscriber_active(conn, 99) is False
    conn.close()


def test_awaiting_ticker_invalid_copy():
    msg = formatters.format_awaiting_ticker_invalid("hello")
    assert "không hợp lệ" in msg.casefold() or "Không hợp lệ" in msg
    assert "FPT" in msg
    assert formatters.DISCLAIMER in msg


def test_nav_home_and_check_prompt_callbacks(tmp_path, monkeypatch):
    """nav:home / nav:check_prompt — answer(); set/clear awaiting_ticker."""
    db = tmp_path / "bot.db"
    monkeypatch.setenv("DATABASE_PATH", str(db))
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    conn.close()

    from bot import main as bot_main

    app = bot_main.build_application("test-token-unused")
    cb_handler = None
    for handlers in app.handlers.values():
        for h in handlers:
            if h.__class__.__name__ == "CallbackQueryHandler":
                cb_handler = h
                break
    assert cb_handler is not None

    async def _fire(data: str, user_data: dict):
        answer = AsyncMock()
        edit = AsyncMock()
        reply = AsyncMock()
        query = SimpleNamespace(
            data=data,
            answer=answer,
            message=SimpleNamespace(reply_text=reply, edit_message_text=edit),
            edit_message_text=edit,
        )
        update = SimpleNamespace(
            callback_query=query,
            effective_chat=SimpleNamespace(id=1),
        )
        context = SimpleNamespace(user_data=user_data, args=None)
        await cb_handler.callback(update, context)
        return answer, edit, reply, user_data

    async def _run():
        ud: dict = {}
        ans, edit, _reply, ud = await _fire("nav:check_prompt", ud)
        ans.assert_awaited()
        assert ud.get("awaiting_ticker") is True
        assert edit.await_count >= 1

        ans2, edit2, _r2, ud = await _fire("nav:home", ud)
        ans2.assert_awaited()
        assert "awaiting_ticker" not in ud
        # edit về home + main menu
        assert edit2.await_count >= 1
        call_kwargs = edit2.await_args.kwargs
        assert call_kwargs.get("reply_markup") is not None

    asyncio.run(_run())


def test_nav_signals_clears_awaiting(tmp_path, monkeypatch):
    db = tmp_path / "bot2.db"
    monkeypatch.setenv("DATABASE_PATH", str(db))
    conn = repository.get_connection(str(db))
    repository.init_schema(conn)
    conn.close()

    from bot import main as bot_main

    app = bot_main.build_application("test-token-unused")
    cb_handler = None
    for handlers in app.handlers.values():
        for h in handlers:
            if h.__class__.__name__ == "CallbackQueryHandler":
                cb_handler = h
                break

    async def _run():
        answer = AsyncMock()
        edit = AsyncMock()
        reply = AsyncMock()
        query = SimpleNamespace(
            data="nav:signals",
            answer=answer,
            message=SimpleNamespace(reply_text=reply, edit_message_text=edit),
            edit_message_text=edit,
        )
        update = SimpleNamespace(
            callback_query=query, effective_chat=SimpleNamespace(id=7)
        )
        context = SimpleNamespace(user_data={"awaiting_ticker": True}, args=None)
        await cb_handler.callback(update, context)
        assert "awaiting_ticker" not in context.user_data

    asyncio.run(_run())
