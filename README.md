# Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam

Bài tập nhóm — kết hợp Fundamental Filter (Graham–Dodd hiện đại) với Quant Regime Engine
(Markov regime switching, Kalman filter, GARCH, Ornstein–Uhlenbeck, Black-Litterman, Monte
Carlo, Hawkes process) để phát tín hiệu Mua/Bán trên một universe cổ phiếu Việt Nam.

> ⚠️ Sản phẩm học thuật phục vụ bài tập môn học, không phải khuyến nghị đầu tư, không thay
> thế tư vấn từ người có chứng chỉ hành nghề. Xem thêm ghi chú pháp lý ở `docs/ARCHITECTURE.md`.

## Bắt đầu từ đâu

1. Đọc `docs/ARCHITECTURE.md` để hiểu sơ đồ tổng thể và bảng phân công.
2. Đọc `docs/BRANCHING.md` trước khi tạo branch/PR đầu tiên.
3. Xem `pipeline/config.yaml` để biết tầng nào đang bật (P0/P1/P2).
4. Tài liệu lý thuyết đầy đủ: `docs/khung_chien_luoc_tich_hop.docx` (đặt file .docx của
   nhóm vào đây).

## Cấu trúc thư mục

```
fundamental_filter/   Tầng 1 — Growth, Quality, Safety, Valuation, scoring
quant_engine/         Tầng 2 — Regime, Alpha, Risk, Portfolio, Probabilistic
pipeline/             Job điều phối (quarterly cho Tầng 1, daily cho Tầng 2) + config
data/                 Ingest, cache, schema dữ liệu thô
store/                Lưu trữ bảng signals/watchlist (SQLite/Parquet) + schema
backtest/             Engine backtest, chi phí giao dịch, walk-forward, ablation
bot/                  Telegram bot — CHỈ ĐỌC từ store/, không tính toán
notebooks/            Notebook nghiên cứu/thăm dò — không chứa logic production
docs/                 Tài liệu kiến trúc, audit dữ liệu, nhật ký quyết định
tests/                Integration test xuyên module
```

## Cài đặt nhanh

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # điền BOT_TOKEN, đường dẫn dữ liệu, v.v.
pytest                 # chạy toàn bộ test
```

## Chạy pipeline (khi đã có dữ liệu)

```bash
python -m pipeline.quarterly_job     # Tầng 1 — chạy khi có BCTC mới
python -m pipeline.daily_job         # Tầng 2 — chạy sau giờ đóng cửa mỗi phiên
python -m bot.main                   # Khởi động bot (chỉ đọc store/)
```

## Chạy live (ops)

1. `cp .env.example .env` rồi điền `BOT_TOKEN` (không commit `.env`).
2. Universe/watchlist: `python -m pipeline.quarterly_job` (hoặc đã có dữ liệu trong `store/`).
3. Một lần pipeline + push: `python scripts/run_daily_pipeline.py` (thêm `--with-sector` nếu cần refresh ngành).
4. Bot polling: `python -m bot.main` (không `--dry-run`). Trong Telegram: `/start` → `/subscribe` → `/signals`.
5. Chạy lại `run_daily_pipeline` sau khi subscribe để nhận push.

### Lịch Windows (sau đóng cửa)

```powershell
# Một lần thủ công (không push Telegram):
.\scripts\run_daily_pipeline.ps1 -NoPush

# Đăng ký Task Scheduler (chỉnh path repo cho khớp máy bạn):
schtasks /Create /TN "VNSignalDaily" /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 15:15 /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\Projects\Telegram-bot-for-investment-signal\scripts\run_daily_pipeline.ps1" /F
```

Bot polling (`python -m bot.main`) chạy riêng nếu muốn nhận tin ngay khi daily xong.

## Backtest

```bash
python -m backtest.walk_forward --config pipeline/config.yaml
python -m backtest.ablation --config pipeline/config.yaml
```
