# Graph Report - Telegram-bot-for-investment-signal  (2026-09-20)

## Corpus Check
- 45 files · ~8,690 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 10 file(s) not represented in the graph (top: (none) 6, .mdc 2, .example 1)

## Summary
- 281 nodes · 264 edges · 41 communities (28 shown, 13 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 1 edges (avg confidence: 0.95)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `595f1bd6`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- growth.py
- walk_forward.py
- repository.py
- formatters.py
- quality.py
- safety.py
- test_regime.py
- garch.py
- valuation.py
- black_litterman.py
- monte_carlo.py
- hawkes.py
- scoring.py
- kalman_trend.py
- ou_meanrev.py
- schema.sql
- costs.py
- ablation.py
- engine.py
- main.py
- test_integration_smoke.py
- 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần
- charts.py
- Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư
- Hướng dẫn đóng góp
- Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1
- Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam
- Chiến lược branch & quy trình làm việc
- PULL_REQUEST_TEMPLATE.md
- Nhật ký quyết định giữ/cắt một tầng (ablation log)

## God Nodes (most connected - your core abstractions)
1. `4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần` - 10 edges
2. `Hướng dẫn dùng Repo (dành cho người mới dùng Git/GitHub)` - 9 edges
3. `Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư` - 8 edges
4. `Hướng dẫn đóng góp` - 6 edges
5. `Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam` - 6 edges
6. `Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1` - 6 edges
7. `6. Các tình huống hay gặp và cách xử lý` - 6 edges
8. `Chiến lược branch & quy trình làm việc` - 5 edges
9. `get_open_positions()` - 4 edges
10. `render_price_regime_chart()` - 3 edges

## Surprising Connections (you probably didn't know these)
- `Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`)` --references--> `get_open_positions()`  [INFERRED]
  docs/ARCHITECTURE.md → store/repository.py
- `test_revenue_growth_yoy_not_implemented_yet()` --calls--> `revenue_growth_yoy()`  [EXTRACTED]
  fundamental_filter/tests/test_growth.py → fundamental_filter/growth.py
- `test_filtered_regime_probability_not_implemented_yet()` --calls--> `filtered_regime_probability()`  [EXTRACTED]
  quant_engine/tests/test_regime.py → quant_engine/regime.py

## Import Cycles
- None detected.

## Communities (41 total, 13 thin omitted)

### Community 0 - "growth.py"
Cohesion: 0.12
Nodes (15): fundamental_filter, eps_cagr(), growth_score(), growth_spread(), positive_growth_ratio(), Module Growth — Câu hỏi 1: Doanh nghiệp có thật sự tăng trưởng không? Tham…, Mục 2.1 — Revenue Growth YoY = (Rev_t - Rev_t-1) / Rev_t-1., Mục 2.2 — Growth Spread = NPAT Growth - Revenue Growth (chỉ báo chẩn đoán). (+7 more)

### Community 1 - "walk_forward.py"
Cohesion: 0.14
Nodes (6): argparse, Walk-forward validation — train N năm, test M tháng, trượt cửa sổ tới. Tham…, Sinh ra danh sách (train_start, train_end, test_start, test_end)., walk_forward_windows(), Job Tầng 2 — chạy mỗi phiên, sau giờ đóng cửa (~15:00). Luồng: store.watchlist…, Job Tầng 1 — chạy lại mỗi khi có BCTC mới (event-driven, theo quý). Luồng:…

### Community 2 - "repository.py"
Cohesion: 0.13
Nodes (22): Connection, Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`), sqlite3, close_position(), get_active_subscribers(), get_backtest_results(), get_connection(), get_latest_signals() (+14 more)

### Community 3 - "formatters.py"
Cohesion: 0.20
Nodes (9): format_signal_message(), format_ta_reference_block(), Sinh câu giải thích tín hiệu theo quy tắc 'im lặng trừ khi cần giải thích' (mục…, Dịch xác suất regime sang câu dễ hiểu — mục 9.7. Ví dụ: 0.78 -> "thị trường…, Dịch t-stat của slope Kalman sang câu dễ hiểu. Ví dụ: 2.6 -> "xu hướng tăng rõ…, Ghép khối 'Tham khảo thêm' từ các chỉ số TA cổ điển đã tính sẵn (RSI,…, Ghép mẫu tin nhắn đầy đủ theo mục 9.7: BUY — <ticker> | <ngày> Regime: ... (kèm…, translate_kalman_trend() (+1 more)

### Community 4 - "quality.py"
Cohesion: 0.20
Nodes (9): cash_conversion(), dupont_decomposition(), quality_score(), Module Quality — Câu hỏi 2: Lợi nhuận có chất lượng và hiệu quả không? Tham…, Mục 3.2 — ROIC = NOPAT / Invested Capital. Headline metric của module này (mục…, Mục 3.3 — ROE = Net Margin x Asset Turnover x Equity Multiplier. Dùng làm…, Mục 3.4 — Cash Conversion = CFO / NPAT., Tổng hợp điểm Quality — xem mục 10 (percentile theo ngành) và mục 6.1… (+1 more)

### Community 5 - "safety.py"
Cohesion: 0.20
Nodes (9): interest_coverage(), merton_distance_to_default(), net_debt_to_ebitda(), Module Safety — Câu hỏi 3: Doanh nghiệp có an toàn tài chính không? Tham chiếu:…, Mục 4.2 — headline metric của module Safety (xem mục 6.1)., Mục 4.3 — supporting metric, chỉ nói khi Net Debt/EBITDA đang xấu đi., Mục 4.6 (P2, ADVANCED) — Distance-to-Default theo Bharath & Shumway (2008). CHỈ…, Tổng hợp điểm Safety. Đọc… (+1 more)

### Community 6 - "test_regime.py"
Cohesion: 0.22
Nodes (8): quant_engine, filtered_regime_probability(), fit_markov_regime(), Regime — Markov switching trên VN-Index. Tham chiếu: Mục 8 lớp 1 / mục 9 của…, Fit Hidden Markov Model trên lợi nhuận VN-Index. Trả về model đã fit.…, Trả về P(state=k | F_t) CHỈ dùng dữ liệu tới thời điểm t (filtered, không…, Ví dụ test cho module Regime., test_filtered_regime_probability_not_implemented_yet()

### Community 7 - "garch.py"
Cohesion: 0.20
Nodes (9): fit_gjr_garch(), forecast_sigma(), position_size(), GARCH/GJR-GARCH — dự báo biến động có điều kiện. Tham chiếu: mục "Risk" trong…, Fit GJR-GARCH(1,1), trả về model đã fit., Dự báo sigma_hat cho phiên tiếp theo — ghi vào store.signals.sigma_hat., size = min(w_max, sigma_target / sigma_hat)., stop = entry_price * (1 - k * sigma_hat). (+1 more)

### Community 8 - "valuation.py"
Cohesion: 0.25
Nodes (7): margin_of_safety(), pe_ratio(), Module Valuation — Câu hỏi 4: Giá cổ phiếu hiện tại có hợp lý không? Tham…, Mục 5.1 — headline metric (so với median 5Y & peer, xem mục 6.1)., Mục 5.5 — (Intrinsic Value - Market Price) / Intrinsic Value. ADVANCED (cần DCF…, Tổng hợp điểm Valuation + trả thêm view_signal cho quant_engine/portfolio/ (xem…, valuation_score()

### Community 9 - "black_litterman.py"
Cohesion: 0.25
Nodes (7): black_litterman_weights(), build_views(), equal_weight_fallback(), Black-Litterman — phân bổ danh mục kết hợp baseline thị trường + view riêng.…, Ghép view từ Alpha và view từ Valuation thành ma trận P, vector Q, Omega. Xem…, Trả về vector trọng số danh mục theo Black-Litterman., Fallback khi portfolio_black_litterman.enabled = false (mục 11.1, P1 có thể…

### Community 10 - "monte_carlo.py"
Cohesion: 0.25
Nodes (7): cvar(), probability_tp_before_sl(), Monte Carlo (filtered historical simulation) — xác suất hóa tín hiệu. Tham…, Trả về mảng (n_paths, horizon_days) đường giá mô phỏng., % kịch bản chạm TP trước khi chạm SL., Conditional Value at Risk ở mức alpha (CVaR95)., simulate_price_paths()

### Community 11 - "hawkes.py"
Cohesion: 0.29
Nodes (5): crowding_size_multiplier(), fit_hawkes(), Hawkes process — bộ lọc crowding (đám đông tự kích hoạt chính nó). Tham chiếu:…, Ước lượng mu, alpha, beta bằng MLE. Trả về {"mu":.., "alpha":.., "beta":..}., Giảm size khi n tiến gần n_max — xem mục 9.5 (Safety/Merton DD -> risk overlay,…

### Community 12 - "scoring.py"
Cohesion: 0.33
Nodes (5): aggregate_fundamental_view(), Tổng hợp 4 module (Growth/Quality/Safety/Valuation) thành Fundamental View.…, Bước 1 mục 10 — z = (x - median_nganh) / MAD_nganh., Bước 3-4 mục 10 — điểm module -> điểm tổng hợp -> PASS/WATCH/FAIL theo…, zscore_by_sector()

### Community 13 - "kalman_trend.py"
Cohesion: 0.33
Nodes (5): alpha_effective(), fit_kalman_trend(), Kalman filter — ước lượng xu hướng (trend/slope) ẩn dưới nhiễu giá. Tham chiếu:…, Trả về (level, slope, slope_variance) theo thời gian., Mục 9.3 — Alpha_effective = Alpha_raw * f(Growth score, Quality score). f là…

### Community 14 - "ou_meanrev.py"
Cohesion: 0.33
Nodes (5): fit_ou_process(), ou_half_life(), Ornstein-Uhlenbeck mean reversion — dùng khi regime đang đi ngang. Tham chiếu:…, Ước lượng theta, mu, sigma từ chuỗi residual (giá - trend Kalman)., half_life = ln(2) / theta.

### Community 15 - "schema.sql"
Cohesion: 0.25
Nodes (10): backtest_results, fundamental_scores, idx_backtest_scope, idx_positions_status, idx_signals_ticker, idx_watchlist_date, positions, signals (+2 more)

### Community 16 - "costs.py"
Cohesion: 0.40
Nodes (3): is_tradable_at_price_limit(), Chi phí giao dịch thực tế — bắt buộc trong mọi backtest (mục 12.2 sai lầm cần…, False nếu giá đã chạm trần/sàn — coi như không khớp được lệnh.

### Community 17 - "ablation.py"
Cohesion: 0.50
Nodes (3): Ablation study — bật/tắt từng tầng theo pipeline/config.yaml, đo đóng góp biên.…, Chạy backtest lần lượt: baseline -> +layer1 -> +layer1+layer2 -> ... Trả về…, run_ablation()

### Community 18 - "engine.py"
Cohesion: 0.50
Nodes (3): Backtest engine — GỌI LẠI đúng hàm trong fundamental_filter/ và quant_engine/,…, Chạy toàn bộ pipeline (Tầng 1 + Tầng 2) trên dữ liệu lịch sử, tôn trọng point-…, run_backtest()

### Community 32 - "4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần"
Cohesion: 0.08
Nodes (25): 1. Vài khái niệm cần hiểu trước (bằng ví dụ, không phải định nghĩa hàn lâm), 2. Cài đặt — chọn 1 trong 2 cách, 3. Lấy code về máy lần đầu (chỉ làm 1 lần), 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần, 5. Tôi nên sửa file ở đâu?, 6. Các tình huống hay gặp và cách xử lý, 7. Bảng lệnh Git tối thiểu cần nhớ (nếu dùng dòng lệnh), 8. Nếu vẫn bị kẹt (+17 more)

### Community 33 - "charts.py"
Cohesion: 0.17
Nodes (15): Vẽ chart để bot gửi qua Telegram (ảnh PNG, gửi qua sendPhoto). QUAN TRỌNG —…, Giá + đường trend Kalman + nền tô theo regime (bull/bear). Thay cho biểu đồ nến…, Dải biến động dự báo GARCH quanh giá — tương tự Bollinger Bands về mặt hình ảnh…, Histogram phân phối kết quả mô phỏng Monte Carlo — không có tương đương TA, thể…, Radar 4 trục Growth/Quality/Safety/Valuation (z-score theo ngành, mục 10) —…, RSI/EMA/Volume — CHỈ gọi khi người dùng chủ động xin (`/chart <mã> ta`), luôn…, Đọc `equity_curve_json` của framework + 3 baseline (B0/B1/B2) từ bảng…, render_backtest_equity_curve_chart() (+7 more)

### Community 34 - "Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư"
Cohesion: 0.25
Nodes (7): Bảng lệnh bot dự kiến, Bảng `signals` (hợp đồng giao diện giữa Tầng 2 và bot), Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư, Module ↔ người phụ trách (theo phân công đã thống nhất), Nguyên tắc bất biến (không được vi phạm khi code), Phân tầng ưu tiên P0 / P1 / P2, Sơ đồ luồng dữ liệu

### Community 35 - "Hướng dẫn đóng góp"
Cohesion: 0.29
Nodes (6): Chuẩn code, Câu hỏi thường gặp, Hướng dẫn đóng góp, Mở Pull Request, Test, Trước khi bắt đầu một task

### Community 36 - "Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1"
Cohesion: 0.29
Nodes (6): 1. Dữ liệu nợ chi tiết (cho Merton Distance-to-Default), 2. Dữ liệu khối lượng/sự kiện theo ngày (cho Hawkes), 3. Dữ liệu khối ngoại / tự doanh ròng (cho Institutional Flow — nếu làm), 4. BCTC — ngày công bố thực tế (cho point-in-time discipline), Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1, Kết luận cuối audit

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

## Knowledge Gaps
- **55 isolated node(s):** `fundamental_scores`, `subscribers`, `Issue liên quan`, `Thay đổi gì`, `Đây là tầng P0 / P1 / P2? (xem docs/ARCHITECTURE.md)` (+50 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 167 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`)` connect `repository.py` to `Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **Why does `Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư` connect `Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư` to `repository.py`?**
  _High betweenness centrality (0.008) - this node is a cross-community bridge._
- **What connects `fundamental_scores`, `subscribers`, `Issue liên quan` to the rest of the system?**
  _55 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `growth.py` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._
- **Should `walk_forward.py` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._
- **Should `repository.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12648221343873517 - nodes in this community are weakly interconnected._
- **Should `4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần` be split into smaller, more focused modules?**
  _Cohesion score 0.07692307692307693 - nodes in this community are weakly interconnected._