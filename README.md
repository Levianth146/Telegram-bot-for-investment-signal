# Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam

Telegram bot — kết hợp **Fundamental Filter** (Growth / Quality / Safety / Valuation) với
**Quant Regime Engine** (Markov regime, Kalman / OU, GARCH) để phát tín hiệu Mua / Bán /
Theo dõi trên thị trường Việt Nam.

> Sản phẩm học thuật — **không** phải khuyến nghị đầu tư. Xem ghi chú
> pháp lý trong [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Scope hiện tại (V1)

| Thành phần | Trạng thái |
|---|---|
| Universe Tier 1 | [`data/universe/vn100.csv`](data/universe/vn100.csv) (loại tài chính theo framework) |
| Smoke / ablation nhanh | [`data/universe/hose_liquid_35.csv`](data/universe/hose_liquid_35.csv) |
| Quant daily | Chỉ mã **PASS / WATCH** trên watchlist (`quant_from_watchlist: true`) |
| P0 bật | FF + Regime + Alpha + GARCH + backtest/ablation |
| P1 tắt mặc định | Black-Litterman, Monte Carlo (chỉ bật khi OOS đạt gate trong `docs/DECISIONS.md`) |
| Bot | Chỉ **đọc** `store/` — không crawl / không fit lại mô hình khi user gõ lệnh |
| Execution backtest | Close **T+1**, phí/thuế, T+2, biên độ giá |

Cờ tầng P0/P1/P2: [`pipeline/config.yaml`](pipeline/config.yaml). Nhật ký giữ/cắt tầng:
[`docs/DECISIONS.md`](docs/DECISIONS.md).

## Bắt đầu từ đâu

1. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — sơ đồ luồng + nguyên tắc bất biến.
2. [`docs/BRANCHING.md`](docs/BRANCHING.md) — branch / PR.
3. [`pipeline/config.yaml`](pipeline/config.yaml) — tầng đang bật.
4. Framework lý thuyết: `Khung_chien_luoc_tich_hop-Fundamental_Filter-Quant_Regime_Engine.docx`
   (repo root — **không** commit nếu nhóm quy ước giữ ngoài git; path đúng là root, không
   phải `docs/khung_…`).
5. Ops chi tiết: [`docs/HUONG_DAN_SU_DUNG_REPO.md`](docs/HUONG_DAN_SU_DUNG_REPO.md).

## Cấu trúc thư mục

```
fundamental_filter/   Tầng 1 — Growth, Quality, Safety, Valuation, scoring
quant_engine/         Tầng 2 — Regime, Alpha, Risk, Portfolio, Probabilistic
pipeline/             quarterly / daily / sector jobs + config.yaml
data/                 providers, ingest, cache OHLCV + scoring_schedule, universe CSV
store/                SQLite (bot.db), schema.sql — signals, watchlist, backtest_results
backtest/             engine (T+1), costs, walk-forward, ablation, metrics, data_bundle
bot/                  Telegram — CHỈ ĐỌC store/
scripts/              run_daily_pipeline, run_backtest_report, ablation quiet, profile
notebooks/            nghiên cứu — không phải production
docs/                 ARCHITECTURE, DECISIONS, DATA_AUDIT, BACKTEST_FINAL_REPORT, …
outputs/              profile / artifacts chạy local (thường không commit số lớn)
tests/                integration xuyên module
```

## Cài đặt nhanh

```bash
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# Linux/macOS:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env   # Windows; hoặc: cp .env.example .env
# Điền BOT_TOKEN, DATABASE_PATH=store/bot.db, VNSTOCK_API_KEY (nếu có)
pytest -q
```

Không commit `.env`, `store/bot.db` có dữ liệu thật, hay file tham số nhóm
(`bảng thông số chi tiết.xlsx`, Project.pdf) nếu đã thống nhất giữ ngoài git.

## Pipeline live (ops)

Bot **không** tự crawl khi bạn gõ lệnh. Automation = job theo lịch → ghi `store/` → bot đọc.

1. `.env`: `BOT_TOKEN`, `DATABASE_PATH=store/bot.db`.
2. **Tầng 1** (khi có BCTC / định kỳ):

   ```bash
   python -m pipeline.quarterly_job --start-year 2021 --end-year 2025
   ```

   Universe mặc định = **VN100** (`fundamental_file` trong config). Smoke 35 mã chỉ dùng
   ablation / fallback nhanh.

3. **Tầng 2** (sau đóng cửa mỗi phiên):

   ```bash
   python scripts/run_daily_pipeline.py
   # tùy chọn: --with-sector | --backfill-days N | --no-push
   ```

4. **Bot polling** (một process / một `BOT_TOKEN`):

   ```bash
   python -m bot.main
   ```

### Lệnh bot (tóm tắt)

| Lệnh | Ý nghĩa |
|---|---|
| `/start` `/help` `/about` | Giới thiệu / hướng dẫn |
| `/subscribe` `/unsubscribe` | Nhận / tắt push sau daily |
| `/signals` `/watchlist` `/positions` | Tín hiệu / watchlist / kích thước GARCH |
| `/check <mã>` | Phân tích theo trạng thái (PASS/WATCH/FAIL/…) |
| `/regime` `/sector` `/status` | Regime, ngành, trạng thái store |
| `/chart <mã> …` | Biểu đồ từ `price_bars` / signals đã lưu |
| `/backtest` | Đọc kết quả ablation đã persist — **không** phải NAV live |

### Lịch Windows (sau đóng cửa)

```powershell
.\scripts\run_daily_pipeline.ps1 -NoPush

schtasks /Create /TN "VNSignalDaily" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 15:15 `
  /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Projects\Telegram-bot-for-investment-signal\scripts\run_daily_pipeline.ps1" /F
```

## Backtest

Backtest **dùng chung** code `fundamental_filter/` + `quant_engine/` với live (Close T+1,
PIT lag 90 ngày giả định nếu không có `filed_at` thật). Chi tiết:
[`docs/BACKTEST_FINAL_REPORT.md`](docs/BACKTEST_FINAL_REPORT.md).

```powershell
# FAST DEV — bảng nhanh (smoke/mini); KHÔNG thay metrics nghiên cứu cuối
python scripts/run_backtest_report.py --fast-dev --fast-dev-mini --with-fundamentals `
  --oos-start 2025-03-22 --oos-end 2025-09-22 --no-walk-forward `
  --out-json store/backtest_fast_dev.json --out-xlsx store/backtest_fast_dev.xlsx

# FINAL — VN100, daily Quant, fund PIT, warmup 3y (chậm; cần cache OHLCV + scoring_schedule)
python scripts/run_backtest_report.py --universe vn100 --with-fundamentals --signal-every 1 `
  --oos-start 2025-03-22 --oos-end 2025-09-22 --warmup-years 3 --no-walk-forward `
  --out-json store/backtest_final_vn100_20260922.json
```

- Cache giá: `data/cache/` · Cache BCTC theo năm: `data/cache/scoring_schedule/{key}/year_*.pkl`
- `--refresh-fundamentals` / `--refresh-data` khi cần tải lại
- Community vnstock (~60 req/phút) → lần đầu có fund rất lâu; lần sau hit cache nhanh hơn

### Ablation / walk-forward

```bash
python -m backtest.ablation --tickers FPT,VNM --with-fundamentals --walk-forward
python scripts/run_ablation_quiet.py --walk-forward   # stdout gọn hơn
python -m backtest.walk_forward --config pipeline/config.yaml
```

Ngưỡng giữ tầng và log OOS (kể cả kết quả âm hợp lệ): [`docs/DECISIONS.md`](docs/DECISIONS.md).
**Không** tune tham số trên OOS chỉ để ra số đẹp.

## Tài liệu chính

| File | Nội dung |
|---|---|
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Luồng FF → Quant → store → bot |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Gate P1, ablation log, checklist |
| [`docs/DATA_AUDIT.md`](docs/DATA_AUDIT.md) | Nguồn dữ liệu / PIT |
| [`docs/BACKTEST_FINAL_REPORT.md`](docs/BACKTEST_FINAL_REPORT.md) | FAST DEV vs FINAL, bugs đã sửa |
| [`docs/BACKTEST_DEBUG_CHECKLIST.md`](docs/BACKTEST_DEBUG_CHECKLIST.md) | Debug trước khi tune |
| [`CONTRIBUTING.md`](CONTRIBUTING.md) | Docstring, test cạnh module |

## Đóng góp ngắn

- Một PR một mục đích; bám `docs/BRANCHING.md`.
- Test cạnh module (`**/tests/`); không mạng trong `fundamental_filter/` / `quant_engine/` unit test.
- Sau đổi code lớn: `graphify update .` nếu dùng knowledge graph local.
