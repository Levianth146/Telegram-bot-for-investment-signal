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
    sql = """
        INSERT INTO signals (
            date, ticker, action, score, p_regime, sigma_hat,
            stop, size, p_tp_before_sl, cvar95, reason_json
        ) VALUES (
            :date, :ticker, :action, :score, :p_regime, :sigma_hat,
            :stop, :size, :p_tp_before_sl, :cvar95, :reason_json
        )
        ON CONFLICT(date, ticker) DO UPDATE SET
            action=excluded.action,
            score=excluded.score,
            p_regime=excluded.p_regime,
            sigma_hat=excluded.sigma_hat,
            stop=excluded.stop,
            size=excluded.size,
            p_tp_before_sl=excluded.p_tp_before_sl,
            cvar95=excluded.cvar95,
            reason_json=excluded.reason_json
    """
    conn.execute(sql, signal)
    conn.commit()


def upsert_signals(conn: sqlite3.Connection, signals: list[dict]) -> None:
    """Batch upsert for daily_job."""
    for signal in signals:
        upsert_signal(conn, signal)


def get_latest_signals(conn: sqlite3.Connection, as_of_date: str | None = None) -> list[dict]:
    """Bot dùng hàm này để trả lời /signals — CHỈ ĐỌC, không tính toán gì thêm."""
    if as_of_date is None:
        row = conn.execute("SELECT MAX(date) AS d FROM signals").fetchone()
        if row is None or row["d"] is None:
            return []
        as_of_date = row["d"]
    cur = conn.execute(
        """
        SELECT date, ticker, action, score, p_regime, sigma_hat,
               stop, size, p_tp_before_sl, cvar95, reason_json
        FROM signals
        WHERE date = ?
        ORDER BY ticker
        """,
        (as_of_date,),
    )
    return [dict(r) for r in cur.fetchall()]


def get_latest_fundamental_scores(
    conn: sqlite3.Connection, tickers: list[str] | None = None
) -> dict[str, dict]:
    """Latest fundamental_scores row per ticker (by filed_at) for Alpha_effective."""
    if tickers:
        placeholders = ",".join("?" for _ in tickers)
        params: list = [t.strip().upper() for t in tickers]
        sql = f"""
            SELECT f.*
            FROM fundamental_scores f
            INNER JOIN (
                SELECT ticker, MAX(filed_at) AS max_filed
                FROM fundamental_scores
                WHERE ticker IN ({placeholders})
                GROUP BY ticker
            ) latest
              ON f.ticker = latest.ticker AND f.filed_at = latest.max_filed
        """
        cur = conn.execute(sql, params)
    else:
        cur = conn.execute(
            """
            SELECT f.*
            FROM fundamental_scores f
            INNER JOIN (
                SELECT ticker, MAX(filed_at) AS max_filed
                FROM fundamental_scores
                GROUP BY ticker
            ) latest
              ON f.ticker = latest.ticker AND f.filed_at = latest.max_filed
            """
        )
    return {str(row["ticker"]).upper(): dict(row) for row in cur.fetchall()}


def upsert_fundamental_scores(conn: sqlite3.Connection, rows: list[dict]) -> None:
    """Ghi/cập nhật bảng fundamental_scores (Tầng 1 output)."""
    sql = """
        INSERT INTO fundamental_scores (
            ticker, filed_at, period,
            growth_score, quality_score, safety_score, valuation_score,
            fundamental_view, headline_json
        ) VALUES (
            :ticker, :filed_at, :period,
            :growth_score, :quality_score, :safety_score, :valuation_score,
            :fundamental_view, :headline_json
        )
        ON CONFLICT(ticker, filed_at) DO UPDATE SET
            period=excluded.period,
            growth_score=excluded.growth_score,
            quality_score=excluded.quality_score,
            safety_score=excluded.safety_score,
            valuation_score=excluded.valuation_score,
            fundamental_view=excluded.fundamental_view,
            headline_json=excluded.headline_json
    """
    conn.executemany(sql, rows)
    conn.commit()


def upsert_watchlist(conn: sqlite3.Connection, rows: list[dict]) -> None:
    """Ghi/cập nhật bảng watchlist (PASS/WATCH only)."""
    sql = """
        INSERT INTO watchlist (as_of_date, ticker, fundamental_view)
        VALUES (:as_of_date, :ticker, :fundamental_view)
        ON CONFLICT(as_of_date, ticker) DO UPDATE SET
            fundamental_view=excluded.fundamental_view
    """
    conn.executemany(sql, rows)
    conn.commit()


def get_watchlist(conn: sqlite3.Connection, as_of_date: str | None = None) -> list[str]:
    if as_of_date is None:
        row = conn.execute(
            "SELECT MAX(as_of_date) AS d FROM watchlist"
        ).fetchone()
        if row is None or row["d"] is None:
            return []
        as_of_date = row["d"]
    cur = conn.execute(
        "SELECT ticker FROM watchlist WHERE as_of_date = ? ORDER BY ticker",
        (as_of_date,),
    )
    return [r["ticker"] for r in cur.fetchall()]


def open_position(conn: sqlite3.Connection, position: dict) -> None:
    """Ghi 1 vị thế mới (status='OPEN') — paper-trading theo tín hiệu BUY.

    Bot chỉ ĐỌC bảng này qua get_open_positions, không tự mở lệnh.
    """
    row = {
        "ticker": str(position["ticker"]).strip().upper(),
        "opened_at": position["opened_at"],
        "entry_price": float(position["entry_price"]),
        "stop_price": float(position["stop_price"]),
        "size_pct_nav": float(position["size_pct_nav"]),
        "status": "OPEN",
        "closed_at": None,
        "close_price": None,
        "pnl_pct": None,
    }
    conn.execute(
        """
        INSERT INTO positions (
            ticker, opened_at, entry_price, stop_price, size_pct_nav,
            status, closed_at, close_price, pnl_pct
        ) VALUES (
            :ticker, :opened_at, :entry_price, :stop_price, :size_pct_nav,
            :status, :closed_at, :close_price, :pnl_pct
        )
        ON CONFLICT(ticker, opened_at) DO UPDATE SET
            entry_price=excluded.entry_price,
            stop_price=excluded.stop_price,
            size_pct_nav=excluded.size_pct_nav,
            status='OPEN',
            closed_at=NULL,
            close_price=NULL,
            pnl_pct=NULL
        """,
        row,
    )
    conn.commit()


def close_position(
    conn: sqlite3.Connection,
    ticker: str,
    opened_at: str,
    close_price: float,
    closed_at: str,
) -> None:
    """Đóng vị thế OPEN → CLOSED và ghi pnl_pct."""
    target = str(ticker).strip().upper()
    cur = conn.execute(
        """
        SELECT entry_price FROM positions
        WHERE ticker = ? AND opened_at = ? AND status = 'OPEN'
        """,
        (target, opened_at),
    )
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"No OPEN position for {target} opened_at={opened_at}")
    entry = float(row["entry_price"])
    pnl = (float(close_price) / entry - 1.0) if entry else None
    conn.execute(
        """
        UPDATE positions
        SET status = 'CLOSED',
            closed_at = ?,
            close_price = ?,
            pnl_pct = ?
        WHERE ticker = ? AND opened_at = ? AND status = 'OPEN'
        """,
        (closed_at, float(close_price), pnl, target, opened_at),
    )
    conn.commit()


def get_backtest_results(conn: sqlite3.Connection, scope: str, run_id: str | None = None) -> list[dict]:
    """Bot dùng hàm này để trả lời /backtest — CHỈ ĐỌC kết quả đã tính sẵn theo lịch
    định kỳ trong backtest_results. `run_id=None` -> lấy lần chạy mới nhất."""
    if run_id is None:
        row = conn.execute(
            """
            SELECT run_id FROM backtest_results
            WHERE scope = ?
            ORDER BY run_at DESC
            LIMIT 1
            """,
            (scope,),
        ).fetchone()
        if row is None:
            return []
        run_id = row["run_id"]
    cur = conn.execute(
        """
        SELECT * FROM backtest_results
        WHERE scope = ? AND run_id = ?
        """,
        (scope, run_id),
    )
    return [dict(r) for r in cur.fetchall()]


def upsert_backtest_results(conn: sqlite3.Connection, rows: list[dict]) -> None:
    """Persist metrics from ``backtest.engine`` / walk-forward / ablation."""
    sql = """
        INSERT INTO backtest_results (
            run_id, run_at, scope, baseline,
            cagr, sharpe, max_drawdown, win_rate, n_trades, equity_curve_json,
            turnover, sortino, calmar, profit_factor, max_drawdown_days,
            cvar95_realized, cvar95_calibration_note,
            sharpe_bull_regime, sharpe_bear_regime
        ) VALUES (
            :run_id, :run_at, :scope, :baseline,
            :cagr, :sharpe, :max_drawdown, :win_rate, :n_trades, :equity_curve_json,
            :turnover, :sortino, :calmar, :profit_factor, :max_drawdown_days,
            :cvar95_realized, :cvar95_calibration_note,
            :sharpe_bull_regime, :sharpe_bear_regime
        )
        ON CONFLICT(run_id, scope, baseline) DO UPDATE SET
            run_at=excluded.run_at,
            cagr=excluded.cagr,
            sharpe=excluded.sharpe,
            max_drawdown=excluded.max_drawdown,
            win_rate=excluded.win_rate,
            n_trades=excluded.n_trades,
            equity_curve_json=excluded.equity_curve_json,
            turnover=excluded.turnover,
            sortino=excluded.sortino,
            calmar=excluded.calmar,
            profit_factor=excluded.profit_factor,
            max_drawdown_days=excluded.max_drawdown_days,
            cvar95_realized=excluded.cvar95_realized,
            cvar95_calibration_note=excluded.cvar95_calibration_note,
            sharpe_bull_regime=excluded.sharpe_bull_regime,
            sharpe_bear_regime=excluded.sharpe_bear_regime
    """
    defaults = {
        "turnover": None,
        "sortino": None,
        "calmar": None,
        "profit_factor": None,
        "max_drawdown_days": None,
        "cvar95_realized": None,
        "cvar95_calibration_note": None,
        "sharpe_bull_regime": None,
        "sharpe_bear_regime": None,
        "equity_curve_json": None,
        "baseline": "framework",
    }
    payload = []
    for row in rows:
        item = {**defaults, **row}
        payload.append(item)
    conn.executemany(sql, payload)
    conn.commit()


def upsert_sector_mapping(conn: sqlite3.Connection, mapping_rows: list[dict]) -> None:
    """Ghi/cập nhật bảng sector_mapping (ticker -> market/sector/industry/subindustry).
    Chạy định kỳ (vd hàng tháng) từ pipeline/, không phải mỗi lần tính signal — phân
    ngành không đổi thường xuyên."""
    sql = """
        INSERT INTO sector_mapping (
            ticker, market, sector, industry, subindustry, updated_at
        ) VALUES (
            :ticker, :market, :sector, :industry, :subindustry, :updated_at
        )
        ON CONFLICT(ticker) DO UPDATE SET
            market=excluded.market,
            sector=excluded.sector,
            industry=excluded.industry,
            subindustry=excluded.subindustry,
            updated_at=excluded.updated_at
    """
    rows = []
    for row in mapping_rows:
        rows.append(
            {
                "ticker": str(row["ticker"]).strip().upper(),
                "market": row.get("market") or None,
                "sector": row.get("sector") or row.get("industry") or "UNKNOWN",
                "industry": row.get("industry") or "UNKNOWN",
                "subindustry": row.get("subindustry"),
                "updated_at": row["updated_at"],
            }
        )
    if rows:
        conn.executemany(sql, rows)
        conn.commit()


def get_sector_for_ticker(conn: sqlite3.Connection, ticker: str) -> dict | None:
    """fundamental_filter/scoring.py dùng hàm này để biết nhóm peer nào khi tính
    z-score theo ngành (mục 10) — KHÔNG hardcode danh sách ngành ở nơi khác."""
    cur = conn.execute(
        """
        SELECT ticker, market, sector, industry, subindustry, updated_at
        FROM sector_mapping
        WHERE ticker = ?
        """,
        (str(ticker).strip().upper(),),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def get_markets_for_tickers(
    conn: sqlite3.Connection, tickers: list[str]
) -> dict[str, str | None]:
    """Map ticker → sector_mapping.market (thiếu mapping → None). Dùng lọc sàn universe."""
    cleaned = [str(t).strip().upper() for t in tickers if str(t).strip()]
    result: dict[str, str | None] = {t: None for t in cleaned}
    if not cleaned:
        return result
    placeholders = ",".join("?" * len(cleaned))
    cur = conn.execute(
        f"""
        SELECT ticker, market
        FROM sector_mapping
        WHERE ticker IN ({placeholders})
        """,
        cleaned,
    )
    for row in cur.fetchall():
        result[str(row["ticker"]).upper()] = row["market"]
    return result


def get_sector_overview(conn: sqlite3.Connection, as_of_date: str) -> list[dict]:
    """Bot dùng hàm này để trả lời /sector — join sector_mapping với watchlist, trả
    về số mã PASS/WATCH/FAIL theo từng ngành tại as_of_date. CHỈ ĐỌC."""
    cur = conn.execute(
        """
        SELECT
            COALESCE(s.industry, 'UNKNOWN') AS industry,
            SUM(CASE WHEN w.fundamental_view = 'PASS' THEN 1 ELSE 0 END) AS n_pass,
            SUM(CASE WHEN w.fundamental_view = 'WATCH' THEN 1 ELSE 0 END) AS n_watch,
            SUM(CASE WHEN w.fundamental_view = 'FAIL' THEN 1 ELSE 0 END) AS n_fail,
            COUNT(*) AS n_total
        FROM watchlist w
        LEFT JOIN sector_mapping s ON s.ticker = w.ticker
        WHERE w.as_of_date = ?
        GROUP BY COALESCE(s.industry, 'UNKNOWN')
        ORDER BY n_total DESC, industry
        """,
        (as_of_date,),
    )
    return [dict(r) for r in cur.fetchall()]


def get_watchlist_rows(
    conn: sqlite3.Connection, as_of_date: str | None = None
) -> list[dict]:
    """Full watchlist rows (ticker + view) for bot /watchlist."""
    if as_of_date is None:
        row = conn.execute(
            "SELECT MAX(as_of_date) AS d FROM watchlist"
        ).fetchone()
        if row is None or row["d"] is None:
            return []
        as_of_date = row["d"]
    cur = conn.execute(
        """
        SELECT as_of_date, ticker, fundamental_view
        FROM watchlist
        WHERE as_of_date = ?
        ORDER BY ticker
        """,
        (as_of_date,),
    )
    return [dict(r) for r in cur.fetchall()]


def get_open_positions(conn: sqlite3.Connection) -> list[dict]:
    """Bot dùng hàm này để trả lời /positions — CHỈ ĐỌC."""
    cur = conn.execute(
        """
        SELECT ticker, opened_at, entry_price, stop_price, size_pct_nav,
               status, closed_at, close_price, pnl_pct
        FROM positions
        WHERE status = 'OPEN'
        ORDER BY ticker, opened_at
        """
    )
    return [dict(r) for r in cur.fetchall()]


def set_subscription(conn: sqlite3.Connection, chat_id: int, is_active: bool) -> None:
    """Dùng cho /subscribe và /unsubscribe. is_active=False vẫn giữ lại dòng (lịch sử),
    không xóa — để biết ai đã từng đăng ký."""
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO subscribers (chat_id, subscribed_at, is_active)
        VALUES (?, ?, ?)
        ON CONFLICT(chat_id) DO UPDATE SET
            is_active=excluded.is_active,
            subscribed_at=CASE
                WHEN excluded.is_active = 1 THEN excluded.subscribed_at
                ELSE subscribers.subscribed_at
            END
        """,
        (int(chat_id), now, 1 if is_active else 0),
    )
    conn.commit()


def get_active_subscribers(conn: sqlite3.Connection) -> list[int]:
    """pipeline/daily_job.py dùng hàm này để biết push tín hiệu cho chat_id nào."""
    cur = conn.execute(
        "SELECT chat_id FROM subscribers WHERE is_active = 1 ORDER BY chat_id"
    )
    return [int(r["chat_id"]) for r in cur.fetchall()]


def upsert_price_bars(conn: sqlite3.Connection, bars: list[dict]) -> int:
    """Batch upsert OHLCV/close cho /chart price (pipeline ghi, bot đọc)."""
    if not bars:
        return 0
    sql = """
        INSERT INTO price_bars (ticker, date, open, high, low, close, volume)
        VALUES (:ticker, :date, :open, :high, :low, :close, :volume)
        ON CONFLICT(ticker, date) DO UPDATE SET
            open=excluded.open,
            high=excluded.high,
            low=excluded.low,
            close=excluded.close,
            volume=excluded.volume
    """
    rows: list[dict] = []
    for bar in bars:
        ticker = str(bar.get("ticker") or "").strip().upper()
        day = str(bar.get("date") or "")[:10]
        close = bar.get("close")
        if not ticker or not day or close is None:
            continue
        try:
            close_f = float(close)
        except (TypeError, ValueError):
            continue
        rows.append(
            {
                "ticker": ticker,
                "date": day,
                "open": bar.get("open"),
                "high": bar.get("high"),
                "low": bar.get("low"),
                "close": close_f,
                "volume": bar.get("volume"),
            }
        )
    if not rows:
        return 0
    conn.executemany(sql, rows)
    conn.commit()
    return len(rows)


def get_price_closes(
    conn: sqlite3.Connection,
    ticker: str,
    *,
    limit_days: int | None = 500,
) -> list[dict]:
    """Chuỗi close ascending theo date — input ``render_price_chart`` / regime chart."""
    ticker_u = str(ticker).strip().upper()
    if limit_days is None or limit_days <= 0:
        cur = conn.execute(
            """
            SELECT date, close, open, high, low, volume
            FROM price_bars
            WHERE ticker = ?
            ORDER BY date ASC
            """,
            (ticker_u,),
        )
    else:
        cur = conn.execute(
            """
            SELECT date, close, open, high, low, volume
            FROM (
                SELECT date, close, open, high, low, volume
                FROM price_bars
                WHERE ticker = ?
                ORDER BY date DESC
                LIMIT ?
            )
            ORDER BY date ASC
            """,
            (ticker_u, int(limit_days)),
        )
    return [dict(r) for r in cur.fetchall()]
