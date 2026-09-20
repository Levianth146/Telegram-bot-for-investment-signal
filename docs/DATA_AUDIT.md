# Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1

Mục đích: xác nhận trước khi code tầng P2 xem dữ liệu có thực sự lấy được không, để quyết
định giữ/cắt P2 ngay từ tuần 1 (xem mục 11 của tài liệu framework).

Người phụ trách audit: __________  Ngày hoàn thành: __________

## 1. Dữ liệu nợ chi tiết (cho Merton Distance-to-Default)

| Mã thử nghiệm | Có nợ ngắn/dài hạn theo quý? | Có kỳ hạn/lãi suất chi tiết? | Nguồn | Kết luận khả thi |
|---|---|---|---|---|
| VD: HPG | | | | |

## 2. Dữ liệu khối lượng/sự kiện theo ngày (cho Hawkes)

| Mã thử nghiệm | Có volume theo ngày đủ dài (2–3 năm)? | Có dữ liệu intraday không (tùy chọn)? | Nguồn | Kết luận khả thi |
|---|---|---|---|---|

## 3. Dữ liệu khối ngoại / tự doanh ròng (cho Institutional Flow — nếu làm)

| Mã thử nghiệm | Có dữ liệu mua/bán ròng theo ngày? | Nguồn | Kết luận khả thi |
|---|---|---|---|

## 4. BCTC — ngày công bố thực tế (cho point-in-time discipline)

| Mã thử nghiệm | Có ngày công bố chính thức (không phải ngày kết thúc kỳ)? | Nguồn | Ghi chú |
|---|---|---|---|

## 4b. `vnfinancialdata` — có field ngày công bố thật không?

Package này (dùng làm nguồn BCTC lịch sử cho backtest — xem `pipeline/config.yaml:
data_sources.financial_statements_backtest`) chỉ ghi "tham chiếu từ file BCTC nguồn",
không xác nhận rõ có lưu ngày công bố thực (`filed_at`) hay chỉ lưu kỳ báo cáo
(`period`, vd "2025Q2"). Nếu chỉ có `period`, phải tự cộng thêm độ trễ công bố giả định
(vd +45–90 ngày sau period-end, tuỳ loại BCTC quý/năm/soát xét) trước khi dùng cho
backtest, nếu không sẽ vi phạm point-in-time discipline (mục 7.1 tài liệu framework).

- [ ] `vnfinancialdata` có cột ngày công bố thực tế? Có / Không
- [ ] Nếu Không, độ trễ giả định áp dụng: __________ ngày (theo loại BCTC: quý/năm/soát xét)
- [ ] Đã cập nhật `data_sources.financial_statements_backtest.point_in_time_verified` trong
      `pipeline/config.yaml` thành `true` sau khi xác nhận

## Kết luận cuối audit

- [ ] Merton DD: khả thi / không khả thi — lý do: __________
- [ ] Hawkes: khả thi / không khả thi — lý do: __________
- [ ] Institutional Flow: khả thi / không khả thi — lý do: __________
- [ ] `vnfinancialdata` point-in-time: xác nhận xong / cần độ trễ giả định — lý do: __________

→ Cập nhật `pipeline/config.yaml` (`enabled: true/false`) và `docs/DECISIONS.md` ngay sau khi
chốt kết luận này.
