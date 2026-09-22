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
-- Cột CORE (P0, luôn tính) + cột ADD-ON (P0 nhưng tính sau nếu thiếu thời gian) + cột
-- ADVANCED (P1, cần logic so sánh dự báo-vs-thực-tế, không chỉ thống kê mô tả).
CREATE TABLE IF NOT EXISTS backtest_results (
    run_id              TEXT NOT NULL,      -- vd commit hash hoặc timestamp lần chạy
    run_at              DATETIME NOT NULL,
    scope               TEXT NOT NULL,      -- ticker cụ thể hoặc 'portfolio'
    baseline            TEXT CHECK (baseline IN ('framework','B0_buyhold','B1_ta','B2_canslim')),
    -- CORE
    cagr                REAL,
    sharpe              REAL,
    max_drawdown        REAL,
    win_rate            REAL,
    n_trades            INTEGER,
    equity_curve_json   TEXT,               -- mảng [{date, equity}] để vẽ chart
    -- ADD-ON (P0, tính rẻ từ dữ liệu backtest đã có, không cần logic mới)
    turnover            REAL,               -- % NAV giao dịch trung bình mỗi kỳ -> input thực cho backtest/costs.py
    sortino             REAL,               -- phạt downside risk riêng, hợp với phân phối lệch
    calmar              REAL,               -- cagr / abs(max_drawdown), dễ trình bày hơn Sharpe
    profit_factor       REAL,               -- tổng lãi / tổng lỗ (bổ trợ win_rate, tránh "thắng nhiều nhưng lỗ nặng")
    max_drawdown_days    INTEGER,           -- số phiên để phục hồi từ đáy drawdown, không chỉ độ sâu
    margin_bps          REAL,               -- lấy cảm hứng từ WQ Brain: return / turnover (đơn vị bps) —
                                             -- "chất lượng mỗi lượt giao dịch", tách biệt khỏi turnover cao/thấp
    -- ADVANCED (P1) — chứng minh giả thuyết cốt lõi của framework, không phải thống kê mô tả
    cvar95_realized     REAL,               -- CVaR thực tế đo được, đối chiếu với cvar95 dự báo trong bảng signals
    cvar95_calibration_note TEXT,           -- ghi chú định tính: dự báo có khớp thực tế không, lệch bao nhiêu
    sharpe_bull_regime  REAL,               -- Sharpe riêng trong các phiên P(bull) cao -> kiểm định giá trị của Regime layer
    sharpe_bear_regime  REAL,
    PRIMARY KEY (run_id, scope, baseline)
);

-- Phân loại market/sector/industry/subindustry — hạ tầng bắt buộc cho scoring z-score
-- "theo ngành" ở mục 10 (chưa từng có bảng riêng dù phương pháp đã giả định nó tồn tại).
-- Nguồn: field phân ngành có sẵn trong vnstock (theo chuẩn ICB của HOSE/HNX).
CREATE TABLE IF NOT EXISTS sector_mapping (
    ticker              TEXT PRIMARY KEY,
    market              TEXT NOT NULL,      -- vd 'HOSE', 'HNX', 'UPCOM'
    sector              TEXT NOT NULL,      -- ICB cấp 1, vd 'Tài chính'
    industry            TEXT NOT NULL,      -- ICB cấp 2/3, vd 'Ngân hàng'
    subindustry         TEXT,               -- ICB cấp 4, có thể NULL nếu nguồn không chi tiết tới mức này
    updated_at          DATE NOT NULL
);

-- Breakdown theo năm — lấy cảm hứng từ bảng "yearly stats" của WQ Brain: cho thấy
-- chiến lược có ổn định qua từng năm hay chỉ tốt nhờ 1-2 năm may mắn (đặc biệt quan
-- trọng khi n_trades tổng còn thấp — xem docs/DECISIONS.md).
CREATE TABLE IF NOT EXISTS backtest_yearly_breakdown (
    run_id              TEXT NOT NULL,
    scope               TEXT NOT NULL,
    baseline            TEXT NOT NULL,
    year                INTEGER NOT NULL,
    cagr                REAL,
    sharpe              REAL,
    max_drawdown        REAL,
    turnover            REAL,
    margin_bps          REAL,
    n_trades            INTEGER,
    PRIMARY KEY (run_id, scope, baseline, year)
);

-- Bảng "Checks" PASS/FAIL — lấy cảm hứng từ WQ Brain (LOW_SHARPE, HIGH_TURNOVER...):
-- đối chiếu từng metric với ngưỡng đã ĐĂNG KÝ TRƯỚC trong docs/DECISIONS.md, để
-- kết quả không bị diễn giải tuỳ tiện sau khi đã thấy số (tránh p-hacking ngầm).
CREATE TABLE IF NOT EXISTS backtest_checks (
    run_id              TEXT NOT NULL,
    scope               TEXT NOT NULL,
    baseline            TEXT NOT NULL,
    check_name          TEXT NOT NULL,      -- vd 'MIN_SHARPE_IMPROVEMENT', 'MIN_TRADES_FOR_SIGNIFICANCE', 'MAX_TURNOVER'
    threshold           REAL,
    actual_value        REAL,
    passed              INTEGER NOT NULL CHECK (passed IN (0, 1)),
    note                TEXT,               -- vd 'n_trades=3, dưới ngưỡng tối thiểu để kết luận có ý nghĩa'
    PRIMARY KEY (run_id, scope, baseline, check_name)
);

CREATE INDEX IF NOT EXISTS idx_positions_status ON positions (status);
CREATE INDEX IF NOT EXISTS idx_backtest_scope ON backtest_results (scope, run_at);
CREATE INDEX IF NOT EXISTS idx_sector_industry ON sector_mapping (sector, industry);
CREATE INDEX IF NOT EXISTS idx_yearly_breakdown ON backtest_yearly_breakdown (scope, baseline, year);
CREATE INDEX IF NOT EXISTS idx_backtest_checks ON backtest_checks (scope, baseline, passed);

-- Giá đóng cửa (và OHLCV nếu có) do pipeline/daily_job ghi — bot /chart price chỉ ĐỌC.
CREATE TABLE IF NOT EXISTS price_bars (
    ticker              TEXT NOT NULL,
    date                DATE NOT NULL,
    open                REAL,
    high                REAL,
    low                 REAL,
    close               REAL NOT NULL,
    volume              REAL,
    PRIMARY KEY (ticker, date)
);

CREATE INDEX IF NOT EXISTS idx_price_bars_ticker_date ON price_bars (ticker, date DESC);
