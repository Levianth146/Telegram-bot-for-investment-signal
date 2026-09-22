# Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư

Tài liệu này tóm tắt kiến trúc kỹ thuật ứng với "Khung chiến lược tích hợp: Fundamental
Filter + Quant Regime Engine" mà nhóm đã thống nhất. Đọc file `.docx` đầy đủ (lưu tại
repo root: `Khung_chien_luoc_tich_hop-Fundamental_Filter-Quant_Regime_Engine.docx`) để
hiểu lý thuyết/công thức chi tiết; file này chỉ ánh xạ lý thuyết đó sang code.

## Sơ đồ luồng dữ liệu

```
                    ┌─────────────────────────────┐
                    │   TẦNG 1 — FUNDAMENTAL      │   chạy lại mỗi khi có BCTC mới
                    │   fundamental_filter/        │   (theo quý, event-driven)
                    │   Growth → Quality → Safety  │
                    │   → Valuation → Score        │
                    └──────────────┬───────────────┘
                                   │  watchlist (PASS/WATCH)
                                   ▼
                    ┌─────────────────────────────┐
                    │   TẦNG 2 — QUANT ENGINE      │   chạy lại mỗi phiên (sau 15:00)
                    │   quant_engine/               │
                    │   Regime → Alpha → Risk       │
                    │   → Portfolio → Probabilistic │
                    └──────────────┬───────────────┘
                                   │  ghi vào bảng `signals`
                                   ▼
                    ┌─────────────────────────────┐
                    │   store/  (SQLite/Parquet)    │
                    └──────────────┬───────────────┘
                                   │  đọc, KHÔNG fit lại mô hình
                                   ▼
                    ┌─────────────────────────────┐
                    │   bot/  (Telegram, chỉ đọc)   │
                    └───────────────────────────────┘

              backtest/  dùng CHUNG code trong fundamental_filter/ và quant_engine/
              để backtest phản ánh đúng logic live, không phải bản sao riêng.
```

## Nguyên tắc bất biến (không được vi phạm khi code)

1. **Bot không bao giờ fit lại mô hình khi người dùng gõ lệnh.** Mọi tính toán nằm trong
   `pipeline/`, chạy offline, kết quả ghi vào `store/`. `bot/` chỉ có quyền `SELECT`.
2. **`backtest/` và pipeline live dùng chung hàm** trong `fundamental_filter/` và
   `quant_engine/`. Không viết logic tính điểm/tín hiệu riêng cho backtest.
3. **Point-in-time bắt buộc**: mọi truy vấn BCTC phải lọc theo ngày công bố + độ trễ, không
   dùng ngày kết thúc kỳ báo cáo (xem `data/schemas/`).
4. **Mỗi tầng P1/P2 có cờ bật/tắt** trong `pipeline/config.yaml`. Tắt một tầng không được
   làm crash pipeline — luôn có giá trị fallback (xem `docs/DECISIONS.md`).
5. **Một chỉ số chỉ có một "nhà chính"** — không chấm điểm lại cùng một tín hiệu ở hai module
   khác nhau (quy tắc chống double-count).

## Phân tầng ưu tiên P0 / P1 / P2

| Mức | Thành phần | Thư mục |
|---|---|---|
| P0 | Growth/Quality/Safety/Valuation | `fundamental_filter/` |
| P0 | Regime, Alpha (Kalman/OU), Risk (GARCH) | `quant_engine/regime.py`, `quant_engine/alpha/`, `quant_engine/risk/` |
| P0 | Backtest + ablation cơ bản (CAGR/Sharpe/MaxDD/Win rate + turnover/Sortino/Calmar/profit factor) | `backtest/` |
| P0 | Phân loại market/sector/industry/subindustry (hạ tầng cho z-score theo ngành, mục 10) | `store/schema.sql:sector_mapping` |
| P1 | Black-Litterman, Monte Carlo | `quant_engine/portfolio/`, `quant_engine/probabilistic/monte_carlo.py` |
| P1 | CVaR calibration (dự báo vs thực tế), Sharpe theo regime, lệnh `/sector` | `backtest/ablation.py`, `bot/charts.py` |
| P2 | Merton DD, Hawkes, Institutional Flow | `fundamental_filter/safety.py` (DD), `quant_engine/probabilistic/hawkes.py` |

Cắt một tầng P1/P2 = set `enabled: false` trong `pipeline/config.yaml`, không phải xóa code.

## Module ↔ người phụ trách (theo phân công đã thống nhất)

| Người | Thư mục chính |
|---|---|
| P1 | `data/`, `store/` |
| P2 | `quant_engine/regime.py`, `quant_engine/alpha/` |
| P3 | `quant_engine/risk/`, `quant_engine/probabilistic/monte_carlo.py` |
| P4 | `backtest/`, `quant_engine/portfolio/` |
| P5 | `bot/`, CI/CD, `pipeline/` |
| P6 | `fundamental_filter/` (Quality/Safety/Merton DD), `quant_engine/probabilistic/hawkes.py`, `docs/` |

## Point-in-time & BCTC V1

- **Annual BCTC** (không phải quý) qua `data.providers` backtest chain; `filed_at` giả định =
  period-end 31/12 + `assumed_publication_lag_days` (mặc định **90**) — xem `data/ingest/pit.py`
  và `docs/DATA_AUDIT.md` §4b.
- **Historical valuation**: year-end closes + cùng lag → PIT observations cho
  `calculate_historical_valuation_score`. Thiếu ≥4 obs an toàn → không PASS (WATCH).
- **Peers**: `store.sector_mapping.industry` (job tháng) ưu tiên; live KBS bổ sung khi thiếu.

## daily_job → subscribers

Sau khi ghi `signals`, `pipeline/daily_job.py` đọc `subscribers` và (nếu `BOT_TOKEN` hợp lệ)
gửi push. Benchmark (`quant_engine.benchmark`, thường VNINDEX) chỉ dùng cho regime — không
sinh hàng `signals`.

### Universe V1 (đồng bộ `pipeline/config.yaml`)

- **Tier 1 Fundamental:** `data/universe/vn100.csv` (`universe.fundamental_file`).
- **Tier 2 Quant (daily):** chỉ mã PASS/WATCH trên watchlist (`quant_from_watchlist: true`)
  + benchmark `VNINDEX` cho regime (không ghi hàng `signals` cho benchmark).
- **Smoke / ablation nhanh:** `data/universe/hose_liquid_35.csv` (`universe.smoke_file`) —
  không phải universe live chính.
- **Sàn:** HOSE + HNX (`allowed_exchanges`); loại tài chính khi `exclude_financials: true`.

### Ops live (một máy)

1. `.env`: `BOT_TOKEN`, `DATABASE_PATH=store/bot.db` (xem `.env.example`).
2. `python -m pipeline.quarterly_job` — Tier 1 trên VN100 (BCTC / event).
3. `python scripts/run_daily_pipeline.py` — optional `--with-sector`; persist + push.
4. `python -m bot.main` — polling; user `/subscribe` trước khi kỳ vọng push > 0.
5. Bot chỉ đọc `store/`; không crawl vendor trong handlers. Chi tiết lệnh: `README.md`.

### Lịch daily (Windows)

- Script: `scripts/run_daily_pipeline.ps1` → gọi `scripts/run_daily_pipeline.py`.
- Đăng ký Task Scheduler mẫu (T2–T6 15:15): xem README mục “Lịch Windows”.
- Không thay thế bot polling; push chỉ gửi khi có subscriber + `BOT_TOKEN`.

## Bảng `signals` (hợp đồng giao diện giữa Tầng 2 và bot)

Xem `store/schema.sql`. Cột bắt buộc: `date, ticker, action, score, p_regime, sigma_hat,
stop, size, p_tp_before_sl, cvar95, reason_json`. Đây là "API nội bộ" — mọi thay đổi schema
này phải thông báo cho cả nhóm `bot/` lẫn `backtest/`.

## Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`)

3 bảng này phục vụ lệnh bot ngoài `/check` và `/signals`, cũng chỉ được `bot/` ĐỌC, không
bao giờ tự tính toán:

- **`positions`** — trạng thái paper-trading đang giữ, KHÁC với `signals` (vốn là output mô
  hình mỗi phiên, không phải "đang giữ hay không"). Do `pipeline/` hoặc 1 job paper-trading
  riêng ghi vào; `bot/` chỉ đọc qua `get_open_positions()` cho lệnh `/positions`.
- **`subscribers`** — ai đã bật `/subscribe` để nhận push tự động; `pipeline/daily_job.py`
  đọc bảng này sau khi ghi `signals` xong để biết gửi cho `chat_id` nào.
- **`backtest_results`** — kết quả backtest chạy ĐỊNH KỲ (không phải mỗi lần người dùng gõ
  `/backtest`, vì walk-forward trên cả rổ quá tốn để chạy real-time). `backtest/` ghi vào
  đây sau mỗi lần chạy theo lịch (hoặc sau khi merge thay đổi model vào `main`, gắn vào CI);
  `bot/` chỉ đọc để trả lời `/backtest`.

## Bảng lệnh bot dự kiến

| Lệnh | Đọc từ bảng | Có phân tầng hiển thị 4 khối như `/check` không |
|---|---|---|
| `/start` | — | Không — text tĩnh |
| `/signals` | `signals` (hôm nay) | Không — 1 dòng/mã, gợi ý `/check <mã>` để xem chi tiết |
| `/check <mã>` | `fundamental_scores`, `signals` | **Có** — 4 khối: Bộ lọc cơ bản (Tầng 1) → Trạng thái thị trường (Regime) → Tín hiệu vào lệnh (Alpha) → Rủi ro & khối lượng (Risk/Probabilistic) |
| `/watchlist` | `watchlist` | Không |
| `/regime` | `signals` (cột `p_regime`, lấy theo thị trường chung) | Không — 1 khối |
| `/chart <mã> [loại]` | `bot/charts.py` đọc từ `signals`/`fundamental_scores` | Không áp dụng — là ảnh, không phải text phân tầng |
| `/backtest <mã\|portfolio>` | `backtest_results` (đã tính sẵn, gồm cả turnover/Sortino/Calmar/profit factor) | Không |
| `/positions` | `positions` | Không — dạng bảng |
| `/subscribe`, `/unsubscribe` | `subscribers` | Không |
| `/status` | đọc `pipeline/config.yaml` + timestamp lần chạy job gần nhất | Không |
| `/sector <ngành>` (P1) | `sector_mapping` JOIN `watchlist` | Không — tổng quan top-down, khác vai trò với `/check` (bottom-up 1 mã) |
| `/about` | — | Không — text tĩnh + disclaimer bắt buộc |

## Chart backtest bổ sung (`bot/charts.py`)

Ngoài 5 chart theo mã đã có (price/risk/prob/fundamental/ta), phần backtest có thêm:
equity curve so baseline, drawdown (underwater) chart, rolling Sharpe, histogram PnL
từng lệnh đã đóng (đối chiếu với chart Monte Carlo — 1 cái là dự báo trước khi vào lệnh,
1 cái là kết quả thực sau khi đóng lệnh), và equity curve tách theo regime (P1, kiểm định
trực tiếp giá trị của lớp Regime).

### Phong cách WQ Brain cho `/backtest` (mới)

Lấy cảm hứng từ cách trình bày kết quả simulation của nền tảng WQ Brain — không chỉ
đưa 1 con số cho cả giai đoạn, mà tách theo năm và đối chiếu ngưỡng đã đăng ký trước:

- **`margin_bps`** (mới trong `backtest_results`): return / turnover, đo "chất lượng
  mỗi lượt giao dịch" tách biệt khỏi mức turnover cao/thấp.
- **`backtest_yearly_breakdown`**: Sharpe/CAGR/MaxDD/Turnover/Margin/số lệnh theo
  từng năm — trực quan hoá qua `render_yearly_stats_chart`, giúp thấy chiến lược ổn
  định qua thời gian hay chỉ tốt nhờ 1-2 năm.
- **`backtest_checks`**: bảng PASS/FAIL đối chiếu với ngưỡng đăng ký trước trong
  `docs/DECISIONS.md` (`pipeline/config.yaml: backtest.checks`) — vd
  `MIN_TRADES_FOR_SIGNIFICANCE`, `MIN_SHARPE_IMPROVEMENT_OOS`, `MAX_TURNOVER_PCT`.
  Bot hiện bảng này dưới dạng ✅/❌ trong `/backtest`, để không ai (kể cả chính nhóm)
  diễn giải số liệu theo hướng có lợi sau khi đã thấy kết quả.
- **`render_pnl_is_os_chart`**: equity curve tô 2 màu in-sample/out-of-sample theo
  đúng ranh giới `backtest.walk_forward` đã cấu hình.
- **`render_turnover_chart`**: turnover trượt theo thời gian, không gộp thành 1 số
  trung bình duy nhất.

Không mang theo phần "correlation với alpha khác" của WQ Brain (không áp dụng — chỉ
có 1 framework để so, không phải hàng nghìn alpha), và không dùng "Long/Short Count"
theo nghĩa short-selling (thị trường VN retail không short được) — giữ nguyên khái
niệm "số mã BUY/WATCH/SELL mỗi phiên" đã có ở `/signals`.
