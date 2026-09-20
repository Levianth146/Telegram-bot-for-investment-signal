# Data schemas / contracts

Prepared frames handed to `fundamental_filter/` and `quant_engine/` should
match these shapes. Providers normalize vendor payloads into them.

## Price OHLCV (`PriceProvider.get_ohlcv`)

| column | type | notes |
|---|---|---|
| date | ISO `YYYY-MM-DD` | session date |
| open, high, low, close | float | VND (or vendor unit — document in adapter) |
| volume | float | shares/day; required for Hawkes later |

Built via `data.ingest.price_history.fetch_ohlcv` (price chain: DNSE close →
vnstock OHLCV → CafeF stub).

## Annual BCTC (`FinancialStatementProvider.get_annual`)

Keys aligned with `fundamental_filter.layer1_engine.financial_data.get_financial_data`:
`revenue`, `gross_profit`, `ebit`, `ebitda`, `npat_parent`, `eps`, `pretax_profit`,
`tax_expense`, `interest_expense`, `cash`, `receivables`, `inventory`,
`current_assets`, `current_liabilities`, `short_term_debt`, `long_term_debt`,
`total_assets`, `equity`, `cfo`, `capex`.

## Scoring frames (`data.ingest.build_scoring_frames`)

Long format matching `layer1_engine.scoring_input.OUTPUT_COLUMNS`, one DataFrame
per ticker, ready for `score_current_universe`. Peer percentiles prefer **same
industry** when ≥ `fundamental_filter.min_industry_peers` (default 3); otherwise
`peer_method=UNIVERSE_CROSS_SECTION`. V1 excludes bank/broker/insurance when
`exclude_financials: true` and industry names are supplied.

## Point-in-time

Prefer `filed_at` / `financial_publication_date`. When vendor has no real filing
date, use `data.ingest.pit.assumed_filed_at(year, lag_days)` with
`financial_statements_backtest.assumed_publication_lag_days` (default 90) —
see `docs/DATA_AUDIT.md` §4b and `docs/DECISIONS.md`.
