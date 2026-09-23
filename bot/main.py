"""Telegram bot — CHỈ ĐỌC từ store/ (ARCHITECTURE invariant #1).

Không fit mô hình, không gọi quant_engine/fundamental_filter để tính điểm.
"""

from __future__ import annotations

import argparse
import logging
import os
from pathlib import Path
from typing import Any

from bot import formatters
from store import repository

logger = logging.getLogger(__name__)

# Telegram giới hạn 4096 ký tự/tin; chừa biên để tránh BadRequest.
TELEGRAM_TEXT_LIMIT = 4000


def chunk_telegram_text(text: str, limit: int = TELEGRAM_TEXT_LIMIT) -> list[str]:
    """Cắt chuỗi tin nhắn Telegram theo đoạn/dòng, mỗi phần ≤ limit (< 4096).

    Ưu tiên cắt tại ``\\n``; nếu một dòng dài hơn limit thì cắt cứng theo ký tự.
    """
    if limit <= 0:
        raise ValueError("limit phải > 0")
    if not text:
        return [""]
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        window = remaining[:limit]
        # Ưu tiên cắt tại xuống dòng gần cuối cửa sổ.
        cut = window.rfind("\n")
        if cut <= 0:
            cut = limit
        piece = remaining[:cut]
        # Bỏ \\n đứng đầu phần còn lại nếu cắt đúng tại newline.
        rest = remaining[cut:]
        if rest.startswith("\n"):
            rest = rest[1:]
        if not piece:
            # Dòng đơn quá dài: cắt cứng.
            piece = remaining[:limit]
            rest = remaining[limit:]
        chunks.append(piece)
        remaining = rest
    return chunks


async def reply_text_safe(
    update: Any,
    text: str,
    *,
    limit: int = TELEGRAM_TEXT_LIMIT,
    reply_markup: Any = None,
) -> None:
    """Gửi ``text`` qua ``update.message.reply_text``, chia chunk nếu cần.

    ``reply_markup`` (nếu có) gắn vào chunk cuối. Nếu ``update.message`` là None
    thì bỏ qua và log.
    """
    message = getattr(update, "message", None)
    if message is None:
        logger.warning("reply_text_safe: update.message is None — bỏ qua gửi tin")
        return
    parts = chunk_telegram_text(text, limit=limit)
    last = len(parts) - 1
    for i, part in enumerate(parts):
        kwargs: dict[str, Any] = {}
        if reply_markup is not None and i == last:
            kwargs["reply_markup"] = reply_markup
        await message.reply_text(part, **kwargs)


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


def read_open_position(ticker: str) -> dict | None:
    """Vị thế giấy OPEN mới nhất cho mã (nếu có)."""
    ticker = ticker.strip().upper()
    conn = _conn()
    try:
        rows = repository.get_open_positions(conn)
    finally:
        conn.close()
    matches = [r for r in rows if str(r.get("ticker", "")).upper() == ticker]
    if not matches:
        return None
    # opened_at mới nhất nếu có nhiều dòng
    matches.sort(key=lambda r: str(r.get("opened_at") or ""), reverse=True)
    return matches[0]


def _universe_and_finance_flags(ticker: str) -> tuple[bool | None, bool, bool]:
    """(in_universe, is_financial, exclude_financials) — chỉ đọc config/store, không crawl.

    ``is_financial`` dùng curated ticker + industry keywords (không phụ thuộc
    sector_mapping đủ) để VCB/SSI → EXCLUDED_FINANCIAL, không nhầm thiếu data.
    """
    ticker = ticker.strip().upper()
    in_univ: bool | None = None
    is_fin = False
    exclude_fin = True
    try:
        from data.ingest.scoring_frames import is_excluded_financial
        from data.universe import load_universe_tickers
        from pipeline.daily_job import load_config

        cfg = load_config()
        # Prefer fundamental_file (VN100 Tier1); fallback file/smoke.
        univ_cfg = cfg.get("universe") or {}
        ufile = (
            univ_cfg.get("fundamental_file")
            or univ_cfg.get("file")
            or univ_cfg.get("smoke_file")
        )
        if ufile:
            univ = {str(t).upper() for t in load_universe_tickers(ufile)}
            in_univ = ticker in univ
        exclude_fin = bool(
            (cfg.get("fundamental_filter") or {}).get("exclude_financials", True)
        )
        industry = None
        conn = _conn()
        try:
            sector = repository.get_sector_for_ticker(conn, ticker)
        finally:
            conn.close()
        if sector:
            industry = sector.get("industry") or sector.get("sector")
        is_fin = is_excluded_financial(ticker, industry)
    except Exception:  # noqa: BLE001
        # Fallback cứng: curated vẫn nhận diện khi import/config lỗi nhẹ.
        try:
            from data.ingest.scoring_frames import is_excluded_financial

            is_fin = is_excluded_financial(ticker, None)
        except Exception:  # noqa: BLE001
            pass
    return in_univ, is_fin, exclude_fin


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


def _load_w_max() -> float:
    """Trần % NAV/mã từ config (GARCH sizing) — mặc định 0.10."""
    import yaml

    path = Path(os.getenv("PIPELINE_CONFIG", "pipeline/config.yaml"))
    if not path.is_file():
        return 0.10
    cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    try:
        return float((cfg.get("quant_engine") or {}).get("w_max", 0.10))
    except (TypeError, ValueError):
        return 0.10


def build_application(token: str):
    """Register command handlers; returns telegram Application."""
    import logging
    import re

    from telegram import InputFile, Update
    from telegram.ext import (
        Application,
        CallbackQueryHandler,
        CommandHandler,
        ContextTypes,
        MessageHandler,
        filters,
    )

    log = logging.getLogger("bot.main")

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        # ReplyKeyboard: điền lệnh thường dùng vào ô chat (không phải InlineKeyboard).
        await update.message.reply_text(
            formatters.format_welcome(),
            reply_markup=formatters.build_start_reply_keyboard(),
        )

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

    async def _send_signals_page(
        *,
        reply_target: Any,
        page: int,
        edit: bool = False,
    ) -> None:
        """Gửi/sửa trang /signals — chỉ đọc store, không fit model."""
        rows = read_latest_signals()
        w_max = _load_w_max()
        total = formatters.signals_total_pages(rows)
        page_i = max(0, min(int(page), total - 1))
        text = formatters.format_signals_list(rows, w_max=w_max, page=page_i)
        kb = formatters.build_signals_keyboard(page_i, total)
        if edit and hasattr(reply_target, "edit_message_text"):
            try:
                await reply_target.edit_message_text(text, reply_markup=kb)
                return
            except Exception:  # noqa: BLE001
                log.debug("edit_message_text failed — fallback reply", exc_info=True)
        # reply_target có thể là Update hoặc Message
        message = getattr(reply_target, "message", None) or reply_target
        if message is None:
            return
        parts = chunk_telegram_text(text)
        last = len(parts) - 1
        for i, part in enumerate(parts):
            kwargs: dict[str, Any] = {}
            if kb is not None and i == last:
                kwargs["reply_markup"] = kb
            await message.reply_text(part, **kwargs)

    async def signals_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        await _send_signals_page(reply_target=update, page=0, edit=False)

    async def watchlist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        rows = read_watchlist()
        await reply_text_safe(update, formatters.format_watchlist(rows))

    async def regime_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        p_bull, as_of = read_regime()
        await update.message.reply_text(
            formatters.format_regime_message(p_bull, as_of),
            reply_markup=formatters.build_regime_keyboard(),
        )

    async def check_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        from telegram import InputFile

        from bot.charts import (
            ChartDataError,
            render_fundamental_radar_chart,
            render_garch_risk_band_chart,
            render_monte_carlo_distribution_chart,
            render_price_chart,
            render_realized_vol_band_chart,
            render_ta_reference_chart,
        )
        from bot.ta_reference import ta_indicators_from_closes

        if not context.args:
            await update.message.reply_text(
                "Cú pháp: /check <mã>\n"
                "Ví dụ: /check FPT\n\n"
                "Luồng: dữ liệu → Fundamental → Quant/Risk (nếu đủ) → "
                "ưu tiên vị thế nếu đang nắm giấy."
            )
            return
        ticker = context.args[0].strip().upper()
        signal, fund = read_signal_and_fundamental(ticker)
        position = read_open_position(ticker)
        in_univ, is_fin, exclude_fin = _universe_and_finance_flags(ticker)

        conn = _conn()
        try:
            sector = repository.get_sector_for_ticker(conn, ticker)
            closes = repository.get_price_closes(conn, ticker, limit_days=120)
            sig_hist = repository.get_signal_history(conn, ticker)
        finally:
            conn.close()

        meta: dict[str, Any] = {}
        if sector:
            meta = {
                "market": sector.get("market"),
                "industry": sector.get("industry"),
            }
        elif is_fin:
            # Curated fallback — vẫn nói «tài chính» khi thiếu sector_mapping.
            meta["industry"] = "ngành tài chính (ước tính)"
        if closes and closes[-1].get("close") is not None:
            try:
                meta["last_close"] = float(closes[-1]["close"])
            except (TypeError, ValueError):
                pass
        ta = ta_indicators_from_closes(closes)

        state = formatters.resolve_check_state(
            in_universe=in_univ,
            is_financial=is_fin,
            exclude_financials=exclude_fin,
            fund=fund,
            signal=signal,
            has_open_position=position is not None,
        )
        text = formatters.format_check_by_state(
            state,
            ticker,
            fund=fund,
            signal=signal,
            position=position,
            ta_indicators=ta,
            meta=meta,
            w_max=_load_w_max(),
        )
        # Nút UX (Phần C) — không đổi state machine; charts vẫn gửi tự động bên dưới.
        check_kb = formatters.build_check_keyboard(
            state, ticker, has_price_bars=len(closes) >= 2
        )
        await update.message.reply_text(text, reply_markup=check_kb)

        async def _send_png(path: Path, caption: str) -> None:
            with path.open("rb") as handle:
                await update.message.reply_photo(
                    photo=InputFile(handle, filename=path.name),
                    caption=caption,
                )

        chart_dir = Path("store/charts")
        pass_like = state in {
            formatters.CHECK_PASS,
            formatters.CHECK_PASS_NO_SIGNAL,
            formatters.CHECK_WATCH,
            formatters.CHECK_POSITION,
        }
        price_ta_states = {
            formatters.CHECK_EXCLUDED_FINANCIAL,
            formatters.CHECK_INSUFFICIENT,
            formatters.CHECK_FAIL,
            formatters.CHECK_OUT_OF_SCOPE,
            formatters.CHECK_WATCH,
            formatters.CHECK_PASS_NO_SIGNAL,
            formatters.CHECK_PASS,
            formatters.CHECK_POSITION,
        }

        def _four_pillars_finite(row: dict | None) -> bool:
            if not row:
                return False
            try:
                vals = [
                    float(row.get("growth_score")),
                    float(row.get("quality_score")),
                    float(row.get("safety_score")),
                    float(row.get("valuation_score")),
                ]
            except (TypeError, ValueError):
                return False
            return all(v == v and v not in (float("inf"), float("-inf")) for v in vals)

        # Pack: giá/TA cho mọi state nếu store có bars; radar khi đủ 4 trụ;
        # risk/MC chỉ khi pass_like + Quant trong store.
        if len(closes) >= 2 and state in price_ta_states:
            try:
                path = render_price_chart(
                    ticker, closes, chart_dir / f"{ticker}_price.png"
                )
                await _send_png(
                    path,
                    f"{ticker} — giá đóng cửa gần đây\n"
                    f"{formatters.DISCLAIMER}",
                )
            except ChartDataError:
                pass

        if fund and _four_pillars_finite(fund):
            try:
                path = render_fundamental_radar_chart(
                    ticker,
                    float(fund.get("growth_score")),
                    float(fund.get("quality_score")),
                    float(fund.get("safety_score")),
                    float(fund.get("valuation_score")),
                    chart_dir / f"{ticker}_fundamental.png",
                )
                await _send_png(path, f"{ticker} — radar 4 trụ Fundamental")
            except (ChartDataError, TypeError, ValueError):
                pass

        if state in price_ta_states and len(closes) >= 20:
            try:
                path = render_ta_reference_chart(
                    ticker, list(closes), ta, chart_dir / f"{ticker}_ta.png"
                )
                await _send_png(
                    path,
                    f"{ticker} — TA tham khảo — không phải tín hiệu hệ thống",
                )
            except ChartDataError:
                pass

        if pass_like and len(closes) >= 5:
            try:
                sigma_hist = [
                    {"date": r["date"], "sigma_hat": r["sigma_hat"]}
                    for r in sig_hist
                    if r.get("sigma_hat") is not None
                ]
                out_risk = chart_dir / f"{ticker}_risk.png"
                if len(sigma_hist) >= 5:
                    path = render_garch_risk_band_chart(
                        ticker, list(closes), sigma_hist, out_risk
                    )
                else:
                    path = render_realized_vol_band_chart(
                        ticker, list(closes), out_risk
                    )
                await _send_png(path, f"{ticker} — dải biến động")
            except ChartDataError:
                pass

        # prob chỉ khi store có MC outcomes (không bịa)
        if pass_like and signal:
            reason: dict = {}
            raw = signal.get("reason_json")
            if isinstance(raw, dict):
                reason = raw
            elif raw:
                try:
                    import json as _json

                    reason = _json.loads(str(raw))
                except (TypeError, ValueError):
                    reason = {}
            outcomes = reason.get("mc_outcomes") or reason.get(
                "monte_carlo_outcomes"
            )
            if outcomes:
                try:
                    path = render_monte_carlo_distribution_chart(
                        ticker,
                        outcomes,
                        chart_dir / f"{ticker}_prob.png",
                    )
                    await _send_png(path, f"{ticker} — Monte Carlo (store)")
                except ChartDataError:
                    pass

    async def positions_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        conn = _conn()
        try:
            rows = repository.get_open_positions(conn)
        finally:
            conn.close()
        await update.message.reply_text(
            formatters.format_positions(rows, w_max=_load_w_max())
        )

    async def backtest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        scope = context.args[0].strip() if context.args else "portfolio"
        conn = _conn()
        try:
            rows = repository.get_backtest_results(conn, scope)
            scopes = repository.list_backtest_scopes(conn)
            run_id_preview = str(rows[0]["run_id"]) if rows else None
            checks = (
                repository.get_backtest_checks(
                    conn, scope, "framework", run_id_preview
                )
                if run_id_preview
                else []
            )
            yearly = (
                repository.get_yearly_breakdown(
                    conn, scope, "framework", run_id_preview
                )
                if run_id_preview
                else []
            )
        finally:
            conn.close()
        # Lưu scope để callback bt:<view>:<run_id> đọc lại (không nhồi scope vào callback).
        context.user_data["bt_scope"] = scope
        bt_kb = None
        if rows:
            run_id = str(rows[0].get("run_id") or "latest")
            context.user_data["bt_run_id"] = run_id
            bt_kb = formatters.build_backtest_keyboard(run_id)
        await reply_text_safe(
            update,
            formatters.format_backtest_results(
                rows,
                scope,
                available_scopes=scopes,
                checks=checks,
                yearly=yearly,
            ),
            reply_markup=bt_kb,
        )
        # Phần C: không gửi hết ảnh 1 lần — chuyển view qua nút bt:<view>:<run_id>.

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

    async def _callback_send_png(message: Any, path: Path, caption: str) -> None:
        with path.open("rb") as handle:
            await message.reply_photo(
                photo=InputFile(handle, filename=path.name),
                caption=caption,
            )

    async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """CallbackQuery — luôn answer(); chỉ đọc store/charts, không network/pipeline."""
        from bot.charts import (
            ChartDataError,
            render_backtest_equity_curve_chart,
            render_fundamental_radar_chart,
            render_price_chart,
            render_ta_reference_chart,
            render_yearly_stats_chart,
        )
        from bot.ta_reference import ta_indicators_from_closes

        query = update.callback_query
        if query is None:
            return
        # Bắt buộc answer() mọi callback — tránh icon loading treo trên client.
        await query.answer()
        data = (query.data or "").strip()
        message = query.message
        if message is None:
            return

        # --- /signals phân trang ---
        if data.startswith("page:signals:"):
            try:
                page_i = int(data.split(":")[-1])
            except ValueError:
                page_i = 0
            await _send_signals_page(reply_target=query, page=page_i, edit=True)
            return

        # --- /regime → /signals ---
        if data == "nav:signals":
            await _send_signals_page(reply_target=message, page=0, edit=False)
            return

        # --- /backtest view switcher ---
        if data.startswith("bt:"):
            parts = data.split(":", 2)
            if len(parts) < 3:
                await message.reply_text("Callback backtest không hợp lệ.")
                return
            view, run_id = parts[1], parts[2]
            scope = str(context.user_data.get("bt_scope") or "portfolio")
            chart_dir = Path("store/charts")
            dbp = _db_path()
            try:
                if view in ("b0", "b1", "b2"):
                    labels = {
                        "b0": "So sánh B0 (mua & giữ)",
                        "b1": "So sánh B1 (TA)",
                        "b2": "So sánh B2 (CANSLIM)",
                    }
                    path = render_backtest_equity_curve_chart(
                        scope,
                        run_id,
                        chart_dir / f"backtest_{scope}_{run_id}_{view}.png",
                        db_path=dbp,
                        align_to_oos=True,
                    )
                    await _callback_send_png(
                        message,
                        path,
                        f"{labels.get(view, view)} · {scope} · {run_id}\n"
                        "(Nghiên cứu — chỉ đọc store)",
                    )
                elif view == "yearly":
                    path = render_yearly_stats_chart(
                        scope,
                        "framework",
                        run_id,
                        chart_dir / f"backtest_{scope}_{run_id}_yearly.png",
                        db_path=dbp,
                    )
                    await _callback_send_png(
                        message, path, f"Sharpe theo năm · {scope} · {run_id}"
                    )
                elif view == "checks":
                    conn = _conn()
                    try:
                        checks = repository.get_backtest_checks(
                            conn, scope, "framework", run_id
                        )
                    finally:
                        conn.close()
                    await message.reply_text(
                        formatters.format_backtest_checks_only(
                            checks, scope=scope, run_id=run_id
                        )
                    )
                else:
                    await message.reply_text(f"Không nhận view «{view}».")
            except ChartDataError as exc:
                await message.reply_text(f"{exc}\n\n{formatters.DISCLAIMER}")
            return

        # --- /check action buttons ---
        if data.startswith("chk:"):
            parts = data.split(":", 2)
            if len(parts) < 3:
                await message.reply_text("Callback /check không hợp lệ.")
                return
            action, ticker = parts[1], parts[2].strip().upper()
            chart_dir = Path("store/charts")

            if action == "watch_add":
                wl = read_watchlist()
                on_wl = any(
                    str(r.get("ticker", "")).upper() == ticker for r in wl
                )
                await message.reply_text(
                    formatters.format_watch_add_ack(
                        ticker, on_system_watchlist=on_wl
                    )
                )
                return

            if action == "pnl":
                signal, fund = read_signal_and_fundamental(ticker)
                position = read_open_position(ticker)
                if not position:
                    await message.reply_text(
                        f"Chưa có vị thế OPEN cho {ticker} trong store.\n\n"
                        + formatters.DISCLAIMER
                    )
                    return
                conn = _conn()
                try:
                    closes = repository.get_price_closes(conn, ticker, limit_days=5)
                finally:
                    conn.close()
                meta: dict[str, Any] = {}
                if closes and closes[-1].get("close") is not None:
                    try:
                        meta["last_close"] = float(closes[-1]["close"])
                    except (TypeError, ValueError):
                        pass
                await message.reply_text(
                    formatters.format_check_position_aware(
                        position, signal, fund, meta=meta
                    )
                )
                return

            conn = _conn()
            try:
                closes = repository.get_price_closes(conn, ticker, limit_days=120)
                funds = repository.get_latest_fundamental_scores(conn, [ticker])
                fund = funds.get(ticker)
            finally:
                conn.close()

            try:
                if action == "price":
                    if len(closes) < 2:
                        raise ChartDataError(f"Chưa đủ giá để vẽ biểu đồ {ticker}.")
                    path = render_price_chart(
                        ticker, closes, chart_dir / f"{ticker}_price.png"
                    )
                    await _callback_send_png(
                        message,
                        path,
                        f"{ticker} — giá đóng cửa gần đây\n{formatters.DISCLAIMER}",
                    )
                elif action == "radar":
                    if not fund:
                        raise ChartDataError(f"Chưa có điểm fundamental cho {ticker}.")
                    path = render_fundamental_radar_chart(
                        ticker,
                        float(fund.get("growth_score")),
                        float(fund.get("quality_score")),
                        float(fund.get("safety_score")),
                        float(fund.get("valuation_score")),
                        chart_dir / f"{ticker}_fundamental.png",
                    )
                    await _callback_send_png(
                        message, path, f"{ticker} — radar 4 trụ Fundamental"
                    )
                elif action == "ta":
                    if len(closes) < 2:
                        raise ChartDataError(f"Chưa đủ giá để vẽ TA {ticker}.")
                    ta = ta_indicators_from_closes(closes)
                    path = render_ta_reference_chart(
                        ticker, list(closes), ta, chart_dir / f"{ticker}_ta.png"
                    )
                    await _callback_send_png(
                        message,
                        path,
                        f"{ticker} — TA tham khảo — không phải tín hiệu hệ thống",
                    )
                    block = formatters.format_ta_reference_block(ta)
                    if block:
                        await message.reply_text(block)
                else:
                    await message.reply_text(f"Không nhận action «{action}».")
            except (ChartDataError, TypeError, ValueError) as exc:
                await message.reply_text(f"{exc}\n\n{formatters.DISCLAIMER}")
            return

        await message.reply_text("Callback không nhận dạng.\n\n" + formatters.DISCLAIMER)

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
    app.add_handler(CallbackQueryHandler(on_callback))

    async def bare_ticker_msg(
        update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """ban_phac P2: nhập ticker thuần (vd FPT) → cùng luồng /check — không Quant on-demand."""
        text = (update.message.text or "").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", text):
            return
        context.args = [text]
        await check_cmd(update, context)

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, bare_ticker_msg)
    )

    async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Error handler nhẹ — không lộ traceback cho user."""
        log.exception("Telegram handler error: %s", context.error)
        message = getattr(update, "effective_message", None) if update else None
        if message is not None:
            try:
                await message.reply_text(
                    "Bot gặp lỗi tạm thời. Thử lại /help hoặc /check <mã>.\n\n"
                    + formatters.DISCLAIMER
                )
            except Exception:  # noqa: BLE001
                pass

    app.add_error_handler(on_error)
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
