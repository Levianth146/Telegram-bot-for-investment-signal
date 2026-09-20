# Nhật ký quyết định giữ/cắt một tầng (ablation log)

Nguyên tắc: một tầng chỉ được giữ trong bản cuối nếu nó cải thiện Sharpe ngoài mẫu
(out-of-sample, walk-forward) tối thiểu ngưỡng đã thống nhất. Nếu không đạt, ghi lại đây
là phát hiện hợp lệ — không xóa khỏi báo cáo.

Ngưỡng thống nhất trước khi chạy ablation lần đầu: **+0.10 Sharpe** (điền lại nếu nhóm chốt
số khác) — điền ngày chốt: __________

## Mẫu ghi log

| Ngày | Tầng thử nghiệm | Kết quả (Sharpe/CAGR/MDD trước–sau) | Quyết định | Người chốt |
|---|---|---|---|---|
| VD: 2026-10-15 | Hawkes crowding filter | Sharpe 1.12 → 1.14 (không đạt ngưỡng +0.10) | Cắt khỏi bản chính, giữ làm phụ lục nghiên cứu | @tên |

## Quyết định V1 (P0 sync — trước Quant)

| Ngày | Quyết định | Lý do |
|---|---|---|
| 2026-09-20 | PIT: dùng **assumed publication lag** 90 ngày sau period-end năm khi chưa có `filed_at` thật; `point_in_time_verified: true` với caveat này | vnfinancialdata chưa xác nhận cột ngày công bố; tránh look-ahead bằng lag bảo thủ (mục 7.1) |
| 2026-09-20 | Peer RELATIVE: ưu tiên **cùng industry** khi ≥3 mã; fallback universe cross-section (peer_quality MEDIUM/LOW) | Framework mục 10 yêu cầu theo ngành; industry từ vnstock KBS |
| 2026-09-20 | Universe Tầng 1: **loại bank / chứng khoán / bảo hiểm** theo industry name | Phạm vi V1 = phi tài chính |
| 2026-09-20 | CORE bổ sung: NPAT YoY, EPS YoY, Cash Conversion (CFO/NPAT) | Đóng gap Table 61; giảm phụ thuộc chỉ Rev/ROE |
| 2026-09-20 | Valuation V1: historical series chưa đủ → **không PASS** nếu `historical_valuation_available=false` (xuống WATCH) | Mục 5.6 cần hist+peer; peer-only = low confidence |
| 2026-09-21 | Hist valuation E2E: year-end close (`fetch_year_price`) + `assumed_filed_at` → `calculate_historical_valuation_score`; auto lookback ≥4 năm | Unblock PASS khi đủ PIT obs; không có year-end price → vẫn WATCH |
| 2026-09-21 | Peer industry: ưu tiên `store.sector_mapping` (sector_job); thiếu thì live KBS | Dual-path mục 10 |
| 2026-09-21 | daily_job: fetch `quant_engine.benchmark` (VNINDEX) cho regime; `signal_tickers` = watchlist only; push Telegram sau upsert | E2E hygiene |
| 2026-09-20 | Current/Quick Ratio: **chưa đưa CORE** (cắt V1, công thức vẫn có) | Tránh ratio zoo trước ablation; Safety vẫn có ND/EBITDA + IntCov + CFO/Debt |
| 2026-09-20 | Trend score V1: first→last binary còn tạm; slope z-score để P1 | Không chặn Quant scaffold |
| 2026-09-21 | Quant Regime: Markov fit chỉ khi ≥252 phiên; ngắn hơn → heuristic rolling mean/vol | Tránh MLE không hội tụ trên sample ngắn |
| 2026-09-21 | Portfolio V1: equal-weight (BL vẫn stub P1) | `portfolio_black_litterman.enabled: false` |
| 2026-09-21 | Black-Litterman P1: `build_views` + `black_litterman_weights` + wire `generate_signals`; default still `enabled: false` | Equal-weight fallback khi tắt / cov kém |
| 2026-09-21 | Hawkes P2: `fit_hawkes_from_returns` + `crowding_size_multiplier` trên size; default `enabled: false` | Data audit volume OK; giữ tắt đến khi ablation |
| 2026-09-21 | Monte Carlo / Hawkes: chưa ghi `p_tp_before_sl` / `cvar95` (null) | P1/P2 flags off |
| 2026-09-21 | Backtest P0: engine gọi lại `score_current_universe` + `generate_signals`; T+2, cost, limit ±7% | Shared live/backtest path (ARCHITECTURE #2) |
| 2026-09-21 | sector_mapping: upsert + `pipeline/sector_job.py` (monthly); industry←KBS name | P0 hạ tầng mục 10 |
| 2026-09-21 | Bot P0: `/signals` `/check` `/watchlist` `/regime` `/subscribe` — chỉ đọc store | ARCHITECTURE #1 |
| 2026-09-21 | Bot P1 cmds: `/positions` `/backtest` `/status` `/sector` (sector flag on) | Text-only; charts PNG vẫn NotImplemented (cần matplotlib) |
| 2026-09-21 | Charts P1: `bot/charts.py` matplotlib Agg + `/chart <mã> fundamental` | price/risk/prob/ta cần history table (V1 chưa có) |
| 2026-09-21 | Paper positions: `open_position`/`close_position` + `pipeline/paper_positions.py`; daily_job sync | Bot chỉ đọc |
| 2026-09-21 | Ablation P1 metrics: CVaR calibration + regime Sharpe (flags off by default) | `compute_metrics` + engine regime_by_date |
| 2026-09-21 | Merton DD: naive BS2008 formula; vẫn `enabled: false` (DATA_AUDIT thiếu kỳ hạn nợ) | Không zero-penalize khi thiếu input |
| 2026-09-21 | Monte Carlo P1 implement; mặc định `enabled: false` | Bật khi cần p_tp_before_sl / cvar95 |
| 2026-09-21 | **Live smoke VNM/FPT (2019–2024)** xanh: sector→quarterly→daily→bot dry-run | Đủ DoD: fundamental + signals trong `store/bot.db`; `benchmark_loaded=true` (VNINDEX); paper 0 open vì cả hai WATCH |
| 2026-09-21 | Live deps bắt buộc ngoài stub: `truststore` (SSL KBS/vnstock), `vnstock` (OHLCV + sector), `vnfinancialdata` (annual BCTC) | Thiếu → sector 0 rows / quarterly NaN; đã pin trong `requirements.txt` |
| 2026-09-21 | Live FS chain (`vnstock`/`cafef`/`vietstock`) vẫn stub; registry **luôn append** `VnFinancialDataStatements` last-resort (`registry.py`) | Ceiling: phụ thuộc annual package đến khi live BCTC API thật; DNSE OHLCV vẫn stub → fallback vnstock (đủ smoke) |
| 2026-09-21 | Hist val live: year-end close + assumed lag đủ cho VNM/FPT (`historical_valuation_available=true`, ~5 obs) → vẫn WATCH (không ép PASS) | Không cần vá `scoring_frames` sau smoke |
| 2026-09-21 | Ablation P0 CLI (`python -m backtest.ablation`); MC/BL vẫn **forced off** trong `_set_quant_flags` | Không flip default P1 trong `config.yaml` đến khi có số OOS đạt +0.10 Sharpe |

## Log thực tế của nhóm

Ablation P0 CLI: `python -m backtest.ablation` → `store/ablation_p0.json`.
Ngưỡng giữ tầng: **ΔSharpe ≥ +0.10** vs bước trước (single-window; chưa phải walk-forward OOS đầy đủ).

| Ngày | Tầng thử nghiệm | Kết quả (Sharpe/CAGR/MDD trước–sau) | Quyết định | Người chốt |
|---|---|---|---|---|
| 2026-09-21 | B0 buy&hold VNM+FPT (2021–2024, equal-weight) | Sharpe **0.92** / CAGR 0.18 / MDD −0.18 | Baseline | auto |
| 2026-09-21 | +fundamental (không `scoring_schedule` → trùng B0) | Sharpe 0.92 → 0.92 (Δ **+0.00**) | Cắt đo lường này — cần schedule BCTC PIT mới tách được FF | auto |
| 2026-09-21 | +regime (+alpha tối thiểu; signal every 40) | Sharpe 0.92 → **−0.70** (Δ **−1.61**); n_trades=2 | Cắt khỏi bản chính trên sample này; giữ code P0, cần WF + schedule + denser signals | auto |
| 2026-09-21 | +alpha (cùng flags regime+alpha, risk off) | Sharpe −0.70 → −0.70 (Δ **+0.00**) | Không tách được khỏi regime trên config hiện tại (layer trùng) | auto |
| 2026-09-21 | +risk GARCH | Sharpe −0.70 → −0.70 (Δ **+0.00**); cùng 2 trades | Chưa đạt ngưỡng trên sample sparse; không flip thêm P1 | auto |
| 2026-09-21 | **P1 MC / BL defaults** | — | **Không bật** `probabilistic_monte_carlo` / `portfolio_black_litterman` cho đến khi ablation P0 có số OOS đạt ngưỡng (hoặc sample lớn hơn) | plan |

Ceiling lần chạy: universe 2 mã; không scoring_schedule; `signal_every=40` (Markov/GARCH refit chậm trên cửa sổ dài); JSON tại `store/ablation_p0.json`.
