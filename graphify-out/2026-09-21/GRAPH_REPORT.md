# Graph Report - Telegram-bot-for-investment-signal  (2026-09-21)

## Corpus Check
- 131 files · ~60,963 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 11 file(s) not represented in the graph (top: (none) 6, .mdc 2, .example 2)

## Summary
- 1284 nodes · 2764 edges · 98 communities (74 shown, 24 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 79 edges (avg confidence: 0.91)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `5b5840d4`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- price_history.py
- get_connection
- repository.py
- formatters.py
- 4. Câu hỏi 3 — Doanh nghiệp có an toàn tài chính không?
- fundamental_engine.py
- ratios_valuation.py
- signal_engine.py
- compute_year_metrics
- compute_metrics
- test_monte_carlo.py
- valuation_scoring.py
- get_financial_data
- main.py
- sector_job.py
- schema.sql
- test_backtest.py
- ablation.py
- engine.py
- charts.py
- test_integration_smoke.py
- generate_signals
- bot/__init__.py
- FinancialStatementProvider
- pipeline/__init__.py
- regime.py
- 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần
- sync_positions_from_signals
- metric_score.py
- Hướng dẫn đóng góp
- Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1
- Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam
- Chiến lược branch & quy trình làm việc
- PULL_REQUEST_TEMPLATE.md
- ProviderError
- module_score.py
- validate_ticker.py
- test_scoring_frames.py
- test_black_litterman.py
- Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư
- 5. Câu hỏi 4 — Giá cổ phiếu hiện tại có hợp lý không?
- quarterly_job.py
- 3. Câu hỏi 2 — Doanh nghiệp tạo lợi nhuận có chất lượng và hiệu quả không?
- Khung chien luoc tich hop - Fundamental Filter  Quant Regime Engine_efa0dec8.md
- 2. Câu hỏi 1 — Doanh nghiệp có thật sự tăng trưởng không?
- fundamental_metrics.py
- 9. Từ Fundamental View đến Quant Regime Engine — các điểm nối cụ thể
- registry.py
- test_systemic_fundamental.py
- 11. Điều chỉnh triển khai
- test_quarterly_job.py
- VnstockPriceProvider
- dnse_price.py
- ClassificationTests
- growth.py
- vnfinancialdata
- daily_job.py
- SafetyScoringTests
- safety_diagnostics.py
- score_current_universe
- quant_engine
- pandas
- walk_forward.py
- scoring_input.py
- scoring_frames.py
- CafeFFinancials
- test_fundamental_refactor.py
- peer_coverage_runner.py
- VnstockFinancials
- trend_analysis.py
- peer_percentile.py
- peer_snapshot_runner.py
- data/__init__.py
- fundamental_score.py
- quality.py
- dotenv
- httpx
- valuation.py
- 1. DYNAMIC SKILL ROUTER (CRITICAL INSTRUCTION)
- historical_percentile.py
- Nhật ký quyết định giữ/cắt một tầng (ablation log)
- pathlib
- 1. Bức tranh tổng thể của Fundamental Filter: Bot đang cố trả lời điều gì?
- ratios_safety.py
- 12. Những sai lầm nhóm cần tránh khi triển khai
- .get_industry
- truststore
- vnstock

## God Nodes (most connected - your core abstractions)
1. `compute_year_metrics()` - 37 edges
2. `get_fundamental_snapshot()` - 31 edges
3. `get_historical_fundamental()` - 31 edges
4. `compute_metrics()` - 28 edges
5. `score_current_universe()` - 28 edges
6. `generate_signals()` - 28 edges
7. `run_backtest()` - 25 edges
8. `ProviderError` - 25 edges
9. `get_connection()` - 25 edges
10. `build_scoring_frames()` - 24 edges

## Surprising Connections (you probably didn't know these)
- `Point-in-time & BCTC V1` --references--> `calculate_historical_valuation_score()`  [INFERRED]
  docs/ARCHITECTURE.md → fundamental_filter/layer1_engine/valuation_scoring.py
- `Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`)` --references--> `get_open_positions()`  [INFERRED]
  docs/ARCHITECTURE.md → store/repository.py
- `Quyết định V1 (P0 sync — trước Quant)` --references--> `compute_metrics()`  [INFERRED]
  docs/DECISIONS.md → backtest/metrics.py
- `Quyết định V1 (P0 sync — trước Quant)` --references--> `assumed_filed_at()`  [INFERRED]
  docs/DECISIONS.md → data/ingest/pit.py
- `Quyết định V1 (P0 sync — trước Quant)` --references--> `VnFinancialDataStatements`  [INFERRED]
  docs/DECISIONS.md → data/providers/financials_vnfinancialdata.py

## Import Cycles
- None detected.

## Communities (98 total, 24 thin omitted)

### Community 0 - "price_history.py"
Cohesion: 0.10
Nodes (23): cache_ohlcv(), fetch_ohlcv(), fetch_universe_ohlcv(), Any, DataFrame, Path, Series, OHLCV history helper for Tầng 2 — uses ``data.providers`` price chain. (+15 more)

### Community 1 - "get_connection"
Cohesion: 0.17
Nodes (23): test_upsert_backtest_results(), test_sector_job_with_prepared_rows(), test_sector_mapping_upsert_and_overview(), test_backtest_and_sector_charts(), industries_from_sector_mapping(), Prefer ``store.sector_mapping.industry`` (sector_job) over live KBS., test_industries_from_sector_mapping(), industry_to_mapping_row() (+15 more)

### Community 2 - "repository.py"
Cohesion: 0.09
Nodes (31): test_subscribe_helpers(), Connection, test_open_close_position(), sqlite3, close_position(), get_active_subscribers(), get_backtest_results(), get_latest_fundamental_scores() (+23 more)

### Community 3 - "formatters.py"
Cohesion: 0.13
Nodes (25): _fmt_num(), format_backtest_results(), format_positions(), format_regime_message(), format_sector_overview(), format_signal_message(), format_signals_list(), format_status() (+17 more)

### Community 4 - "4. Câu hỏi 3 — Doanh nghiệp có an toàn tài chính không?"
Cohesion: 0.09
Nodes (23): 4.1 Có đủ khả năng thanh toán ngắn hạn không?, 4.2 Doanh nghiệp đang vay nợ nhiều đến mức nào?, 4.3 Doanh nghiệp có đủ sức trả lãi vay không?, 4.4 Dòng tiền có thật sự đủ để hỗ trợ nợ không?, 4.5 Có rủi ro ẩn nào trong bảng cân đối không?, 4.6 Thị trường đang định giá rủi ro vỡ nợ ra sao? — Merton Distance-to-Default (Advanced, MỚI), 4. Câu hỏi 3 — Doanh nghiệp có an toàn tài chính không?, Cash Ratio (+15 more)

### Community 5 - "fundamental_engine.py"
Cohesion: 0.23
Nodes (12): argparse, analyze_fundamental(), analyze_fundamental_universe(), _empty_historical_percentiles(), _normalize_tickers(), Write only final production outputs; debug frames are opt-in and isolated., Run the Fundamental Layer in memory for an explicit ticker universe.…, Backward-compatible single-ticker entry point without stale CSV state. (+4 more)

### Community 6 - "ratios_valuation.py"
Cohesion: 0.11
Nodes (23): parse_as_of_date(), get_latest_reported_financial_data(), Return auditable financial input for valuation. The configured annual source…, aggregate_ttm(), calculate_book_value_per_share(), calculate_enterprise_value(), calculate_ev_to_ebitda(), calculate_fcf() (+15 more)

### Community 7 - "signal_engine.py"
Cohesion: 0.11
Nodes (28): alpha_effective(), Mục 9.3 — Alpha_effective = Alpha_raw * f(Growth, Quality). f is monotone in…, fit_ou_process(), ou_half_life(), Ornstein-Uhlenbeck mean reversion — dùng khi regime đang đi ngang. Tham chiếu:…, Estimate theta, mu, sigma from residual series (price − Kalman level). Discrete…, half_life = ln(2) / theta (sessions). Requires theta > 0., _as_returns() (+20 more)

### Community 8 - "compute_year_metrics"
Cohesion: 0.18
Nodes (29): compute_year_metrics(), Return one wide row of CORE (+ helper) metrics for ``ticker``/``year``., get_fundamental_snapshot(), get_historical_fundamental(), get_output_file(), get_value(), cfo_growth_yoy(), eps_cagr_3_year() (+21 more)

### Community 9 - "compute_metrics"
Cohesion: 0.13
Nodes (25): cagr(), calibrate_cvar95(), calmar_ratio(), compute_metrics(), cvar95_realized(), _equity_series(), max_drawdown(), max_drawdown_days() (+17 more)

### Community 10 - "test_monte_carlo.py"
Cohesion: 0.21
Nodes (14): _as_array(), cvar(), monte_carlo_signal_stats(), probability_tp_before_sl(), ndarray, Convenience wrapper → ``{p_tp_before_sl, cvar95, sl_pct}``., Return array shape (n_paths, horizon_days) of simulated prices., Fraction of paths that hit TP before SL within the horizon. (+6 more)

### Community 11 - "valuation_scoring.py"
Cohesion: 0.22
Nodes (9): normalize_available_weights(), Normalize configured weights over available components only. Multipliers…, validate_weights(), ValuationHybridTests, calculate_historical_valuation_score(), calculate_peer_valuation_score(), calculate_valuation_components(), is_point_in_time_observation() (+1 more)

### Community 12 - "get_financial_data"
Cohesion: 0.18
Nodes (16): fetch_shares(), get_financial_exchange(), _ensure_runtime_deps(), get_financial_data(), get_value(), Annual BCTC via vnfinancialdata. Transitional location: pipeline should call…, _vnf(), get_data() (+8 more)

### Community 13 - "main.py"
Cohesion: 0.11
Nodes (31): bot, build_application(), backtest_cmd(), chart_cmd(), check_cmd(), help_cmd(), positions_cmd(), regime_cmd() (+23 more)

### Community 14 - "sector_job.py"
Cohesion: 0.20
Nodes (10): data_providers, pipeline, load_config(), main(), Path, Job refresh ``store.sector_mapping`` (monthly cadence — config…, Tests for sector_job dry-run., test_sector_job_dry_run() (+2 more)

### Community 15 - "schema.sql"
Cohesion: 0.22
Nodes (12): backtest_results, fundamental_scores, idx_backtest_scope, idx_positions_status, idx_sector_industry, idx_signals_ticker, idx_watchlist_date, positions (+4 more)

### Community 16 - "test_backtest.py"
Cohesion: 0.18
Nodes (16): apply_transaction_costs(), is_tradable_at_price_limit(), Chi phí giao dịch thực tế — bắt buộc trong mọi backtest (mục 12.2). T+2 (không…, Net return after sell tax + round-trip fee (applied once per closed trade)., False nếu giá đã chạm trần/sàn — coi như không khớp được lệnh., _close(), _config(), Series (+8 more)

### Community 17 - "ablation.py"
Cohesion: 0.18
Nodes (13): append_decisions_log(), _buyhold_result(), format_decisions_row(), Any, Path, Ablation study — bật/tắt từng tầng theo pipeline/config.yaml, đo đóng góp biên.…, One markdown table row for docs/DECISIONS.md ablation log., Append ablation summary lines under the decisions log section. (+5 more)

### Community 18 - "engine.py"
Cohesion: 0.14
Nodes (23): buy_cost_fraction(), Half of round-trip fee charged on entry (NAV haircut)., Sell tax + half round-trip fee charged on exit., sell_cost_fraction(), _active_watchlist(), _as_date_index(), _business_days_between(), default_scoring_dates() (+15 more)

### Community 19 - "charts.py"
Cohesion: 0.14
Nodes (39): ChartDataError, _dates_values(), _ensure_out(), _load_backtest_curves(), _parse_equity(), Any, Path, Vẽ chart để bot gửi qua Telegram (ảnh PNG, gửi qua sendPhoto). QUAN TRỌNG —… (+31 more)

### Community 21 - "generate_signals"
Cohesion: 0.14
Nodes (17): fit_kalman_trend(), Return (level, slope, slope_variance) arrays aligned with input. Input: log-…, t-stat of Kalman slope — proxy for trend strength (framework mục 9.7)., slope_tstat(), Quant Regime Engine — Tầng 2 (daily). Pure modules (no network): ``regime``,…, _compute_alpha_pack(), _decide_action(), generate_signals() (+9 more)

### Community 24 - "FinancialStatementProvider"
Cohesion: 0.09
Nodes (15): FinancialStatementProvider, PriceProvider, Any, Giá/khối lượng — Tầng 2 (+ valuation close cho Tầng 1)., Close price (+ metadata). ``as_of_date=None`` → live/latest., BCTC — Tầng 1. Prefer point-in-time ``filed_at`` when available., Annual statement fields used by Growth/Quality/Safety/Valuation., Latest published snapshot as of date (PIT). May be incomplete. (+7 more)

### Community 27 - "regime.py"
Cohesion: 0.24
Nodes (13): _as_series(), filtered_regime_probability(), fit_markov_regime(), fit_or_fallback_regime(), _heuristic_regime_probability(), Any, Series, Regime — Markov switching trên chuỗi lợi nhuận (thường VN-Index). Tham chiếu:… (+5 more)

### Community 32 - "4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần"
Cohesion: 0.08
Nodes (25): 1. Vài khái niệm cần hiểu trước (bằng ví dụ, không phải định nghĩa hàn lâm), 2. Cài đặt — chọn 1 trong 2 cách, 3. Lấy code về máy lần đầu (chỉ làm 1 lần), 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần, 5. Tôi nên sửa file ở đâu?, 6. Các tình huống hay gặp và cách xử lý, 7. Bảng lệnh Git tối thiểu cần nhớ (nếu dùng dòng lệnh), 8. Nếu vẫn bị kẹt (+17 more)

### Community 33 - "sync_positions_from_signals"
Cohesion: 0.33
Nodes (7): main(), Any, Paper-trading sync — ghi/đóng ``store.positions`` từ ``store.signals``. Bot chỉ…, Apply latest signal actions onto OPEN positions. - BUY + no OPEN →…, run(), sync_positions_from_signals(), Tests for paper positions + Merton DD.

### Community 34 - "metric_score.py"
Cohesion: 0.22
Nodes (8): calculate_metric_scores(), get_output_file(), get_scoring_input_file(), _peer_multiplier(), _peer_trend_score(), run_metric_score(), _safety_metric_score(), HistoricalPercentileExclusionTests

### Community 35 - "Hướng dẫn đóng góp"
Cohesion: 0.29
Nodes (6): Chuẩn code, Câu hỏi thường gặp, Hướng dẫn đóng góp, Mở Pull Request, Test, Trước khi bắt đầu một task

### Community 36 - "Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1"
Cohesion: 0.29
Nodes (6): 1. Dữ liệu nợ chi tiết (cho Merton Distance-to-Default), 2. Dữ liệu khối lượng/sự kiện theo ngày (cho Hawkes), 3. Dữ liệu khối ngoại / tự doanh ròng (cho Institutional Flow — nếu làm), 4. BCTC — ngày công bố thực tế (cho point-in-time discipline), 4b. `vnfinancialdata` — có field ngày công bố thật không?, Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1

### Community 37 - "Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam"
Cohesion: 0.29
Nodes (6): Backtest, Bắt đầu từ đâu, Chạy pipeline (khi đã có dữ liệu), Cài đặt nhanh, Cấu trúc thư mục, Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam

### Community 38 - "Chiến lược branch & quy trình làm việc"
Cohesion: 0.33
Nodes (5): Chiến lược branch & quy trình làm việc, Quy trình một task điển hình, Quy tắc áp dụng từ dự án này, Review checklist tối thiểu, Vấn đề với 3 branch dài hạn ban đầu

### Community 39 - "PULL_REQUEST_TEMPLATE.md"
Cohesion: 0.33
Nodes (5): Checklist, Cách test, Issue liên quan, Thay đổi gì, Đây là tầng P0 / P1 / P2? (xem docs/ARCHITECTURE.md)

### Community 40 - "ProviderError"
Cohesion: 0.12
Nodes (19): ProviderError, Raised when a single vendor fails; chain may try the next source., call_chain(), Any, Try providers in config order; skip failures and continue the chain., Call ``provider.method(*args, **kwargs)`` across the chain. Skips ``None``…, Any, VnFinancialDataStatements (+11 more)

### Community 41 - "module_score.py"
Cohesion: 0.28
Nodes (13): get_metric_score_file(), get_output_file(), run_module_score(), validate_module_weights(), calculate_absolute_metric_score(), calculate_safety_components(), get_safety_gate_status(), _is_missing() (+5 more)

### Community 42 - "validate_ticker.py"
Cohesion: 0.24
Nodes (15): audit_ticker(), _close(), _expected_classification(), _fmt(), _formula_check(), _independent_ratios(), _independent_valuation(), _load_debug_frames() (+7 more)

### Community 43 - "test_scoring_frames.py"
Cohesion: 0.22
Nodes (10): is_financial_industry(), True when industry name matches V1 financial exclusion keywords., _annual(), Tests for scoring_frames builder (no network)., ≥4 prior year-end closes + assumed lag → hist valuation available., test_build_scoring_frames_and_score(), test_compute_year_metrics_revenue_growth(), test_exclude_financials_and_industry_peers() (+2 more)

### Community 44 - "test_black_litterman.py"
Cohesion: 0.15
Nodes (23): Quyết định V1 (P0 sync — trước Quant), bl_portfolio_weights(), black_litterman_weights(), build_views(), covariance_from_closes(), equal_weight_fallback(), _market_weights(), DataFrame (+15 more)

### Community 45 - "Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư"
Cohesion: 0.17
Nodes (11): Bảng lệnh bot dự kiến, Bảng `signals` (hợp đồng giao diện giữa Tầng 2 và bot), Chart backtest bổ sung (`bot/charts.py`), Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`), daily_job → subscribers, Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư, Module ↔ người phụ trách (theo phân công đã thống nhất), Nguyên tắc bất biến (không được vi phạm khi code) (+3 more)

### Community 46 - "5. Câu hỏi 4 — Giá cổ phiếu hiện tại có hợp lý không?"
Cohesion: 0.11
Nodes (18): 5.1 Ta đang trả bao nhiêu cho 1 đồng lợi nhuận?, 5.2 Ta đang trả bao nhiêu cho một đồng tài sản ròng?, 5.3 Giá trị toàn doanh nghiệp so với lợi nhuận hoạt động thế nào?, 5.4 Giá cổ phiếu so với dòng tiền thật thế nào?, 5.5 Giá thị trường có thấp hơn giá trị nội tại không?, 5.6 Hai phép so sánh bắt buộc của Valuation, 5. Câu hỏi 4 — Giá cổ phiếu hiện tại có hợp lý không?, DCF — Discounted Cash Flow (+10 more)

### Community 47 - "quarterly_job.py"
Cohesion: 0.25
Nodes (14): Provider interfaces + fallback chains for price / BCTC / sector. Pipeline loads…, get_financial_statement_provider(), get_price_provider(), get_sector_provider(), load_pipeline_config(), Any, Path, ``mode='live'`` uses financial_statements_live.chain; ``mode='backtest'`` uses… (+6 more)

### Community 48 - "3. Câu hỏi 2 — Doanh nghiệp tạo lợi nhuận có chất lượng và hiệu quả không?"
Cohesion: 0.12
Nodes (16): 3.1 Mỗi đồng doanh thu tạo ra được bao nhiêu lợi nhuận?, 3.2 Mỗi đồng tài sản và vốn tạo ra được bao nhiêu lợi nhuận?, 3.3 ROE cao do doanh nghiệp giỏi hay do vay nợ nhiều?, 3.4 Lợi nhuận có chuyển thành tiền thật không?, 3.5 Lợi nhuận có đến từ hoạt động cốt lõi và có lặp lại được không?, 3. Câu hỏi 2 — Doanh nghiệp tạo lợi nhuận có chất lượng và hiệu quả không?, Accrual Ratio, Cash Conversion (+8 more)

### Community 49 - "Khung chien luoc tich hop - Fundamental Filter  Quant Regime Engine_efa0dec8.md"
Cohesion: 0.11
Nodes (17): 0. Sơ đồ tổng thể: Hai tầng, hai nhịp, 10. Đề xuất phương pháp chấm điểm (giải quyết “chưa đặt ngưỡng”), 13.1 Fundamental Filter, 13.2 Quant Regime Engine, 13. Bảng công thức nhanh (Quick Reference), 14.1 Thuật ngữ Fundamental, 14.2 Thuật ngữ Quant (MỚI), 14. Thuật ngữ cần nhớ (+9 more)

### Community 50 - "2. Câu hỏi 1 — Doanh nghiệp có thật sự tăng trưởng không?"
Cohesion: 0.12
Nodes (16): 2.1 Doanh thu hiện tại có tăng không?, 2.2 Lợi nhuận có tăng cùng doanh thu không?, 2.3 EPS có thật sự tăng không?, 2.4 Tăng trưởng có chuyển thành tiền thật không?, 2.5 Tăng trưởng có bền vững hay chỉ là một cú nhảy?, 2. Câu hỏi 1 — Doanh nghiệp có thật sự tăng trưởng không?, CAGR 3Y/5Y, CFO Growth (+8 more)

### Community 51 - "fundamental_metrics.py"
Cohesion: 0.29
Nodes (6): core_metric_names(), _get(), module_for_metric(), Any, Pure metric computation from annual BCTC dicts (no network). Uses…, fundamental_filter_layer1_engine

### Community 52 - "9. Từ Fundamental View đến Quant Regime Engine — các điểm nối cụ thể"
Cohesion: 0.22
Nodes (9): 9.1 Cadence: hai vòng lặp độc lập, 9.2 Điểm nối (a): Fundamental Score → Watchlist / Universe, 9.3 Điểm nối (b): Growth + Quality Score → trọng số Alpha, 9.4 Điểm nối (c): Valuation Score → View của Black-Litterman, 9.5 Điểm nối (d): Safety / Merton DD → Risk overlay hằng ngày, 9.6 Ví dụ minh họa xuyên suốt một mã, 9.7 Vị trí của TA cổ điển: không dùng để ra quyết định, chỉ dùng để trình bày (MỚI), 9. Từ Fundamental View đến Quant Regime Engine — các điểm nối cụ thể (+1 more)

### Community 54 - "registry.py"
Cohesion: 0.11
Nodes (16): Provider protocols — shared contracts for all vendor adapters., Stub BCTC vendors from config chain (CafeF, Vietstock)., vnfinancialdata annual BCTC — wraps transitional layer1 financial_data., Vnstock live BCTC adapter — placeholder until field mapping is audited., DnsePriceProvider, DataFrame, DNSE price adapter — wraps transitional layer1 I/O until code moves here., CafeFPriceProvider (+8 more)

### Community 55 - "test_systemic_fundamental.py"
Cohesion: 0.27
Nodes (5): _apply_size_filter(), _clean_tickers(), Select one deterministic peer universe and return audit metadata., select_peer_universe(), PeerSelectionTests

### Community 56 - "11. Điều chỉnh triển khai"
Cohesion: 0.33
Nodes (6): 11.1 Phân tầng bắt buộc: P0 / P1 / P2, 11.2 Audit khả thi dữ liệu trước khi code, 11.3 Tiêu chí giữ/cắt một tầng — chốt trước khi chạy ablation, 11.4 Fallback khi thiếu dữ liệu — hành vi cụ thể của bot, 11.5 Cách trình bày trong báo cáo, 11. Điều chỉnh triển khai

### Community 57 - "test_quarterly_job.py"
Cohesion: 0.24
Nodes (9): _assumed_lag_days(), Score universe and optionally persist store-shaped records. Provide either…, run(), _annual(), quarterly_job / daily_job hooks., test_quarterly_job_dry_run(), test_quarterly_job_requires_inputs(), test_quarterly_job_run_with_synthetic_frames() (+1 more)

### Community 58 - "VnstockPriceProvider"
Cohesion: 0.50
Nodes (3): Any, DataFrame, VnstockPriceProvider

### Community 59 - "dnse_price.py"
Cohesion: 0.17
Nodes (14): base64, create_headers(), _ensure_runtime_deps(), get_close_price(), get_historical_close_price(), get_live_close_price(), DNSE close prices. Transitional location: pipeline should call…, Return live close or the last close on/before ``as_of_date``. Historical KBS… (+6 more)

### Community 61 - "growth.py"
Cohesion: 0.13
Nodes (17): fundamental_filter, eps_cagr(), growth_score(), growth_spread(), positive_growth_ratio(), Module Growth — Câu hỏi 1: Doanh nghiệp có thật sự tăng trưởng không? Tham…, Mục 2.1 — Revenue Growth YoY = (Rev_t - Rev_t-1) / Rev_t-1., Mục 2.2 — Growth Spread = NPAT Growth - Revenue Growth (chỉ báo chẩn đoán). (+9 more)

### Community 63 - "daily_job.py"
Cohesion: 0.17
Nodes (17): load_config(), load_watchlist_tickers(), main(), _maybe_push_signals(), _pd_to_last_close(), prepare_price_inputs(), Any, Path (+9 more)

### Community 65 - "safety_diagnostics.py"
Cohesion: 0.46
Nodes (7): build_summary(), get_metric_score_file(), get_output_file(), get_relative_position(), get_scoring_input_file(), get_trend_status(), run_safety_diagnostics()

### Community 66 - "score_current_universe"
Cohesion: 0.06
Nodes (46): copy, Tầng 1 — Fundamental Filter (facade + re-export engine entrypoints). Public…, load_scoring_config(), Any, Path, Load scoring / classification thresholds from pipeline/config.yaml. Maps repo…, Return classification thresholds synced with pipeline/config.yaml. Output keys…, _read_yaml() (+38 more)

### Community 68 - "pandas"
Cohesion: 0.16
Nodes (17): numpy, pandas, Kalman filter — ước lượng xu hướng (trend/slope) ẩn dưới nhiễu giá. Tham chiếu:…, branching_ratio(), crowding_size_multiplier(), fit_hawkes(), fit_hawkes_from_returns(), Series (+9 more)

### Community 69 - "walk_forward.py"
Cohesion: 0.24
Nodes (12): test_walk_forward_windows(), _add_months(), _fmt(), main(), _parse(), Any, Walk-forward validation — train N năm, test M tháng, trượt cửa sổ tới. Tham…, Yield (train_start, train_end, test_start, test_end) ISO dates. (+4 more)

### Community 70 - "scoring_input.py"
Cohesion: 0.46
Nodes (7): build_scoring_input(), get_historical_percentile_file(), get_output_file(), get_peer_percentile_file(), get_peer_snapshot_file(), get_trend_score_file(), select_metric_values()

### Community 71 - "scoring_frames.py"
Cohesion: 0.11
Nodes (32): AnnualFetcher, Ingest helpers — prepare frames/series for filter and quant engines., assumed_filed_at(), Return ISO date = period-end (31 Dec ``year``) + ``lag_days``. Used when vendor…, _assign_peer_percentiles(), build_metric_history(), build_scoring_frames(), build_scoring_frames_from_providers() (+24 more)

### Community 72 - "CafeFFinancials"
Cohesion: 0.38
Nodes (3): CafeFFinancials, Any, VietstockFinancials

### Community 73 - "test_fundamental_refactor.py"
Cohesion: 0.17
Nodes (9): contextlib, _headline_json(), Series, Map layer1 classification results to store/schema.sql record shapes. Does not…, Build headline_json per framework mục 6.1 (headline + supporting flags)., io, json, math (+1 more)

### Community 74 - "peer_coverage_runner.py"
Cohesion: 0.29
Nodes (9): _ensure_ssl(), get_industry(), Industry lookup via vnstock KBS. Network deps are lazy so importing this module…, get_coverage_file(), get_selection_file(), run_peer_coverage(), _ensure_ssl(), get_peer_group() (+1 more)

### Community 77 - "trend_analysis.py"
Cohesion: 0.52
Nodes (6): analyze_metric(), classify_change(), get_fundamental_file(), get_output_file(), get_overall_direction(), run_trend_analysis()

### Community 78 - "peer_percentile.py"
Cohesion: 0.60
Nodes (5): calculate_metric_percentile(), get_percentile_file(), get_selection_file(), get_snapshot_file(), run_peer_percentile()

### Community 79 - "peer_snapshot_runner.py"
Cohesion: 0.48
Nodes (6): flatten_snapshot(), get_coverage_file(), get_snapshot_file(), read_eligible_peers(), run_peer_snapshot(), time

### Community 83 - "fundamental_score.py"
Cohesion: 0.70
Nodes (4): get_module_score_file(), get_output_file(), run_fundamental_score(), validate_module_weights()

### Community 84 - "quality.py"
Cohesion: 0.20
Nodes (9): cash_conversion(), dupont_decomposition(), quality_score(), Module Quality — Câu hỏi 2: Lợi nhuận có chất lượng và hiệu quả không? Tham…, Mục 3.2 — ROIC = NOPAT / Invested Capital. Headline metric của module này (mục…, Mục 3.3 — ROE = Net Margin x Asset Turnover x Equity Multiplier. Dùng làm…, Mục 3.4 — Cash Conversion = CFO / NPAT., Tổng hợp điểm Quality — xem mục 10 (percentile theo ngành) và mục 6.1… (+1 more)

### Community 87 - "valuation.py"
Cohesion: 0.25
Nodes (8): calculate_pe(), margin_of_safety(), pe_ratio(), Module Valuation — Câu hỏi 4: Giá cổ phiếu hiện tại có hợp lý không? Tham…, Mục 5.1 — headline metric (so với median 5Y & peer, xem mục 6.1)., Mục 5.5 — (Intrinsic Value - Market Price) / Intrinsic Value. ADVANCED (cần DCF…, Tổng hợp điểm Valuation + trả thêm view_signal cho quant_engine/portfolio/ (xem…, valuation_score()

### Community 88 - "1. DYNAMIC SKILL ROUTER (CRITICAL INSTRUCTION)"
Cohesion: 0.25
Nodes (7): 1. DYNAMIC SKILL ROUTER (CRITICAL INSTRUCTION), 2. CORE VIBE CODING PRINCIPLES, 3. UNIFIED UI CRASH COURSE (For Sponsor Tier), 📝 Analytics & Review, 🧠 Core System & Debugging, 📊 Data & Market, 📈 Trading & Portfolio

### Community 89 - "historical_percentile.py"
Cohesion: 0.70
Nodes (4): calculate_metric_percentile(), get_fundamental_file(), get_percentile_file(), run_historical_percentile()

### Community 90 - "Nhật ký quyết định giữ/cắt một tầng (ablation log)"
Cohesion: 0.50
Nodes (3): Log thực tế của nhóm, Mẫu ghi log, Nhật ký quyết định giữ/cắt một tầng (ablation log)

### Community 91 - "pathlib"
Cohesion: 0.60
Nodes (4): get_analysis_file(), get_output_file(), run_trend_score(), pathlib

### Community 92 - "1. Bức tranh tổng thể của Fundamental Filter: Bot đang cố trả lời điều gì?"
Cohesion: 0.50
Nodes (4): 1.1 Luồng logic của chiến lược, 1.2 Ba nguyên tắc đọc mọi chỉ số, 1.3 Quy tắc chống “double-count”, 1. Bức tranh tổng thể của Fundamental Filter: Bot đang cố trả lời điều gì?

### Community 93 - "ratios_safety.py"
Cohesion: 0.15
Nodes (17): test_safety_edge_cases(), cfo_to_debt(), interest_coverage(), net_debt_to_ebitda(), Net Debt / EBITDA. Non-positive EBITDA: net cash → 0; levered → 99 (gate/score…, EBIT / Interest. Zero/negative interest with positive EBIT → 999 (no burden)., CFO / Debt. Zero debt with positive CFO → 1.0 (top of Safety anchors)., interest_coverage() (+9 more)

### Community 94 - "12. Những sai lầm nhóm cần tránh khi triển khai"
Cohesion: 0.67
Nodes (3): 12.1 Nhóm sai lầm ở tầng Fundamental (giữ nguyên từ bản gốc), 12.2 Nhóm sai lầm ở tầng Quant và tại điểm ghép nối (MỚI), 12. Những sai lầm nhóm cần tránh khi triển khai

## Knowledge Gaps
- **148 isolated node(s):** `fundamental_scores`, `subscribers`, `Issue liên quan`, `Thay đổi gì`, `Đây là tầng P0 / P1 / P2? (xem docs/ARCHITECTURE.md)` (+143 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 476 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `compute_year_metrics()` connect `compute_year_metrics` to `ratios_valuation.py`, `scoring_frames.py`, `test_scoring_frames.py`, `fundamental_metrics.py`, `valuation.py`, `ratios_safety.py`?**
  _High betweenness centrality (0.036) - this node is a cross-community bridge._
- **Why does `score_current_universe()` connect `score_current_universe` to `price_history.py`, `metric_score.py`, `fundamental_engine.py`, `module_score.py`, `test_fundamental_refactor.py`, `test_scoring_frames.py`, `test_black_litterman.py`, `quarterly_job.py`, `engine.py`, `fundamental_score.py`, `test_quarterly_job.py`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `PriceProvider` connect `FinancialStatementProvider` to `price_history.py`, `registry.py`, `quarterly_job.py`?**
  _High betweenness centrality (0.021) - this node is a cross-community bridge._
- **What connects `fundamental_scores`, `subscribers`, `Issue liên quan` to the rest of the system?**
  _148 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `price_history.py` be split into smaller, more focused modules?**
  _Cohesion score 0.10256410256410256 - nodes in this community are weakly interconnected._
- **Should `repository.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09475806451612903 - nodes in this community are weakly interconnected._
- **Should `formatters.py` be split into smaller, more focused modules?**
  _Cohesion score 0.13230769230769232 - nodes in this community are weakly interconnected._