# Fintech Stock Bot — Fundamental Layer

Fundamental Filter cho cổ phiếu Việt Nam, gồm Growth, Quality, Safety,
Valuation, Fundamental Score và phân loại PASS/WATCH/FAIL. Quant Layer và
Telegram delivery là các lớp mở rộng về sau, không thuộc pipeline hiện tại.

## Architecture

```text
Financial + market data
  -> current-run peer universe
  -> snapshots and ratios
  -> peer percentiles + trends
  -> metric/module/fundamental scores
  -> safety/data-quality gates
  -> current-run classification
  -> final outputs
```

Pipeline production truyền `DataFrame` giữa các stage. Classification chỉ nhận
universe của lần chạy hiện tại, không quét CSV của các lần chạy trước.

## Financial modules

- **Growth:** tăng trưởng doanh thu, EPS CAGR và CFO.
- **Quality:** operating margin, ROE và ROIC.
- **Safety:** absolute strength, peer relative và trend.
- **Valuation:** P/E, P/B, EV/EBITDA và FCF Yield; historical valuation chỉ
  được dùng khi point-in-time safe.

## Setup — Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Điền credentials DNSE vào `.env`. Không commit file `.env`.

## Run

Chạy một current-run universe bằng danh sách ticker phân cách bởi dấu phẩy:

```powershell
python fundamental_engine.py VNM,FPT,VHE 2021 2025
```

Debug artifacts là opt-in:

```powershell
python fundamental_engine.py VNM,FPT,VHE 2021 2025 --debug
```

Các CLI stage cũ vẫn tồn tại để diagnostic/backward compatibility, nhưng không
phải production entry point.

## Tests

```powershell
python -m unittest -v test_fundamental_refactor.py test_systemic_fundamental.py test_safety_scoring.py test_valuation_point_in_time.py
```

Regression tests dùng frozen inputs và không gọi network.

## Outputs

Production mặc định chỉ ghi:

- `outputs/fundamental_results.csv`: một dòng cho mỗi target ticker.
- `outputs/fundamental_metrics.csv`: metric-level audit.

`debug=False` không tạo intermediate CSV. Khi bật debug, artifacts chỉ nằm
trong `outputs/debug/<run_id>/`; mỗi run có thư mục riêng. Production outputs
không cần commit vì có thể tái tạo từ current-run inputs.

## Data limitations

- Nguồn company/industry hiện tại có thể không cung cấp sub-industry, khiến
  peer selector phải dùng industry fallback với quality thấp.
- Publication date và historical shares chưa đầy đủ cho nhiều ticker.
- Historical valuation không được fabricate; component này được đánh dấu
  unavailable khi không point-in-time safe.
- API/data vendor availability vẫn ảnh hưởng một live run, nhưng regression
  suite không phụ thuộc network.

## Reproducibility

Ticker universe được truyền trực tiếp vào canonical engine. Old CSV artifacts
không được scan hoặc đưa vào classification. Cùng frozen input tạo cùng score,
gate và classification trong tolerance `1e-8`.
