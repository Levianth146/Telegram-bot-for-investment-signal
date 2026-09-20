# Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư

Tài liệu này tóm tắt kiến trúc kỹ thuật ứng với "Khung chiến lược tích hợp: Fundamental
Filter + Quant Regime Engine" mà nhóm đã thống nhất. Đọc file `.docx` đầy đủ (lưu trong
`docs/khung_chien_luoc_tich_hop.docx`) để hiểu lý thuyết/công thức chi tiết; file này chỉ
ánh xạ lý thuyết đó sang code.

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
