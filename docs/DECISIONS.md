# Nhật ký quyết định giữ/cắt một tầng (ablation log)

Nguyên tắc: một tầng chỉ được giữ trong bản cuối nếu nó cải thiện Sharpe ngoài mẫu
(out-of-sample, walk-forward) tối thiểu ngưỡng đã thống nhất. Nếu không đạt, ghi lại đây
là phát hiện hợp lệ — không xóa khỏi báo cáo.

Ngưỡng thống nhất trước khi chạy ablation lần đầu (đồng bộ với
`pipeline/config.yaml: backtest.checks` — sửa ở đây thì phải sửa cả bên đó):

- **Cải thiện Sharpe tối thiểu (OOS)**: +0.10
- **Số lệnh tối thiểu để kết luận có ý nghĩa thống kê**: 30 lệnh — dưới mức này, Sharpe/Calmar/Sortino chỉ mang tính minh hoạ, KHÔNG được dùng để kết luận "framework thắng baseline"
- **Turnover tối đa**: 200%/năm — vượt mức này cần xem lại vì chi phí giao dịch (`backtest/costs.py`) có thể ăn hết phần alpha đo được
- **Trọng số tối đa / mã (`max_position_weight_pct`)**: 0.10 — khớp `quant_engine.w_max`; check `CONCENTRATED_WEIGHT`

`backtest/ablation.py` đối chiếu các ngưỡng trên và ghi PASS/FAIL vào bảng
`backtest_checks` sau mỗi lần chạy — nhóm xem bảng đó thay vì tự diễn giải số liệu.

Điền ngày chốt các ngưỡng trên: __________

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
| 2026-09-21 | Ablation CLI: `--with-fundamentals` → `build_scoring_schedule`; tách regime (alpha off) vs alpha; `--walk-forward` | Fundamental giữ (+0.71 Sharpe); quant single-window cắt; WF OOS mỏng — chưa flip P1 |
| 2026-09-21 | Universe CSV + `request_delay_ms` OHLCV throttle; smoke N=10 missing 0% | Scale có kiểm soát trước full board / flip P1 |
| 2026-09-21 | OHLCV disk cache (`cache_ohlcv` + `cache_dir`) keyed by ticker/start/end | Giảm vendor calls khi re-run daily; không ảnh hưởng PIT BCTC |
| 2026-09-21 | Ops live path: `scripts/run_daily_pipeline.py` + `.env` `BOT_TOKEN`; getMe OK; daily push **sent=1** (1 subscriber) | Token chỉ local; MC/BL vẫn `enabled: false` |
| 2026-09-21 | Bot UX: `/signals` chú thích regime chung + hiện score/σ̂; `/start` hướng dẫn; p_bull/size đồng nhất = thiết kế P0 (không bug) | Equal-weight + regime VNINDEX; MC/BL vẫn off |
| 2026-09-21 | Universe V1 = **HOSE + HNX only** (`universe.allowed_exchanges`); UPCOM out of scope — filter qua `sector_mapping.market` | Không crawl/score UPCOM; unmapped/`VN` giữ nếu CSV curated |
| 2026-09-21 | `sector_job` chuẩn hoá `market` via vnstock `Listing.symbols_by_exchange` + `normalize_exchange`; không ghi `VN` mơ hồ | Phục vụ filter `allowed_exchanges`; lịch daily: `scripts/run_daily_pipeline.ps1` |
| 2026-09-21 | `/chart <mã> price`: `price_bars` do daily_job ghi; bot chỉ đọc store → PNG | Không vendor trong handler; risk/prob/ta vẫn stub |
| 2026-09-21 | Bot UX plain-VI: `/check` `/signals` `/regime` bỏ jargon module; schtasks `VNSignalDaily` 15:15 T2–T6 | Chart lỗi cũng nói tiếng người dùng |

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

### Ablation P0 + scoring_schedule + walk-forward (2026-09-21, lần 2)

CLI: `python -m backtest.ablation --with-fundamentals --walk-forward --signal-every 20`
Window 2021–2024, VNM/FPT, schedule keys `2021-03-31`…`2025-03-31` (assumed lag 90d).

| Ngày | Tầng thử nghiệm | Kết quả (Sharpe/CAGR/MDD) | Quyết định | Người chốt |
|---|---|---|---|---|
| 2026-09-21 | B0 buy&hold | Sharpe **0.92** / CAGR 0.18 / MDD −0.18 | Baseline | auto |
| 2026-09-21 | +fundamental (PIT PASS/WATCH buyhold) | Sharpe **1.63** (Δ **+0.71**) / CAGR 0.50 / MDD −0.31 | **Giữ** (≥ +0.10) — schedule tách được FF khỏi B0 | auto |
| 2026-09-21 | +regime (alpha off) | 0 trades; Sharpe null | Pending — alpha off → WATCH-only (đúng thiết kế tách layer) | auto |
| 2026-09-21 | +alpha | Sharpe **−0.22** (Δ **−1.85** vs fundamental); n_trades=5 | Cắt khỏi bản chính trên single-window này | auto |
| 2026-09-21 | +risk GARCH | Sharpe −0.22 (Δ **+0.00**); cùng 5 trades | Chưa đạt ngưỡng biên vs alpha | auto |
| 2026-09-21 | Walk-forward OOS full P0 (2 folds 2024 H1/H2) | Sharpe OOS **1.15** / CAGR 0.017 / n_trades=2 | Số OOS dương nhưng sample rất mỏng (2 trades) — **chưa đủ** để flip MC/BL; giữ quant P0 code, mở rộng universe trước khi chốt | auto |

MC/BL defaults vẫn `enabled: false`. JSON: `store/ablation_p0.json`.

### Scale smoke N=10 + OHLCV throttle (2026-09-21)

- Universe file: `data/universe/smoke_scale10.csv` (subset of `vn30_sample.csv`); config `request_delay_ms: 250`.
- CLI: `--universe-file` trên `sector_job` / `quarterly_job`.
- Kết quả: sector upsert **10**/10 (~206s); quarterly 10 mã 2020–2024 OK (~3.3 phút sau sector); daily watchlist **5** PASS/WATCH (FPT,GAS,PNJ,SAB,VNM); OHLCV **6/6 missing=0%** (5 + VNINDEX); `request_delay_ms=250`; tổng pipeline ~**412s**. Không thấy rate-limit 429 trên lần này.
- Ceiling: quarterly vẫn nặng (BCTC/năm); daily chỉ chạy watchlist đã lọc — scale 25–100 mã cần throttle + có thể tăng delay / cache OHLCV. MC/BL vẫn tắt.

### OHLCV disk cache (2026-09-21)

- Config: `data_sources.price.cache_ohlcv: true`, `cache_dir: data/cache` (đã trong `.gitignore` qua `data/cache/*`).
- Key file: `ohlcv_{TICKER}_{start}_{end}.csv` — reuse cùng cửa sổ = hit; cache hit **không** sleep throttle.
- Ceiling: cache chỉ cho giá daily Quant; **không** thay PIT BCTC / assumed lag. MC/BL vẫn `enabled: false`.

### VN30 sample live smoke + OOS dày hơn (2026-09-21)

- Universe: `data/universe/vn30_sample.csv` (25 mã, config `universe.file`).
- Quarterly 2019–2024 → watchlist **16** PASS/WATCH; daily: **16** signals, OHLCV **17/17 missing=0%**, actions BUY=4 / SELL=7 / WATCH=5; paper opened=3.
- Ops push trước đó: `sent=1` (1 subscriber) — xem dòng ops live path.
- Ablation rộng hơn (4 mã FPT,VNM,HPG,GAS; 2021–2024; `signal_every=42`; `scripts/run_ablation_quiet.py` + `--walk-forward`) → JSON `store/ablation_vn30_scale4.json`:

| Ngày | Tầng / OOS | Kết quả | Quyết định | Người chốt |
|---|---|---|---|---|
| 2026-09-21 | B0 buy&hold 4 mã | Sharpe **0.67** / CAGR 0.13 | Baseline | auto |
| 2026-09-21 | +fundamental PIT | Sharpe **0.74** (Δ **+0.065**) | Cắt ngưỡng trên sample này (< +0.10); lần VNM/FPT trước vẫn KEEP | auto |
| 2026-09-21 | +alpha | Sharpe **−0.35** (Δ **−1.09**); n_trades=**5** (dày hơn 2 trades cũ) | Cắt khỏi bản chính | auto |
| 2026-09-21 | +risk | Δ **+0.00** vs alpha | Không flip thêm | auto |
| 2026-09-21 | WF OOS 2 folds 2024 | Sharpe OOS **0.90** / CAGR 0.015 / n_trades=**1** | Vẫn mỏng OOS — **không** flip MC/BL | auto |

MC/BL defaults vẫn `enabled: false` trong `pipeline/config.yaml`.

### HOSE liquid 35 + ablation 6 mã (2026-09-21)

- Universe mặc định: [`data/universe/hose_liquid_35.csv`](data/universe/hose_liquid_35.csv) (35 mã HOSE liquid; `pipeline/config.yaml` `universe.file`); sector_mapping backfill 10 mã mới → **35 HOSE**.
- Ablation quiet 6 mã FPT,VNM,HPG,GAS,MWG,REE; 2021–2024; `signal_every=42`; JSON `store/ablation_hose8_wf.json`:

| Ngày | Tầng / OOS | Kết quả | Quyết định | Người chốt |
|---|---|---|---|---|
| 2026-09-21 | B0 buy&hold 6 mã | Sharpe **0.76** / CAGR 0.13 | Baseline | auto |
| 2026-09-21 | +fundamental PIT | Sharpe **0.84** (Δ **+0.081**) | Cắt ngưỡng trên sample này (< +0.10); sample VNM/FPT trước vẫn KEEP | auto |
| 2026-09-21 | +alpha | Sharpe **−0.19** (Δ **−1.03**); n_trades=**7** (dày hơn 1–5 trades cũ) | Cắt khỏi bản chính | auto |
| 2026-09-21 | +risk | Δ **+0.00** vs alpha | Không flip thêm | auto |
| 2026-09-21 | WF OOS 2 folds 2024 | Sharpe OOS **1.07** / CAGR 0.024 / n_trades=**1** | OOS vẫn mỏng — **không** flip MC/BL | auto |

MC/BL defaults vẫn `enabled: false`.

### /check §9.7 polish + hose_liquid_35 live (2026-09-21)

- UX: banner khuyến nghị, header sàn/ngành, CTA `/chart`; khối TA reference từ `price_bars` (RSI/MA/Vol) — **chỉ hiển thị**, không vào score/size.
- Quarterly `hose_liquid_35` 2021–2024 → watchlist **22** (PASS 7 / WATCH 15); daily: **22** signals, OHLCV **23/23 missing=0%**, `price_bars` 23 mã.
- MC/BL vẫn `enabled: false`.

### Ablation watchlist 12 mã + walk-forward (2026-09-22)

- Universe subset 12 mã: FPT,VNM,GAS,MWG,REE,PNJ,PLX,GVR,VHM,VHC,DCM,SAB; 2021–2024; `signal_every=42`; CLI `scripts/run_ablation_quiet.py --walk-forward`; JSON `store/ablation_watchlist12_wf.json`.

| Ngày | Tầng / OOS | Kết quả | Quyết định | Người chốt |
|---|---|---|---|---|
| 2026-09-22 | B0 buy&hold 12 mã | Sharpe **0.66** / CAGR 0.13 | Baseline | auto |
| 2026-09-22 | +fundamental PIT | Sharpe **0.70** (Δ **+0.043**) | Cắt ngưỡng trên sample này (< +0.10) | auto |
| 2026-09-22 | +regime (alpha off) | 0 trades; Sharpe null | Pending — alpha off → WATCH-only (đúng thiết kế tách layer) | auto |
| 2026-09-22 | +alpha | Sharpe **−0.92** (Δ **−1.62** vs fundamental); n_trades=**23** (dày hơn sample 4–6 mã) | Cắt khỏi bản chính | auto |
| 2026-09-22 | +risk GARCH | Sharpe **−0.94** (Δ **−0.028** vs alpha); cùng 23 trades | Cắt — không đạt ngưỡng giữ | auto |
| 2026-09-22 | WF OOS 2 folds 2024 | Sharpe OOS **0.80** / CAGR 0.029 / n_trades=**3** | OOS vẫn mỏng (< dày hơn 1-trade cũ nhưng chưa đủ) — **không** flip MC/BL (cần ΔSharpe OOS ≥ +0.10 và sample dày hơn) | auto |

MC/BL defaults vẫn `enabled: false` trong `pipeline/config.yaml`.

### Bot UX plain-VI + /chart ta (2026-09-22)

- UX: `/start` vs `/help` tách riêng; banner/CTA tiếng Việt rõ hơn trên `/signals` `/check` `/watchlist` `/status` `/regime`; PASS/WATCH có gloss; hiển thị giá đóng cửa gần nhất + ghi chú thiếu dữ liệu (`insufficient_price_history`) theo framework 11.4.
- `/chart <mã> ta` mở từ `price_bars` (display-only) — risk/prob vẫn deferred (thiếu sigma history / MC off).
- MC/BL vẫn `enabled: false` (WF watchlist12: n_trades=3, gate chưa đạt).

### Audit E2E + sửa /sector FAIL + /backtest ablation UX (2026-09-22)

- Audit: pipeline Tier1/Tier2 P0 khớp framework; lệch chính là UX (`/sector` FAIL luôn 0 vì join watchlist; `/backtest` nhãn dễ hiểu nhầm là NAV live).
- `/sector`: đếm PASS/WATCH/FAIL từ `fundamental_scores` (PIT `filed_at`), ghi chú as_of quý.
- `/backtest`: copy «Ablation nghiên cứu · không phải NAV live»; persist `equity_curve_json` từ ablation/WF; gắn PNG equity + drawdown khi có curve.
- `/check` khối ①: đọc nhẹ `headline_json` (ghi chú lọc / phân vị).
- `/chart risk`: dải rolling từ `price_bars` (+ annotate σ̂ GARCH phiên gần nhất nếu có); `prob` vẫn tắt (MC off).
- Doc: ARCHITECTURE trỏ đúng `.docx` ở repo root. MC/BL vẫn `enabled: false`.

### Wire thêm metrics/charts tầng 2 từ schema + charts.py (2026-09-22)

- Metrics ADD-ON trên `/backtest` luôn hiện (Sortino/Calmar/turnover/profit factor/DD days); persist từ `compute_metrics` khi ablation ghi store.
- Charts: `/backtest` thêm rolling Sharpe + regime-equity + PnL histogram (khi có data); `/sector` gửi PNG overview; `/chart price` dùng nền regime nếu có lịch sử `p_regime`; `/chart risk` ưu tiên GARCH từ lịch sử `signals.sigma_hat` (≥5 phiên), không thì rolling; `/chart prob` đọc `mc_outcomes` trong `reason_json` nếu có.
- `/check`: hiện slot MC/CVaR dù null; OU half-life / regime_method khi có trong `reason_json`.
- Vẫn không flip MC/BL; Kalman level history chưa có trong store → chưa vẽ đường Kalman trên price chart.

### UX plain + ngành + tích lũy data tầng 2 (2026-09-22)

- Ngành: `data/universe/sector_overrides.csv` + `sector_job.apply_sector_overrides` — sửa UNKNOWN (DIG/DXG/KDH/POW/VIC) và VRE → Bán lẻ TTTM.
- UX: `/check` `/watchlist` `/backtest` `/sector` `/positions` dùng tiếng Việt ngắn, ngày `dd/mm/yyyy`, giải thích rõ ngày lọc báo cáo ≠ ngày phiên.
- Tầng 2 đủ data **không bịa số**: (1) chạy `daily_job` đều → `signals` tích `p_regime`/`sigma_hat` theo ngày; (2) ghi `kalman_level_last` vào `reason_json`; (3) chart GARCH/regime chỉ bật khi ≥5 phiên lịch sử; (4) MC/CVaR outcomes chỉ khi bật flag + OOS đạt gate.
- Catch-up: `python -m pipeline.daily_job --backfill-days 20 --no-push` (hoặc `scripts/run_daily_pipeline.py --backfill-days 20`) — tính lại từ `price_bars` đã có, không sync paper, không bịa số.
- MC/BL vẫn `enabled: false`.

### Audit UX vs framework (2026-09-22) — không lệch dần

| Điểm | Kết luận | Hành động |
|------|----------|-----------|
| `/check` 4 điểm 0–100 | **Bản rút gọn tạm** so với mục 6.1 (1 headline metric thật + supporting khi bất thường). `headline_json` mới lưu *tên* metric, chưa persist giá trị (EPS CAGR %, ROIC…). | Copy bot ghi «điểm nội bộ (tạm)»; P1: wire giá trị headline từ Tầng 1 vào store. |
| `/check VCB` trống | **Không phải DNSE thiếu VCB trước.** VCB **không có** trong `hose_liquid_35` → không vào universe → không Tầng 1 → không watchlist → `daily_job` không sinh signal. Bot **không** crawl khi gõ lệnh (ARCHITECTURE: chỉ đọc store). Automation = quarterly + daily theo lịch. | `/check` giải thích rõ ngoài universe / FAIL / chưa daily. |
| `/sector` 31/03/2025 | **PIT as_of** = `assumed_filed_at(FY2024, lag≈90d)` từ lần `quarterly_job` đã chạy — đúng công thức, **cũ** vì chưa chạy lại với BCTC 2025+. | Hỏi data: re-run quarterly với period mới; không nhầm là bug ngày session. |
| `/backtest` thiếu B1/B2 + n=3 | Schema có `B1_ta`/`B2_canslim` nhưng ablation **chỉ persist B0 + framework**. `ablation_watchlist12_wf` n_trades=3 → sơ bộ, chưa đủ kết luận mục 11.3. | Copy cảnh báo mẫu mỏng + thiếu B1/B2; backtest team implement 2 baseline. |

### Sprint next-framework (2026-09-22)

- **Mục 6.1:** `store_adapter._headline_json` persist giá trị (EPS CAGR / ROIC / Net Debt/EBITDA / P/E) + supporting khi bất thường; `quarterly_job` truyền `scoring_frames`; `/check` ưu tiên metric thật.
- **Tier1 refresh:** `quarterly_job --tickers` 8 mã liquid (VNM/FPT/…) `2021–2025` → `filed_at`/`as_of` **2026-03-31** (FY2025+lag). Full 35 mã live fetch quá chậm/HF — chạy nốt theo đợt.
- **Daily:** 24 signals phiên `2026-09-22` + backfill 10 phiên; MC/BL vẫn off.
- **Ops:** `VNSignalDaily` schtasks Ready (T2–T6 15:15); README checklist rõ bot không crawl on-command.
- **Ablation B1/B2:** `_b1_ta_result` (EMA20/50+RSI) + `_b2_canslim_result` (RS 6M top-half tháng) persist vào `backtest_results`.
- **OOS denser (smoke):** `ablation_b012_smoke` 6 mã 2023–2026 `signal_every=42` no-fund: B0 Sharpe≈0.43; B1 n_trades=257 Sharpe≈0.55; B2 n=57; framework stack risk n=14 Sharpe≈−0.50. Full WF+fund 12 mã quá chậm (scoring_schedule) — không flip MC/BL (gate chưa đạt; framework vẫn mỏng / thua B0 trên sample này).

### Bot UX ban_phac + universe VN100 Tier1 (2026-09-22)

- **Bot UX (ban_phac):** `/check` state machine store-only (`OUT_OF_SCOPE` / `INSUFFICIENT` / `FAIL` / `WATCH` / `PASS` ± signal); copy «Tín hiệu hệ thống»; WATCH không action BUY; không Quant on-demand — bot chỉ đọc `store/`. `/start` 3 CTA; `/signals` nhóm theo độ mạnh; có OPEN paper → ưu tiên HOLD/REDUCE/EXIT.
- **Universe hai tầng:** Tier1 Fundamental = **VN100** (`universe.fundamental_file` → `data/universe/vn100.csv`); Quant/`daily_job` chỉ watchlist (`quant_from_watchlist: true`); `hose_liquid_35` = smoke/fallback (`smoke_file` / ablation), không còn universe chính live.
- **Backtest:** walk-forward `test_months: 6` **giữ nguyên**; MC/BL vẫn `enabled: false`.
- **Tài chính:** VCB và mã ngân hàng/tài chính vẫn loại qua `exclude_financials: true` trước scoring — `/check VCB` = ngoài phạm vi chiến lược V1, không phải thiếu data.

### Ops: VN100 Tier1 batch populate (2026-09-22)

- **sector_job:** full VN100 **skipped** (prior live pull hung → Windows exit `4294967295`). `sector_mapping` **unchanged = 35** rows; no small-batch sector retry this run.
- **quarterly_job:** batches ~12 tickers, `--start-year 2021 --end-year 2025` → `filed_at`/`as_of` **2026-03-31**. Batch0–5 all exit 0 (~4–5 min each). Persist `store/bot.db`.
- **Hygiene:** deleted stale `watchlist`/`fundamental_scores` with `2027-03-31` (old end_year=2026 run) so `MAX(as_of_date)` = **2026-03-31** for `daily_job`.
- **Store after:** fund distinct @2026-03-31 = **70** (VN100 overlap **68**); watchlist PASS **13** / WATCH **35** (n=**48**). **32** VN100 tickers not scored — mostly `exclude_financials` (banks/brokers/insurers: VCB, ACB, TCB, …); thin/new names (e.g. TCX, VPX, VCK, DSE) also absent.
- **daily_job:** `python scripts/run_daily_pipeline.py --no-push` → **48** signals date **2026-09-22**; OHLCV **49/49 missing 0%** (incl. VNINDEX); MC/BL still off.
- **Logs:** `store/ops/vn100_quarterly_progress.txt`, `store/ops/batch*.log`, `store/ops/daily_after_vn100.log`.

### E2E audit A–E (2026-09-22) — PASS / FAIL / GAP

Readonly store + config + pytest spot-check vs framework `.docx` / ban_phac / `docs/ARCHITECTURE.md`.
Spot-check: `filed_at`/`as_of` max **2026-03-31**; **0** rows `2027-*`; `sector_mapping` **35**; fund@max **70** (VN100 overlap **68**); wl PASS **13** / WATCH **35**; signals **2026-09-22** BUY2/SELL16/WATCH30; MC/BL **off**; WF `test_months: 6`.

| ID | Hạng mục | Kết quả | Ghi chú / bằng chứng | Việc tiếp theo |
|---|---|---|---|---|
| A1 | PIT annual BCTC + lag 90d → as_of FY | **PASS** | `assumed_filed_at`; store max `2026-03-31` (=FY2025+90d); không ép Q2 lịch | Giữ; hygiene nếu job `end_year=2026` tạo `2027-03-31` |
| A2 | Bot store-only (ARCHITECTURE #1) | **PASS** | `bot/main` chỉ SELECT; không crawl trong handler | — |
| A3 | Shared live↔backtest path | **PASS** | `generate_signals` / `score_current_universe` dùng chung | Smoke pytest giữ khi harden |
| A4 | `sector_mapping` coverage VN100 | **GAP** | Chỉ **35**/100; 67 mã thiếu (incl. VCB/SSI) → peer INDUSTRY + `/sector` mỏng | Phase 2: `sector_job` batch nhỏ ~12 |
| A5 | Stale as_of look-ahead | **PASS** *(hiện tại)* | `n2027=0` lúc audit | Phase 2: re-check sau job `end_year=2026` đang chạy |
| A6 | Hist valuation / headline values | **PASS** | FAIL sample HPG `headline.value` có trong JSON | — |
| B1 | quarterly → watchlist → daily signals | **PASS** | wl 48 @2026-03-31; signals date 2026-09-22 | Daily sau sector ổn |
| B2 | Push subscribers | **PASS** *(cơ bản)* | `daily_job._maybe_push_signals`; 4 subscribers | Phase 3.3: ưu tiên đổi action |
| C1 | P0 FF + Regime/Alpha/Risk flags on | **PASS** | config yaml | — |
| C2 | exclude_financials V1 | **PASS** *(sau P0 UX)* | Curated ticker + industry; missing_fund ≈ banks/brokers; VCB không có fund row | Giữ V1 tắt tài chính |
| C3 | Peer `min_industry_peers` + fallback | **PASS** *(logic)* / **GAP** *(data)* | Code OK; thiếu sector → nhiều cross-section | Sector batch |
| C4 | MC / BL / Merton / Hawkes / DCF | **PASS** *(đúng off)* | `enabled: false`; gate OOS chưa đạt | Không flip đến gate |
| C5 | OOS WF denser (gate) | **GAP** | Smoke ablation framework thua B0; n_trades mỏng | Phase 3.2 denser WF; **không** flip MC/BL |
| D1 | `/check` state machine ban_phac §5–6 | **PASS** | OUT/INSUFF/FAIL/WATCH/PASS/EXCLUDED; pytest ban_phac | — |
| D2 | §6.1 basic giá/TA trên INSUFFICIENT/EXCLUDED | **PASS** *(sau P0 UX)* | Header giá + TA block; EXCLUDED không nhầm thiếu data | % phiên / volume chi tiết vẫn mỏng nếu thiếu bars |
| D3 | §6.2 FAIL full 4 trụ + lý do | **PASS** | `format_check_fundamental_fail` + headline values | Spot-check live `/check HPG` |
| D4 | WATCH không nâng BUY | **PASS** | `cap_action_for_fundamental` | — |
| D5 | Không Quant on-demand | **PASS** | ARCHITECTURE thắng ban_phac §5 bước 4 «nếu cho phép» | **Không** build on-demand |
| D6 | Alert khi đổi action / follow CTA | **GAP** | Push = full `/signals` list mỗi ngày | Phase 3.3 |
| D7 | Ticker thuần → `/check` (ban_phac P2) | **GAP** | Chưa có `MessageHandler` hẹp | Phase 3.3 |
| D8 | Bot error_handler / chunk 4096 | **PARTIAL** | `chunk_telegram_text` có; chưa `add_error_handler` | Phase 3.1 nhẹ |
| D9 | Copy as_of = BCTC năm (không «quý») | **PASS** *(sau P0 UX)* | `/watchlist` `/sector` copy FY | — |
| E1 | VCB/SSI = EXCLUDED không «thiếu data» | **PASS** *(sau P0 UX)* | `is_excluded_financial` curated; flags `(True,True,True)` | Sector batch vẫn hữu ích cho industry label |
| E2 | VCF / ngoài VN100 = OUT_OF_SCOPE | **PASS** | Đúng thiết kế; không crawl on-command | Chỉ mở rộng CSV có chủ đích |

**Tóm tắt ưu tiên sau audit:** (1) sector batch nhỏ + hygiene as_of; (2) P0 harden theo GAP A4/C3/D8; (3) P1 denser OOS — MC/BL giữ off; (4) ban_phac polish alert/ticker handler.

### Ops + Build sau audit (2026-09-22, plan e2e_audit_next_steps)

- **P0 UX:** `is_excluded_financial` (curated ticker ∪ industry keywords); `/check` EXCLUDED hiện giá/TA; copy `/watchlist`/`/sector` = BCTC năm (không quý lịch).
- **Sector:** overrides tài chính + mapping đủ VN100 (`sector_mapping` ≥100); VCB/SSI có industry «Ngân hàng»/«Chứng khoán». Live full-100 vẫn tránh — batch nhỏ / overrides.
- **Hygiene:** sau `quarterly_job --end-year 2026` (đã xong): xóa `2027-03-31` fund+wl (`store/ops/hygiene_stale_asof.py --apply`); max lại **2026-03-31**. Daily `--no-push` → **48** signals.
- **P0 harden:** error_handler Telegram; shared-path pytest; FAIL full view đã PASS audit; chunk 4096 giữ.
- **P1 denser OOS:** `ablation_watchlist12_wf_dense.json` — 12 mã, `signal_every=21`, **no-fund**, WF `test_months=6`, folds=4, **n_trades=36**, Sharpe OOS **−0.84**. Gate ΔSharpe/+MC/BL **chưa đạt** → MC/BL/`cvar95_calibration`/`regime_conditional_sharpe` **vẫn `enabled: false`**.
- **Ban_phac polish:** push ưu tiên đổi action (`diff_signal_actions`); MessageHandler ticker 3 ký tự → `/check`; CTA `/subscribe` trên PASS. **Không** Quant on-demand.

### Storytelling + sizing + backtest trung thực (2026-09-22)

- **Denser OOS = phát hiện hợp lệ:** framework Sharpe OOS ≈ −0.84 thua B0 (≈ +0.24) trên sample denser — **giữ trong báo cáo / DECISIONS**; **không** đổi tín hiệu để vá OOS; **không** flip MC/BL.
- **Sizing:** tỷ trọng `/signals` + `/positions` = GARCH `position_size` (trần `w_max=0.10`) — **không** phải chia đều; BL chỉ khi `portfolio_black_litterman.enabled`. Check `CONCENTRATED_WEIGHT` / `max_position_weight_pct: 0.10` ghi vào `backtest_checks`.
- **Chart OOS fairness:** `/backtest` equity align mọi baseline về cùng cửa sổ ngày framework OOS + rebase; wire yearly / IS–OS / turnover / checks ✅❌; persist Sortino/Calmar/`margin_bps` khi đủ dữ liệu.
- **Copy:** `/backtest` mở đầu = nghiên cứu OOS, không cam kết lãi; denser thua B0 nói rõ là phát hiện hợp lệ.

### BACKTEST_DEBUG_CHECKLIST audit + T+1 fill + report CLI (2026-09-22)

Audit theo `docs/BACKTEST_DEBUG_CHECKLIST.md` (đọc code thật; **không** sửa ngưỡng alpha/regime). Log denser OOS Sharpe **−0.84** **giữ nguyên** ở trên.

| # | Mục | Kết quả | Ghi chú / fix |
|---|---|---|---|
| P1 | BUY = long | ✅ | `engine.py`: BUY mở long, SELL đóng; `pnl = net_proceeds − cost_basis` (không đảo direction). Pytest `test_buy_opens_long_positive_pnl_on_rise`. |
| P1 | Score sign FF ↔ alpha | ✅ | Fundamental percentile `higher_is_better`; `alpha_effective` nhân growth/quality (điểm cao → factor lớn hơn). BUY cần `alpha_eff > 0`. |
| P2 | Fill cùng close tín hiệu | ❌→✅ **fix** | Trước: signal closes ≤ T rồi fill `px` cùng T (look-ahead). Sau: khớp **T+1**; stop vẫn cùng phiên. Pytest `test_signal_fill_is_t_plus_1`. |
| P2 | PIT `assumed_filed_at` / lag 90d | ✅ | `pit.assumed_filed_at` + `assumed_publication_lag_days: 90`; `build_scoring_schedule` khóa theo filed_at. |
| P2 | Watchlist lịch sử | ✅ / ⚠ | Có `scoring_schedule` = tái tạo PASS/WATCH theo thời điểm; `--no-fundamentals` / ticker cố định = survivorship — ghi rõ trên smoke. |
| P3 | Phí / T+2 / limit | ✅ | `buy_cost_fraction`/`sell_cost_fraction` 1 lần mỗi chân; T+2 `held_days < 2`; `is_tradable_at_price_limit`. |
| P4 | GARCH size nghịch đảo | ✅ | `position_size = min(w_max, σ_t/σ̂)`; stop gán + đóng khi `px ≤ stop`. |
| P5 | Adjusted close | ✅ *(provider)* | `to_close_series` dùng cột `close` từ chain DNSE/vnstock/cafef — không lẫn raw/adj trong engine. |

**Re-run note:** sau T+1, OOS denser cũ (−0.84) **không còn so sánh 1-1**; cần **một** lần đo lại cùng protocol nếu muốn số post-fix. **Không** cook / scale equity. MC/BL vẫn `enabled: false`.

**Phase B:** `run_walk_forward` trả `n_folds`, `fold_sharpes`, `fold_sharpe_mean` / `fold_sharpe_std` (JSON + terminal ablation/report). Kéo `start_date` sớm hơn tăng fold — **≠** thử cửa sổ đến khi đẹp.

**Phase C:** `scripts/run_backtest_report.py` — bảng B0/B1/B2/Framework(WF)/VN-Index/VN30 + `store/backtest_report.xlsx`.

```text
python scripts/run_backtest_report.py --universe smoke --start-date 2015-01-01 --walk-forward --signal-every 21
# smoke nhanh:
python scripts/run_backtest_report.py --tickers FPT,VNM,GAS --start-date 2022-01-01 --walk-forward --signal-every 42 --no-fundamentals --out-xlsx store/backtest_report_smoke.xlsx --no-persist-store
```

**Phase D (IS):** Checklist sạch sau fix T+1; **không** đổi ngưỡng live. Layer **+alpha** vẫn là drag đã log (watchlist12 / denser) — khuyến nghị: tune alpha **chỉ IS** rồi **một** lần OOS; **không** tắt alpha trong `config.yaml` khi chưa có bằng chứng IS + dòng DECISIONS. MC/BL giữ off đến gate (+0.10 Sharpe OOS, ≥30 lệnh).

**Phase D xlsx spot-check (2026-09-22):** strings từ `bảng thông số chi tiết.xlsx` (không commit) khớp config: `Size = min(w_max, σ_target/σ̂)`, `Alpha_effective = raw × f(G,Q)` f∈[0.5,1.5], Markov filtered, GJR-GARCH, lag 90. **Không** đổi `sigma_target`/`w_max`/`bull_threshold`/`min_slope_tstat` ở bước này — chưa tune IS; chưa đo lại OOS denser post-T+1 (chỉ note cần 1 lần nếu muốn so sánh). Smoke báo cáo 3 mã 2022+ (post-T+1) **không** thay thế denser −0.84 và **không** phải bằng chứng lãi hợp lệ cho full sample.

### Framework correctness P0/P1 + VN100 CLI (2026-09-22)

Fix theo `VIBE_CODE_MASTER_PROMPT_FIX_BACKTEST_VN100` / plan — **không** retune OOS; denser Sharpe **−0.84** **giữ nguyên** phía trên.

| Fix | Chi tiết |
|---|---|
| Schema | `_active_watchlist` → `fundamental_view` (+ alias `classification`) |
| Stop / FAIL | Risk override `stop_hit` / `fundamental_fail_exit`; FAIL hold → SELL T+1 |
| Ablation FF | Dynamic PIT equal-weight (không BH `end_date`) |
| B0/B1/B2 | Cùng fee ledger + T+1 cost trên Δ vị thế; report gross/net/cost_drag |
| OU / Bear | Neutral OU có thể BUY; bear không mở long |
| Risk | `inverse_vol_normalize_weights` rồi cap `w_max` (không đổi config) |
| Markov | Reject ConvergenceWarning / non-converge → `heuristic_nonconverged_markov`; turbulent = max σ² |
| Regime Sharpe | Research display `N/A (n < min)` — không literal `None` |
| CLI | `--universe vn100`, `--oos-start/--oos-end`, `--warmup-years`, `--signal-every` (default 1), `--with-fundamentals` |

**Smoke (không phải final VN100):** 3 mã FPT/VNM/GAS, OOS 2025-06→2025-09, `signal_every=5`, no-fund, warmup 1y — Framework Total Return ≈ **+2.0%**, Sharpe ≈ **+2.45**, MDD ≈ **−1.3%**, avg exposure ≈ **15%**, n_trades=7. Ablation cùng cửa sổ không warmup: risk Sharpe ≈ **−0.50** (alpha drag vẫn thấy). **Không** kết luận edge VN100 từ smoke.

```text
# Smoke
python scripts/run_backtest_report.py --tickers FPT,VNM,GAS --oos-start 2025-06-01 --oos-end 2025-09-01 --warmup-years 1 --signal-every 5 --no-fundamentals --no-walk-forward --no-persist-store --out-json store/backtest_final_vn100_smoke.json

# Full VN100 (chậm)
python scripts/run_backtest_report.py --universe vn100 --with-fundamentals --signal-every 1 --oos-start 2025-03-22 --oos-end 2025-09-22 --warmup-years 3 --no-walk-forward --out-json store/backtest_final_vn100_20260922.json
```

Báo cáo: `docs/BACKTEST_FINAL_REPORT.md`.

### Speed-only (2026-09-22) — không đổi logic / denser −0.84 giữ

Tối ưu tương đương kết quả (cùng trades/equity semantics):

| Thay đổi | Chi tiết |
|---|---|
| FF event cache | `precompute_fundamental_states` — score 1× / `filed_at`; daily chỉ lookup |
| Schedule year cache | `data/cache/scoring_schedule/{key}/year_{Y}.pkl` — ghi sau mỗi năm, resume Ctrl+C |
| Loop | `_truncate` searchsorted; prev_price qua `day_pos`; regime memo optional |
| CLI | `--refresh-fundamentals` / `--refresh-data`; `scripts/profile_backtest_smoke.py` |

**Không** đổi `signal_every`, universe, thresholds, T+1/costs, Markov daily expanding. Denser OOS Sharpe **−0.84** (P1 denser) **vẫn giữ** phía trên — speed-only, không retune.

```text
# Profile
python scripts/profile_backtest_smoke.py --out outputs/performance/profile_after.txt

# VN100 warm (cache hit OHLCV + year schedule)
python scripts/run_backtest_report.py --universe vn100 --with-fundamentals --signal-every 1 --oos-start 2025-03-22 --oos-end 2025-09-22 --warmup-years 3 --no-walk-forward --out-json store/backtest_final_vn100_20260922.json
```

### FAST DEV vs FINAL (2026-09-22) — không cook OOS; denser −0.84 giữ

Hai chế độ trên `scripts/run_backtest_report.py` (prompt tối ưu §14):

| Mode | Khi nào | Universe | Cadence | Warmup | Plots | Dùng làm research? |
|---|---|---|---|---|---|---|
| **FAST DEV** (`--fast-dev`) | Cần bảng/metrics debug **tonight** | smoke 35 hoặc `--fast-dev-mini` (12 mã) | `signal_every=5` | 2y | off | **Không** |
| **FINAL** | Báo cáo / so sánh chiến lược | VN100 | `signal_every=1` daily | 3y | sau sim | **Có** |

Banner bắt buộc khi FAST DEV: `FAST DEV MODE — NOT FOR FINAL RESEARCH METRICS`.

Thêm (không đổi semantics final):

| Thay đổi | Chi tiết |
|---|---|
| `BacktestDataBundle` | Load prices + PIT schedule **1×**; B0/B1/B2/FW/ablation share |
| `--no-plots` | Skip chart generation (mặc định với `--fast-dev`) |
| year_*.pkl log | `CACHE HIT` / `CACHE MISS` + ETA ước lượng khi cold |
| Markov/GARCH | Same-day memo trong một run — **không** đổi daily→weekly |

**Denser OOS Sharpe −0.84** (12 mã, no-fund, `signal_every=21`) **vẫn giữ** ở mục P1 denser phía trên — FAST DEV **không** thay thế số đó.

```text
# FAST DEV (smoke 35)
python scripts/run_backtest_report.py --fast-dev --with-fundamentals --oos-start 2025-03-22 --oos-end 2025-09-22 --no-walk-forward --out-json store/backtest_fast_dev.json --out-xlsx store/backtest_fast_dev.xlsx

# FAST DEV mini (12 mã) nếu fund 35 chậm
python scripts/run_backtest_report.py --fast-dev --fast-dev-mini --with-fundamentals --oos-start 2025-03-22 --oos-end 2025-09-22 --no-walk-forward --out-json store/backtest_fast_dev.json --out-xlsx store/backtest_fast_dev.xlsx
```

### Sync audit framework ↔ ARCHITECTURE ↔ code (2026-09-22)

Kiểm tra readonly + `pytest -q` (không retune OOS).

| Invariant / scope | Kết quả | Ghi chú |
|---|---|---|
| Bot chỉ đọc store (no fit/crawl on command) | **PASS** | `bot/main.py` không import vnstock/HTTP; `is_excluded_financial` chỉ phân loại OUT_OF_SCOPE |
| Shared live↔backtest (`score_current_universe` / `generate_signals`) | **PASS** | `test_shared_live_backtest_path` + backtest engine |
| PIT lag 90d / annual BCTC V1 | **PASS** | `config` + `data/ingest/pit.py` |
| VN100 Tier1 + `quant_from_watchlist` + smoke 35 | **PASS** | `pipeline/config.yaml`; README + ARCHITECTURE đã ghi rõ |
| P0 FF+Regime+Alpha+GARCH on; MC/BL/Merton/Hawkes/DCF off | **PASS** | Đúng gate DECISIONS |
| Backtest T+1 / costs / FAIL exit / `fundamental_view` | **PASS** | Tests trong `backtest/tests/test_backtest.py` |
| Pytest suite | **PASS** | **189 passed**, 8 skipped |
| Doc path framework `.docx` | **PASS** | Repo root (không `docs/khung_…`) |

**GAP ops (không chặn compile/test):** `sector_mapping` historically mỏng vs full VN100 peer INDUSTRY — xem audit E2E A4; bổ sung batch `sector_job` khi ops. Final VN100 daily+fund vẫn **chạy lâu** (API Community) — dùng FAST DEV cho bảng nhanh; denser −0.84 giữ nguyên.
