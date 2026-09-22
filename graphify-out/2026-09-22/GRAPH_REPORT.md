# Graph Report - Telegram-bot-for-investment-signal  (2026-09-22)

## Corpus Check
- 144 files · ~165,627 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 15 file(s) not represented in the graph (top: (none) 6, .csv 4, .mdc 2)

## Summary
- 1377 nodes · 3229 edges · 94 communities (70 shown, 24 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 102 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `365296ed`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- price_history.py
- metric_score.py
- test_regime.py
- validate_ticker.py
- formatters.py
- fundamental_engine.py
- sector_job.py
- test_providers.py
- compute_year_metrics
- compute_metrics
- pandas
- peer_coverage_runner.py
- dnse_price.py
- FinancialStatementProvider
- test_valuation_point_in_time.py
- schema.sql
- test_backtest.py
- ablation.py
- engine.py
- main.py
- test_integration_smoke.py
- test_universe.py
- bot/__init__.py
- test_quarterly_job.py
- pipeline/__init__.py
- fit_or_fallback_regime
- 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần
- module_score.py
- daily_job.py
- Hướng dẫn đóng góp
- Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1
- Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam
- Chiến lược branch & quy trình làm việc
- PULL_REQUEST_TEMPLATE.md
- to_store_records
- signal_engine.py
- SafetyScoringTests
- argparse
- test_black_litterman.py
- peer_coverage.py
- test_paper_positions.py
- quarterly_job.py
- Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư
- Quyết định V1 (P0 sync — trước Quant)
- test_scoring_frames.py
- load_scoring_config
- repository.py
- typing
- score_current_universe
- test_systemic_fundamental.py
- safety_diagnostics.py
- ClassificationTests
- scoring_input.py
- VnstockPriceProvider
- growth.py
- vnfinancialdata
- quality.py
- valuation.py
- trend_analysis.py
- peer_percentile.py
- quant_engine
- test_hawkes.py
- walk_forward.py
- scoring_frames.py
- financials_stubs.py
- VnstockFinancials
- historical_percentile.py
- ratios_valuation.py
- select_peer_universe
- pathlib
- Fintech Stock Bot — Fundamental Layer engine (`layer1_engine/`)
- data/__init__.py
- get_financial_data
- Log thực tế của nhóm
- dotenv
- httpx
- _b1_ta_result
- 1. DYNAMIC SKILL ROUTER (CRITICAL INSTRUCTION)
- peer_snapshot_runner.py
- fundamental_score.py
- upsert_signals
- truststore
- vnstock

## God Nodes (most connected - your core abstractions)
1. `compute_year_metrics()` - 37 edges
2. `build_application()` - 34 edges
3. `compute_metrics()` - 32 edges
4. `get_connection()` - 32 edges
5. `get_fundamental_snapshot()` - 31 edges
6. `get_historical_fundamental()` - 31 edges
7. `init_schema()` - 29 edges
8. `score_current_universe()` - 28 edges
9. `generate_signals()` - 28 edges
10. `run_backtest()` - 26 edges

## Surprising Connections (you probably didn't know these)
- `Wire thêm metrics/charts tầng 2 từ schema + charts.py (2026-09-22)` --references--> `compute_metrics()`  [INFERRED]
  docs/DECISIONS.md → backtest/metrics.py
- `Point-in-time & BCTC V1` --references--> `calculate_historical_valuation_score()`  [INFERRED]
  docs/ARCHITECTURE.md → fundamental_filter/layer1_engine/valuation_scoring.py
- `UX plain + ngành + tích lũy data tầng 2 (2026-09-22)` --references--> `apply_sector_overrides()`  [INFERRED]
  docs/DECISIONS.md → pipeline/sector_job.py
- `Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`)` --references--> `get_open_positions()`  [INFERRED]
  docs/ARCHITECTURE.md → store/repository.py
- `Quyết định V1 (P0 sync — trước Quant)` --references--> `_set_quant_flags()`  [INFERRED]
  docs/DECISIONS.md → backtest/ablation.py

## Import Cycles
- None detected.

## Communities (94 total, 24 thin omitted)

### Community 0 - "price_history.py"
Cohesion: 0.10
Nodes (37): data_ingest, cache_ohlcv(), cache_ohlcv_enabled(), cache_ohlcv_path(), fetch_ohlcv(), fetch_universe_ohlcv(), load_cached_ohlcv(), _price_cfg() (+29 more)

### Community 1 - "metric_score.py"
Cohesion: 0.16
Nodes (10): calculate_metric_scores(), get_output_file(), get_scoring_input_file(), _peer_multiplier(), _peer_trend_score(), run_metric_score(), _safety_metric_score(), normalize_available_weights() (+2 more)

### Community 2 - "test_regime.py"
Cohesion: 0.13
Nodes (24): alpha_effective(), fit_kalman_trend(), Kalman filter — ước lượng xu hướng (trend/slope) ẩn dưới nhiễu giá. Tham chiếu:…, Return (level, slope, slope_variance) arrays aligned with input. Input: log-…, t-stat of Kalman slope — proxy for trend strength (framework mục 9.7)., Mục 9.3 — Alpha_effective = Alpha_raw * f(Growth, Quality). f is monotone in…, slope_tstat(), fit_ou_process() (+16 more)

### Community 3 - "validate_ticker.py"
Cohesion: 0.24
Nodes (15): audit_ticker(), _close(), _expected_classification(), _fmt(), _formula_check(), _independent_ratios(), _independent_valuation(), _load_debug_frames() (+7 more)

### Community 4 - "formatters.py"
Cohesion: 0.07
Nodes (54): _data_gap_note(), _fmt_day_vi(), _fmt_metric_value(), _fmt_num(), _fmt_pct(), format_backtest_results(), format_check_unavailable(), format_help() (+46 more)

### Community 5 - "fundamental_engine.py"
Cohesion: 0.19
Nodes (14): analyze_fundamental(), analyze_fundamental_universe(), _empty_historical_percentiles(), _normalize_tickers(), Write only final production outputs; debug frames are opt-in and isolated., Run the Fundamental Layer in memory for an explicit ticker universe.…, Backward-compatible single-ticker entry point without stale CSV state., _write_debug_frames() (+6 more)

### Community 6 - "sector_job.py"
Cohesion: 0.12
Nodes (28): Tests for sector_mapping + bot formatters (no Telegram network)., test_sector_overrides_applied(), enrich_industry_info_with_exchange(), load_symbol_exchange_map(), Any, Tra cứu sàn HOSE/HNX/UPCOM (live via vnstock Listing) — chỉ gọi từ pipeline I/O., Map ticker → HOSE|HNX|UPCOM từ vnstock Listing (một lần / process).…, Gắn ``exchange``/``market`` đã chuẩn hoá vào payload industry (nếu thiếu). (+20 more)

### Community 7 - "test_providers.py"
Cohesion: 0.18
Nodes (11): call_chain(), Any, Call ``provider.method(*args, **kwargs)`` across the chain. Skips ``None``…, _ChainedFinancials, _FailClose, _NoneClose, _OkClose, Tests for data provider registry + chain (no network required). (+3 more)

### Community 8 - "compute_year_metrics"
Cohesion: 0.16
Nodes (30): compute_year_metrics(), _get(), Any, Pure metric computation from annual BCTC dicts (no network). Uses…, Return one wide row of CORE (+ helper) metrics for ``ticker``/``year``., get_fundamental_snapshot(), get_historical_fundamental(), get_output_file() (+22 more)

### Community 9 - "compute_metrics"
Cohesion: 0.15
Nodes (23): cagr(), calibrate_cvar95(), calmar_ratio(), compute_metrics(), cvar95_realized(), _equity_series(), max_drawdown(), max_drawdown_days() (+15 more)

### Community 10 - "pandas"
Cohesion: 0.14
Nodes (20): math, numpy, pandas, Ornstein-Uhlenbeck mean reversion — dùng khi regime đang đi ngang. Tham chiếu:…, _as_array(), cvar(), monte_carlo_signal_stats(), probability_tp_before_sl() (+12 more)

### Community 11 - "peer_coverage_runner.py"
Cohesion: 0.26
Nodes (10): _ensure_ssl(), get_industry(), Industry lookup via vnstock KBS. Network deps are lazy so importing this module…, get_coverage_file(), get_selection_file(), run_peer_coverage(), _ensure_ssl(), get_peer_group() (+2 more)

### Community 12 - "dnse_price.py"
Cohesion: 0.17
Nodes (15): base64, create_headers(), _ensure_runtime_deps(), get_close_price(), get_historical_close_price(), get_live_close_price(), parse_as_of_date(), DNSE close prices. Transitional location: pipeline should call… (+7 more)

### Community 13 - "FinancialStatementProvider"
Cohesion: 0.07
Nodes (20): FinancialStatementProvider, PriceProvider, Any, DataFrame, Giá/khối lượng — Tầng 2 (+ valuation close cho Tầng 1)., Close price (+ metadata). ``as_of_date=None`` → live/latest., Daily OHLCV with columns including ``date``, ``close``, ``volume``. Required…, BCTC — Tầng 1. Prefer point-in-time ``filed_at`` when available. (+12 more)

### Community 14 - "test_valuation_point_in_time.py"
Cohesion: 0.15
Nodes (8): aggregate_ttm(), Return the newest record that was public on the requested date., Aggregate four consecutive, already-published quarters into TTM data., select_latest_published_financial(), _to_date(), ValuationPointInTimeTests, patch, unittest_mock

### Community 15 - "schema.sql"
Cohesion: 0.19
Nodes (14): backtest_results, fundamental_scores, idx_backtest_scope, idx_positions_status, idx_price_bars_ticker_date, idx_sector_industry, idx_signals_ticker, idx_watchlist_date (+6 more)

### Community 16 - "test_backtest.py"
Cohesion: 0.14
Nodes (18): apply_transaction_costs(), Net return after sell tax + round-trip fee (applied once per closed trade)., _close(), _config(), Series, Backtest P0 tests — synthetic prices, no network., regime layer must disable alpha; alpha/risk enable it., generate_signals must only see closes on or before as_of_date. (+10 more)

### Community 17 - "ablation.py"
Cohesion: 0.11
Nodes (43): ablation_payload_to_store_rows(), append_decisions_log(), _assumed_lag_days(), _benchmark_ticker(), build_scoring_schedule(), _buyhold_result(), decide_keep_cut(), _equity_curve_json() (+35 more)

### Community 18 - "engine.py"
Cohesion: 0.15
Nodes (22): buy_cost_fraction(), is_tradable_at_price_limit(), Chi phí giao dịch thực tế — bắt buộc trong mọi backtest (mục 12.2). T+2 (không…, Half of round-trip fee charged on entry (NAV haircut)., Sell tax + half round-trip fee charged on exit., False nếu giá đã chạm trần/sàn — coi như không khớp được lệnh., sell_cost_fraction(), _active_watchlist() (+14 more)

### Community 19 - "main.py"
Cohesion: 0.07
Nodes (74): bot, ChartDataError, _dates_values(), _ensure_out(), _load_backtest_curves(), _parse_equity(), Any, Path (+66 more)

### Community 21 - "test_universe.py"
Cohesion: 0.12
Nodes (24): Universe CSV loader tests (no network)., test_filter_tickers_drops_upcom_keeps_hose_and_unmapped(), test_load_hose_liquid_35(), test_load_universe_missing_file(), test_load_universe_tickers_comments(), test_load_universe_tickers_sample(), test_normalize_exchange_aliases(), test_resolve_tickers_prefers_cli() (+16 more)

### Community 24 - "test_quarterly_job.py"
Cohesion: 0.15
Nodes (14): main(), test_bot_dry_run(), _assumed_lag_days(), Score universe and optionally persist store-shaped records. Provide either…, run(), _annual(), quarterly_job / daily_job hooks., test_quarterly_job_dry_run() (+6 more)

### Community 27 - "fit_or_fallback_regime"
Cohesion: 0.24
Nodes (12): _as_series(), filtered_regime_probability(), fit_markov_regime(), fit_or_fallback_regime(), _heuristic_regime_probability(), Any, Series, Fit Markov when series is long enough; otherwise heuristic probs only. (+4 more)

### Community 32 - "4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần"
Cohesion: 0.08
Nodes (25): 1. Vài khái niệm cần hiểu trước (bằng ví dụ, không phải định nghĩa hàn lâm), 2. Cài đặt — chọn 1 trong 2 cách, 3. Lấy code về máy lần đầu (chỉ làm 1 lần), 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần, 5. Tôi nên sửa file ở đâu?, 6. Các tình huống hay gặp và cách xử lý, 7. Bảng lệnh Git tối thiểu cần nhớ (nếu dùng dòng lệnh), 8. Nếu vẫn bị kẹt (+17 more)

### Community 33 - "module_score.py"
Cohesion: 0.26
Nodes (14): get_metric_score_file(), get_output_file(), run_module_score(), validate_module_weights(), calculate_absolute_metric_score(), calculate_safety_components(), get_safety_gate_status(), _is_missing() (+6 more)

### Community 34 - "daily_job.py"
Cohesion: 0.12
Nodes (26): backfill_from_store(), bars_from_price_inputs(), _closes_from_store(), load_config(), load_watchlist_tickers(), main(), _maybe_push_signals(), _pd_to_last_close() (+18 more)

### Community 35 - "Hướng dẫn đóng góp"
Cohesion: 0.29
Nodes (6): Chuẩn code, Câu hỏi thường gặp, Hướng dẫn đóng góp, Mở Pull Request, Test, Trước khi bắt đầu một task

### Community 36 - "Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1"
Cohesion: 0.29
Nodes (6): 1. Dữ liệu nợ chi tiết (cho Merton Distance-to-Default), 2. Dữ liệu khối lượng/sự kiện theo ngày (cho Hawkes), 3. Dữ liệu khối ngoại / tự doanh ròng (cho Institutional Flow — nếu làm), 4. BCTC — ngày công bố thực tế (cho point-in-time discipline), 4b. `vnfinancialdata` — có field ngày công bố thật không?, Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1

### Community 37 - "Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam"
Cohesion: 0.22
Nodes (8): Backtest, Bắt đầu từ đâu, Chạy live (ops), Chạy pipeline (khi đã có dữ liệu), Cài đặt nhanh, Cấu trúc thư mục, Lịch Windows (sau đóng cửa), Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam

### Community 38 - "Chiến lược branch & quy trình làm việc"
Cohesion: 0.33
Nodes (5): Chiến lược branch & quy trình làm việc, Quy trình một task điển hình, Quy tắc áp dụng từ dự án này, Review checklist tối thiểu, Vấn đề với 3 branch dài hạn ban đầu

### Community 39 - "PULL_REQUEST_TEMPLATE.md"
Cohesion: 0.33
Nodes (5): Checklist, Cách test, Issue liên quan, Thay đổi gì, Đây là tầng P0 / P1 / P2? (xem docs/ARCHITECTURE.md)

### Community 40 - "to_store_records"
Cohesion: 0.13
Nodes (20): fundamental_filter_layer1_engine, _finite(), _headline_json(), _is_abnormal(), latest_raw_metrics(), Any, DataFrame, Series (+12 more)

### Community 41 - "signal_engine.py"
Cohesion: 0.13
Nodes (21): Quant Regime Engine — Tầng 2 (daily). Pure modules (no network): ``regime``,…, _as_returns(), fit_gjr_garch(), fit_or_fallback_sigma(), forecast_sigma(), position_size(), Series, GARCH/GJR-GARCH — dự báo biến động có điều kiện. Tham chiếu: mục "Risk" trong… (+13 more)

### Community 43 - "argparse"
Cohesion: 0.18
Nodes (13): argparse, main(), Any, Paper-trading sync — ghi/đóng ``store.positions`` từ ``store.signals``. Bot chỉ…, Apply latest signal actions onto OPEN positions. - BUY + no OPEN →…, run(), sync_positions_from_signals(), close_position() (+5 more)

### Community 44 - "test_black_litterman.py"
Cohesion: 0.16
Nodes (22): bl_portfolio_weights(), black_litterman_weights(), build_views(), covariance_from_closes(), equal_weight_fallback(), _market_weights(), DataFrame, ndarray (+14 more)

### Community 45 - "peer_coverage.py"
Cohesion: 0.29
Nodes (9): fetch_shares(), get_financial_exchange(), _ensure_ssl(), get_kbs_company_data(), KBS company profile via vnstock (shares outstanding). Network deps are lazy so…, check_peer_coverage(), get_error_message(), get_shares_outstanding() (+1 more)

### Community 46 - "test_paper_positions.py"
Cohesion: 0.14
Nodes (18): test_safety_edge_cases(), cfo_to_debt(), interest_coverage(), net_debt_to_ebitda(), Net Debt / EBITDA. Non-positive EBITDA: net cash → 0; levered → 99 (gate/score…, EBIT / Interest. Zero/negative interest with positive EBIT → 999 (no burden)., CFO / Debt. Zero debt with positive CFO → 1.0 (top of Safety anchors)., interest_coverage() (+10 more)

### Community 47 - "quarterly_job.py"
Cohesion: 0.25
Nodes (14): Provider interfaces + fallback chains for price / BCTC / sector. Pipeline loads…, get_financial_statement_provider(), get_price_provider(), get_sector_provider(), load_pipeline_config(), Any, Path, ``mode='live'`` uses financial_statements_live.chain; ``mode='backtest'`` uses… (+6 more)

### Community 48 - "Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư"
Cohesion: 0.14
Nodes (13): Bảng lệnh bot dự kiến, Bảng `signals` (hợp đồng giao diện giữa Tầng 2 và bot), Chart backtest bổ sung (`bot/charts.py`), Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`), daily_job → subscribers, Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư, Lịch daily (Windows), Module ↔ người phụ trách (theo phân công đã thống nhất) (+5 more)

### Community 49 - "Quyết định V1 (P0 sync — trước Quant)"
Cohesion: 0.20
Nodes (8): default_scoring_dates(), Assumed filing dates for annual fundamental refreshes., test_build_scoring_schedule_keys(), assumed_filed_at(), Point-in-time helpers for assumed BCTC publication dates., Return ISO date = period-end (31 Dec ``year``) + ``lag_days``. Used when vendor…, datetime, Quyết định V1 (P0 sync — trước Quant)

### Community 50 - "test_scoring_frames.py"
Cohesion: 0.16
Nodes (13): is_financial_industry(), True when industry name matches V1 financial exclusion keywords., data_tests, _annual(), Tests for scoring_frames builder (no network)., ≥4 prior year-end closes + assumed lag → hist valuation available., test_assumed_filed_at(), test_build_scoring_frames_and_score() (+5 more)

### Community 51 - "load_scoring_config"
Cohesion: 0.15
Nodes (20): Tầng 1 — Fundamental Filter (facade + re-export engine entrypoints). Public…, load_scoring_config(), Any, Path, Return classification thresholds synced with pipeline/config.yaml. Output keys…, _read_yaml(), _as_bool(), classify_fundamental_universe() (+12 more)

### Community 52 - "repository.py"
Cohesion: 0.07
Nodes (56): test_ablation_persist_to_store(), test_upsert_backtest_results(), test_sector_mapping_upsert_and_overview(), test_subscribe_helpers(), test_backtest_and_sector_charts(), test_price_bars_store_roundtrip_and_chart(), Connection, industries_from_sector_mapping() (+48 more)

### Community 54 - "typing"
Cohesion: 0.09
Nodes (24): ProviderError, Provider protocols — shared contracts for all vendor adapters., Raised when a single vendor fails; chain may try the next source., Try providers in config order; skip failures and continue the chain., Any, vnfinancialdata annual BCTC — wraps transitional layer1 financial_data., VnFinancialDataStatements, Vnstock live BCTC adapter — placeholder until field mapping is audited. (+16 more)

### Community 55 - "score_current_universe"
Cohesion: 0.19
Nodes (7): Score and classify only the explicitly supplied current-run universe. Pure…, score_current_universe(), FundamentalRefactorTests, Facade vs engine, `fundamental_filter/` — Tầng 1 (Fundamental Filter), Network / I/O, skipUnless

### Community 56 - "test_systemic_fundamental.py"
Cohesion: 0.27
Nodes (6): validate_weights(), ValuationHybridTests, calculate_historical_valuation_score(), calculate_valuation_components(), is_point_in_time_observation(), _to_date()

### Community 57 - "safety_diagnostics.py"
Cohesion: 0.46
Nodes (7): build_summary(), get_metric_score_file(), get_output_file(), get_relative_position(), get_scoring_input_file(), get_trend_status(), run_safety_diagnostics()

### Community 59 - "scoring_input.py"
Cohesion: 0.46
Nodes (7): build_scoring_input(), get_historical_percentile_file(), get_output_file(), get_peer_percentile_file(), get_peer_snapshot_file(), get_trend_score_file(), select_metric_values()

### Community 60 - "VnstockPriceProvider"
Cohesion: 0.50
Nodes (3): Any, DataFrame, VnstockPriceProvider

### Community 61 - "growth.py"
Cohesion: 0.13
Nodes (17): fundamental_filter, eps_cagr(), growth_score(), growth_spread(), positive_growth_ratio(), Module Growth — Câu hỏi 1: Doanh nghiệp có thật sự tăng trưởng không? Tham…, Mục 2.1 — Revenue Growth YoY = (Rev_t - Rev_t-1) / Rev_t-1., Mục 2.2 — Growth Spread = NPAT Growth - Revenue Growth (chỉ báo chẩn đoán). (+9 more)

### Community 63 - "quality.py"
Cohesion: 0.20
Nodes (11): cfo_to_npat(), roic(), cash_conversion(), dupont_decomposition(), quality_score(), Module Quality — Câu hỏi 2: Lợi nhuận có chất lượng và hiệu quả không? Tham…, Mục 3.2 — ROIC = NOPAT / Invested Capital. Headline metric của module này (mục…, Mục 3.3 — ROE = Net Margin x Asset Turnover x Equity Multiplier. Dùng làm… (+3 more)

### Community 64 - "valuation.py"
Cohesion: 0.25
Nodes (7): margin_of_safety(), pe_ratio(), Module Valuation — Câu hỏi 4: Giá cổ phiếu hiện tại có hợp lý không? Tham…, Mục 5.1 — headline metric (so với median 5Y & peer, xem mục 6.1)., Mục 5.5 — (Intrinsic Value - Market Price) / Intrinsic Value. ADVANCED (cần DCF…, Tổng hợp điểm Valuation + trả thêm view_signal cho quant_engine/portfolio/ (xem…, valuation_score()

### Community 65 - "trend_analysis.py"
Cohesion: 0.52
Nodes (6): analyze_metric(), classify_change(), get_fundamental_file(), get_output_file(), get_overall_direction(), run_trend_analysis()

### Community 66 - "peer_percentile.py"
Cohesion: 0.60
Nodes (5): calculate_metric_percentile(), get_percentile_file(), get_selection_file(), get_snapshot_file(), run_peer_percentile()

### Community 68 - "test_hawkes.py"
Cohesion: 0.23
Nodes (13): branching_ratio(), crowding_size_multiplier(), fit_hawkes(), fit_hawkes_from_returns(), Series, Hawkes process — bộ lọc crowding (đám đông tự kích hoạt chính nó). Tham chiếu:…, Estimate μ, α, β via a simple moment/OLS proxy (V1, no heavy MLE dependency).…, Giảm size khi n tiến gần n_max — mục 9.5 crowding overlay. n ≤ 0 → 1.0; n ≥… (+5 more)

### Community 69 - "walk_forward.py"
Cohesion: 0.22
Nodes (14): __getattr__(), Any, Backtest package — shared FF + Quant path (ARCHITECTURE invariant #2)., _add_months(), _fmt(), main(), _parse(), Any (+6 more)

### Community 71 - "scoring_frames.py"
Cohesion: 0.11
Nodes (31): AnnualFetcher, core_metric_names(), module_for_metric(), Ingest helpers — prepare frames/series for filter and quant engines., _assign_peer_percentiles(), build_metric_history(), build_scoring_frames(), build_scoring_frames_from_providers() (+23 more)

### Community 72 - "financials_stubs.py"
Cohesion: 0.31
Nodes (4): CafeFFinancials, Any, Stub BCTC vendors from config chain (CafeF, Vietstock)., VietstockFinancials

### Community 74 - "historical_percentile.py"
Cohesion: 0.70
Nodes (4): calculate_metric_percentile(), get_fundamental_file(), get_percentile_file(), run_historical_percentile()

### Community 76 - "ratios_valuation.py"
Cohesion: 0.24
Nodes (14): get_latest_reported_financial_data(), Return auditable financial input for valuation. The configured annual source…, calculate_book_value_per_share(), calculate_enterprise_value(), calculate_ev_to_ebitda(), calculate_fcf(), calculate_fcf_yield(), calculate_market_cap() (+6 more)

### Community 77 - "select_peer_universe"
Cohesion: 0.35
Nodes (5): _apply_size_filter(), _clean_tickers(), Select one deterministic peer universe and return audit metadata., select_peer_universe(), PeerSelectionTests

### Community 78 - "pathlib"
Cohesion: 0.20
Nodes (7): contextlib, copy, Load scoring / classification thresholds from pipeline/config.yaml. Maps repo…, io, pathlib, tempfile, unittest

### Community 79 - "Fintech Stock Bot — Fundamental Layer engine (`layer1_engine/`)"
Cohesion: 0.20
Nodes (8): Architecture (repo), Data limitations, Fintech Stock Bot — Fundamental Layer engine (`layer1_engine/`), Outputs, Pure path vs I/O path, Run, Setup — Windows PowerShell (from repo root), Tests

### Community 83 - "get_financial_data"
Cohesion: 0.36
Nodes (7): _ensure_runtime_deps(), get_financial_data(), get_value(), Annual BCTC via vnfinancialdata. Transitional location: pipeline should call…, _vnf(), get_data(), get_value()

### Community 84 - "Log thực tế của nhóm"
Cohesion: 0.12
Nodes (15): Ablation P0 + scoring_schedule + walk-forward (2026-09-21, lần 2), Ablation watchlist 12 mã + walk-forward (2026-09-22), Audit E2E + sửa /sector FAIL + /backtest ablation UX (2026-09-22), Audit UX vs framework (2026-09-22) — không lệch dần, Bot UX plain-VI + /chart ta (2026-09-22), /check §9.7 polish + hose_liquid_35 live (2026-09-21), HOSE liquid 35 + ablation 6 mã (2026-09-21), Log thực tế của nhóm (+7 more)

### Community 87 - "_b1_ta_result"
Cohesion: 0.33
Nodes (7): _b1_ta_result(), _b2_canslim_result(), Baseline B1 — TA thuần: long khi EMA20>EMA50 và RSI14<70 (mục 10/11.3)., Baseline B2 — CANSLIM rút gọn: mỗi tháng giữ nửa mã RS 6 tháng cao nhất., _rsi(), test_b1_b2_baseline_runners_finite(), Sprint next-framework (2026-09-22)

### Community 88 - "1. DYNAMIC SKILL ROUTER (CRITICAL INSTRUCTION)"
Cohesion: 0.25
Nodes (7): 1. DYNAMIC SKILL ROUTER (CRITICAL INSTRUCTION), 2. CORE VIBE CODING PRINCIPLES, 3. UNIFIED UI CRASH COURSE (For Sponsor Tier), 📝 Analytics & Review, 🧠 Core System & Debugging, 📊 Data & Market, 📈 Trading & Portfolio

### Community 89 - "peer_snapshot_runner.py"
Cohesion: 0.60
Nodes (5): flatten_snapshot(), get_coverage_file(), get_snapshot_file(), read_eligible_peers(), run_peer_snapshot()

### Community 90 - "fundamental_score.py"
Cohesion: 0.70
Nodes (4): get_module_score_file(), get_output_file(), run_fundamental_score(), validate_module_weights()

### Community 91 - "upsert_signals"
Cohesion: 0.50
Nodes (4): Ghi một dòng vào bảng signals. `signal` phải khớp cột trong schema.sql., Batch upsert for daily_job., upsert_signal(), upsert_signals()

## Knowledge Gaps
- **81 isolated node(s):** `fundamental_scores`, `subscribers`, `Issue liên quan`, `Thay đổi gì`, `Đây là tầng P0 / P1 / P2? (xem docs/ARCHITECTURE.md)` (+76 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 482 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `score_current_universe()` connect `score_current_universe` to `metric_score.py`, `module_score.py`, `fundamental_engine.py`, `FinancialStatementProvider`, `pathlib`, `Fintech Stock Bot — Fundamental Layer engine (`layer1_engine/`)`, `quarterly_job.py`, `Quyết định V1 (P0 sync — trước Quant)`, `engine.py`, `load_scoring_config`, `test_scoring_frames.py`, `test_quarterly_job.py`, `fundamental_score.py`?**
  _High betweenness centrality (0.052) - this node is a cross-community bridge._
- **Why does `Quyết định V1 (P0 sync — trước Quant)` connect `Quyết định V1 (P0 sync — trước Quant)` to `price_history.py`, `test_hawkes.py`, `sector_job.py`, `compute_metrics`, `signal_engine.py`, `argparse`, `test_black_litterman.py`, `ablation.py`, `Log thực tế của nhóm`, `typing`, `score_current_universe`, `test_systemic_fundamental.py`?**
  _High betweenness centrality (0.028) - this node is a cross-community bridge._
- **Why does `Pure path vs I/O path` connect `Fintech Stock Bot — Fundamental Layer engine (`layer1_engine/`)` to `to_store_records`, `load_scoring_config`, `fundamental_engine.py`, `score_current_universe`?**
  _High betweenness centrality (0.024) - this node is a cross-community bridge._
- **Are the 14 inferred relationships involving `build_application()` (e.g. with `about()` and `backtest_cmd()`) actually correct?**
  _`build_application()` has 14 INFERRED edges - model-reasoned connections that need verification._
- **What connects `fundamental_scores`, `subscribers`, `Issue liên quan` to the rest of the system?**
  _81 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `price_history.py` be split into smaller, more focused modules?**
  _Cohesion score 0.09872241579558652 - nodes in this community are weakly interconnected._
- **Should `test_regime.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12615384615384614 - nodes in this community are weakly interconnected._