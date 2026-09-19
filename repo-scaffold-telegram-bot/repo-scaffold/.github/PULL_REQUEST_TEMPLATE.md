## Issue liên quan
Closes #

## Thay đổi gì
-

## Đây là tầng P0 / P1 / P2? (xem docs/ARCHITECTURE.md)
-

## Cách test
-

## Checklist
- [ ] Có test cho logic mới, `pytest` xanh local
- [ ] Không hardcode ngưỡng (đọc từ `pipeline/config.yaml`)
- [ ] Nếu thêm tầng P1/P2: đã có cờ bật/tắt trong `pipeline/config.yaml`
- [ ] Nếu đổi schema bảng `signals`: đã báo nhóm `bot/` và `backtest/`
- [ ] Không gọi network bên trong `fundamental_filter/` hoặc `quant_engine/`
