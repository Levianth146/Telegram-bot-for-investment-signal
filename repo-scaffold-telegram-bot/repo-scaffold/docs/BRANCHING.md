# Chiến lược branch & quy trình làm việc

## Vấn đề với 3 branch dài hạn ban đầu

`fundamental_filter` và `quant_regime_engine` nếu để tồn tại song song suốt 2 tháng sẽ
khiến việc merge cuối kỳ (dự kiến tuần 5 theo lộ trình) trở thành điểm rủi ro cao nhất:
càng để lâu, hai branch càng lệch nhau (schema, format dữ liệu, dependency), càng khó review
một PR khổng lồ, và bug tích hợp chỉ lộ ra rất muộn.

## Quy tắc áp dụng từ dự án này

1. **`main` là branch duy nhất tồn tại lâu dài.** Được bảo vệ (protected branch): không push
   trực tiếp, chỉ merge qua Pull Request, bắt buộc CI xanh + tối thiểu 1 reviewer.
2. **`fundamental_filter` và `quant_regime_engine` chỉ dùng 2–3 ngày đầu tuần 1** để mỗi
   nhóm nhỏ dựng khung thư mục ban đầu của mình mà không chặn nhóm kia. Ngay khi khung
   thư mục ổn (cuối ngày 3–4 tuần 1), merge cả hai vào `main` qua PR, rồi **xóa hai branch
   này**. Từ đó không ai code trực tiếp trên hai branch đó nữa.
3. **Từ ngày 4 tuần 1 trở đi, mọi thay đổi đi qua feature branch ngắn hạn**, đặt tên theo
   mẫu:
   - `feature/<số-issue>-<mô-tả-ngắn>` — ví dụ `feature/12-garch-sizing`
   - `fix/<số-issue>-<mô-tả-ngắn>` — cho sửa lỗi
   - Nhánh tạo từ `main`, sống tối đa vài ngày, merge xong thì xóa.
4. **Không branch nào được sống quá 1 tuần** mà không mở PR (kể cả PR draft) — nếu một
   task lớn hơn 1 tuần, chia nhỏ issue ra.
5. **Tích hợp end-to-end sớm**: cuối tuần 2 phải có một lần chạy được toàn bộ pipeline
   trên `main` với dữ liệu giả (mọi tầng P1/P2 chỉ là stub trả giá trị mặc định — xem
   `pipeline/config.yaml`). Từ tuần 3, họp tích hợp hằng tuần, merge thường xuyên, không
   dồn tới tuần 5 mới ghép.

## Quy trình một task điển hình

1. Tạo GitHub Issue, gắn nhãn theo mức ưu tiên `P0` / `P1` / `P2` (xem `docs/ARCHITECTURE.md`
   mục phân tầng) và nhãn module (`fundamental`, `quant`, `bot`, `backtest`, `infra`).
2. Nhận issue (assign chính mình), tạo branch từ `main`: `feature/<issue>-<slug>`.
3. Code + viết test trong cùng branch. Chạy `pytest` và `ruff check .` local trước khi push.
4. Mở PR, mô tả rõ: issue liên quan, thay đổi gì, cách test. Điền theo
   `.github/PULL_REQUEST_TEMPLATE.md`.
5. CI tự chạy (xem `.github/workflows/ci.yml`). PR cần ít nhất 1 reviewer — ưu tiên chéo:
   người ở nhóm Fundamental review PR của nhóm Quant và ngược lại vài lần trong dự án, để
   tránh hai nhóm thành hai "silo" không hiểu code của nhau.
6. Merge bằng "Squash and merge" để lịch sử `main` gọn gàng. Xóa branch sau khi merge.

## Review checklist tối thiểu

- [ ] Có test cho logic mới (hoặc test hiện có vẫn pass)?
- [ ] Không hardcode ngưỡng "chết" (xem mục 12 sai lầm cần tránh trong tài liệu framework)?
- [ ] Nếu thêm một tầng P1/P2: có cờ bật/tắt trong `pipeline/config.yaml` không?
- [ ] Nếu đụng tới `store/schema.sql` hoặc bảng `signals`: có cập nhật cho cả hai nhóm biết không?
- [ ] Không gọi API bên ngoài (kéo giá, BCTC) từ trong code của `bot/` — bot chỉ đọc từ `store/`.
