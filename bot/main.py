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
        await update.message.reply_text(formatters.format_help())

    async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            "ℹ Giới thiệu ngắn\n\n"
            "Bot kết hợp Bộ lọc cơ bản (Tầng 1) và Quant Regime Engine (Tầng 2).\n"
            "Luồng: lọc theo quý → tín hiệu mỗi phiên ghi vào store/ → "
            "bạn đọc bằng lệnh Telegram.\n"
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
                "Ví dụ: /check FPT\n\n"
                "Lệnh này mở 4 khối giải thích:\n"
                "① doanh nghiệp · ② thị trường · ③ xu hướng mã · ④ rủi ro & tỷ trọng"
            )
            return
        ticker = context.args[0].strip().upper()
        signal, fund = read_signal_and_fundamental(ticker)
        if signal is None:
            conn = _conn()
            try:
                wl = {
                    str(r.get("ticker", "")).upper()
                    for r in repository.get_watchlist_rows(conn)
                }
                funds = repository.get_latest_fundamental_scores(conn, [ticker])
            finally:
                conn.close()
            in_univ: bool | None = None
            try:
                from data.universe import load_universe_tickers
                from pipeline.daily_job import load_config

                cfg = load_config()
                ufile = (cfg.get("universe") or {}).get("file")
                if ufile:
                    univ = {str(t).upper() for t in load_universe_tickers(ufile)}
                    in_univ = ticker in univ
            except Exception:  # noqa: BLE001
                in_univ = None
            await update.message.reply_text(
                formatters.format_check_unavailable(
                    ticker,
                    in_watchlist=ticker in wl,
                    has_fundamental=ticker in funds,
                    in_universe_csv=in_univ,
                )
            )
            return

        conn = _conn()
        try:
            sector = repository.get_sector_for_ticker(conn, ticker)
            closes = repository.get_price_closes(conn, ticker, limit_days=120)
        finally:
            conn.close()

        meta: dict[str, Any] = {}
        if sector:
            meta = {
                "market": sector.get("market"),
                "industry": sector.get("industry"),
            }
        if closes and closes[-1].get("close") is not None:
            try:
                meta["last_close"] = float(closes[-1]["close"])
            except (TypeError, ValueError):
                pass
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
                    caption=(
                        f"{ticker} — giá đóng cửa gần đây\n"
                        f"Chi tiết: /check {ticker} · TA tham khảo: /chart {ticker} ta\n\n"
                        f"{formatters.DISCLAIMER}"
                    ),
                )

    async def positions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        conn = _conn()
        try:
            rows = repository.get_open_positions(conn)
        finally:
            conn.close()
        await update.message.reply_text(formatters.format_positions(rows))

    async def backtest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        from telegram import InputFile

        from bot.charts import (
            ChartDataError,
            render_backtest_equity_curve_chart,
            render_drawdown_chart,
            render_regime_conditional_equity_chart,
            render_rolling_sharpe_chart,
            render_trade_pnl_histogram,
        )

        scope = context.args[0].strip() if context.args else "portfolio"
        conn = _conn()
        try:
            rows = repository.get_backtest_results(conn, scope)
            scopes = repository.list_backtest_scopes(conn)
            regime_hist = repository.get_market_regime_history(conn)
        finally:
            conn.close()
        await update.message.reply_text(
            formatters.format_backtest_results(
                rows, scope, available_scopes=scopes
            )
        )
        if not rows:
            return
        run_id = str(rows[0].get("run_id") or "latest")
        chart_dir = Path("store/charts")
        dbp = _db_path()

        async def _send_chart(path: Path, caption: str) -> None:
            with path.open("rb") as handle:
                await update.message.reply_photo(
                    photo=InputFile(handle, filename=path.name),
                    caption=caption,
                )

        try:
            eq_path = render_backtest_equity_curve_chart(
                scope,
                run_id,
                chart_dir / f"backtest_{scope}_{run_id}_equity.png",
                db_path=dbp,
            )
            await _send_chart(
                eq_path,
                f"Đường vốn ablation · {scope} · {run_id}\n"
                "(Nghiên cứu — không phải NAV live)",
            )
        except ChartDataError:
            pass
        try:
            dd_path = render_drawdown_chart(
                scope,
                run_id,
                chart_dir / f"backtest_{scope}_{run_id}_dd.png",
                db_path=dbp,
            )
            await _send_chart(dd_path, f"Drawdown · {scope} · {run_id}")
        except ChartDataError:
            pass
        try:
            rs_path = render_rolling_sharpe_chart(
                scope,
                run_id,
                out_path=chart_dir / f"backtest_{scope}_{run_id}_roll_sharpe.png",
                db_path=dbp,
            )
            await _send_chart(rs_path, f"Rolling Sharpe · {scope} · {run_id}")
        except ChartDataError:
            pass
        try:
            reg_path = render_regime_conditional_equity_chart(
                scope,
                run_id,
                chart_dir / f"backtest_{scope}_{run_id}_regime_eq.png",
                db_path=dbp,
                regime_history=regime_hist or None,
            )
            await _send_chart(
                reg_path,
                f"Equity theo regime · {scope}\n"
                "(Nền màu khi store có lịch sử p_regime nhiều phiên)",
            )
        except ChartDataError:
            pass
        try:
            pnl_path = render_trade_pnl_histogram(
                scope,
                run_id,
                chart_dir / f"backtest_{scope}_{run_id}_pnl.png",
                db_path=dbp,
            )
            await _send_chart(pnl_path, f"PnL% lệnh đã đóng · {scope}")
        except ChartDataError:
            pass

    async def sector_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        flags = _load_config_flags()
        if not flags.get("sector_overview_command", False):
            await update.message.reply_text(
                "Lệnh /sector đang tắt trong cấu hình.\n"
                "Gõ /status để xem các cờ đang bật.\n\n"
                + formatters.DISCLAIMER
            )
            return
        industry_filter = (
            " ".join(context.args).strip() if context.args else ""
        )
        conn = _conn()
        try:
            # as_of quý từ watchlist (PIT); đếm PASS/WATCH/FAIL từ fundamental_scores.
            wl = repository.get_watchlist_rows(conn)
            as_of = wl[0]["as_of_date"] if wl else None
            rows = repository.get_sector_overview(conn, as_of)
            if as_of is None and rows:
                # Fallback khi chưa có watchlist nhưng đã có điểm cơ bản.
                as_of = conn.execute(
                    "SELECT MAX(filed_at) AS d FROM fundamental_scores"
                ).fetchone()["d"]
            n_mapped = conn.execute(
                "SELECT COUNT(*) AS n FROM sector_mapping"
            ).fetchone()["n"]
            n_scores = conn.execute(
                "SELECT COUNT(*) AS n FROM fundamental_scores"
            ).fetchone()["n"]
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
            formatters.format_sector_overview(
                rows,
                as_of,
                has_sector_mapping=bool(n_mapped),
                has_watchlist=bool(wl) or bool(n_scores),
            )
        )
        if rows and as_of:
            from telegram import InputFile

            from bot.charts import ChartDataError, render_sector_overview_chart

            try:
                path = render_sector_overview_chart(
                    str(as_of),
                    Path("store/charts") / f"sector_{as_of}.png",
                    db_path=_db_path(),
                )
                with path.open("rb") as handle:
                    await update.message.reply_photo(
                        photo=InputFile(handle, filename=path.name),
                        caption=f"Tổng quan ngành · {as_of} (PASS/WATCH/FAIL)",
                    )
            except ChartDataError:
                pass

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

    async def chart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Render PNG from store-ready inputs; default chart = fundamental radar."""
        from telegram import InputFile

        from bot.charts import (
            ChartDataError,
            render_fundamental_radar_chart,
            render_garch_risk_band_chart,
            render_monte_carlo_distribution_chart,
            render_price_chart,
            render_price_regime_chart,
            render_realized_vol_band_chart,
            render_ta_reference_chart,
        )
        from bot.ta_reference import ta_indicators_from_closes

        if not context.args:
            await update.message.reply_text(
                "Cú pháp: /chart <mã> [loại]\n\n"
                "Loại tầng 2 / store:\n"
                "• price — giá (+ nền regime nếu có lịch sử p_regime)\n"
                "• fundamental — radar 4 trụ cơ bản (mặc định)\n"
                "• risk — dải GARCH nếu có lịch sử σ̂; không thì rolling\n"
                "• prob — histogram Monte Carlo (khi MC bật + có outcomes)\n"
                "• ta — RSI / đường TB (chỉ tham khảo)\n\n"
                "Ví dụ: /chart FPT price · /chart FPT risk\n"
                "Ablation charts: dùng /backtest"
            )
            return
        ticker = context.args[0].strip().upper()
        kind = context.args[1].strip().lower() if len(context.args) > 1 else "fundamental"
        out = Path("store/charts") / f"{ticker}_{kind}.png"

        captions = {
            "fundamental": f"{ticker} — radar chất lượng doanh nghiệp",
            "price": f"{ticker} — giá + khí hậu thị trường (nếu có)",
            "risk": f"{ticker} — dải biến động (GARCH hoặc rolling)",
            "prob": f"{ticker} — phân phối Monte Carlo",
            "ta": (
                f"{ticker} — TA tham khảo (RSI / đường TB)\n"
                "Không dùng để ra tín hiệu mua/bán"
            ),
        }

        try:
            if kind == "fundamental":
                _, fund = read_signal_and_fundamental(ticker)
                if not fund:
                    raise ChartDataError(
                        f"Chưa có điểm cơ bản cho {ticker}.\n"
                        f"Thử: /chart {ticker} price · /chart {ticker} risk"
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
                    sig_hist = repository.get_signal_history(conn, ticker)
                    regime_hist = repository.get_market_regime_history(conn)
                finally:
                    conn.close()
                if len(closes) < 2:
                    raise ChartDataError(
                        f"Chưa có đủ lịch sử giá cho {ticker}.\n"
                        f"Thử: /chart {ticker} fundamental · /check {ticker}"
                    )
                # Regime nền: ưu tiên chuỗi theo mã, không thì median thị trường.
                p_series = [
                    {"date": r["date"], "p_bull": r["p_regime"]}
                    for r in sig_hist
                    if r.get("p_regime") is not None
                ]
                if len(p_series) < 2:
                    p_series = regime_hist
                if len(p_series) >= 2:
                    path = render_price_regime_chart(
                        ticker, list(closes), [], p_series, out
                    )
                else:
                    path = render_price_chart(ticker, closes, out)
            elif kind == "risk":
                conn = _conn()
                try:
                    closes = repository.get_price_closes(conn, ticker, limit_days=500)
                    sig_hist = repository.get_signal_history(conn, ticker)
                finally:
                    conn.close()
                sigma_hist = [
                    {"date": r["date"], "sigma_hat": r["sigma_hat"]}
                    for r in sig_hist
                    if r.get("sigma_hat") is not None
                ]
                if len(sigma_hist) >= 5:
                    path = render_garch_risk_band_chart(
                        ticker, list(closes), sigma_hist, out
                    )
                    captions["risk"] = (
                        f"{ticker} — dải ±2σ̂ GARCH (lịch sử signals)"
                    )
                else:
                    signal, _ = read_signal_and_fundamental(ticker)
                    sigma = None
                    if signal and signal.get("sigma_hat") is not None:
                        try:
                            sigma = float(signal["sigma_hat"])
                        except (TypeError, ValueError):
                            sigma = None
                    path = render_realized_vol_band_chart(
                        ticker, list(closes), out, latest_sigma_hat=sigma
                    )
                    captions["risk"] = (
                        f"{ticker} — biến động rolling "
                        f"(cần ≥5 phiên σ̂ trong signals để vẽ GARCH đầy đủ)"
                    )
            elif kind == "prob":
                # Bot không fit MC — chỉ vẽ nếu reason_json đã có outcomes.
                signal, _ = read_signal_and_fundamental(ticker)
                reason = {}
                if signal and signal.get("reason_json"):
                    import json as _json

                    try:
                        reason = _json.loads(str(signal["reason_json"]))
                    except _json.JSONDecodeError:
                        reason = {}
                outcomes = reason.get("mc_outcomes") or reason.get("monte_carlo_outcomes")
                if not isinstance(outcomes, list) or not outcomes:
                    await update.message.reply_text(
                        "Biểu đồ «prob» chưa có dữ liệu trong store.\n"
                        "Monte Carlo đang tắt (hoặc chưa ghi outcomes vào reason_json).\n\n"
                        f"Dùng: /chart {ticker} price · risk · fundamental · ta\n"
                        "Hoặc /check để xem slot CVaR / p(TP trước SL).\n\n"
                        + formatters.DISCLAIMER
                    )
                    return
                tp = float(reason.get("tp_pct") or 0.08)
                sl = float(reason.get("sl_pct") or 0.05)
                path = render_monte_carlo_distribution_chart(
                    ticker, [float(x) for x in outcomes], tp, sl, out
                )
            elif kind == "ta":
                conn = _conn()
                try:
                    closes = repository.get_price_closes(conn, ticker, limit_days=500)
                finally:
                    conn.close()
                if len(closes) < 30:
                    raise ChartDataError(
                        f"Chưa đủ lịch sử giá để vẽ TA cho {ticker} "
                        f"(cần ≥30 phiên).\n"
                        f"Thử: /chart {ticker} price · /chart {ticker} fundamental"
                    )
                ta = ta_indicators_from_closes(closes)
                path = render_ta_reference_chart(ticker, list(closes), ta, out)
            else:
                await update.message.reply_text(
                    f"Không nhận loại biểu đồ «{kind}».\n"
                    f"Dùng: /chart {ticker} price · fundamental · risk · prob · ta\n"
                    "Ablation: /backtest\n\n"
                    + formatters.DISCLAIMER
                )
                return
        except ChartDataError as exc:
            await update.message.reply_text(f"{exc}\n\n{formatters.DISCLAIMER}")
            return

        caption = captions.get(kind, f"{ticker} — {kind}")
        with path.open("rb") as handle:
            await update.message.reply_photo(
                photo=InputFile(handle, filename=path.name),
                caption=f"{caption}\n\n{formatters.DISCLAIMER}",
            )

    async def subscribe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        chat_id = update.effective_chat.id
        conn = _conn()
        try:
            repository.set_subscription(conn, chat_id, True)
        finally:
            conn.close()
        await update.message.reply_text(
            "✅ Đã bật nhận tin tự động.\n"
            "Bạn sẽ nhận tín hiệu sau mỗi phiên khi hệ thống chạy xong.\n\n"
            "Tiếp: /signals để xem ngay danh sách hiện có.\n\n"
            + formatters.DISCLAIMER
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
            "Đã tắt nhận tin tự động.\n"
            "Bạn vẫn có thể xem bằng /signals hoặc /check <mã>.\n\n"
            + formatters.DISCLAIMER
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
