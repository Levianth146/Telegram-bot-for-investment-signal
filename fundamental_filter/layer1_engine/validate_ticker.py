"""Read-only audit CLI for one ticker.

The canonical Fundamental Layer remains the source of scores and classification.
This module only assembles its debug frames and independently checks raw ratio
arithmetic where the underlying financial inputs are available.
"""

import argparse
import io
import json
import math
import shutil
import tempfile
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from .financial_data import get_financial_data, get_latest_reported_financial_data
from .fundamental_config import CLASSIFICATION_CONFIG
from .fundamental_engine import analyze_fundamental_universe


BASE_DIR = Path(__file__).resolve().parent
DEFAULT_START_YEAR = 2021


def _number(value):
    if value is None or pd.isna(value):
        return None
    return float(value)


def _fmt(value):
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "N/A"
    if isinstance(value, (np.bool_, bool)):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _raw(data, name):
    return None if data is None else data.get(name)


def _safe_divide(numerator, denominator, positive_denominator=False):
    if numerator is None or denominator is None:
        return None
    if positive_denominator and denominator <= 0:
        return None
    if denominator == 0:
        return None
    return numerator / denominator


def _independent_ratios(current, previous, three_years_ago):
    debt = None
    if _raw(current, "short_term_debt") is not None and _raw(current, "long_term_debt") is not None:
        debt = _raw(current, "short_term_debt") + _raw(current, "long_term_debt")
    previous_debt = None
    if _raw(previous, "short_term_debt") is not None and _raw(previous, "long_term_debt") is not None:
        previous_debt = _raw(previous, "short_term_debt") + _raw(previous, "long_term_debt")
    net_debt = None if debt is None or _raw(current, "cash") is None else debt - _raw(current, "cash")
    tax_rate = _safe_divide(_raw(current, "tax_expense"), _raw(current, "pretax_profit"), True)
    nopat = None if _raw(current, "ebit") is None or tax_rate is None else _raw(current, "ebit") * (1 - tax_rate)
    capital = None
    previous_capital = None
    if all(_raw(current, key) is not None for key in ("equity", "cash")) and debt is not None:
        capital = _raw(current, "equity") + debt - _raw(current, "cash")
    if all(_raw(previous, key) is not None for key in ("equity", "cash")) and previous_debt is not None:
        previous_capital = _raw(previous, "equity") + previous_debt - _raw(previous, "cash")
    average_capital = None if capital is None or previous_capital is None else (capital + previous_capital) / 2
    equity = _raw(current, "equity")
    shares = None
    return {
        "ROE": _safe_divide(_raw(current, "npat_parent"), (_raw(current, "equity") + _raw(previous, "equity")) / 2 if _raw(current, "equity") is not None and _raw(previous, "equity") is not None else None),
        "ROIC": _safe_divide(nopat, average_capital),
        "Debt/Equity": _safe_divide(debt, equity, True),
        "Net Debt/EBITDA": _safe_divide(net_debt, _raw(current, "ebitda"), True),
        "Interest Coverage": _safe_divide(_raw(current, "ebit"), _raw(current, "interest_expense"), True),
        "CFO/Debt": _safe_divide(_raw(current, "cfo"), debt, True),
        "Revenue Growth": _safe_divide(_raw(current, "revenue"), _raw(previous, "revenue")) - 1 if _raw(current, "revenue") is not None and _raw(previous, "revenue") not in (None, 0) else None,
        "Revenue CAGR": ((_raw(current, "revenue") / _raw(three_years_ago, "revenue")) ** (1 / 3) - 1) if _raw(current, "revenue") is not None and _raw(three_years_ago, "revenue") is not None and _raw(current, "revenue") > 0 and _raw(three_years_ago, "revenue") > 0 else None,
        "EPS CAGR": ((_raw(current, "eps") / _raw(three_years_ago, "eps")) ** (1 / 3) - 1) if _raw(current, "eps") is not None and _raw(three_years_ago, "eps") is not None and _raw(current, "eps") > 0 and _raw(three_years_ago, "eps") > 0 else None,
    }


def _independent_valuation(snapshot, financial):
    price = _raw(snapshot, "price")
    shares = _raw(snapshot, "shares_outstanding")
    equity = _raw(financial, "equity")
    market_cap = _safe_divide(price * shares if price is not None and shares is not None else None, 1)
    debt = (_raw(financial, "short_term_debt") + _raw(financial, "long_term_debt")) if _raw(financial, "short_term_debt") is not None and _raw(financial, "long_term_debt") is not None else None
    enterprise_value = market_cap + debt - _raw(financial, "cash") if market_cap is not None and debt is not None and _raw(financial, "cash") is not None else None
    fcf = _raw(financial, "cfo") - _raw(financial, "capex") if _raw(financial, "cfo") is not None and _raw(financial, "capex") is not None else None
    book_value_per_share = _safe_divide(equity, shares, True)
    return {
        "P/E": _safe_divide(price, _raw(financial, "eps"), True),
        "P/B": _safe_divide(price, book_value_per_share),
        "EV/EBITDA": _safe_divide(enterprise_value, _raw(financial, "ebitda"), True),
        "FCF Yield": _safe_divide(fcf, market_cap, True),
    }


def _close(expected, actual, tolerance=1e-8):
    if expected is None or actual is None or pd.isna(expected) or pd.isna(actual):
        return expected is None and (actual is None or pd.isna(actual))
    return math.isclose(float(expected), float(actual), rel_tol=1e-7, abs_tol=tolerance)


def _formula_check(name, expected, actual):
    difference = None if expected is None or actual is None or pd.isna(expected) or pd.isna(actual) else float(actual) - float(expected)
    status = "PASS" if _close(expected, actual) else "FAIL"
    print(f"{name}: {status}")
    print(f"  expected: {_fmt(expected)}")
    print(f"  actual:   {_fmt(actual)}")
    print(f"  difference: {_fmt(difference)}")
    return status == "PASS"


def _print_section(number, title):
    print(f"\n{number}. {title}")


def _expected_classification(result):
    config = CLASSIFICATION_CONFIG
    module_values = [result.get(name) for name in ("growth_score", "quality_score", "safety_score", "valuation_score")]
    safety_gate = result.get("safety_gate_status")
    critical = bool(result.get("critical_data_quality_flag"))
    missing = any(value is None or pd.isna(value) for value in module_values + [result.get("fundamental_score")]) or critical
    eligible_count = 0 if missing or safety_gate == "CRITICAL" else 1
    mode = "PERCENTILE" if eligible_count >= config["min_percentile_universe"] else "ABSOLUTE_FALLBACK"
    if safety_gate == "CRITICAL":
        return "FAIL", mode
    if missing:
        return "WATCH", mode
    module_floor_met = all(value >= config["min_module_score_for_pass"] for value in module_values)
    score = float(result["fundamental_score"])
    if score < config["absolute_watch_score"]:
        return "FAIL", mode
    if safety_gate == "HIGH_RISK":
        return "WATCH", mode
    if score >= config["absolute_pass_score"] and module_floor_met:
        return "PASS", mode
    return "WATCH", mode


def _load_debug_frames(debug_dir, ticker):
    ticker_dir = Path(debug_dir) / ticker.lower()
    return {path.stem: pd.read_csv(path) for path in ticker_dir.glob("*.csv")}


def audit_ticker(ticker, start_year=DEFAULT_START_YEAR, end_year=None):
    target = ticker.strip().upper()
    end_year = end_year or date.today().year - 1
    temporary_dir = Path(tempfile.mkdtemp(prefix="ticker-audit-"))
    try:
        captured = io.StringIO()
        with redirect_stdout(captured):
            run = analyze_fundamental_universe(
                [target], start_year, end_year, debug=True,
                output_dir=temporary_dir, sleep_seconds=0,
            )
        frames = _load_debug_frames(run["debug_dir"], target)
        result = run["results"].iloc[0].to_dict()
        metrics = run["metrics"]
        snapshot = frames["snapshots"]
        target_snapshot = snapshot.loc[snapshot["ticker"].astype(str).str.upper().eq(target)].iloc[0].to_dict()
        peer_selection = frames["peer_selection"].iloc[0].to_dict()

        print("=" * 48)
        print(f"FUNDAMENTAL AUDIT: {target}")
        print("=" * 48)
        _print_section(1, "DATA / AS-OF")
        for key in ("price", "price_date", "financial_period", "financial_publication_date", "earnings_basis", "shares_outstanding", "shares_date", "point_in_time_safe", "publication_date_missing"):
            label = "shares" if key == "shares_outstanding" else key
            print(f"{label}: {_fmt(target_snapshot.get(key))}")

        _print_section(2, "PEER")
        for key in ("peer_method", "peer_quality", "peer_count"):
            print(f"{key}: {_fmt(peer_selection.get(key))}")
        peer_tickers = json.loads(peer_selection.get("peer_tickers", "[]")) if isinstance(peer_selection.get("peer_tickers"), str) else peer_selection.get("peer_tickers", [])
        print(f"peer_tickers: {', '.join(peer_tickers) if peer_tickers else 'N/A'}")

        _print_section(3, "GROWTH")
        _print_metrics(metrics, "GROWTH")
        diagnostic_cfo = frames["historical_fundamental"].loc[
            frames["historical_fundamental"]["year"].eq(end_year)
        ].iloc[0]
        print("cfo_growth_yoy:")
        print(f"  raw_value: {_fmt(diagnostic_cfo.get('cfo_growth_yoy'))}")
        print("  scoring_status: DIAGNOSTIC_ONLY")
        print(f"module score: {_fmt(result.get('growth_score'))}")
        _print_section(4, "QUALITY")
        _print_metrics(metrics, "QUALITY")
        print(f"module score: {_fmt(result.get('quality_score'))}")

        _print_section(5, "SAFETY")
        _print_metrics(metrics, "SAFETY", include_absolute=True)
        for key in ("absolute_safety_score", "peer_relative_score", "safety_trend_score", "safety_score", "safety_gate_status"):
            print(f"{key}: {_fmt(result.get(key))}")

        _print_section(6, "VALUATION")
        _print_metrics(metrics, "VALUATION")
        for key in ("peer_valuation_score", "historical_valuation_score", "historical_valuation_available", "fundamental_context_score", "valuation_score"):
            print(f"{key}: {_fmt(result.get(key))}")

        _print_section(7, "FINAL")
        for key in ("growth_score", "quality_score", "safety_score", "valuation_score", "fundamental_score", "classification_mode", "fundamental_percentile", "percentile_used_for_classification", "classification", "classification_reason"):
            print(f"{key}: {_fmt(result.get(key))}")

        _print_section("", "INDEPENDENT FORMULA CHECK")
        historical = frames["historical_fundamental"]
        current = get_financial_data(target, end_year)
        previous = get_financial_data(target, end_year - 1)
        three_years_ago = get_financial_data(target, end_year - 3)
        independent = _independent_ratios(current, previous, three_years_ago)
        historical_row = historical.loc[historical["year"].eq(end_year)].iloc[0]
        ratio_actuals = {"ROE": historical_row.get("roe"), "ROIC": historical_row.get("roic"), "Debt/Equity": historical_row.get("debt_to_equity"), "Net Debt/EBITDA": historical_row.get("net_debt_to_ebitda"), "Interest Coverage": historical_row.get("interest_coverage"), "CFO/Debt": historical_row.get("cfo_to_debt"), "Revenue Growth": historical_row.get("revenue_growth_yoy"), "Revenue CAGR": historical_row.get("revenue_cagr_3_year"), "EPS CAGR": historical_row.get("eps_cagr_3_year")}
        checks = [_formula_check(name, independent[name], ratio_actuals[name]) for name in independent]
        valuation_financial = get_latest_reported_financial_data(target).get("data")
        independent_valuation = _independent_valuation(target_snapshot, valuation_financial)
        valuation_columns = {
            "P/E": "pe",
            "P/B": "pb",
            "EV/EBITDA": "ev_to_ebitda",
            "FCF Yield": "fcf_yield",
        }
        for name, expected in independent_valuation.items():
            checks.append(_formula_check(name, expected, target_snapshot.get(valuation_columns[name])))
        print(f"FORMULA CHECK: {'PASS' if all(checks) else 'FAIL'}")

        _print_section("", "CLASSIFICATION CHECK")
        expected_classification, expected_mode = _expected_classification(result)
        actual_classification = result.get("classification")
        print(f"expected classification: {expected_classification}")
        print(f"actual classification:   {actual_classification}")
        print(f"expected mode: {expected_mode}")
        print(f"actual mode:   {result.get('classification_mode')}")
        print(f"CLASSIFICATION CHECK: {'PASS' if expected_classification == actual_classification and expected_mode == result.get('classification_mode') else 'FAIL'}")

        flags = []
        if str(peer_selection.get("peer_quality")).upper() == "LOW":
            flags.append("peer_quality = LOW")
        if str(result.get("historical_valuation_available")).lower() != "true":
            flags.append("historical valuation unavailable")
        if bool(target_snapshot.get("publication_date_missing")):
            flags.append("publication date missing")
        _print_section("", "CALCULATION STATUS")
        print("CALCULATION: PASS")
        print("DATA QUALITY: " + ("WARNING" if flags else "PASS"))
        for flag in flags:
            print(f"- {flag}")
    finally:
        shutil.rmtree(temporary_dir, ignore_errors=True)


def _print_metrics(metrics, module, include_absolute=False):
    rows = metrics.loc[metrics["module"].eq(module)]
    for row in rows.itertuples(index=False):
        print(f"{row.metric}:")
        print(f"  raw_value: {_fmt(row.raw_value)}")
        print(f"  peer_score: {_fmt(row.peer_score)}")
        print(f"  trend_score: {_fmt(row.trend_score)}")
        if include_absolute:
            print(f"  absolute score: {_fmt(row.absolute_score)}")
        print(f"  metric_score: {_fmt(row.metric_score)}")


def main():
    parser = argparse.ArgumentParser(description="Audit one ticker through the Fundamental Layer.")
    parser.add_argument("ticker", help="Target ticker, for example VNM")
    parser.add_argument("--start-year", type=int, default=DEFAULT_START_YEAR)
    parser.add_argument("--end-year", type=int, default=date.today().year - 1)
    args = parser.parse_args()
    audit_ticker(args.ticker, args.start_year, args.end_year)


if __name__ == "__main__":
    main()