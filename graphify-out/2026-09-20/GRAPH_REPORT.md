# Graph Report - Telegram-bot-for-investment-signal  (2026-09-20)

## Corpus Check
- 108 files · ~41,618 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 6, .mdc 2, .example 2)

## Summary
- 908 nodes · 1616 edges · 83 communities (66 shown, 17 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 35 edges (avg confidence: 0.92)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5b5840d4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_regime.py
- argparse
- repository.py
- formatters.py
- 4. Câu hỏi 3 — Doanh nghiệp có an toàn tài chính không?
- fundamental_engine.py
- test_valuation_point_in_time.py
- garch.py
- growth.py
- black_litterman.py
- monte_carlo.py
- hawkes.py
- test_scoring_store.py
- kalman_trend.py
- ou_meanrev.py
- schema.sql
- costs.py
- ablation.py
- engine.py
- main.py
- test_integration_smoke.py
- test_providers.py
- pipeline/__init__.py
- 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần
- charts.py
- pandas
- Hướng dẫn đóng góp
- Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1
- Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam
- Chiến lược branch & quy trình làm việc
- PULL_REQUEST_TEMPLATE.md
- Nhật ký quyết định giữ/cắt một tầng (ablation log)
- get_fundamental_snapshot
- validate_ticker.py
- ClassificationTests
- FundamentalRefactorTests
- select_peer_universe
- 5. Câu hỏi 4 — Giá cổ phiếu hiện tại có hợp lý không?
- Fintech Stock Bot — Fundamental Layer engine (`layer1_engine/`)
- 3. Câu hỏi 2 — Doanh nghiệp tạo lợi nhuận có chất lượng và hiệu quả không?
- Khung chien luoc tich hop - Fundamental Filter  Quant Regime Engine_efa0dec8.md
- 2. Câu hỏi 1 — Doanh nghiệp có thật sự tăng trưởng không?
- score_current_universe
- 9. Từ Fundamental View đến Quant Regime Engine — các điểm nối cụ thể
- pathlib
- registry.py
- trend_analysis.py
- 11. Điều chỉnh triển khai
- fundamental_score.py
- ProviderError
- 1. Bức tranh tổng thể của Fundamental Filter: Bot đang cố trả lời điều gì?
- 13. Bảng công thức nhanh (Quick Reference)
- 14. Thuật ngữ cần nhớ
- dnse_price.py
- call_chain
- financial_data.py
- FinancialStatementProvider
- ratios_valuation.py
- peer_coverage_runner.py
- financials_stubs.py
- valuation.py
- scoring_input.py
- .get_ohlcv
- peer_percentile.py
- DnsePriceProvider
- CafeFPriceProvider
- historical_percentile.py
- VnstockFinancials
- 5.1 Ta đang trả bao nhiêu cho 1 đồng lợi nhuận?
- 5.3 Giá trị toàn doanh nghiệp so với lợi nhuận hoạt động thế nào?
- 12. Những sai lầm nhóm cần tránh khi triển khai
- data/__init__.py

## God Nodes (most connected - your core abstractions)
1. `get_fundamental_snapshot()` - 30 edges
2. `get_historical_fundamental()` - 30 edges
3. `ProviderError` - 23 edges
4. `get_valuation()` - 22 edges
5. `score_current_universe()` - 21 edges
6. `analyze_fundamental_universe()` - 20 edges
7. `get_financial_data()` - 18 edges
8. `to_store_records()` - 16 edges
9. `load_scoring_config()` - 15 edges
10. `ClassificationTests` - 15 edges

## Surprising Connections (you probably didn't know these)
- `Annual BCTC (`FinancialStatementProvider.get_annual`)` --references--> `get_financial_data()`  [INFERRED]
  data/schemas/README.md → fundamental_filter/layer1_engine/financial_data.py
- `Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`)` --references--> `get_open_positions()`  [INFERRED]
  docs/ARCHITECTURE.md → store/repository.py
- `Pure path vs I/O path` --references--> `load_scoring_config()`  [INFERRED]
  fundamental_filter/layer1_engine/README.md → fundamental_filter/layer1_engine/config_loader.py
- `Pure path vs I/O path` --references--> `analyze_fundamental_universe()`  [INFERRED]
  fundamental_filter/layer1_engine/README.md → fundamental_filter/layer1_engine/fundamental_engine.py
- `Network / I/O` --references--> `analyze_fundamental_universe()`  [INFERRED]
  fundamental_filter/README.md → fundamental_filter/layer1_engine/fundamental_engine.py

## Import Cycles
- None detected.

## Communities (83 total, 17 thin omitted)

### Community 0 - "test_regime.py"
Cohesion: 0.20
Nodes (9): pytest, quant_engine, filtered_regime_probability(), fit_markov_regime(), Regime — Markov switching trên VN-Index. Tham chiếu: Mục 8 lớp 1 / mục 9 của…, Fit Hidden Markov Model trên lợi nhuận VN-Index. Trả về model đã fit.…, Trả về P(state=k | F_t) CHỈ dùng dữ liệu tới thời điểm t (filtered, không…, Ví dụ test cho module Regime. (+1 more)

### Community 1 - "argparse"
Cohesion: 0.20
Nodes (5): argparse, Walk-forward validation — train N năm, test M tháng, trượt cửa sổ tới. Tham…, Sinh ra danh sách (train_start, train_end, test_start, test_end)., walk_forward_windows(), Job Tầng 2 — chạy mỗi phiên, sau giờ đóng cửa (~15:00). Luồng: store.watchlist…

### Community 2 - "repository.py"
Cohesion: 0.05
Nodes (54): Connection, Bảng lệnh bot dự kiến, Bảng `signals` (hợp đồng giao diện giữa Tầng 2 và bot), Chart backtest bổ sung (`bot/charts.py`), Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`), Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư, Module ↔ người phụ trách (theo phân công đã thống nhất), Nguyên tắc bất biến (không được vi phạm khi code) (+46 more)

### Community 3 - "formatters.py"
Cohesion: 0.20
Nodes (9): format_signal_message(), format_ta_reference_block(), Sinh câu giải thích tín hiệu theo quy tắc 'im lặng trừ khi cần giải thích' (mục…, Dịch xác suất regime sang câu dễ hiểu — mục 9.7. Ví dụ: 0.78 -> "thị trường…, Dịch t-stat của slope Kalman sang câu dễ hiểu. Ví dụ: 2.6 -> "xu hướng tăng rõ…, Ghép khối 'Tham khảo thêm' từ các chỉ số TA cổ điển đã tính sẵn (RSI,…, Ghép mẫu tin nhắn đầy đủ theo mục 9.7: BUY — <ticker> | <ngày> Regime: ... (kèm…, translate_kalman_trend() (+1 more)

### Community 4 - "4. Câu hỏi 3 — Doanh nghiệp có an toàn tài chính không?"
Cohesion: 0.09
Nodes (23): 4.1 Có đủ khả năng thanh toán ngắn hạn không?, 4.2 Doanh nghiệp đang vay nợ nhiều đến mức nào?, 4.3 Doanh nghiệp có đủ sức trả lãi vay không?, 4.4 Dòng tiền có thật sự đủ để hỗ trợ nợ không?, 4.5 Có rủi ro ẩn nào trong bảng cân đối không?, 4.6 Thị trường đang định giá rủi ro vỡ nợ ra sao? — Merton Distance-to-Default (Advanced, MỚI), 4. Câu hỏi 3 — Doanh nghiệp có an toàn tài chính không?, Cash Ratio (+15 more)

### Community 5 - "fundamental_engine.py"
Cohesion: 0.23
Nodes (11): analyze_fundamental(), analyze_fundamental_universe(), _empty_historical_percentiles(), _normalize_tickers(), Run the Fundamental Layer in memory for an explicit ticker universe.…, Backward-compatible single-ticker entry point without stale CSV state., main(), CLI: python -m fundamental_filter.layer1_engine VNM,FPT 2021 2025 [--debug]. (+3 more)

### Community 6 - "test_valuation_point_in_time.py"
Cohesion: 0.15
Nodes (9): aggregate_ttm(), calculate_fcf(), Return the newest record that was public on the requested date., Aggregate four consecutive, already-published quarters into TTM data., select_latest_published_financial(), _to_date(), ValuationPointInTimeTests, patch (+1 more)

### Community 7 - "garch.py"
Cohesion: 0.20
Nodes (9): fit_gjr_garch(), forecast_sigma(), position_size(), GARCH/GJR-GARCH — dự báo biến động có điều kiện. Tham chiếu: mục "Risk" trong…, Fit GJR-GARCH(1,1), trả về model đã fit., Dự báo sigma_hat cho phiên tiếp theo — ghi vào store.signals.sigma_hat., size = min(w_max, sigma_target / sigma_hat)., stop = entry_price * (1 - k * sigma_hat). (+1 more)

### Community 8 - "growth.py"
Cohesion: 0.13
Nodes (17): fundamental_filter, eps_cagr(), growth_score(), growth_spread(), positive_growth_ratio(), Module Growth — Câu hỏi 1: Doanh nghiệp có thật sự tăng trưởng không? Tham…, Mục 2.1 — Revenue Growth YoY = (Rev_t - Rev_t-1) / Rev_t-1., Mục 2.2 — Growth Spread = NPAT Growth - Revenue Growth (chỉ báo chẩn đoán). (+9 more)

### Community 9 - "black_litterman.py"
Cohesion: 0.25
Nodes (7): black_litterman_weights(), build_views(), equal_weight_fallback(), Black-Litterman — phân bổ danh mục kết hợp baseline thị trường + view riêng.…, Ghép view từ Alpha và view từ Valuation thành ma trận P, vector Q, Omega. Xem…, Trả về vector trọng số danh mục theo Black-Litterman., Fallback khi portfolio_black_litterman.enabled = false (mục 11.1, P1 có thể…

### Community 10 - "monte_carlo.py"
Cohesion: 0.25
Nodes (7): cvar(), probability_tp_before_sl(), Monte Carlo (filtered historical simulation) — xác suất hóa tín hiệu. Tham…, Trả về mảng (n_paths, horizon_days) đường giá mô phỏng., % kịch bản chạm TP trước khi chạm SL., Conditional Value at Risk ở mức alpha (CVaR95)., simulate_price_paths()

### Community 11 - "hawkes.py"
Cohesion: 0.29
Nodes (5): crowding_size_multiplier(), fit_hawkes(), Hawkes process — bộ lọc crowding (đám đông tự kích hoạt chính nó). Tham chiếu:…, Ước lượng mu, alpha, beta bằng MLE. Trả về {"mu":.., "alpha":.., "beta":..}., Giảm size khi n tiến gần n_max — xem mục 9.5 (Safety/Merton DD -> risk overlay,…

### Community 12 - "test_scoring_store.py"
Cohesion: 0.22
Nodes (8): fundamental_filter_layer1_engine, Bước 1 mục 10 — z = (x - median_nganh) / MAD_nganh., zscore_by_sector(), Tests for scoring helpers + store adapter shape (framework mục 10 / schema)., test_aggregate_fundamental_view_single_ticker(), test_load_scoring_config_reads_pipeline_yaml(), test_to_store_records_watchlist_excludes_fail(), test_zscore_by_sector()

### Community 13 - "kalman_trend.py"
Cohesion: 0.33
Nodes (5): alpha_effective(), fit_kalman_trend(), Kalman filter — ước lượng xu hướng (trend/slope) ẩn dưới nhiễu giá. Tham chiếu:…, Trả về (level, slope, slope_variance) theo thời gian., Mục 9.3 — Alpha_effective = Alpha_raw * f(Growth score, Quality score). f là…

### Community 14 - "ou_meanrev.py"
Cohesion: 0.33
Nodes (5): fit_ou_process(), ou_half_life(), Ornstein-Uhlenbeck mean reversion — dùng khi regime đang đi ngang. Tham chiếu:…, Ước lượng theta, mu, sigma từ chuỗi residual (giá - trend Kalman)., half_life = ln(2) / theta.

### Community 15 - "schema.sql"
Cohesion: 0.22
Nodes (12): backtest_results, fundamental_scores, idx_backtest_scope, idx_positions_status, idx_sector_industry, idx_signals_ticker, idx_watchlist_date, positions (+4 more)

### Community 16 - "costs.py"
Cohesion: 0.40
Nodes (3): is_tradable_at_price_limit(), Chi phí giao dịch thực tế — bắt buộc trong mọi backtest (mục 12.2 sai lầm cần…, False nếu giá đã chạm trần/sàn — coi như không khớp được lệnh.

### Community 17 - "ablation.py"
Cohesion: 0.50
Nodes (3): Ablation study — bật/tắt từng tầng theo pipeline/config.yaml, đo đóng góp biên.…, Chạy backtest lần lượt: baseline -> +layer1 -> +layer1+layer2 -> ... Trả về…, run_ablation()

### Community 18 - "engine.py"
Cohesion: 0.50
Nodes (3): Backtest engine — GỌI LẠI đúng hàm trong fundamental_filter/ và quant_engine/,…, Chạy toàn bộ pipeline (Tầng 1 + Tầng 2) trên dữ liệu lịch sử, tôn trọng point-…, run_backtest()

### Community 24 - "test_providers.py"
Cohesion: 0.20
Nodes (16): Provider interfaces + fallback chains for price / BCTC / sector. Pipeline loads…, get_financial_statement_provider(), get_price_provider(), get_sector_provider(), load_pipeline_config(), Any, Path, ``mode='live'`` uses financial_statements_live.chain; ``mode='backtest'`` uses… (+8 more)

### Community 32 - "4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần"
Cohesion: 0.08
Nodes (25): 1. Vài khái niệm cần hiểu trước (bằng ví dụ, không phải định nghĩa hàn lâm), 2. Cài đặt — chọn 1 trong 2 cách, 3. Lấy code về máy lần đầu (chỉ làm 1 lần), 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần, 5. Tôi nên sửa file ở đâu?, 6. Các tình huống hay gặp và cách xử lý, 7. Bảng lệnh Git tối thiểu cần nhớ (nếu dùng dòng lệnh), 8. Nếu vẫn bị kẹt (+17 more)

### Community 33 - "charts.py"
Cohesion: 0.11
Nodes (24): Path, Vẽ chart để bot gửi qua Telegram (ảnh PNG, gửi qua sendPhoto). QUAN TRỌNG —…, Equity curve tách theo regime (tô màu đoạn nào chạy trong lúc P(bull) cao vs…, Tổng quan theo ngành cho lệnh /sector — bao nhiêu mã PASS/WATCH/FAIL mỗi ngành…, Giá + đường trend Kalman + nền tô theo regime (bull/bear). Thay cho biểu đồ nến…, Dải biến động dự báo GARCH quanh giá — tương tự Bollinger Bands về mặt hình ảnh…, Histogram phân phối kết quả mô phỏng Monte Carlo — không có tương đương TA, thể…, Radar 4 trục Growth/Quality/Safety/Valuation (z-score theo ngành, mục 10) —… (+16 more)

### Community 34 - "pandas"
Cohesion: 0.08
Nodes (41): calculate_metric_scores(), get_output_file(), get_scoring_input_file(), _peer_multiplier(), _peer_trend_score(), run_metric_score(), _safety_metric_score(), get_metric_score_file() (+33 more)

### Community 35 - "Hướng dẫn đóng góp"
Cohesion: 0.29
Nodes (6): Chuẩn code, Câu hỏi thường gặp, Hướng dẫn đóng góp, Mở Pull Request, Test, Trước khi bắt đầu một task

### Community 36 - "Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1"
Cohesion: 0.25
Nodes (7): 1. Dữ liệu nợ chi tiết (cho Merton Distance-to-Default), 2. Dữ liệu khối lượng/sự kiện theo ngày (cho Hawkes), 3. Dữ liệu khối ngoại / tự doanh ròng (cho Institutional Flow — nếu làm), 4. BCTC — ngày công bố thực tế (cho point-in-time discipline), 4b. `vnfinancialdata` — có field ngày công bố thật không?, Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1, Kết luận cuối audit

### Community 37 - "Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam"
Cohesion: 0.29
Nodes (6): Backtest, Bắt đầu từ đâu, Chạy pipeline (khi đã có dữ liệu), Cài đặt nhanh, Cấu trúc thư mục, Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam

### Community 38 - "Chiến lược branch & quy trình làm việc"
Cohesion: 0.33
Nodes (5): Chiến lược branch & quy trình làm việc, Quy trình một task điển hình, Quy tắc áp dụng từ dự án này, Review checklist tối thiểu, Vấn đề với 3 branch dài hạn ban đầu

### Community 39 - "PULL_REQUEST_TEMPLATE.md"
Cohesion: 0.33
Nodes (5): Checklist, Cách test, Issue liên quan, Thay đổi gì, Đây là tầng P0 / P1 / P2? (xem docs/ARCHITECTURE.md)

### Community 40 - "Nhật ký quyết định giữ/cắt một tầng (ablation log)"
Cohesion: 0.50
Nodes (3): Log thực tế của nhóm, Mẫu ghi log, Nhật ký quyết định giữ/cắt một tầng (ablation log)

### Community 41 - "get_fundamental_snapshot"
Cohesion: 0.07
Nodes (55): get_financial_data(), get_data(), get_fundamental_snapshot(), get_value(), get_historical_fundamental(), get_output_file(), get_value(), flatten_snapshot() (+47 more)

### Community 42 - "validate_ticker.py"
Cohesion: 0.11
Nodes (25): contextlib, get_latest_reported_financial_data(), Return auditable financial input for valuation. The configured annual source…, _headline_json(), Map layer1 classification results to store/schema.sql record shapes. Does not…, Build headline_json per framework mục 6.1 (headline + supporting flags)., audit_ticker(), _close() (+17 more)

### Community 44 - "FundamentalRefactorTests"
Cohesion: 0.21
Nodes (5): Write only final production outputs; debug frames are opt-in and isolated., _write_debug_frames(), write_run_outputs(), FundamentalRefactorTests, skipUnless

### Community 45 - "select_peer_universe"
Cohesion: 0.30
Nodes (5): _apply_size_filter(), _clean_tickers(), Select one deterministic peer universe and return audit metadata., select_peer_universe(), PeerSelectionTests

### Community 46 - "5. Câu hỏi 4 — Giá cổ phiếu hiện tại có hợp lý không?"
Cohesion: 0.20
Nodes (10): 5.2 Ta đang trả bao nhiêu cho một đồng tài sản ròng?, 5.4 Giá cổ phiếu so với dòng tiền thật thế nào?, 5.5 Giá thị trường có thấp hơn giá trị nội tại không?, 5.6 Hai phép so sánh bắt buộc của Valuation, 5. Câu hỏi 4 — Giá cổ phiếu hiện tại có hợp lý không?, DCF — Discounted Cash Flow, FCF Yield, Margin of Safety (+2 more)

### Community 47 - "Fintech Stock Bot — Fundamental Layer engine (`layer1_engine/`)"
Cohesion: 0.22
Nodes (7): Architecture (repo), Data limitations, Fintech Stock Bot — Fundamental Layer engine (`layer1_engine/`), Outputs, Run, Setup — Windows PowerShell (from repo root), Tests

### Community 48 - "3. Câu hỏi 2 — Doanh nghiệp tạo lợi nhuận có chất lượng và hiệu quả không?"
Cohesion: 0.12
Nodes (16): 3.1 Mỗi đồng doanh thu tạo ra được bao nhiêu lợi nhuận?, 3.2 Mỗi đồng tài sản và vốn tạo ra được bao nhiêu lợi nhuận?, 3.3 ROE cao do doanh nghiệp giỏi hay do vay nợ nhiều?, 3.4 Lợi nhuận có chuyển thành tiền thật không?, 3.5 Lợi nhuận có đến từ hoạt động cốt lõi và có lặp lại được không?, 3. Câu hỏi 2 — Doanh nghiệp tạo lợi nhuận có chất lượng và hiệu quả không?, Accrual Ratio, Cash Conversion (+8 more)

### Community 49 - "Khung chien luoc tich hop - Fundamental Filter  Quant Regime Engine_efa0dec8.md"
Cohesion: 0.17
Nodes (11): 0. Sơ đồ tổng thể: Hai tầng, hai nhịp, 10. Đề xuất phương pháp chấm điểm (giải quyết “chưa đặt ngưỡng”), 15. Framework chốt lại, 16.1 Nền tảng Fundamental, 16.2 Nền tảng Quant (MỚI), 16. Nguồn nền tảng và phạm vi sử dụng, 6.1 Chấm điểm rộng, kể chuyện hẹp — quy tắc “im lặng trừ khi cần giải thích” (MỚI), 6. Phân loại chỉ số để Bot V1 không trở thành “ratio zoo” (+3 more)

### Community 50 - "2. Câu hỏi 1 — Doanh nghiệp có thật sự tăng trưởng không?"
Cohesion: 0.12
Nodes (16): 2.1 Doanh thu hiện tại có tăng không?, 2.2 Lợi nhuận có tăng cùng doanh thu không?, 2.3 EPS có thật sự tăng không?, 2.4 Tăng trưởng có chuyển thành tiền thật không?, 2.5 Tăng trưởng có bền vững hay chỉ là một cú nhảy?, 2. Câu hỏi 1 — Doanh nghiệp có thật sự tăng trưởng không?, CAGR 3Y/5Y, CFO Growth (+8 more)

### Community 51 - "score_current_universe"
Cohesion: 0.14
Nodes (23): Tầng 1 — Fundamental Filter (facade + re-export engine entrypoints). Public…, _as_bool(), classify_fundamental_universe(), get_output_file(), Classify an explicit current-run universe; never scan old artifacts., Classify current-run universe into PASS/WATCH/FAIL (framework mục 10).…, run_fundamental_classification(), Score and classify only the explicitly supplied current-run universe. Pure… (+15 more)

### Community 52 - "9. Từ Fundamental View đến Quant Regime Engine — các điểm nối cụ thể"
Cohesion: 0.22
Nodes (9): 9.1 Cadence: hai vòng lặp độc lập, 9.2 Điểm nối (a): Fundamental Score → Watchlist / Universe, 9.3 Điểm nối (b): Growth + Quality Score → trọng số Alpha, 9.4 Điểm nối (c): Valuation Score → View của Black-Litterman, 9.5 Điểm nối (d): Safety / Merton DD → Risk overlay hằng ngày, 9.6 Ví dụ minh họa xuyên suốt một mã, 9.7 Vị trí của TA cổ điển: không dùng để ra quyết định, chỉ dùng để trình bày (MỚI), 9. Từ Fundamental View đến Quant Regime Engine — các điểm nối cụ thể (+1 more)

### Community 53 - "pathlib"
Cohesion: 0.31
Nodes (8): copy, load_scoring_config(), Any, Path, Load scoring / classification thresholds from pipeline/config.yaml. Maps repo…, Return classification thresholds synced with pipeline/config.yaml. Output keys…, _read_yaml(), pathlib

### Community 54 - "registry.py"
Cohesion: 0.18
Nodes (10): Provider protocols — shared contracts for all vendor adapters., Try providers in config order; skip failures and continue the chain., vnfinancialdata annual BCTC — wraps transitional layer1 financial_data., Vnstock live BCTC adapter — placeholder until field mapping is audited., DNSE price adapter — wraps transitional layer1 I/O until code moves here., Stub price vendors listed in config but not implemented yet., Vnstock price adapter — OHLCV history for Tầng 2 (when deps installed)., Build provider chains from ``pipeline/config.yaml``. (+2 more)

### Community 55 - "trend_analysis.py"
Cohesion: 0.52
Nodes (6): analyze_metric(), classify_change(), get_fundamental_file(), get_output_file(), get_overall_direction(), run_trend_analysis()

### Community 56 - "11. Điều chỉnh triển khai"
Cohesion: 0.33
Nodes (6): 11.1 Phân tầng bắt buộc: P0 / P1 / P2, 11.2 Audit khả thi dữ liệu trước khi code, 11.3 Tiêu chí giữ/cắt một tầng — chốt trước khi chạy ablation, 11.4 Fallback khi thiếu dữ liệu — hành vi cụ thể của bot, 11.5 Cách trình bày trong báo cáo, 11. Điều chỉnh triển khai

### Community 57 - "fundamental_score.py"
Cohesion: 0.70
Nodes (4): get_module_score_file(), get_output_file(), run_fundamental_score(), validate_module_weights()

### Community 58 - "ProviderError"
Cohesion: 0.16
Nodes (11): ProviderError, Raised when a single vendor fails; chain may try the next source., Any, VnFinancialDataStatements, Any, DataFrame, VnstockPriceProvider, Any (+3 more)

### Community 59 - "1. Bức tranh tổng thể của Fundamental Filter: Bot đang cố trả lời điều gì?"
Cohesion: 0.50
Nodes (4): 1.1 Luồng logic của chiến lược, 1.2 Ba nguyên tắc đọc mọi chỉ số, 1.3 Quy tắc chống “double-count”, 1. Bức tranh tổng thể của Fundamental Filter: Bot đang cố trả lời điều gì?

### Community 60 - "13. Bảng công thức nhanh (Quick Reference)"
Cohesion: 0.67
Nodes (3): 13.1 Fundamental Filter, 13.2 Quant Regime Engine, 13. Bảng công thức nhanh (Quick Reference)

### Community 61 - "14. Thuật ngữ cần nhớ"
Cohesion: 0.67
Nodes (3): 14.1 Thuật ngữ Fundamental, 14.2 Thuật ngữ Quant (MỚI), 14. Thuật ngữ cần nhớ

### Community 62 - "dnse_price.py"
Cohesion: 0.15
Nodes (15): base64, dotenv, create_headers(), get_close_price(), get_historical_close_price(), get_live_close_price(), parse_as_of_date(), DNSE close prices. Transitional location: pipeline should call… (+7 more)

### Community 63 - "call_chain"
Cohesion: 0.16
Nodes (10): PriceProvider, Giá/khối lượng — Tầng 2 (+ valuation close cho Tầng 1)., Phân ngành ICB — peer z-score + ``store.sector_mapping``., SectorProvider, call_chain(), Any, Call ``provider.method(*args, **kwargs)`` across the chain. Skips ``None``…, _ChainedPrice (+2 more)

### Community 64 - "financial_data.py"
Cohesion: 0.23
Nodes (11): datetime, get_financial_exchange(), get_value(), Annual BCTC via vnfinancialdata. Transitional location: pipeline should call…, get_kbs_company_data(), check_peer_coverage(), get_error_message(), get_shares_outstanding() (+3 more)

### Community 65 - "FinancialStatementProvider"
Cohesion: 0.16
Nodes (8): FinancialStatementProvider, Any, Close price (+ metadata). ``as_of_date=None`` → live/latest., BCTC — Tầng 1. Prefer point-in-time ``filed_at`` when available., Annual statement fields used by Growth/Quality/Safety/Valuation., Latest published snapshot as of date (PIT). May be incomplete., _ChainedFinancials, Annual BCTC (`FinancialStatementProvider.get_annual`)

### Community 66 - "ratios_valuation.py"
Cohesion: 0.33
Nodes (10): calculate_book_value_per_share(), calculate_enterprise_value(), calculate_ev_to_ebitda(), calculate_fcf_yield(), calculate_market_cap(), calculate_pb(), calculate_total_debt(), get_valuation() (+2 more)

### Community 67 - "peer_coverage_runner.py"
Cohesion: 0.38
Nodes (7): get_industry(), get_coverage_file(), get_selection_file(), run_peer_coverage(), get_peer_group(), truststore, vnstock

### Community 68 - "financials_stubs.py"
Cohesion: 0.31
Nodes (4): CafeFFinancials, Any, Stub BCTC vendors from config chain (CafeF, Vietstock)., VietstockFinancials

### Community 69 - "valuation.py"
Cohesion: 0.25
Nodes (8): calculate_pe(), margin_of_safety(), pe_ratio(), Module Valuation — Câu hỏi 4: Giá cổ phiếu hiện tại có hợp lý không? Tham…, Mục 5.1 — headline metric (so với median 5Y & peer, xem mục 6.1)., Mục 5.5 — (Intrinsic Value - Market Price) / Intrinsic Value. ADVANCED (cần DCF…, Tổng hợp điểm Valuation + trả thêm view_signal cho quant_engine/portfolio/ (xem…, valuation_score()

### Community 70 - "scoring_input.py"
Cohesion: 0.46
Nodes (7): build_scoring_input(), get_historical_percentile_file(), get_output_file(), get_peer_percentile_file(), get_peer_snapshot_file(), get_trend_score_file(), select_metric_values()

### Community 71 - ".get_ohlcv"
Cohesion: 0.29
Nodes (5): DataFrame, Daily OHLCV with columns including ``date``, ``close``, ``volume``. Required…, Data schemas / contracts, Point-in-time, Price OHLCV (`PriceProvider.get_ohlcv`)

### Community 72 - "peer_percentile.py"
Cohesion: 0.60
Nodes (5): calculate_metric_percentile(), get_percentile_file(), get_selection_file(), get_snapshot_file(), run_peer_percentile()

### Community 73 - "DnsePriceProvider"
Cohesion: 0.40
Nodes (3): DnsePriceProvider, Any, DataFrame

### Community 74 - "CafeFPriceProvider"
Cohesion: 0.40
Nodes (3): CafeFPriceProvider, Any, DataFrame

### Community 75 - "historical_percentile.py"
Cohesion: 0.70
Nodes (4): calculate_metric_percentile(), get_fundamental_file(), get_percentile_file(), run_historical_percentile()

### Community 77 - "5.1 Ta đang trả bao nhiêu cho 1 đồng lợi nhuận?"
Cohesion: 0.50
Nodes (4): 5.1 Ta đang trả bao nhiêu cho 1 đồng lợi nhuận?, Earnings Yield, Normalized P/E, P/E

### Community 78 - "5.3 Giá trị toàn doanh nghiệp so với lợi nhuận hoạt động thế nào?"
Cohesion: 0.50
Nodes (4): 5.3 Giá trị toàn doanh nghiệp so với lợi nhuận hoạt động thế nào?, Enterprise Value — biến đầu vào, không phải metric chấm điểm độc lập, EV / EBIT, EV / EBITDA

### Community 79 - "12. Những sai lầm nhóm cần tránh khi triển khai"
Cohesion: 0.67
Nodes (3): 12.1 Nhóm sai lầm ở tầng Fundamental (giữ nguyên từ bản gốc), 12.2 Nhóm sai lầm ở tầng Quant và tại điểm ghép nối (MỚI), 12. Những sai lầm nhóm cần tránh khi triển khai

## Knowledge Gaps
- **142 isolated node(s):** `fundamental_scores`, `subscribers`, `Issue liên quan`, `Thay đổi gì`, `Đây là tầng P0 / P1 / P2? (xem docs/ARCHITECTURE.md)` (+137 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 361 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **17 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `score_current_universe()` connect `score_current_universe` to `pandas`, `repository.py`, `fundamental_engine.py`, `validate_ticker.py`, `FundamentalRefactorTests`, `pathlib`, `fundamental_score.py`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **Why does `get_financial_data()` connect `get_fundamental_snapshot` to `financial_data.py`, `FinancialStatementProvider`, `validate_ticker.py`, `registry.py`, `ProviderError`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Why does `to_store_records()` connect `score_current_universe` to `validate_ticker.py`, `repository.py`, `test_scoring_store.py`?**
  _High betweenness centrality (0.017) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `ProviderError` (e.g. with `VnFinancialDataStatements` and `DnsePriceProvider`) actually correct?**
  _`ProviderError` has 6 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fundamental_scores`, `subscribers`, `Issue liên quan` to the rest of the system?**
  _142 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `repository.py` be split into smaller, more focused modules?**
  _Cohesion score 0.05323653962492438 - nodes in this community are weakly interconnected._
- **Should `4. Câu hỏi 3 — Doanh nghiệp có an toàn tài chính không?` be split into smaller, more focused modules?**
  _Cohesion score 0.08695652173913043 - nodes in this community are weakly interconnected._