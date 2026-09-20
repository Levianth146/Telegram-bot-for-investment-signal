# Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1

Mục đích: xác nhận trước khi code tầng P2 xem dữ liệu có thực sự lấy được không, để quyết
định giữ/cắt P2 ngay từ tuần 1 (xem mục 11 của tài liệu framework).

Người phụ trách audit: repo sync (P0)  Ngày hoàn thành: 2026-09-20

## 1. Dữ liệu nợ chi tiết (cho Merton Distance-to-Default)

| Mã thử nghiệm | Có nợ ngắn/dài hạn theo quý? | Có kỳ hạn/lãi suất chi tiết? | Nguồn | Kết luận khả thi |
|---|---|---|---|---|
| (mẫu) | Có ST/LT debt năm qua vnfinancialdata | Không kỳ hạn/lãi suất chi tiết | vnfinancialdata | **Không khả thi P2** cho đến khi có thuyết minh nợ |

## 2. Dữ liệu khối lượng/sự kiện theo ngày (cho Hawkes)

| Mã thử nghiệm | Có volume theo ngày đủ dài (2–3 năm)? | Có dữ liệu intraday không (tùy chọn)? | Nguồn | Kết luận khả thi |
|---|---|---|---|---|
| (chain) | Có qua vnstock OHLCV trong `data.providers` | Không yêu cầu V1 | vnstock | Khả thi P2 sau; Hawkes vẫn `enabled: false` |

## 3. Dữ liệu khối ngoại / tự doanh ròng (cho Institutional Flow — nếu làm)

| Mã thử nghiệm | Có dữ liệu mua/bán ròng theo ngày? | Nguồn | Kết luận khả thi |
|---|---|---|---|
| — | Chưa audit nguồn ổn định | — | **Không làm V1** |

## 4. BCTC — ngày công bố thực tế (cho point-in-time discipline)

| Mã thử nghiệm | Có ngày công bố chính thức (không phải ngày kết thúc kỳ)? | Nguồn | Ghi chú |
|---|---|---|---|
| (vnfinancialdata) | **Chưa có** cột `filed_at` xác nhận | vnfinancialdata annual | Dùng assumed lag |

## 4b. `vnfinancialdata` — có field ngày công bố thật không?

- [x] `vnfinancialdata` có cột ngày công bố thực tế? **Không** (chưa xác nhận / live path đánh dấu `publication_date_missing`)
- [x] Nếu Không, độ trễ giả định áp dụng: **90 ngày** sau period-end năm (BCTC năm)
- [x] Đã cập nhật `data_sources.financial_statements_backtest.point_in_time_verified` trong
      `pipeline/config.yaml` thành `true` sau khi xác nhận **assumed lag** (xem `docs/DECISIONS.md`)

## Kết luận cuối audit

- [x] Merton DD: **không khả thi** V1 — thiếu kỳ hạn nợ chi tiết
- [x] Hawkes: **khả thi dữ liệu volume** qua vnstock, nhưng giữ `enabled: false` đến khi Quant P0 xong
- [x] Institutional Flow: **không khả thi** V1
- [x] `vnfinancialdata` point-in-time: **cần độ trễ giả định 90 ngày** — đã ghi config + DECISIONS
- [x] Hist valuation E2E (2026-09-21): year-end close + assumed lag → PASS path khi ≥4 obs
- [x] Live smoke 2026-09-21 (VNM/FPT): OHLCV + sector qua **vnstock**; annual BCTC qua **vnfinancialdata**
  (live chain `vnstock`/`cafef`/`vietstock` vẫn stub — `get_financial_statement_provider` append
  `VnFinancialDataStatements` last-resort). DNSE multi-year OHLCV chưa cần khi vnstock đủ.
  Runtime: `truststore` + packages trong `requirements.txt`. Chi tiết → `docs/DECISIONS.md`.

→ Cập nhật `pipeline/config.yaml` (`enabled: true/false`) và `docs/DECISIONS.md` ngay sau khi
chốt kết luận này.
