import argparse
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from fundamental_classification import classify_fundamental_universe
from fundamental_score import run_fundamental_score
from historical_fundamental import get_historical_fundamental
from metric_score import run_metric_score
from module_score import run_module_score
from peer_coverage_runner import run_peer_coverage
from peer_percentile import run_peer_percentile
from peer_snapshot_runner import run_peer_snapshot
from scoring_input import CORE_METRICS, build_scoring_input
from trend_analysis import run_trend_analysis
from trend_score import run_trend_score


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = BASE_DIR / "outputs"


def _normalize_tickers(tickers):
    if isinstance(tickers, str):
        tickers = tickers.split(",")
    result = []
    seen = set()
    for value in tickers:
        ticker = str(value).strip().upper()
        if ticker and ticker not in seen:
            result.append(ticker)
            seen.add(ticker)
    if not result:
        raise ValueError("At least one ticker is required")
    return result


def _empty_historical_percentiles(ticker, year):
    return pd.DataFrame(
        [
            {
                "ticker": ticker,
                "year": year,
                "metric": metric,
                "historical_percentile": np.nan,
            }
            for metrics in CORE_METRICS.values()
            for metric in metrics
        ]
    )


def score_current_universe(scoring_frames, start_year, end_year):
    """Score and classify only the explicitly supplied current-run universe."""
    metric_frames = []
    score_frames = []
    stage_results = {}

    for ticker, scoring_df in scoring_frames.items():
        target = ticker.strip().upper()
        metric_df = run_metric_score(
            target, start_year, end_year, scoring_df=scoring_df, persist=False
        )
        module_df = run_module_score(
            target, start_year, end_year, metric_df=metric_df, persist=False
        )
        score_df = run_fundamental_score(
            target, start_year, end_year, module_df=module_df, persist=False
        )
        metric_frames.append(metric_df)
        score_frames.append(score_df)
        stage_results[target] = {
            "scoring_input": scoring_df,
            "metric_score": metric_df,
            "module_score": module_df,
            "fundamental_score": score_df,
        }

    score_universe = pd.concat(score_frames, ignore_index=True)
    classification = classify_fundamental_universe(score_universe)
    results = score_universe.merge(
        classification[
            [
                "ticker",
                "fundamental_percentile",
                "classification",
                "classification_reason",
                "classification_flags",
                "classification_mode",
                "percentile_used_for_classification",
                "classification_universe_size",
                "classification_as_of_date",
            ]
        ],
        on="ticker",
        how="left",
        validate="one_to_one",
    )
    metrics = pd.concat(metric_frames, ignore_index=True).rename(
        columns={
            "peer_percentile": "peer_score",
            "absolute_metric_score": "absolute_score",
            "score_reweight_reason": "data_quality",
        }
    )
    return results, metrics, stage_results


def _write_debug_frames(debug_dir, ticker, frames):
    ticker_dir = debug_dir / ticker.lower()
    ticker_dir.mkdir(parents=True, exist_ok=True)
    for name, frame in frames.items():
        if isinstance(frame, pd.DataFrame):
            frame.to_csv(
                ticker_dir / f"{name}.csv", index=False, encoding="utf-8-sig"
            )


def write_run_outputs(results, metrics, output_dir=None, debug=False, debug_frames=None):
    """Write only final production outputs; debug frames are opt-in and isolated."""
    destination = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    destination.mkdir(parents=True, exist_ok=True)
    results.to_csv(
        destination / "fundamental_results.csv", index=False, encoding="utf-8-sig"
    )
    metrics.to_csv(
        destination / "fundamental_metrics.csv", index=False, encoding="utf-8-sig"
    )
    debug_dir = None
    if debug:
        run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        debug_dir = destination / "debug" / run_id
        for ticker, frames in (debug_frames or {}).items():
            _write_debug_frames(debug_dir, ticker, frames)
    return debug_dir


def analyze_fundamental_universe(
    tickers,
    start_year,
    end_year,
    debug=False,
    output_dir=None,
    sleep_seconds=4,
):
    """Run the Fundamental Layer in memory for an explicit ticker universe."""
    targets = _normalize_tickers(tickers)
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year")

    scoring_frames = {}
    upstream_frames = {}
    for ticker in targets:
        coverage = run_peer_coverage(
            ticker, end_year, persist=False, sleep_seconds=sleep_seconds
        )
        selection_columns = [
            "peer_method",
            "peer_quality",
            "peer_count",
            "peer_tickers",
            "peer_industry",
            "peer_industry_code",
            "peer_sub_industry",
            "size_filter_applied",
            "fallback_used",
            "peer_warning",
        ]
        selection = coverage.iloc[[0]][selection_columns].copy()
        selection.insert(0, "ticker", ticker)
        snapshots = run_peer_snapshot(
            ticker,
            end_year,
            coverage_df=coverage,
            persist=False,
            sleep_seconds=sleep_seconds,
        )
        peer_percentiles = run_peer_percentile(
            ticker,
            end_year,
            snapshot_df=snapshots,
            selection_df=selection,
            persist=False,
        )
        historical = get_historical_fundamental(
            ticker, start_year, end_year, persist=False
        )
        trend_analysis = run_trend_analysis(
            ticker,
            start_year,
            end_year,
            historical_df=historical,
            persist=False,
        )
        trends = run_trend_score(
            ticker,
            start_year,
            end_year,
            trend_df=trend_analysis,
            persist=False,
        )
        scoring = build_scoring_input(
            ticker,
            start_year,
            end_year,
            peer_df=peer_percentiles,
            snapshot_df=snapshots,
            historical_df=_empty_historical_percentiles(ticker, end_year),
            trend_df=trends,
            persist=False,
        )
        scoring_frames[ticker] = scoring
        upstream_frames[ticker] = {
            "coverage": coverage,
            "peer_selection": selection,
            "snapshots": snapshots,
            "peer_percentiles": peer_percentiles,
            "historical_fundamental": historical,
            "trend_analysis": trend_analysis,
            "trend_scores": trends,
        }

    results, metrics, downstream = score_current_universe(
        scoring_frames, start_year, end_year
    )
    debug_frames = {
        ticker: {**upstream_frames[ticker], **downstream[ticker]}
        for ticker in targets
    }
    debug_dir = write_run_outputs(
        results,
        metrics,
        output_dir=output_dir,
        debug=debug,
        debug_frames=debug_frames,
    )

    return {"results": results, "metrics": metrics, "debug_dir": debug_dir}


def analyze_fundamental(ticker, start_year, end_year):
    """Backward-compatible single-ticker entry point without stale CSV state."""
    run = analyze_fundamental_universe([ticker], start_year, end_year)
    return run["results"].iloc[0].to_dict()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run the in-memory Fundamental Layer for a current universe."
    )
    parser.add_argument("tickers", help="Comma-separated tickers, for example VNM,FPT")
    parser.add_argument("start_year", type=int)
    parser.add_argument("end_year", type=int)
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--sleep-seconds", type=float, default=4.0)
    args = parser.parse_args()
    run = analyze_fundamental_universe(
        args.tickers,
        args.start_year,
        args.end_year,
        debug=args.debug,
        output_dir=args.output_dir,
        sleep_seconds=args.sleep_seconds,
    )
    print(run["results"].to_string(index=False))
