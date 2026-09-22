# Graph Report - Telegram-bot-for-investment-signal  (2026-09-21)

## Corpus Check
- 141 files · ~69,210 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 14 file(s) not represented in the graph (top: (none) 6, .csv 3, .mdc 2)

## Summary
- 1303 nodes · 3000 edges · 91 communities (67 shown, 24 thin omitted)
- Extraction: 97% EXTRACTED · 3% INFERRED · 0% AMBIGUOUS · INFERRED: 99 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f20e6b4b`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- price_history.py
- metric_score.py
- compute_year_metrics
- sector_job.py
- formatters.py
- validate_ticker.py
- ProviderError
- test_systemic_fundamental.py
- get_fundamental_snapshot
- compute_metrics
- test_monte_carlo.py
- peer_coverage_runner.py
- test_scoring_frames.py
- repository.py
- ratios_valuation.py
- schema.sql
- test_backtest.py
- ablation.py
- engine.py
- charts.py
- test_integration_smoke.py
- score_current_universe
- bot/__init__.py
- call_chain
- pipeline/__init__.py
- regime.py
- 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần
- select_peer_universe
- signal_engine.py
- Hướng dẫn đóng góp
- Data Feasibility Audit — điền trong 2–3 ngày đầu tuần 1
- Telegram Bot Tín hiệu Đầu tư Chứng khoán Việt Nam
- Chiến lược branch & quy trình làm việc
- PULL_REQUEST_TEMPLATE.md
- assumed_filed_at
- module_score.py
- test_paper_positions.py
- ta_indicators_from_closes
- Quyết định V1 (P0 sync — trước Quant)
- get_financial_data
- fundamental_engine.py
- quarterly_job.py
- Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư
- quality.py
- main.py
- SafetyScoringTests
- daily_job.py
- typing
- DnsePriceProvider
- pathlib
- scoring_input.py
- safety_diagnostics.py
- trend_analysis.py
- ClassificationTests
- growth.py
- vnfinancialdata
- math
- test_regime.py
- VnstockFinancials
- sync_positions_from_signals
- quant_engine
- pandas
- walk_forward.py
- scoring_frames.py
- CafeFFinancials
- peer_snapshot_runner.py
- historical_percentile.py
- append_decisions_log
- VnFinancialDataStatements
- peer_percentile.py
- VnstockPriceProvider
- data/__init__.py
- argparse
- Log thực tế của nhóm
- dotenv
- httpx
- test_daily_job_signals.py
- 1. DYNAMIC SKILL ROUTER (CRITICAL INSTRUCTION)
- truststore
- vnstock

## God Nodes (most connected - your core abstractions)
1. `compute_year_metrics()` - 37 edges
2. `get_fundamental_snapshot()` - 31 edges
3. `get_historical_fundamental()` - 31 edges
4. `compute_metrics()` - 29 edges
5. `get_connection()` - 28 edges
6. `score_current_universe()` - 28 edges
7. `generate_signals()` - 28 edges
8. `init_schema()` - 26 edges
9. `run_backtest()` - 26 edges
10. `ProviderError` - 25 edges

## Surprising Connections (you probably didn't know these)
- `Point-in-time & BCTC V1` --references--> `calculate_historical_valuation_score()`  [INFERRED]
  docs/ARCHITECTURE.md → fundamental_filter/layer1_engine/valuation_scoring.py
- `Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`)` --references--> `get_open_positions()`  [INFERRED]
  docs/ARCHITECTURE.md → store/repository.py
- `Quyết định V1 (P0 sync — trước Quant)` --references--> `build_scoring_schedule()`  [INFERRED]
  docs/DECISIONS.md → backtest/ablation.py
- `Quyết định V1 (P0 sync — trước Quant)` --references--> `_set_quant_flags()`  [INFERRED]
  docs/DECISIONS.md → backtest/ablation.py
- `Quyết định V1 (P0 sync — trước Quant)` --references--> `compute_metrics()`  [INFERRED]
  docs/DECISIONS.md → backtest/metrics.py

## Import Cycles
- None detected.

## Communities (91 total, 24 thin omitted)

### Community 0 - "price_history.py"
Cohesion: 0.10
Nodes (36): data_ingest, cache_ohlcv(), cache_ohlcv_enabled(), cache_ohlcv_path(), fetch_ohlcv(), fetch_universe_ohlcv(), load_cached_ohlcv(), _price_cfg() (+28 more)

### Community 1 - "metric_score.py"
Cohesion: 0.16
Nodes (10): calculate_metric_scores(), get_output_file(), get_scoring_input_file(), _peer_multiplier(), _peer_trend_score(), run_metric_score(), _safety_metric_score(), normalize_available_weights() (+2 more)

### Community 2 - "compute_year_metrics"
Cohesion: 0.22
Nodes (13): compute_year_metrics(), _get(), Any, Pure metric computation from annual BCTC dicts (no network). Uses…, Return one wide row of CORE (+ helper) metrics for ``ticker``/``year``., average_invested_capital(), gross_margin(), invested_capital() (+5 more)

### Community 3 - "sector_job.py"
Cohesion: 0.07
Nodes (44): data_providers, Universe CSV loader tests (no network)., test_filter_tickers_drops_upcom_keeps_hose_and_unmapped(), test_load_hose_liquid_35(), test_load_universe_missing_file(), test_load_universe_tickers_comments(), test_load_universe_tickers_sample(), test_normalize_exchange_aliases() (+36 more)

### Community 4 - "formatters.py"
Cohesion: 0.11
Nodes (32): _fmt_num(), format_backtest_results(), format_positions(), format_regime_message(), format_sector_overview(), format_signal_message(), format_signals_list(), format_status() (+24 more)

### Community 5 - "validate_ticker.py"
Cohesion: 0.16
Nodes (19): contextlib, audit_ticker(), _close(), _expected_classification(), _fmt(), _formula_check(), _independent_ratios(), _independent_valuation() (+11 more)

### Community 6 - "ProviderError"
Cohesion: 0.16
Nodes (13): ProviderError, Raised when a single vendor fails; chain may try the next source., Try providers in config order; skip failures and continue the chain., Any, VnstockSectorProvider, _FailClose, _NoneClose, _OkClose (+5 more)

### Community 7 - "test_systemic_fundamental.py"
Cohesion: 0.27
Nodes (6): validate_weights(), ValuationHybridTests, calculate_historical_valuation_score(), calculate_valuation_components(), is_point_in_time_observation(), _to_date()

### Community 8 - "get_fundamental_snapshot"
Cohesion: 0.20
Nodes (19): get_data(), get_fundamental_snapshot(), get_value(), get_historical_fundamental(), get_output_file(), get_value(), cfo_growth_yoy(), eps_cagr_3_year() (+11 more)

### Community 9 - "compute_metrics"
Cohesion: 0.14
Nodes (23): cagr(), calibrate_cvar95(), calmar_ratio(), compute_metrics(), cvar95_realized(), _equity_series(), max_drawdown(), max_drawdown_days() (+15 more)

### Community 10 - "test_monte_carlo.py"
Cohesion: 0.21
Nodes (14): _as_array(), cvar(), monte_carlo_signal_stats(), probability_tp_before_sl(), ndarray, Convenience wrapper → ``{p_tp_before_sl, cvar95, sl_pct}``., Return array shape (n_paths, horizon_days) of simulated prices., Fraction of paths that hit TP before SL within the horizon. (+6 more)

### Community 11 - "peer_coverage_runner.py"
Cohesion: 0.26
Nodes (10): _ensure_ssl(), get_industry(), Industry lookup via vnstock KBS. Network deps are lazy so importing this module…, get_coverage_file(), get_selection_file(), run_peer_coverage(), _ensure_ssl(), get_peer_group() (+2 more)

### Community 12 - "test_scoring_frames.py"
Cohesion: 0.19
Nodes (12): is_financial_industry(), True when industry name matches V1 financial exclusion keywords., _annual(), Tests for scoring_frames builder (no network)., ≥4 prior year-end closes + assumed lag → hist valuation available., test_compute_year_metrics_revenue_growth(), test_exclude_financials_and_industry_peers(), fetch_annual() (+4 more)

### Community 13 - "repository.py"
Cohesion: 0.08
Nodes (38): test_subscribe_helpers(), test_price_bars_store_roundtrip_and_chart(), Connection, test_open_close_position(), sqlite3, close_position(), get_active_subscribers(), get_backtest_results() (+30 more)

### Community 14 - "ratios_valuation.py"
Cohesion: 0.06
Nodes (43): base64, create_headers(), _ensure_runtime_deps(), get_close_price(), get_historical_close_price(), get_live_close_price(), parse_as_of_date(), DNSE close prices. Transitional location: pipeline should call… (+35 more)

### Community 15 - "schema.sql"
Cohesion: 0.19
Nodes (14): backtest_results, fundamental_scores, idx_backtest_scope, idx_positions_status, idx_price_bars_ticker_date, idx_sector_industry, idx_signals_ticker, idx_watchlist_date (+6 more)

### Community 16 - "test_backtest.py"
Cohesion: 0.12
Nodes (21): apply_transaction_costs(), is_tradable_at_price_limit(), Net return after sell tax + round-trip fee (applied once per closed trade)., False nếu giá đã chạm trần/sàn — coi như không khớp được lệnh., sharpe_ratio(), _close(), _config(), Series (+13 more)

### Community 17 - "ablation.py"
Cohesion: 0.18
Nodes (27): _assumed_lag_days(), _benchmark_ticker(), build_scoring_schedule(), _buyhold_result(), decide_keep_cut(), _fmt_metric(), format_steps_table(), _json_safe() (+19 more)

### Community 18 - "engine.py"
Cohesion: 0.17
Nodes (20): buy_cost_fraction(), Chi phí giao dịch thực tế — bắt buộc trong mọi backtest (mục 12.2). T+2 (không…, Half of round-trip fee charged on entry (NAV haircut)., Sell tax + half round-trip fee charged on exit., sell_cost_fraction(), _active_watchlist(), _as_date_index(), _business_days_between() (+12 more)

### Community 19 - "charts.py"
Cohesion: 0.14
Nodes (39): ChartDataError, _dates_values(), _ensure_out(), _load_backtest_curves(), _parse_equity(), Any, Path, Vẽ chart để bot gửi qua Telegram (ảnh PNG, gửi qua sendPhoto). QUAN TRỌNG —… (+31 more)

### Community 21 - "score_current_universe"
Cohesion: 0.05
Nodes (50): test_build_scoring_frames_and_score(), Tầng 1 — Fundamental Filter (facade + re-export engine entrypoints). Public…, fundamental_filter_layer1_engine, load_scoring_config(), Any, Path, Return classification thresholds synced with pipeline/config.yaml. Output keys…, _read_yaml() (+42 more)

### Community 24 - "call_chain"
Cohesion: 0.09
Nodes (18): FinancialStatementProvider, PriceProvider, Any, Giá/khối lượng — Tầng 2 (+ valuation close cho Tầng 1)., Close price (+ metadata). ``as_of_date=None`` → live/latest., BCTC — Tầng 1. Prefer point-in-time ``filed_at`` when available., Annual statement fields used by Growth/Quality/Safety/Valuation., Latest published snapshot as of date (PIT). May be incomplete. (+10 more)

### Community 27 - "regime.py"
Cohesion: 0.24
Nodes (13): _as_series(), filtered_regime_probability(), fit_markov_regime(), fit_or_fallback_regime(), _heuristic_regime_probability(), Any, Series, Regime — Markov switching trên chuỗi lợi nhuận (thường VN-Index). Tham chiếu:… (+5 more)

### Community 32 - "4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần"
Cohesion: 0.08
Nodes (25): 1. Vài khái niệm cần hiểu trước (bằng ví dụ, không phải định nghĩa hàn lâm), 2. Cài đặt — chọn 1 trong 2 cách, 3. Lấy code về máy lần đầu (chỉ làm 1 lần), 4. Quy trình làm việc hằng ngày — làm đúng thứ tự này mỗi lần, 5. Tôi nên sửa file ở đâu?, 6. Các tình huống hay gặp và cách xử lý, 7. Bảng lệnh Git tối thiểu cần nhớ (nếu dùng dòng lệnh), 8. Nếu vẫn bị kẹt (+17 more)

### Community 33 - "select_peer_universe"
Cohesion: 0.35
Nodes (5): _apply_size_filter(), _clean_tickers(), Select one deterministic peer universe and return audit metadata., select_peer_universe(), PeerSelectionTests

### Community 34 - "signal_engine.py"
Cohesion: 0.15
Nodes (19): alpha_effective(), fit_kalman_trend(), Kalman filter — ước lượng xu hướng (trend/slope) ẩn dưới nhiễu giá. Tham chiếu:…, Return (level, slope, slope_variance) arrays aligned with input. Input: log-…, t-stat of Kalman slope — proxy for trend strength (framework mục 9.7)., Mục 9.3 — Alpha_effective = Alpha_raw * f(Growth, Quality). f is monotone in…, slope_tstat(), Quant Regime Engine — Tầng 2 (daily). Pure modules (no network): ``regime``,… (+11 more)

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

### Community 40 - "assumed_filed_at"
Cohesion: 0.20
Nodes (8): default_scoring_dates(), Assumed filing dates for annual fundamental refreshes., test_build_scoring_schedule_keys(), assumed_filed_at(), Point-in-time helpers for assumed BCTC publication dates., Return ISO date = period-end (31 Dec ``year``) + ``lag_days``. Used when vendor…, test_assumed_filed_at(), datetime

### Community 41 - "module_score.py"
Cohesion: 0.26
Nodes (14): get_metric_score_file(), get_output_file(), run_module_score(), validate_module_weights(), calculate_absolute_metric_score(), calculate_safety_components(), get_safety_gate_status(), _is_missing() (+6 more)

### Community 42 - "test_paper_positions.py"
Cohesion: 0.17
Nodes (15): interest_coverage(), net_debt_to_ebitda(), Net Debt / EBITDA. Non-positive EBITDA: net cash → 0; levered → 99 (gate/score…, EBIT / Interest. Zero/negative interest with positive EBIT → 999 (no burden)., interest_coverage(), merton_distance_to_default(), net_debt_to_ebitda(), Module Safety — Câu hỏi 3: Doanh nghiệp có an toàn tài chính không? Tham chiếu:… (+7 more)

### Community 43 - "ta_indicators_from_closes"
Cohesion: 0.29
Nodes (8): Any, Chỉ số TA cổ điển cho khối «Tham khảo thêm» (§9.7) — CHỈ HIỂN THỊ. Không dùng…, Trả dict cho ``format_ta_reference_block`` từ rows ``{date, close, volume?}``., _rsi(), ta_indicators_from_closes(), Tests for display-only TA reference (§9.7)., test_ta_empty_when_too_short(), test_ta_from_closes_rsi_and_ma()

### Community 44 - "Quyết định V1 (P0 sync — trước Quant)"
Cohesion: 0.15
Nodes (23): Quyết định V1 (P0 sync — trước Quant), bl_portfolio_weights(), black_litterman_weights(), build_views(), covariance_from_closes(), equal_weight_fallback(), _market_weights(), DataFrame (+15 more)

### Community 45 - "get_financial_data"
Cohesion: 0.26
Nodes (11): get_financial_exchange(), _ensure_runtime_deps(), get_financial_data(), get_value(), Annual BCTC via vnfinancialdata. Transitional location: pipeline should call…, _vnf(), _ensure_ssl(), get_kbs_company_data() (+3 more)

### Community 46 - "fundamental_engine.py"
Cohesion: 0.24
Nodes (11): analyze_fundamental(), analyze_fundamental_universe(), _empty_historical_percentiles(), _normalize_tickers(), Write only final production outputs; debug frames are opt-in and isolated., Run the Fundamental Layer in memory for an explicit ticker universe.…, Backward-compatible single-ticker entry point without stale CSV state., _write_debug_frames() (+3 more)

### Community 47 - "quarterly_job.py"
Cohesion: 0.23
Nodes (15): Provider interfaces + fallback chains for price / BCTC / sector. Pipeline loads…, get_financial_statement_provider(), get_price_provider(), get_sector_provider(), load_pipeline_config(), Any, Path, ``mode='live'`` uses financial_statements_live.chain; ``mode='backtest'`` uses… (+7 more)

### Community 48 - "Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư"
Cohesion: 0.14
Nodes (13): Bảng lệnh bot dự kiến, Bảng `signals` (hợp đồng giao diện giữa Tầng 2 và bot), Chart backtest bổ sung (`bot/charts.py`), Các bảng lệnh Telegram khác (`positions`, `subscribers`, `backtest_results`), daily_job → subscribers, Kiến trúc tổng thể — Telegram Bot Tín hiệu Đầu tư, Lịch daily (Windows), Module ↔ người phụ trách (theo phân công đã thống nhất) (+5 more)

### Community 49 - "quality.py"
Cohesion: 0.20
Nodes (11): cfo_to_npat(), roic(), cash_conversion(), dupont_decomposition(), quality_score(), Module Quality — Câu hỏi 2: Lợi nhuận có chất lượng và hiệu quả không? Tham…, Mục 3.2 — ROIC = NOPAT / Invested Capital. Headline metric của module này (mục…, Mục 3.3 — ROE = Net Margin x Asset Turnover x Equity Multiplier. Dùng làm… (+3 more)

### Community 50 - "main.py"
Cohesion: 0.10
Nodes (33): bot, Close-only chart từ ``store.price_bars`` (không Kalman/regime — bot V1)., render_price_chart(), build_application(), backtest_cmd(), chart_cmd(), check_cmd(), help_cmd() (+25 more)

### Community 52 - "daily_job.py"
Cohesion: 0.08
Nodes (47): test_upsert_backtest_results(), test_sector_job_with_prepared_rows(), test_sector_mapping_upsert_and_overview(), test_backtest_and_sector_charts(), industries_from_sector_mapping(), Prefer ``store.sector_mapping.industry`` (sector_job) over live KBS., test_industries_from_sector_mapping(), test_filter_tickers_for_config_uses_db() (+39 more)

### Community 54 - "typing"
Cohesion: 0.13
Nodes (13): Provider protocols — shared contracts for all vendor adapters., Stub BCTC vendors from config chain (CafeF, Vietstock)., vnfinancialdata annual BCTC — wraps transitional layer1 financial_data., Vnstock live BCTC adapter — placeholder until field mapping is audited., DNSE price adapter — wraps transitional layer1 I/O until code moves here., CafeFPriceProvider, Any, DataFrame (+5 more)

### Community 55 - "DnsePriceProvider"
Cohesion: 0.40
Nodes (3): DnsePriceProvider, Any, DataFrame

### Community 56 - "pathlib"
Cohesion: 0.32
Nodes (6): copy, Load scoring / classification thresholds from pipeline/config.yaml. Maps repo…, get_analysis_file(), get_output_file(), run_trend_score(), pathlib

### Community 57 - "scoring_input.py"
Cohesion: 0.46
Nodes (7): build_scoring_input(), get_historical_percentile_file(), get_output_file(), get_peer_percentile_file(), get_peer_snapshot_file(), get_trend_score_file(), select_metric_values()

### Community 58 - "safety_diagnostics.py"
Cohesion: 0.46
Nodes (7): build_summary(), get_metric_score_file(), get_output_file(), get_relative_position(), get_scoring_input_file(), get_trend_status(), run_safety_diagnostics()

### Community 59 - "trend_analysis.py"
Cohesion: 0.52
Nodes (6): analyze_metric(), classify_change(), get_fundamental_file(), get_output_file(), get_overall_direction(), run_trend_analysis()

### Community 61 - "growth.py"
Cohesion: 0.13
Nodes (17): fundamental_filter, eps_cagr(), growth_score(), growth_spread(), positive_growth_ratio(), Module Growth — Câu hỏi 1: Doanh nghiệp có thật sự tăng trưởng không? Tham…, Mục 2.1 — Revenue Growth YoY = (Rev_t - Rev_t-1) / Rev_t-1., Mục 2.2 — Growth Spread = NPAT Growth - Revenue Growth (chỉ báo chẩn đoán). (+9 more)

### Community 63 - "math"
Cohesion: 0.29
Nodes (7): math, fit_ou_process(), ou_half_life(), Ornstein-Uhlenbeck mean reversion — dùng khi regime đang đi ngang. Tham chiếu:…, Estimate theta, mu, sigma from residual series (price − Kalman level). Discrete…, half_life = ln(2) / theta (sessions). Requires theta > 0., test_ou_half_life()

### Community 64 - "test_regime.py"
Cohesion: 0.14
Nodes (21): _as_returns(), fit_gjr_garch(), fit_or_fallback_sigma(), forecast_sigma(), position_size(), Series, GARCH/GJR-GARCH — dự báo biến động có điều kiện. Tham chiếu: mục "Risk" trong…, Fit GJR-GARCH(1,1). Returns arch ``ARCHModelResult`` or raises. (+13 more)

### Community 66 - "sync_positions_from_signals"
Cohesion: 0.43
Nodes (6): main(), Any, Paper-trading sync — ghi/đóng ``store.positions`` từ ``store.signals``. Bot chỉ…, Apply latest signal actions onto OPEN positions. - BUY + no OPEN →…, run(), sync_positions_from_signals()

### Community 68 - "pandas"
Cohesion: 0.17
Nodes (16): numpy, pandas, branching_ratio(), crowding_size_multiplier(), fit_hawkes(), fit_hawkes_from_returns(), Series, Hawkes process — bộ lọc crowding (đám đông tự kích hoạt chính nó). Tham chiếu:… (+8 more)

### Community 69 - "walk_forward.py"
Cohesion: 0.22
Nodes (14): __getattr__(), Any, Backtest package — shared FF + Quant path (ARCHITECTURE invariant #2)., _add_months(), _fmt(), main(), _parse(), Any (+6 more)

### Community 71 - "scoring_frames.py"
Cohesion: 0.08
Nodes (40): AnnualFetcher, core_metric_names(), module_for_metric(), Ingest helpers — prepare frames/series for filter and quant engines., _assign_peer_percentiles(), build_metric_history(), build_scoring_frames(), build_scoring_frames_from_providers() (+32 more)

### Community 72 - "CafeFFinancials"
Cohesion: 0.38
Nodes (3): CafeFFinancials, Any, VietstockFinancials

### Community 73 - "peer_snapshot_runner.py"
Cohesion: 0.60
Nodes (5): flatten_snapshot(), get_coverage_file(), get_snapshot_file(), read_eligible_peers(), run_peer_snapshot()

### Community 74 - "historical_percentile.py"
Cohesion: 0.70
Nodes (4): calculate_metric_percentile(), get_fundamental_file(), get_percentile_file(), run_historical_percentile()

### Community 76 - "append_decisions_log"
Cohesion: 0.40
Nodes (5): append_decisions_log(), format_decisions_row(), Path, One markdown table row for docs/DECISIONS.md ablation log., Append ablation summary lines under the decisions log section.

### Community 77 - "VnFinancialDataStatements"
Cohesion: 0.50
Nodes (3): Any, VnFinancialDataStatements, Kết luận cuối audit

### Community 78 - "peer_percentile.py"
Cohesion: 0.60
Nodes (5): calculate_metric_percentile(), get_percentile_file(), get_selection_file(), get_snapshot_file(), run_peer_percentile()

### Community 79 - "VnstockPriceProvider"
Cohesion: 0.50
Nodes (3): Any, DataFrame, VnstockPriceProvider

### Community 83 - "argparse"
Cohesion: 0.24
Nodes (9): argparse, get_module_score_file(), get_output_file(), run_fundamental_score(), validate_module_weights(), os, _load_dotenv(), Path (+1 more)

### Community 84 - "Log thực tế của nhóm"
Cohesion: 0.20
Nodes (9): Ablation P0 + scoring_schedule + walk-forward (2026-09-21, lần 2), /check §9.7 polish + hose_liquid_35 live (2026-09-21), HOSE liquid 35 + ablation 6 mã (2026-09-21), Log thực tế của nhóm, Mẫu ghi log, Nhật ký quyết định giữ/cắt một tầng (ablation log), OHLCV disk cache (2026-09-21), Scale smoke N=10 + OHLCV throttle (2026-09-21) (+1 more)

### Community 87 - "test_daily_job_signals.py"
Cohesion: 0.67
Nodes (3): _close(), Tests for daily_job signal persistence (no network)., test_daily_job_run_with_synthetic_closes()

### Community 88 - "1. DYNAMIC SKILL ROUTER (CRITICAL INSTRUCTION)"
Cohesion: 0.25
Nodes (7): 1. DYNAMIC SKILL ROUTER (CRITICAL INSTRUCTION), 2. CORE VIBE CODING PRINCIPLES, 3. UNIFIED UI CRASH COURSE (For Sponsor Tier), 📝 Analytics & Review, 🧠 Core System & Debugging, 📊 Data & Market, 📈 Trading & Portfolio

## Knowledge Gaps
- **77 isolated node(s):** `Mẫu ghi log`, `Ablation P0 + scoring_schedule + walk-forward (2026-09-21, lần 2)`, `Scale smoke N=10 + OHLCV throttle (2026-09-21)`, `OHLCV disk cache (2026-09-21)`, `VN30 sample live smoke + OOS dày hơn (2026-09-21)` (+72 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 448 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **24 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `score_current_universe()` connect `score_current_universe` to `metric_score.py`, `validate_ticker.py`, `scoring_frames.py`, `module_score.py`, `test_scoring_frames.py`, `Quyết định V1 (P0 sync — trước Quant)`, `fundamental_engine.py`, `quarterly_job.py`, `engine.py`, `argparse`, `daily_job.py`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `compute_year_metrics()` connect `compute_year_metrics` to `scoring_frames.py`, `get_fundamental_snapshot`, `test_paper_positions.py`, `test_scoring_frames.py`, `ratios_valuation.py`, `quality.py`?**
  _High betweenness centrality (0.029) - this node is a cross-community bridge._
- **Why does `generate_signals()` connect `signal_engine.py` to `test_regime.py`, `pandas`, `test_monte_carlo.py`, `Quyết định V1 (P0 sync — trước Quant)`, `engine.py`, `daily_job.py`, `regime.py`?**
  _High betweenness centrality (0.025) - this node is a cross-community bridge._
- **What connects `Mẫu ghi log`, `Ablation P0 + scoring_schedule + walk-forward (2026-09-21, lần 2)`, `Scale smoke N=10 + OHLCV throttle (2026-09-21)` to the rest of the system?**
  _77 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `price_history.py` be split into smaller, more focused modules?**
  _Cohesion score 0.1024390243902439 - nodes in this community are weakly interconnected._
- **Should `sector_job.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06887755102040816 - nodes in this community are weakly interconnected._
- **Should `formatters.py` be split into smaller, more focused modules?**
  _Cohesion score 0.11174242424242424 - nodes in this community are weakly interconnected._