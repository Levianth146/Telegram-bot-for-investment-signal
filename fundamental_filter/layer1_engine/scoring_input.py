import argparse
from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent

CORE_METRICS = {
    "GROWTH": [
        "revenue_growth_yoy",
        "revenue_cagr_3_year",
        "eps_cagr_3_year",
    ],
    "QUALITY": [
        "operating_margin",
        "roe",
        "roic",
    ],
    "SAFETY": [
        "debt_to_equity",
        "net_debt_to_ebitda",
        "interest_coverage",
        "cfo_to_debt",
    ],
    "VALUATION": [
        "pe",
        "pb",
        "ev_to_ebitda",
        "fcf_yield",
    ],
}

OUTPUT_COLUMNS = [
    "ticker",
    "year",
    "module",
    "metric",
    "raw_value",
    "peer_percentile",
    "historical_percentile",
    "trend_score",
    "equity",
    "peer_method",
    "peer_quality",
    "peer_count",
    "peer_warning",
    "historical_valuation_score",
    "historical_valuation_available",
    "historical_valuation_reason",
    "fundamental_context_score",
]


def get_peer_percentile_file(ticker, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"peer_percentile_{ticker_lower}_{end_year}.csv"


def get_peer_snapshot_file(ticker, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"peer_snapshot_{ticker_lower}_{end_year}.csv"


def get_historical_percentile_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return (
        BASE_DIR
        / f"historical_percentile_{ticker_lower}_{start_year}_{end_year}.csv"
    )


def get_trend_score_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"trend_score_{ticker_lower}_{start_year}_{end_year}.csv"


def get_output_file(ticker, start_year, end_year):
    ticker_lower = ticker.strip().lower()
    return BASE_DIR / f"scoring_input_{ticker_lower}_{start_year}_{end_year}.csv"


def select_metric_values(dataframe, ticker, value_columns, year=None):
    required_columns = {"ticker", "metric", *value_columns}
    if year is not None:
        required_columns.add("year")

    missing_columns = required_columns.difference(dataframe.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Input CSV is missing required columns: {missing}")

    normalized_tickers = dataframe["ticker"].astype(str).str.strip().str.upper()
    mask = normalized_tickers.eq(ticker)
    if year is not None:
        mask &= dataframe["year"].eq(year)

    selected = dataframe.loc[mask, ["metric", *value_columns]].copy()
    if selected["metric"].duplicated().any():
        duplicates = selected.loc[selected["metric"].duplicated(), "metric"].tolist()
        raise ValueError(f"Duplicate metrics in input CSV: {duplicates}")

    return selected


def build_scoring_input(
    ticker,
    start_year,
    end_year,
    peer_df=None,
    snapshot_df=None,
    historical_df=None,
    trend_df=None,
    persist=True,
):
    target_ticker = ticker.strip().upper()
    current_year = end_year
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    peer_df = (
        pd.read_csv(get_peer_percentile_file(target_ticker, end_year))
        if peer_df is None else peer_df.copy()
    )
    snapshot_df = (
        pd.read_csv(get_peer_snapshot_file(target_ticker, end_year))
        if snapshot_df is None else snapshot_df.copy()
    )
    historical_df = (
        pd.read_csv(get_historical_percentile_file(
            target_ticker, start_year, end_year
        ))
        if historical_df is None else historical_df.copy()
    )
    trend_df = (
        pd.read_csv(get_trend_score_file(target_ticker, start_year, end_year))
        if trend_df is None else trend_df.copy()
    )

    peer_values = select_metric_values(
        peer_df,
        target_ticker,
        ["raw_value", "peer_percentile"],
        year=current_year,
    )
    peer_metadata_columns = [
        "peer_method",
        "peer_quality",
        "peer_count",
        "peer_warning",
    ]
    missing_peer_metadata = set(peer_metadata_columns).difference(peer_df.columns)
    if missing_peer_metadata:
        missing = ", ".join(sorted(missing_peer_metadata))
        raise ValueError(f"Peer percentile CSV is missing metadata: {missing}")
    normalized_peer_tickers = peer_df["ticker"].astype(str).str.strip().str.upper()
    target_peer_rows = peer_df.loc[normalized_peer_tickers.eq(target_ticker)]
    if target_peer_rows.empty:
        raise ValueError(f"No peer metadata for {target_ticker}")
    peer_metadata = {
        column: target_peer_rows.iloc[0][column]
        for column in peer_metadata_columns
    }
    historical_values = select_metric_values(
        historical_df,
        target_ticker,
        ["historical_percentile"],
        year=current_year,
    )
    trend_values = select_metric_values(
        trend_df,
        target_ticker,
        ["trend_score"],
    )

    required_snapshot_columns = {"ticker", "year", "equity"}
    missing_snapshot_columns = required_snapshot_columns.difference(
        snapshot_df.columns
    )
    if missing_snapshot_columns:
        missing = ", ".join(sorted(missing_snapshot_columns))
        raise ValueError(f"Peer snapshot CSV is missing required columns: {missing}")
    normalized_snapshot_tickers = (
        snapshot_df["ticker"].astype(str).str.strip().str.upper()
    )
    target_snapshot = snapshot_df.loc[
        normalized_snapshot_tickers.eq(target_ticker)
        & snapshot_df["year"].eq(current_year)
    ]
    if len(target_snapshot) != 1:
        raise ValueError(
            f"Expected one snapshot row for {target_ticker} {current_year}, "
            f"found {len(target_snapshot)}"
        )
    equity = pd.to_numeric(
        pd.Series([target_snapshot.iloc[0]["equity"]]), errors="coerce"
    ).iloc[0]

    base_rows = [
        {
            "ticker": target_ticker,
            "year": current_year,
            "module": module,
            "metric": metric,
        }
        for module, metrics in CORE_METRICS.items()
        for metric in metrics
    ]
    result_df = pd.DataFrame(base_rows)
    result_df = result_df.merge(
        peer_values, on="metric", how="left", validate="one_to_one"
    )
    result_df = result_df.merge(
        historical_values, on="metric", how="left", validate="one_to_one"
    )
    result_df = result_df.merge(
        trend_values, on="metric", how="left", validate="one_to_one"
    )
    result_df["equity"] = equity
    for field, value in peer_metadata.items():
        result_df[field] = value
    result_df["historical_valuation_score"] = float("nan")
    result_df["historical_valuation_available"] = False
    result_df["historical_valuation_reason"] = (
        "No point-in-time historical valuation series with publication-dated "
        "financials and historical shares is available."
    )
    result_df["fundamental_context_score"] = float("nan")
    result_df = result_df[OUTPUT_COLUMNS]

    output_file = get_output_file(target_ticker, start_year, end_year)
    if persist:
        result_df.to_csv(output_file, index=False, encoding="utf-8-sig")

    module_counts = result_df["module"].value_counts()
    missing_peer = result_df.loc[
        result_df["peer_percentile"].isna(), "metric"
    ].tolist()
    missing_historical = result_df.loc[
        result_df["historical_percentile"].isna(), "metric"
    ].tolist()
    missing_trend = result_df.loc[
        result_df["trend_score"].isna(), "metric"
    ].tolist()

    print(result_df.to_string(index=False))
    print("\nSUMMARY")
    print(f"Total rows: {len(result_df)}")
    for module in CORE_METRICS:
        print(f"{module} metrics: {int(module_counts.get(module, 0))}")
    print(
        "Metrics missing peer_percentile: "
        + (", ".join(missing_peer) if missing_peer else "none")
    )
    print(
        "Metrics missing historical_percentile: "
        + (", ".join(missing_historical) if missing_historical else "none")
    )
    print(
        "Metrics missing trend_score: "
        + (", ".join(missing_trend) if missing_trend else "none")
    )
    print("NaN values are preserved and were not filled with zero.")
    if persist:
        print(f"Saved to: {output_file.name}")

    return result_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build core metric scoring input.")
    parser.add_argument("ticker", help="Target ticker, for example FPT")
    parser.add_argument("start_year", type=int, help="First historical year")
    parser.add_argument("end_year", type=int, help="Current financial year")
    args = parser.parse_args()
    build_scoring_input(args.ticker, args.start_year, args.end_year)
