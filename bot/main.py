"""Telegram bot — CHỈ ĐỌC từ store/ (ARCHITECTURE invariant #1).

Không fit mô hình, không gọi quant_engine/fundamental_filter để tính điểm.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from bot import formatters
from store import repository


def _db_path() -> str:
    return os.getenv("DATABASE_PATH", "store/bot.db")


def _conn():
    conn = repository.get_connection(_db_path())
    repository.init_schema(conn)
    return conn


def read_latest_signals() -> list[dict]:
    conn = _conn()
    try:
        return repository.get_latest_signals(conn)
    finally:
        conn.close()


def read_watchlist() -> list[dict]:
    conn = _conn()
    try:
        return repository.get_watchlist_rows(conn)
    finally:
        conn.close()


def read_signal_and_fundamental(ticker: str) -> tuple[dict | None, dict | None]:
    ticker = ticker.strip().upper()
    conn = _conn()
    try:
        signals = repository.get_latest_signals(conn)
        signal = next(
            (s for s in signals if str(s["ticker"]).upper() == ticker), None
        )
        funds = repository.get_latest_fundamental_scores(conn, [ticker])
        return signal, funds.get(ticker)
    finally:
        conn.close()


def read_regime() -> tuple[float | None, str | None]:
    signals = read_latest_signals()
    if not signals:
        return None, None
    # Market regime: median p_regime across names (shared index filter in daily_job)
    values = [
        float(s["p_regime"])
        for s in signals
        if s.get("p_regime") is not None
    ]
    if not values:
        return None, signals[0].get("date")
    values.sort()
    mid = values[len(values) // 2]
    return mid, signals[0].get("date")


def _load_config_flags() -> dict[str, bool]:
    import yaml

    path = Path(os.getenv("PIPELINE_CONFIG", "pipeline/config.yaml"))
    if not path.is_file():
        return {}
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    qe = cfg.get("quant_engine") or {}
    ff = cfg.get("fundamental_filter") or {}
    sector = cfg.get("sector_classification") or {}
    flags: dict[str, bool] = {}
    for key, block in {
        "regime_markov": qe.get("regime_markov"),
        "alpha_kalman_trend": qe.get("alpha_kalman_trend"),
        "risk_garch": qe.get("risk_garch"),
        "portfolio_black_litterman": qe.get("portfolio_black_litterman"),
        "probabilistic_monte_carlo": qe.get("probabilistic_monte_carlo"),
        "probabilistic_hawkes": qe.get("probabilistic_hawkes"),
        "safety_merton_dd": ff.get("safety_merton_dd"),
        "sector_overview_command": (sector.get("sector_overview_command") or {}),
    }.items():
        if isinstance(block, dict):
            flags[key] = bool(block.get("enabled", False))
        else:
            flags[key] = False
    return flags


def build_application(token: str):
    """Register command handlers; returns telegram Application."""
    from telegram import Update
    from telegram.ext import Application, CommandHandler, ContextTypes

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(formatters.format_welcome())

    async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await start(update, context)

    async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "Bot kết hợp Bộ lọc cơ bản (Tầng 1) và Quant Regime Engine (Tầng 2).\n"
            "Luồng: quarterly → daily ghi store/ → bạn đọc bằng lệnh Telegram.\n"
            "Bot không tự tính lại mô hình và không khuyến nghị đầu tư.\n\n"
            "Gõ /help để xem cách dùng từng lệnh.\n\n"
            + formatters.DISCLAIMER
        )

    async def signals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        rows = read_latest_signals()
        await update.message.reply_text(formatters.format_signals_list(rows))

    async def watchlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        rows = read_watchlist()
        await update.message.reply_text(formatters.format_watchlist(rows))

    async def regime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        p_bull, as_of = read_regime()
        await update.message.reply_text(formatters.format_regime_message(p_bull, as_of))

    async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        from telegram import InputFile

        from bot.charts import ChartDataError, render_price_chart
        from bot.ta_reference import ta_indicators_from_closes

        if not context.args:
            await update.message.reply_text(
                "Cú pháp: /check <mã>\n"
                "Ví dụ: /check VNM\n"
                "Lệnh này mở 4 khối giải thích cho một mã (cơ bản, regime, alpha, risk)."
            )
            return
        ticker = context.args[0].strip().upper()
        signal, fund = read_signal_and_fundamental(ticker)
        if signal is None:
            await update.message.reply_text(
                f"Chưa có tín hiệu phiên cho {ticker}.\n"
                f"Đợi pipeline daily chạy xong rồi thử lại.\n\n"
                + formatters.DISCLAIMER
            )
            return

        conn = _conn()
        try:
            sector = repository.get_sector_for_ticker(conn, ticker)
            closes = repository.get_price_closes(conn, ticker, limit_days=120)
        finally:
            conn.close()

        meta = {}
        if sector:
            meta = {
                "market": sector.get("market"),
                "industry": sector.get("industry"),
            }
        ta = ta_indicators_from_closes(closes)
        text = formatters.format_signal_message(
            signal, fund, ta_indicators=ta, meta=meta
        )
        await update.message.reply_text(text)

        # Gửi PNG giá nếu đã có đủ bars (không gọi vendor)
        if len(closes) >= 2:
            out = Path("store/charts") / f"{ticker}_price.png"
            try:
                path = render_price_chart(ticker, closes, out)
            except ChartDataError:
                return
            with path.open("rb") as handle:
                await update.message.reply_photo(
                    photo=InputFile(handle, filename=path.name),
                    caption=f"{ticker} — giá gần đây\n\n{formatters.DISCLAIMER}",
                )

    async def positions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        conn = _conn()
        try:
            rows = repository.get_open_positions(conn)
        finally:
            conn.close()
        await update.message.reply_text(formatters.format_positions(rows))

    async def backtest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        scope = context.args[0].strip() if context.args else "portfolio"
        conn = _conn()
        try:
            rows = repository.get_backtest_results(conn, scope)
        finally:
            conn.close()
        await update.message.reply_text(
            formatters.format_backtest_results(rows, scope)
        )

    async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        conn = _conn()
        try:
            signals = repository.get_latest_signals(conn)
            watchlist = repository.get_watchlist(conn)
            positions = repository.get_open_positions(conn)
        finally:
            conn.close()
        latest = signals[0].get("date") if signals else None
        await update.message.reply_text(
            formatters.format_status(
                config_flags=_load_config_flags(),
                latest_signal_date=latest,
                watchlist_n=len(watchlist),
                open_positions_n=len(positions),
            )
        )

    async def sector_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        flags = _load_config_flags()
        if not flags.get("sector_overview_command", False):
            await update.message.reply_text(
                "/sector đang tắt (sector_overview_command.enabled=false).\n\n"
                + formatters.DISCLAIMER
            )
            return
        industry_filter = (
            " ".join(context.args).strip() if context.args else ""
        )
        conn = _conn()
        try:
            signals = repository.get_latest_signals(conn)
            as_of = signals[0]["date"] if signals else None
            if as_of is None:
                wl = repository.get_watchlist_rows(conn)
                as_of = wl[0]["as_of_date"] if wl else None
            if as_of is None:
                rows = []
            else:
                rows = repository.get_sector_overview(conn, as_of)
        finally:
            conn.close()
        if industry_filter:
            needle = industry_filter.casefold()
            rows = [
                r
                for r in rows
                if needle in str(r.get("industry", "")).casefold()
            ]
        await update.message.reply_text(
            formatters.format_sector_overview(rows, as_of)
        )

    async def chart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Render PNG from store-ready inputs; default chart = fundamental radar."""
        from telegram import InputFile

        from bot.charts import (
            ChartDataError,
            render_fundamental_radar_chart,
            render_price_chart,
        )

        if not context.args:
            await update.message.reply_text(
                "Dùng: /chart VNM [fundamental|price|risk|prob|ta]\n"
                "Mặc định: fundamental (radar từ store)."
            )
            return
        ticker = context.args[0].strip().upper()
        kind = context.args[1].strip().lower() if len(context.args) > 1 else "fundamental"
        out = Path("store/charts") / f"{ticker}_{kind}.png"

        try:
            if kind == "fundamental":
                _, fund = read_signal_and_fundamental(ticker)
                if not fund:
                    raise ChartDataError(
                        f"Chưa có điểm cơ bản cho {ticker}. "
                        f"Đợi sau kỳ lọc doanh nghiệp (quý) rồi thử lại."
                    )
                path = render_fundamental_radar_chart(
                    ticker,
                    float(fund.get("growth_score") or float("nan")),
                    float(fund.get("quality_score") or float("nan")),
                    float(fund.get("safety_score") or float("nan")),
                    float(fund.get("valuation_score") or float("nan")),
                    out,
                )
            elif kind == "price":
                conn = _conn()
                try:
                    closes = repository.get_price_closes(conn, ticker, limit_days=500)
                finally:
                    conn.close()
                if len(closes) < 2:
                    raise ChartDataError(
                        f"Chưa có đủ lịch sử giá cho {ticker}. "
                        f"Biểu đồ sẽ có sau khi pipeline phiên chạy xong "
                        f"(thường sau 15:00 ngày giao dịch)."
                    )
                path = render_price_chart(ticker, closes, out)
            else:
                await update.message.reply_text(
                    f"Loại biểu đồ `{kind}` chưa mở trong bản này. "
                    f"Dùng /chart {ticker} fundamental hoặc /chart {ticker} price.\n\n"
                    + formatters.DISCLAIMER
                )
                return
        except ChartDataError as exc:
            await update.message.reply_text(f"{exc}\n\n{formatters.DISCLAIMER}")
            return

        with path.open("rb") as handle:
            await update.message.reply_photo(
                photo=InputFile(handle, filename=path.name),
                caption=f"{ticker} — {kind}\n\n{formatters.DISCLAIMER}",
            )

    async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        conn = _conn()
        try:
            repository.set_subscription(conn, chat_id, True)
        finally:
            conn.close()
        await update.message.reply_text(
            "Đã bật thông báo.\n\n" + formatters.DISCLAIMER
        )

    async def unsubscribe_cmd(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        chat_id = update.effective_chat.id
        conn = _conn()
        try:
            repository.set_subscription(conn, chat_id, False)
        finally:
            conn.close()
        await update.message.reply_text(
            "Đã tắt thông báo.\n\n" + formatters.DISCLAIMER
        )

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("signals", signals_cmd))
    app.add_handler(CommandHandler("watchlist", watchlist_cmd))
    app.add_handler(CommandHandler("regime", regime_cmd))
    app.add_handler(CommandHandler("check", check_cmd))
    app.add_handler(CommandHandler("positions", positions_cmd))
    app.add_handler(CommandHandler("backtest", backtest_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("sector", sector_cmd))
    app.add_handler(CommandHandler("chart", chart_cmd))
    app.add_handler(CommandHandler("subscribe", subscribe_cmd))
    app.add_handler(CommandHandler("unsubscribe", unsubscribe_cmd))
    return app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Telegram bot (store read-only)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate wiring without polling Telegram",
    )
    args = parser.parse_args(argv)

    # Optional .env load without requiring python-dotenv
    env_path = Path(".env")
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())

    token = os.getenv("BOT_TOKEN", "")
    db = _db_path()

    if args.dry_run or token in ("", "changeme"):
        print("bot dry-run OK")
        print(f"  DATABASE_PATH={db}")
        print(f"  BOT_TOKEN set: {bool(token and token != 'changeme')}")
        # Touch schema so empty store is ready
        conn = repository.get_connection(db)
        try:
            repository.init_schema(conn)
            n_sig = len(repository.get_latest_signals(conn))
            n_wl = len(repository.get_watchlist(conn))
        finally:
            conn.close()
        print(f"  signals rows (latest date): {n_sig}")
        print(f"  watchlist size: {n_wl}")
        if not args.dry_run and token in ("", "changeme"):
            print("  Set BOT_TOKEN in .env to start polling.")
        return

    app = build_application(token)
    print("bot polling…")
    app.run_polling()


if __name__ == "__main__":
    main()
