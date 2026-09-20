-- Hợp đồng giao diện giữa Tầng 1, Tầng 2 và bot/.
-- Đổi schema ở đây PHẢI báo cho nhóm bot/ và backtest/ (xem docs/BRANCHING.md checklist).

-- Tầng 1 — cập nhật mỗi khi có BCTC mới (point-in-time: filed_at là ngày công bố thực tế,
-- KHÔNG phải ngày kết thúc kỳ báo cáo).
CREATE TABLE IF NOT EXISTS fundamental_scores (
    ticker              TEXT NOT NULL,
    filed_at            DATE NOT NULL,      -- ngày công bố BCTC + độ trễ an toàn
    period              TEXT NOT NULL,      -- vd '2026Q2'
    growth_score        REAL,
    quality_score       REAL,
    safety_score        REAL,
    valuation_score     REAL,
    fundamental_view    TEXT CHECK (fundamental_view IN ('PASS','WATCH','FAIL')),
    headline_json       TEXT,               -- xem mục 6.1: headline + supporting metrics
    PRIMARY KEY (ticker, filed_at)
);

CREATE TABLE IF NOT EXISTS watchlist (
    as_of_date          DATE NOT NULL,
    ticker              TEXT NOT NULL,
    fundamental_view    TEXT NOT NULL,
    PRIMARY KEY (as_of_date, ticker)
);

-- Tầng 2 — cập nhật mỗi phiên, sau giờ đóng cửa.
CREATE TABLE IF NOT EXISTS signals (
    date                DATE NOT NULL,
    ticker              TEXT NOT NULL,
    action              TEXT CHECK (action IN ('BUY','WATCH','SELL')),
    score               REAL,
    p_regime            REAL,               -- P(bull) từ Markov switching
    sigma_hat           REAL,               -- GARCH forecast volatility
    stop                REAL,
    size                REAL,               -- % NAV
    p_tp_before_sl      REAL,               -- Monte Carlo output
    cvar95              REAL,
    reason_json         TEXT,               -- câu chuyện headline/supporting, ghi rõ nếu thiếu dữ liệu
    PRIMARY KEY (date, ticker)
);

CREATE INDEX IF NOT EXISTS idx_signals_ticker ON signals (ticker);
CREATE INDEX IF NOT EXISTS idx_watchlist_date ON watchlist (as_of_date);

-- Theo dõi vị thế paper-trading (KHÁC với `signals`: signals là output mô hình mỗi
-- phiên, positions là trạng thái "đang thực sự giữ" — phục vụ lệnh /positions).
CREATE TABLE IF NOT EXISTS positions (
    ticker              TEXT NOT NULL,
    opened_at           DATE NOT NULL,
    entry_price         REAL NOT NULL,
    stop_price          REAL NOT NULL,
    size_pct_nav        REAL NOT NULL,
    status              TEXT CHECK (status IN ('OPEN','CLOSED')) DEFAULT 'OPEN',
    closed_at           DATE,
    close_price         REAL,
    pnl_pct             REAL,
    PRIMARY KEY (ticker, opened_at)
);

-- Người dùng Telegram đã bật thông báo tự động — phục vụ /subscribe, /unsubscribe.
CREATE TABLE IF NOT EXISTS subscribers (
    chat_id             INTEGER PRIMARY KEY,
    subscribed_at       DATETIME NOT NULL,
    is_active           INTEGER NOT NULL DEFAULT 1  -- 0 sau khi /unsubscribe, giữ lịch sử
);

-- Kết quả backtest chạy ĐỊNH KỲ (không phải theo mỗi lần người dùng gõ /backtest —
-- walk-forward trên cả rổ quá tốn để chạy real-time). pipeline/ ghi vào đây, bot/ chỉ đọc.
CREATE TABLE IF NOT EXISTS backtest_results (
    run_id              TEXT NOT NULL,      -- vd commit hash hoặc timestamp lần chạy
    run_at              DATETIME NOT NULL,
    scope               TEXT NOT NULL,      -- ticker cụ thể hoặc 'portfolio'
    baseline            TEXT CHECK (baseline IN ('framework','B0_buyhold','B1_ta','B2_canslim')),
    cagr                REAL,
    sharpe              REAL,
    max_drawdown        REAL,
    win_rate            REAL,
    n_trades            INTEGER,
    equity_curve_json   TEXT,               -- mảng [{date, equity}] để vẽ chart
    PRIMARY KEY (run_id, scope, baseline)
);

CREATE INDEX IF NOT EXISTS idx_positions_status ON positions (status);
CREATE INDEX IF NOT EXISTS idx_backtest_scope ON backtest_results (scope, run_at);
