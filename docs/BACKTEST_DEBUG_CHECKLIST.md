# Checklist tìm bug backtest — trước khi kết luận "framework không hoạt động"

Bối cảnh: lần chạy `ablation_watchlist12_wf_dense` (22/09/2026) cho kết quả OOS
**CAGR -5.6%, Sharpe -0.84**, thua cả 3 baseline B0/B1/B2 (xem `docs/DECISIONS.md`).
Mức âm sâu này (không chỉ "không có edge" mà "âm mạnh") gợi ý khả năng cao có
**lỗi thực thi**, không chỉ đơn thuần framework không hoạt động. Đi qua checklist
này THEO ĐÚNG THỨ TỰ trước khi tinh chỉnh bất kỳ tham số nào — sửa tham số trước
khi loại trừ bug sẽ khiến không biết cải thiện đến từ đâu.

**Quy tắc chung khi debug**: chỉ sửa CODE (logic sai), không sửa THAM SỐ (ngưỡng,
window size...) ở bước này. Sửa tham số là bước tinh chỉnh sau, làm ở
`docs/DECISIONS.md` với kỷ luật in-sample-only đã nêu.

## Ưu tiên 1 — Lỗi dấu / hướng lệnh (khả năng cao nhất cho Sharpe âm sâu)

- [ ] `signals.action = 'BUY'` có được `backtest/engine.py` map đúng thành **mua**
      (direction = +1), không bị đảo ngược thành bán/short ở đâu đó?
- [ ] Quy ước dấu của `score` có nhất quán xuyên suốt: điểm cao hơn = tích cực hơn,
      ở cả `fundamental_filter/scoring.py` LẪN các module `quant_engine/alpha/`?
      Một module quy ước ngược (điểm cao = xấu) trong khi module khác quy ước
      xuôi sẽ triệt tiêu lẫn nhau một cách âm thầm, không báo lỗi rõ ràng.
- [ ] Công thức PnL trong `backtest/engine.py`: `pnl = (giá_thoát - giá_vào) / giá_vào * direction`
      — in thử `direction` cho vài lệnh BUY thực tế, xác nhận đúng là `+1`.

## Ưu tiên 2 — Look-ahead / lệch thời gian

- [ ] Giá dùng để vào lệnh trong backtest có phải giá **đã biết tại thời điểm ra
      tín hiệu** (vd đóng cửa T-1 hoặc mở cửa T), hay đang lỡ dùng đóng cửa T
      (chính là giá dùng để TÍNH tín hiệu) — nếu vậy là look-ahead, backtest đang
      "biết trước" giá đóng cửa ngay khi ra quyết định, điều không thể xảy ra khi
      chạy thật.
- [ ] BCTC dùng trong backtest có lọc theo `filed_at` (ngày công bố + độ trễ) đúng
      như mục 7.1 point-in-time, hay đang vô tình dùng ngày kết thúc kỳ báo cáo?
      Nếu công bố trễ hơn giả định, mô hình có thể "biết" BCTC sớm hơn thực tế —
      kiểm tra theo cả 2 hướng vì lệch có thể làm kết quả TỐT giả tạo (inflate) hoặc
      hỏng cấu trúc dữ liệu theo cách khó đoán.
- [ ] `watchlist12` dùng trong backtest có được **tái tạo lại theo từng ngày lịch
      sử** (dùng đúng dữ liệu Tầng 1 tại đúng thời điểm đó), hay đang dùng watchlist
      **hiện tại** áp ngược về quá khứ? Cách sau gây survivorship bias — chỉ giữ
      lại mã sau này biết là "sống sót", thường làm kết quả tốt giả tạo, nhưng nếu
      áp sai chiều/lẫn lộn ngày tháng có thể tạo ra nhiễu ngẫu nhiên trông giống âm.

## Ưu tiên 3 — Mô hình hoá chi phí/thực thi

- [ ] `tax_sell_pct`/`fee_roundtrip_pct` trong `backtest/costs.py` áp đúng 1 lần mỗi
      lệnh, không bị tính trùng (vd áp cả lúc vào lẫn lúc tính lại khi thoát).
- [ ] Phí có đang tính trên đúng giá trị lệnh (`size_pct_nav` × NAV) chứ không phải
      nhầm trên toàn bộ NAV mỗi lần giao dịch — với 36 lệnh mà phí tính sai theo
      hướng này có thể ăn hết lợi nhuận mà trông như framework tệ.
- [ ] Biên độ giá trần/sàn (HOSE ±7%, HNX ±10%) có được tôn trọng khi backtest cố
      thoát lệnh ở mức stop — nếu code cho phép thoát ở giá vượt biên độ thực tế
      cho phép trong ngày, lỗ tính được sẽ ảo (quá bi quan) so với thực tế.
- [ ] Quy tắc T+2 (không bán được cổ phiếu mới mua trong 2 ngày) — nếu backtest
      chặn nhầm cả những lệnh SELL hợp lệ (đã đủ T+2) thành không thực thi được,
      lệnh cắt lỗ đúng lúc sẽ bị trễ, biến lỗ nhỏ dự kiến thành lỗ lớn thực tế.

## Ưu tiên 4 — Sizing / stop-loss

- [ ] Công thức sizing theo GARCH: `size = mức_rủi_ro_mục_tiêu / sigma_hat` — biến
      động CAO hơn phải cho size NHỎ hơn. Nếu công thức bị đảo (size tỷ lệ thuận
      với biến động thay vì nghịch), tiền sẽ dồn nhiều nhất vào đúng mã rủi ro
      nhất — đối chiếu với quan sát mã GAS có tỷ trọng 10% (cao bất thường) ở lần
      test `/positions` trước, xem GAS có phải mã biến động cao nhất trong rổ
      không — nếu đúng, đây có thể là bằng chứng cho lỗi này.
- [ ] Lệnh cắt lỗ (`stop`) có thực sự được kiểm tra và đóng vị thế đúng lúc trong
      vòng lặp backtest, hay code chỉ ghi `stop` vào bảng mà không dùng nó để đóng
      lệnh khi giá chạm — biến "lỗ nhỏ có kiểm soát" thành lỗ không giới hạn.

## Ưu tiên 5 — Đồng nhất dữ liệu

- [ ] Giá dùng cho backtest có được điều chỉnh cổ tức/chia tách (adjusted close)
      nhất quán, hay đang lẫn giữa giá điều chỉnh và giá thô ở các đoạn khác nhau
      (dễ xảy ra nếu từng chuyển nguồn giữa DNSE/vnstock/cafef theo chain fallback)
      — 1 lần chia tách không điều chỉnh sẽ tạo ra 1 "cú sập giá" giả trong dữ liệu.

## Sau khi đi hết checklist

- Nếu tìm thấy bug ở bất kỳ mục nào → sửa code, chạy lại **đúng 1 lần** trên cùng
  OOS, ghi kết quả mới vào `docs/DECISIONS.md` (dòng log mới, không sửa đè dòng cũ).
- Nếu không tìm thấy bug nào → chuyển sang bước tinh chỉnh tham số **chỉ trên
  in-sample**, theo đúng quy trình đã nêu ở `docs/DECISIONS.md`.
- Dù kết quả sau cùng là gì, **giữ nguyên log 22/09/2026 trong `docs/DECISIONS.md`**
  — đây là bằng chứng cho thấy nhóm có quy trình debug nghiêm túc, có giá trị khi
  bảo vệ đồ án hơn là một bảng số liệu "sạch" không rõ nguồn gốc.
