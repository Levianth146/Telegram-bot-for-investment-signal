"""Pure metric computation from annual BCTC dicts (no network).

Uses ``fundamental_filter.layer1_engine.ratios_*`` formulas. Input dicts match
``FinancialStatementProvider.get_annual`` / ``data/schemas/README.md``.
"""

from __future__ import annotations

from typing import Any

from fundamental_filter.layer1_engine import ratios_growth as growth
from fundamental_filter.layer1_engine import ratios_quality as quality
from fundamental_filter.layer1_engine import ratios_safety as safety
from fundamental_filter.layer1_engine import ratios_valuation as valuation
from fundamental_filter.layer1_engine.scoring_input import CORE_METRICS


def _get(data: dict[str, Any] | None, name: str):
    if data is None:
        return None
    return data.get(name)


def compute_year_metrics(
    ticker: str,
    year: int,
    current: dict[str, Any] | None,
    previous: dict[str, Any] | None,
    three_years_ago: dict[str, Any] | None,
    *,
    price: float | None = None,
    shares: float | None = None,
) -> dict[str, Any]:
    """Return one wide row of CORE (+ helper) metrics for ``ticker``/``year``."""
    current_tax_rate = quality.tax_rate(
        _get(current, "tax_expense"), _get(current, "pretax_profit")
    )
    current_nopat = quality.nopat(_get(current, "ebit"), current_tax_rate)
    current_debt = quality.total_debt(
        _get(current, "short_term_debt"), _get(current, "long_term_debt")
    )
    previous_debt = quality.total_debt(
        _get(previous, "short_term_debt"), _get(previous, "long_term_debt")
    )
    current_capital = quality.invested_capital(
        _get(current, "equity"), current_debt, _get(current, "cash")
    )
    previous_capital = quality.invested_capital(
        _get(previous, "equity"), previous_debt, _get(previous, "cash")
    )
    average_capital = quality.average_invested_capital(
        current_capital, previous_capital
    )
    debt = safety.total_debt(
        _get(current, "short_term_debt"), _get(current, "long_term_debt")
    )
    current_net_debt = safety.net_debt(debt, _get(current, "cash"))

    market_cap = valuation.calculate_market_cap(price, shares)
    book_value_per_share = valuation.calculate_book_value_per_share(
        _get(current, "equity"), shares
    )
    total_debt = valuation.calculate_total_debt(
        _get(current, "short_term_debt"), _get(current, "long_term_debt")
    )
    enterprise_value = valuation.calculate_enterprise_value(
        market_cap, total_debt, _get(current, "cash")
    )
    fcf = valuation.calculate_fcf(_get(current, "cfo"), _get(current, "capex"))

    return {
        "ticker": ticker.strip().upper(),
        "year": year,
        "equity": _get(current, "equity"),
        "revenue_growth_yoy": growth.revenue_growth_yoy(
            _get(current, "revenue"), _get(previous, "revenue")
        ),
        "npat_growth_yoy": growth.npat_growth_yoy(
            _get(current, "npat_parent"), _get(previous, "npat_parent")
        ),
        "eps_growth_yoy": growth.eps_growth_yoy(
            _get(current, "eps"), _get(previous, "eps")
        ),
        "revenue_cagr_3_year": growth.revenue_cagr_3_year(
            _get(current, "revenue"), _get(three_years_ago, "revenue")
        ),
        "eps_cagr_3_year": growth.eps_cagr_3_year(
            _get(current, "eps"), _get(three_years_ago, "eps")
        ),
        "operating_margin": quality.operating_margin(
            _get(current, "ebit"), _get(current, "revenue")
        ),
        "roe": quality.roe(
            _get(current, "npat_parent"),
            _get(current, "equity"),
            _get(previous, "equity"),
        ),
        "roic": quality.roic(current_nopat, average_capital),
        "cfo_to_npat": quality.cfo_to_npat(
            _get(current, "cfo"), _get(current, "npat_parent")
        ),
        "debt_to_equity": safety.debt_to_equity(debt, _get(current, "equity")),
        "net_debt_to_ebitda": safety.net_debt_to_ebitda(
            current_net_debt, _get(current, "ebitda")
        ),
        "interest_coverage": safety.interest_coverage(
            _get(current, "ebit"), _get(current, "interest_expense")
        ),
        "cfo_to_debt": safety.cfo_to_debt(_get(current, "cfo"), debt),
        "pe": valuation.calculate_pe(price, _get(current, "eps")),
        "pb": valuation.calculate_pb(
            price, book_value_per_share, _get(current, "equity")
        ),
        "ev_to_ebitda": valuation.calculate_ev_to_ebitda(
            enterprise_value, _get(current, "ebitda")
        ),
        "fcf_yield": valuation.calculate_fcf_yield(fcf, market_cap),
    }


def core_metric_names() -> list[str]:
    return [m for metrics in CORE_METRICS.values() for m in metrics]


def module_for_metric(metric: str) -> str:
    for module, metrics in CORE_METRICS.items():
        if metric in metrics:
            return module
    raise KeyError(metric)
