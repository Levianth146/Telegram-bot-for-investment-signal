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

## Kết luận cuối audit

- [ ] Merton DD: khả thi / không khả thi — lý do: __________
- [ ] Hawkes: khả thi / không khả thi — lý do: __________
- [ ] Institutional Flow: khả thi / không khả thi — lý do: __________

→ Cập nhật `pipeline/config.yaml` (`enabled: true/false`) và `docs/DECISIONS.md` ngay sau khi
chốt kết luận này.
