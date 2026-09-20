# Graph Report - Telegram-bot-for-investment-signal  (2026-09-20)

## Corpus Check
- cluster-only mode — file stats not available

## Summary
- 178 nodes · 155 edges · 32 communities (19 shown, 13 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `14b11132`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- Community 0
- Community 1
- Community 2
- Community 3
- Community 4
- Community 5
- Community 6
- Community 7
- Community 8
- Community 9
- Community 10
- Community 11
- Community 12
- Community 13
- Community 14
- Community 15
- Community 16
- Community 17
- Community 18
- Community 19
- Community 20

## God Nodes (most connected - your core abstractions)
1. `revenue_growth_yoy()` - 3 edges
2. `get_latest_signals()` - 3 edges
3. `upsert_signal()` - 3 edges
4. `filtered_regime_probability()` - 3 edges
5. `eps_cagr()` - 2 edges
6. `growth_score()` - 2 edges
7. `growth_spread()` - 2 edges
8. `positive_growth_ratio()` - 2 edges
9. `test_revenue_growth_yoy_not_implemented_yet()` - 2 edges
10. `walk_forward_windows()` - 2 edges

## Surprising Connections (you probably didn't know these)
- `test_revenue_growth_yoy_not_implemented_yet()` --calls--> `revenue_growth_yoy()`  [EXTRACTED]
  fundamental_filter/tests/test_growth.py → fundamental_filter/growth.py
- `test_filtered_regime_probability_not_implemented_yet()` --calls--> `filtered_regime_probability()`  [EXTRACTED]
  quant_engine/tests/test_regime.py → quant_engine/regime.py

## Import Cycles
- None detected.

## Communities (32 total, 13 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.12
Nodes (15): fundamental_filter, eps_cagr(), growth_score(), growth_spread(), positive_growth_ratio(), Module Growth — Câu hỏi 1: Doanh nghiệp có thật sự tăng trưởng không? Tham…, Mục 2.1 — Revenue Growth YoY = (Rev_t - Rev_t-1) / Rev_t-1., Mục 2.2 — Growth Spread = NPAT Growth - Revenue Growth (chỉ báo chẩn đoán). (+7 more)

### Community 1 - "Community 1"
Cohesion: 0.14
Nodes (6): argparse, Walk-forward validation — train N năm, test M tháng, trượt cửa sổ tới. Tham…, Sinh ra danh sách (train_start, train_end, test_start, test_end)., walk_forward_windows(), Job Tầng 2 — chạy mỗi phiên, sau giờ đóng cửa (~15:00). Luồng: store.watchlist…, Job Tầng 1 — chạy lại mỗi khi có BCTC mới (event-driven, theo quý). Luồng:…

### Community 2 - "Community 2"
Cohesion: 0.23
Nodes (11): Connection, pathlib, sqlite3, get_connection(), get_latest_signals(), get_watchlist(), init_schema(), Lớp truy cập dữ liệu cho store/schema.sql — cả pipeline lẫn bot đều đi qua đây,… (+3 more)

### Community 3 - "Community 3"
Cohesion: 0.20
Nodes (9): format_signal_message(), format_ta_reference_block(), Sinh câu giải thích tín hiệu theo quy tắc 'im lặng trừ khi cần giải thích' (mục…, Dịch xác suất regime sang câu dễ hiểu — mục 9.7. Ví dụ: 0.78 -> "thị trường…, Dịch t-stat của slope Kalman sang câu dễ hiểu. Ví dụ: 2.6 -> "xu hướng tăng rõ…, Ghép khối 'Tham khảo thêm' từ các chỉ số TA cổ điển đã tính sẵn (RSI,…, Ghép mẫu tin nhắn đầy đủ theo mục 9.7: BUY — <ticker> | <ngày> Regime: ... (kèm…, translate_kalman_trend() (+1 more)

### Community 4 - "Community 4"
Cohesion: 0.20
Nodes (9): cash_conversion(), dupont_decomposition(), quality_score(), Module Quality — Câu hỏi 2: Lợi nhuận có chất lượng và hiệu quả không? Tham…, Mục 3.2 — ROIC = NOPAT / Invested Capital. Headline metric của module này (mục…, Mục 3.3 — ROE = Net Margin x Asset Turnover x Equity Multiplier. Dùng làm…, Mục 3.4 — Cash Conversion = CFO / NPAT., Tổng hợp điểm Quality — xem mục 10 (percentile theo ngành) và mục 6.1… (+1 more)

### Community 5 - "Community 5"
Cohesion: 0.20
Nodes (9): interest_coverage(), merton_distance_to_default(), net_debt_to_ebitda(), Module Safety — Câu hỏi 3: Doanh nghiệp có an toàn tài chính không? Tham chiếu:…, Mục 4.2 — headline metric của module Safety (xem mục 6.1)., Mục 4.3 — supporting metric, chỉ nói khi Net Debt/EBITDA đang xấu đi., Mục 4.6 (P2, ADVANCED) — Distance-to-Default theo Bharath & Shumway (2008). CHỈ…, Tổng hợp điểm Safety. Đọc… (+1 more)

### Community 6 - "Community 6"
Cohesion: 0.22
Nodes (8): quant_engine, filtered_regime_probability(), fit_markov_regime(), Regime — Markov switching trên VN-Index. Tham chiếu: Mục 8 lớp 1 / mục 9 của…, Fit Hidden Markov Model trên lợi nhuận VN-Index. Trả về model đã fit.…, Trả về P(state=k | F_t) CHỈ dùng dữ liệu tới thời điểm t (filtered, không…, Ví dụ test cho module Regime., test_filtered_regime_probability_not_implemented_yet()

### Community 7 - "Community 7"
Cohesion: 0.20
Nodes (9): fit_gjr_garch(), forecast_sigma(), position_size(), GARCH/GJR-GARCH — dự báo biến động có điều kiện. Tham chiếu: mục "Risk" trong…, Fit GJR-GARCH(1,1), trả về model đã fit., Dự báo sigma_hat cho phiên tiếp theo — ghi vào store.signals.sigma_hat., size = min(w_max, sigma_target / sigma_hat)., stop = entry_price * (1 - k * sigma_hat). (+1 more)

### Community 8 - "Community 8"
Cohesion: 0.25
Nodes (7): margin_of_safety(), pe_ratio(), Module Valuation — Câu hỏi 4: Giá cổ phiếu hiện tại có hợp lý không? Tham…, Mục 5.1 — headline metric (so với median 5Y & peer, xem mục 6.1)., Mục 5.5 — (Intrinsic Value - Market Price) / Intrinsic Value. ADVANCED (cần DCF…, Tổng hợp điểm Valuation + trả thêm view_signal cho quant_engine/portfolio/ (xem…, valuation_score()

### Community 9 - "Community 9"
Cohesion: 0.25
Nodes (7): black_litterman_weights(), build_views(), equal_weight_fallback(), Black-Litterman — phân bổ danh mục kết hợp baseline thị trường + view riêng.…, Ghép view từ Alpha và view từ Valuation thành ma trận P, vector Q, Omega. Xem…, Trả về vector trọng số danh mục theo Black-Litterman., Fallback khi portfolio_black_litterman.enabled = false (mục 11.1, P1 có thể…

### Community 10 - "Community 10"
Cohesion: 0.25
Nodes (7): cvar(), probability_tp_before_sl(), Monte Carlo (filtered historical simulation) — xác suất hóa tín hiệu. Tham…, Trả về mảng (n_paths, horizon_days) đường giá mô phỏng., % kịch bản chạm TP trước khi chạm SL., Conditional Value at Risk ở mức alpha (CVaR95)., simulate_price_paths()

### Community 11 - "Community 11"
Cohesion: 0.29
Nodes (5): crowding_size_multiplier(), fit_hawkes(), Hawkes process — bộ lọc crowding (đám đông tự kích hoạt chính nó). Tham chiếu:…, Ước lượng mu, alpha, beta bằng MLE. Trả về {"mu":.., "alpha":.., "beta":..}., Giảm size khi n tiến gần n_max — xem mục 9.5 (Safety/Merton DD -> risk overlay,…

### Community 12 - "Community 12"
Cohesion: 0.33
Nodes (5): aggregate_fundamental_view(), Tổng hợp 4 module (Growth/Quality/Safety/Valuation) thành Fundamental View.…, Bước 1 mục 10 — z = (x - median_nganh) / MAD_nganh., Bước 3-4 mục 10 — điểm module -> điểm tổng hợp -> PASS/WATCH/FAIL theo…, zscore_by_sector()

### Community 13 - "Community 13"
Cohesion: 0.33
Nodes (5): alpha_effective(), fit_kalman_trend(), Kalman filter — ước lượng xu hướng (trend/slope) ẩn dưới nhiễu giá. Tham chiếu:…, Trả về (level, slope, slope_variance) theo thời gian., Mục 9.3 — Alpha_effective = Alpha_raw * f(Growth score, Quality score). f là…

### Community 14 - "Community 14"
Cohesion: 0.33
Nodes (5): fit_ou_process(), ou_half_life(), Ornstein-Uhlenbeck mean reversion — dùng khi regime đang đi ngang. Tham chiếu:…, Ước lượng theta, mu, sigma từ chuỗi residual (giá - trend Kalman)., half_life = ln(2) / theta.

### Community 15 - "Community 15"
Cohesion: 0.47
Nodes (5): fundamental_scores, idx_signals_ticker, idx_watchlist_date, signals, watchlist

### Community 16 - "Community 16"
Cohesion: 0.40
Nodes (3): is_tradable_at_price_limit(), Chi phí giao dịch thực tế — bắt buộc trong mọi backtest (mục 12.2 sai lầm cần…, False nếu giá đã chạm trần/sàn — coi như không khớp được lệnh.

### Community 17 - "Community 17"
Cohesion: 0.50
Nodes (3): Ablation study — bật/tắt từng tầng theo pipeline/config.yaml, đo đóng góp biên.…, Chạy backtest lần lượt: baseline -> +layer1 -> +layer1+layer2 -> ... Trả về…, run_ablation()

### Community 18 - "Community 18"
Cohesion: 0.50
Nodes (3): Backtest engine — GỌI LẠI đúng hàm trong fundamental_filter/ và quant_engine/,…, Chạy toàn bộ pipeline (Tầng 1 + Tầng 2) trên dữ liệu lịch sử, tôn trọng point-…, run_backtest()

## Knowledge Gaps
- **1 isolated node(s):** `fundamental_scores`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 95 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **13 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **What connects `fundamental_scores` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Community 0` be split into smaller, more focused modules?**
  _Cohesion score 0.125 - nodes in this community are weakly interconnected._
- **Should `Community 1` be split into smaller, more focused modules?**
  _Cohesion score 0.14285714285714285 - nodes in this community are weakly interconnected._