# Hướng dẫn đóng góp

Đọc `docs/BRANCHING.md` trước — đây là quy trình bắt buộc, không phải gợi ý.

## Trước khi bắt đầu một task

1. Kiểm tra đã có Issue chưa; nếu chưa, tạo issue mới, gắn nhãn ưu tiên (`P0`/`P1`/`P2`)
   và nhãn module (`fundamental`/`quant`/`bot`/`backtest`/`infra`).
2. Tự assign issue cho mình để tránh trùng việc.
3. Tạo branch từ `main`: `feature/<số-issue>-<mô-tả-ngắn>`.

## Chuẩn code

- Python 3.11+, format bằng `black`, lint bằng `ruff`.
- Mọi hàm tính toán (fundamental_filter/, quant_engine/, backtest/) phải có docstring nêu
  rõ: công thức tham chiếu (số mục trong tài liệu framework), input, output, đơn vị.
- Không hardcode ngưỡng — đọc từ `pipeline/config.yaml` hoặc tham số hàm.
- Không gọi network (kéo giá, BCTC) bên trong `quant_engine/` hoặc `fundamental_filter/` —
  các module này chỉ nhận DataFrame/dict đã được `data/` chuẩn bị sẵn. Việc này giúp
  test được mà không cần mạng, và giữ đúng nguyên tắc "backtest và live dùng chung code".

## Test

- Mỗi module logic mới cần ít nhất 1 unit test trong thư mục `tests/` cạnh nó.
- Chạy `pytest` xanh trước khi mở PR.
- Nếu thêm một tầng mới ảnh hưởng tới bảng `signals`, thêm test kiểm tra schema không vỡ.

## Mở Pull Request

Dùng template có sẵn (`.github/PULL_REQUEST_TEMPLATE.md`). PR cần:
- Liên kết issue (`Closes #<số>`)
- CI xanh
- Ít nhất 1 reviewer duyệt

## Câu hỏi thường gặp

**Tôi nên đặt logic tính toán mới ở fundamental_filter/ hay quant_engine/?**
Nếu câu hỏi là "doanh nghiệp này có tốt không" (dựa trên BCTC, cập nhật theo quý) →
`fundamental_filter/`. Nếu câu hỏi là "bây giờ có nên mua/bán, bao nhiêu, dừng ở đâu"
(dựa trên giá/khối lượng, cập nhật mỗi phiên) → `quant_engine/`.

**Tôi muốn thử một mô hình mới chưa có trong framework, đặt ở đâu?**
Đặt trong `notebooks/` trước để thử nghiệm. Chỉ đưa vào `fundamental_filter/` hoặc
`quant_engine/` sau khi đã thống nhất với nhóm và ghi vào `docs/DECISIONS.md`.
