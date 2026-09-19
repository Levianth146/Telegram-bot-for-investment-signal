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
