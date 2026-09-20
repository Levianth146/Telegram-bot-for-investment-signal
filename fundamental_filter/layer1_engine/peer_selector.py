import json

import pandas as pd

from fundamental_config import CURATED_PEERS, PEER_SELECTION_CONFIG


def _clean_tickers(values, target):
    cleaned = []
    seen = {target}
    for value in values:
        if not isinstance(value, str):
            continue
        ticker = value.strip().upper()
        if ticker and ticker not in seen:
            cleaned.append(ticker)
            seen.add(ticker)
    return cleaned


def _apply_size_filter(rows, target_market_cap):
    if target_market_cap is None or pd.isna(target_market_cap) or target_market_cap <= 0:
        return rows.iloc[0:0].copy(), False
    lower = target_market_cap * PEER_SELECTION_CONFIG["size_ratio_min"]
    upper = target_market_cap * PEER_SELECTION_CONFIG["size_ratio_max"]
    market_caps = pd.to_numeric(rows["market_cap"], errors="coerce")
    return rows.loc[market_caps.between(lower, upper)].copy(), True


def select_peer_universe(
    target_ticker,
    candidates_df,
    industry_code=None,
    industry_name=None,
    target_market_cap=None,
    target_sub_industry=None,
    curated_peers=None,
):
    """Select one deterministic peer universe and return audit metadata."""
    target = target_ticker.strip().upper()
    data = candidates_df.copy()
    data["ticker"] = data["ticker"].astype(str).str.strip().str.upper()
    data = data.loc[data["ticker"].ne(target)].drop_duplicates("ticker")
    coverage_column = (
        "coverage_eligible" if "coverage_eligible" in data.columns else "eligible"
    )
    eligible = data.loc[data[coverage_column].fillna(False).astype(bool)].copy()
    minimum = PEER_SELECTION_CONFIG["min_primary_peers"]

    configured = curated_peers
    if configured is None:
        configured = CURATED_PEERS.get(target, [])
    curated = _clean_tickers(configured, target)
    valid_curated = eligible.loc[eligible["ticker"].isin(curated)]

    warning = None
    if curated and len(valid_curated) >= minimum:
        selected = valid_curated
        method = "CURATED"
        quality = "HIGH"
        fallback_used = False
        size_filter_applied = False
    else:
        sub_industry_available = (
            target_sub_industry is not None
            and "sub_industry" in eligible.columns
        )
        sub_industry_rows = eligible.iloc[0:0]
        if sub_industry_available:
            sub_industry_rows = eligible.loc[
                eligible["sub_industry"].eq(target_sub_industry)
            ]
        sub_size_rows, sub_size_applied = _apply_size_filter(
            sub_industry_rows, target_market_cap
        )

        if len(sub_size_rows) >= minimum:
            selected = sub_size_rows
            method = "SUB_INDUSTRY_SIZE"
            quality = "HIGH"
            fallback_used = False
            size_filter_applied = sub_size_applied
        elif len(sub_industry_rows) >= minimum:
            selected = sub_industry_rows
            method = "SUB_INDUSTRY"
            quality = "MEDIUM"
            fallback_used = False
            size_filter_applied = False
        else:
            size_rows, size_applied = _apply_size_filter(
                eligible, target_market_cap
            )
            if len(size_rows) >= minimum:
                selected = size_rows
                method = "INDUSTRY_SIZE_FALLBACK"
                size_filter_applied = size_applied
            else:
                selected = eligible
                method = "INDUSTRY_FALLBACK"
                size_filter_applied = False
            quality = "LOW"
            fallback_used = True
            if target_sub_industry is None:
                warning = "Sub-industry is unavailable from the configured source."

    selected_tickers = _clean_tickers(selected["ticker"].tolist(), target)
    if len(selected_tickers) < PEER_SELECTION_CONFIG["min_percentile_peers"]:
        short_warning = (
            f"Only {len(selected_tickers)} valid peers; at least "
            f"{PEER_SELECTION_CONFIG['min_percentile_peers']} are required."
        )
        warning = short_warning if warning is None else f"{warning} {short_warning}"

    metadata = {
        "ticker": target,
        "peer_method": method,
        "peer_quality": quality,
        "peer_count": len(selected_tickers),
        "peer_tickers": json.dumps(selected_tickers, ensure_ascii=False),
        "peer_industry": industry_name,
        "peer_industry_code": industry_code,
        "peer_sub_industry": target_sub_industry,
        "size_filter_applied": bool(size_filter_applied),
        "fallback_used": bool(fallback_used),
        "peer_warning": warning,
    }
    return selected_tickers, metadata
