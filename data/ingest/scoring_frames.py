"""Build ``scoring_frames`` for ``score_current_universe`` from BCTC (+ optional price).

Peer percentiles prefer **same industry** when enough peers exist; otherwise fall
back to the run universe cross-section. Optional financial-industry exclusion
keeps V1 scope non-financial (framework + ``pipeline/config.yaml``).

Historical valuation uses year-end closes + ``assumed_filed_at`` PIT observations
(see ``docs/DECISIONS.md``) so PASS is reachable when ≥4 safe observations exist.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

import numpy as np
import pandas as pd

from fundamental_filter.layer1_engine.peer_percentile import (
    HIGHER_IS_BETTER,
    LOWER_IS_BETTER,
)
from fundamental_filter.layer1_engine.scoring_input import OUTPUT_COLUMNS
from fundamental_filter.layer1_engine.valuation_scoring import (
    MIN_HISTORICAL_OBSERVATIONS,
    calculate_historical_valuation_score,
)

from .fundamental_metrics import compute_year_metrics, core_metric_names, module_for_metric
from .pit import assumed_filed_at

AnnualFetcher = Callable[[str, int], dict[str, Any] | None]
PriceFetcher = Callable[[str], float | None]
YearPriceFetcher = Callable[[str, int], float | None]
SharesFetcher = Callable[[str], float | None]
IndustryFetcher = Callable[[str], dict[str, Any] | None]

_VALUATION_METRICS = ("pe", "pb", "ev_to_ebitda", "fcf_yield")

# Vietnamese + English keywords for bank / brokerage / insurance (V1 exclude)
_FINANCIAL_KEYWORDS = (
    "ngân hàng",
    "bank",
    "chứng khoán",
    "securities",
    "bảo hiểm",
    "insurance",
    "tài chính",
    "finance",
)

# Fallback khi sector_mapping thiếu — không phụ thuộc industry_name.
# Ngân hàng / chứng khoán / bảo hiểm / tài chính phổ biến VN100 (+ vài mã lân cận).
CURATED_FINANCIAL_TICKERS: frozenset[str] = frozenset(
    {
        # Ngân hàng
        "ACB",
        "BID",
        "CTG",
        "EIB",
        "HDB",
        "LPB",
        "MBB",
        "MSB",
        "NAB",
        "OCB",
        "SHB",
        "SSB",
        "STB",
        "TCB",
        "TPB",
        "VCB",
        "VIB",
        "VPB",
        # Chứng khoán / môi giới
        "BSI",
        "CTS",
        "DSE",
        "FTS",
        "HCM",
        "ORS",
        "SHS",
        "SSI",
        "VCI",
        "VCK",
        "VIX",
        "VND",
        # Bảo hiểm / tài chính khác
        "BMI",
        "BVH",
        "EVF",
        "MIG",
        "PVI",
        "VNR",
    }
)


def is_financial_industry(industry_name: str | None) -> bool:
    """True khi tên ngành khớp từ khóa loại trừ tài chính V1."""
    if not industry_name:
        return False
    lowered = str(industry_name).casefold()
    return any(keyword in lowered for keyword in _FINANCIAL_KEYWORDS)


def is_excluded_financial(
    ticker: str | None,
    industry_name: str | None = None,
) -> bool:
    """True nếu mã tài chính V1 — ticker curated HOẶC industry keywords.

    Dùng khi ``sector_mapping`` thiếu: vẫn EXCLUDED (không nhầm «thiếu data»).
    """
    t = str(ticker or "").strip().upper()
    if t and t in CURATED_FINANCIAL_TICKERS:
        return True
    return is_financial_industry(industry_name)


def _trend_score(series: list[float | None]) -> float | None:
    values = [v for v in series if v is not None and not pd.isna(v)]
    if len(values) < 2:
        return None
    first, last = values[0], values[-1]
    if first == last:
        return 50.0
    return 100.0 if last > first else 0.0


def _percentile_series(values: pd.Series, *, higher_is_better: bool) -> pd.Series:
    valid = values.notna().sum()
    if valid < 2:
        return pd.Series(np.nan, index=values.index, dtype=float)
    ranks = values.rank(
        method="average", ascending=higher_is_better, na_option="keep"
    )
    return ((ranks - 1) / (valid - 1) * 100).clip(0, 100)


def _higher_is_better(metric: str) -> bool:
    if metric in LOWER_IS_BETTER:
        return False
    return metric in HIGHER_IS_BETTER


def _assign_peer_percentiles(
    current: pd.DataFrame,
    metrics: list[str],
    industry_by_ticker: Mapping[str, str] | None,
    min_industry_peers: int,
) -> tuple[dict[str, pd.Series], dict[Any, dict[str, Any]]]:
    """Industry percentiles when group size ≥ min; else universe cross-section."""
    peer_by_metric: dict[str, pd.Series] = {
        metric: pd.Series(np.nan, index=current.index, dtype=float)
        for metric in metrics
    }
    meta: dict[Any, dict[str, Any]] = {
        idx: {
            "peer_method": None,
            "peer_quality": "MEDIUM",
            "peer_count": 0,
            "peer_warning": "",
            "industry": None,
        }
        for idx in current.index
    }

    industry_series = current["ticker"].map(
        lambda t: (industry_by_ticker or {}).get(str(t).strip().upper())
    )
    assigned: set[Any] = set()

    if industry_by_ticker:
        for industry, group in current.groupby(industry_series, dropna=False):
            if industry is None or (isinstance(industry, float) and pd.isna(industry)):
                continue
            if len(group) < min_industry_peers:
                continue
            quality = "HIGH" if len(group) >= 5 else "MEDIUM"
            for metric in metrics:
                peer_by_metric[metric].loc[group.index] = _percentile_series(
                    pd.to_numeric(group[metric], errors="coerce"),
                    higher_is_better=_higher_is_better(metric),
                )
            for idx in group.index:
                meta[idx] = {
                    "peer_method": "INDUSTRY",
                    "peer_quality": quality,
                    "peer_count": int(len(group)),
                    "peer_warning": "",
                    "industry": str(industry),
                }
                assigned.add(idx)

    remaining = current.index.difference(assigned)
    if len(remaining) > 0:
        rem = current.loc[remaining]
        universe_n = int(current["ticker"].nunique())
        quality = "MEDIUM" if universe_n >= min_industry_peers else "LOW"
        warning = (
            "Industry peers below min_industry_peers; "
            "percentiles are within run universe"
            if industry_by_ticker
            else "Industry peers not used; percentiles are within run universe"
        )
        for metric in metrics:
            peer_by_metric[metric].loc[remaining] = _percentile_series(
                pd.to_numeric(rem[metric], errors="coerce"),
                higher_is_better=_higher_is_better(metric),
            )
        for idx in remaining:
            meta[idx] = {
                "peer_method": "UNIVERSE_CROSS_SECTION",
                "peer_quality": quality,
                "peer_count": universe_n,
                "peer_warning": warning,
                "industry": industry_series.get(idx),
            }

    return peer_by_metric, meta


def _fundamental_context_score(rows: list[dict[str, Any]]) -> float:
    """Mean peer percentile of GROWTH+QUALITY+SAFETY (valuation fundamental_context)."""
    context_modules = {"GROWTH", "QUALITY", "SAFETY"}
    values = [
        float(row["peer_percentile"])
        for row in rows
        if row["module"] in context_modules
        and row["peer_percentile"] is not None
        and not pd.isna(row["peer_percentile"])
    ]
    if not values:
        return float("nan")
    return float(np.mean(values))


def _hist_valuation_observation(
    year_row: Mapping[str, Any], *, lag_days: int
) -> dict[str, Any] | None:
    """One PIT-safe year-end valuation observation, or None if metrics missing."""
    year = int(year_row["year"])
    metrics = {
        metric: year_row.get(metric)
        for metric in _VALUATION_METRICS
        if year_row.get(metric) is not None and not pd.isna(year_row.get(metric))
    }
    if len(metrics) < 2:
        return None
    filed = assumed_filed_at(year, lag_days)
    price_date = f"{year}-12-31"
    return {
        "observation_date": filed,
        "price_date": price_date,
        "shares_date": price_date,
        "financial_publication_date": filed,
        "point_in_time_safe": True,
        **metrics,
    }


def _historical_valuation_for_ticker(
    ticker_hist: pd.DataFrame,
    *,
    end_year: int,
    lag_days: int,
    min_observations: int = MIN_HISTORICAL_OBSERVATIONS,
) -> tuple[float, bool, str]:
    """Score current end-year valuation vs prior year-end PIT observations."""
    current_rows = ticker_hist.loc[ticker_hist["year"].eq(end_year)]
    if current_rows.empty:
        return (
            float("nan"),
            False,
            "No current-year metrics for historical valuation",
        )
    current = current_rows.iloc[0]
    current_values = {metric: current.get(metric) for metric in _VALUATION_METRICS}
    if all(
        current_values.get(metric) is None or pd.isna(current_values.get(metric))
        for metric in _VALUATION_METRICS
    ):
        return (
            float("nan"),
            False,
            "Current valuation metrics missing (need year-end price+shares)",
        )

    observations: list[dict[str, Any]] = []
    prior = ticker_hist.loc[ticker_hist["year"].lt(end_year)].sort_values("year")
    for _, row in prior.iterrows():
        obs = _hist_valuation_observation(row, lag_days=lag_days)
        if obs is not None:
            observations.append(obs)

    as_of = assumed_filed_at(end_year, lag_days)
    score, _, n_valid = calculate_historical_valuation_score(
        current_values,
        observations,
        as_of,
        min_observations=min_observations,
    )
    if pd.isna(score):
        return (
            float("nan"),
            False,
            (
                f"Need ≥{min_observations} PIT year-end valuation observations "
                f"(have {n_valid}); supply fetch_year_price for prior years"
            ),
        )
    return (
        float(score),
        True,
        f"Year-end closes + assumed_filed_at lag={lag_days}d ({n_valid} obs)",
    )


def industries_from_sector_mapping(
    tickers: list[str],
    db_path: str = "store/bot.db",
) -> dict[str, str]:
    """Prefer ``store.sector_mapping.industry`` (sector_job) over live KBS."""
    from store import repository

    out: dict[str, str] = {}
    conn = repository.get_connection(db_path)
    try:
        repository.init_schema(conn)
        for ticker in tickers:
            target = ticker.strip().upper()
            row = repository.get_sector_for_ticker(conn, target)
            if not row:
                continue
            industry = row.get("industry")
            if industry and str(industry).strip().upper() not in {"", "UNKNOWN"}:
                out[target] = str(industry)
    finally:
        conn.close()
    return out


def build_metric_history(
    tickers: list[str],
    start_year: int,
    end_year: int,
    fetch_annual: AnnualFetcher,
    *,
    fetch_price: PriceFetcher | None = None,
    fetch_year_price: YearPriceFetcher | None = None,
    fetch_shares: SharesFetcher | None = None,
) -> pd.DataFrame:
    """Wide metric history for all tickers/years (includes lookback years for CAGR).

    ``fetch_year_price(ticker, year)`` supplies Dec-31 closes for historical
    valuation; when absent, only ``end_year`` uses ``fetch_price`` (legacy).
    """
    rows: list[dict[str, Any]] = []
    for ticker in tickers:
        target = ticker.strip().upper()
        cache: dict[int, dict[str, Any] | None] = {}
        for year in range(start_year - 3, end_year + 1):
            try:
                cache[year] = fetch_annual(target, year)
            except Exception:  # noqa: BLE001 — one bad year must not kill the batch
                cache[year] = None

        latest_price = None
        shares = None
        if fetch_price is not None:
            try:
                latest_price = fetch_price(target)
            except Exception:  # noqa: BLE001
                latest_price = None
        if fetch_shares is not None:
            try:
                shares = fetch_shares(target)
            except Exception:  # noqa: BLE001
                shares = None

        for year in range(start_year, end_year + 1):
            use_price = None
            if fetch_year_price is not None:
                try:
                    use_price = fetch_year_price(target, year)
                except Exception:  # noqa: BLE001
                    use_price = None
            if use_price is None and year == end_year:
                use_price = latest_price
            # ponytail: reuse latest shares for prior years; shares history when vendor exposes it
            use_shares = shares
            rows.append(
                compute_year_metrics(
                    target,
                    year,
                    cache.get(year),
                    cache.get(year - 1),
                    cache.get(year - 3),
                    price=use_price,
                    shares=use_shares,
                )
            )
    return pd.DataFrame(rows)


def build_scoring_frames(
    tickers: list[str],
    start_year: int,
    end_year: int,
    fetch_annual: AnnualFetcher,
    *,
    fetch_price: PriceFetcher | None = None,
    fetch_year_price: YearPriceFetcher | None = None,
    fetch_shares: SharesFetcher | None = None,
    industry_by_ticker: Mapping[str, str] | None = None,
    exclude_financials: bool = True,
    min_industry_peers: int = 3,
    publication_lag_days: int = 90,
) -> dict[str, pd.DataFrame]:
    """Return ``{ticker: scoring_input DataFrame}`` ready for ``score_current_universe``."""
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")
    targets = [t.strip().upper() for t in tickers]
    if not targets:
        raise ValueError("At least one ticker is required")

    industries = {
        t: (industry_by_ticker or {}).get(t)
        for t in targets
        if (industry_by_ticker or {}).get(t)
    }
    if exclude_financials:
        # Curated ticker + industry keywords — không chờ sector_mapping đủ.
        targets = [
            t
            for t in targets
            if not is_excluded_financial(t, industries.get(t))
        ]
        if not targets:
            return {}

    history = build_metric_history(
        targets,
        min(start_year, end_year - MIN_HISTORICAL_OBSERVATIONS),
        end_year,
        fetch_annual,
        fetch_price=fetch_price,
        fetch_year_price=fetch_year_price,
        fetch_shares=fetch_shares,
    )
    current = history.loc[history["year"].eq(end_year)].copy()
    metrics = core_metric_names()
    peer_by_metric, peer_meta = _assign_peer_percentiles(
        current,
        metrics,
        {t: industries[t] for t in targets if t in industries} or None,
        min_industry_peers,
    )

    frames: dict[str, pd.DataFrame] = {}
    for ticker in targets:
        ticker_hist = history.loc[history["ticker"].eq(ticker)].sort_values("year")
        ticker_now = current.loc[current["ticker"].eq(ticker)]
        if ticker_now.empty:
            continue
        now_idx = ticker_now.index[0]
        equity = ticker_now.iloc[0].get("equity")
        meta = peer_meta[now_idx]
        hist_score, hist_available, hist_reason = _historical_valuation_for_ticker(
            ticker_hist,
            end_year=end_year,
            lag_days=publication_lag_days,
        )

        rows: list[dict[str, Any]] = []
        for metric in metrics:
            module = module_for_metric(metric)
            raw_series = [
                None if pd.isna(v) else float(v)
                for v in pd.to_numeric(ticker_hist[metric], errors="coerce").tolist()
            ]
            trend_input = (
                [None if v is None else -v for v in raw_series]
                if metric in LOWER_IS_BETTER
                else raw_series
            )
            rows.append(
                {
                    "ticker": ticker,
                    "year": end_year,
                    "module": module,
                    "metric": metric,
                    "raw_value": raw_series[-1] if raw_series else None,
                    "peer_percentile": peer_by_metric[metric].get(now_idx, np.nan),
                    "historical_percentile": np.nan,
                    "trend_score": _trend_score(trend_input),
                    "equity": equity,
                    "peer_method": meta["peer_method"],
                    "peer_quality": meta["peer_quality"],
                    "peer_count": meta["peer_count"],
                    "peer_warning": meta["peer_warning"],
                    "historical_valuation_score": hist_score,
                    "historical_valuation_available": hist_available,
                    "historical_valuation_reason": hist_reason,
                    "fundamental_context_score": np.nan,
                }
            )
        context = _fundamental_context_score(rows)
        for row in rows:
            row["fundamental_context_score"] = context
        frames[ticker] = pd.DataFrame(rows, columns=OUTPUT_COLUMNS)
    return frames


def build_scoring_frames_from_providers(
    tickers: list[str],
    start_year: int,
    end_year: int,
    config: Mapping[str, Any] | None = None,
    *,
    db_path: str = "store/bot.db",
) -> dict[str, pd.DataFrame]:
    """Fetch annual BCTC (+ year-end price/shares/industry) via ``data.providers``.

    Industry prefers ``store.sector_mapping`` (from ``sector_job``); live KBS fills gaps.
    """
    from data.providers import (
        get_financial_statement_provider,
        get_price_provider,
        get_sector_provider,
        load_pipeline_config,
    )

    cfg = dict(config) if config is not None else load_pipeline_config()
    fs = get_financial_statement_provider(cfg, mode="backtest")
    price_provider = get_price_provider(cfg)
    sector = get_sector_provider(cfg)
    ff = cfg.get("fundamental_filter") or {}
    exclude_financials = bool(ff.get("exclude_financials", True))
    min_industry_peers = int(ff.get("min_industry_peers", 3))
    sources = cfg.get("data_sources") or {}
    backtest = sources.get("financial_statements_backtest") or {}
    lag_days = int(backtest.get("assumed_publication_lag_days", 90))

    def fetch_annual(ticker: str, year: int):
        return fs.get_annual(ticker, year)

    def fetch_price(ticker: str) -> float | None:
        try:
            result = price_provider.get_close(ticker, None)
        except Exception:  # noqa: BLE001
            return None
        if not result:
            return None
        price = result.get("price")
        return None if price is None else float(price)

    def fetch_year_price(ticker: str, year: int) -> float | None:
        try:
            result = price_provider.get_close(ticker, f"{year}-12-31")
        except Exception:  # noqa: BLE001
            return None
        if not result:
            return None
        price = result.get("price")
        return None if price is None else float(price)

    def fetch_shares(ticker: str) -> float | None:
        try:
            from fundamental_filter.layer1_engine.shares_data import (
                get_shares_outstanding,
            )
        except ImportError:
            return None
        try:
            result = get_shares_outstanding(ticker)
        except Exception:  # noqa: BLE001
            return None
        if not result:
            return None
        shares = result.get("shares_outstanding")
        return None if shares is None else float(shares)

    industry_by_ticker = industries_from_sector_mapping(tickers, db_path=db_path)
    for ticker in tickers:
        target = ticker.strip().upper()
        if target in industry_by_ticker:
            continue
        try:
            info = sector.get_industry(target)
        except Exception:  # noqa: BLE001
            info = None
        if info and info.get("industry_name"):
            industry_by_ticker[target] = str(info["industry_name"])

    return build_scoring_frames(
        tickers,
        start_year,
        end_year,
        fetch_annual,
        fetch_price=fetch_price,
        fetch_year_price=fetch_year_price,
        fetch_shares=fetch_shares,
        industry_by_ticker=industry_by_ticker or None,
        exclude_financials=exclude_financials,
        min_industry_peers=min_industry_peers,
        publication_lag_days=lag_days,
    )
