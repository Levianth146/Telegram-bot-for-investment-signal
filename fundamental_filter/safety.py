"""Module Safety — Câu hỏi 3: Doanh nghiệp có an toàn tài chính không?

Tham chiếu: Mục 4 (Current/Quick/Cash Ratio, D/E, Net Debt/EBITDA,
Interest Coverage, DSO/DIO, và Merton Distance-to-Default ở mục 4.6 — P2,
chỉ bật sau khi qua docs/DATA_AUDIT.md).
"""

from __future__ import annotations

from .layer1_engine.ratios_safety import interest_coverage as _interest_coverage
from .layer1_engine.ratios_safety import net_debt_to_ebitda as _net_debt_to_ebitda


def net_debt_to_ebitda(net_debt: float, ebitda: float) -> float:
    """Mục 4.2 — headline metric của module Safety (xem mục 6.1)."""
    result = _net_debt_to_ebitda(net_debt, ebitda)
    if result is None:
        raise ValueError("net_debt_to_ebitda requires finite net debt and positive EBITDA")
    return float(result)


def interest_coverage(ebit: float, interest_expense: float) -> float:
    """Mục 4.3 — supporting metric, chỉ nói khi Net Debt/EBITDA đang xấu đi."""
    result = _interest_coverage(ebit, interest_expense)
    if result is None:
        raise ValueError("interest_coverage requires finite EBIT and positive interest")
    return float(result)


def merton_distance_to_default(
    equity_value: float,
    equity_vol: float,
    debt_face_value: float,
    risk_free_rate: float,
    horizon_years: float = 1.0,
) -> float:
    """Mục 4.6 (P2) — naive Bharath & Shumway (2008) Distance-to-Default.

    Uses equity value/vol as asset proxies when full liability term structure is
    unavailable (DATA_AUDIT: maturity detail missing). Callers must keep
    ``safety_merton_dd.enabled=false`` until audit says otherwise; when enabled,
    missing inputs should omit the metric (ARCHITECTURE #4 fallback) rather than
    zero-penalize.

    DD ≈ [ln((E+D)/D) + (r − 0.5 σ_E²) T] / (σ_E √T)
    """
    import math

    e = float(equity_value)
    sigma = float(equity_vol)
    d = float(debt_face_value)
    r = float(risk_free_rate)
    t = float(horizon_years)
    if e <= 0 or d <= 0 or sigma <= 0 or t <= 0:
        raise ValueError(
            "merton_distance_to_default requires positive equity, debt, vol, horizon"
        )
    asset = e + d
    numer = math.log(asset / d) + (r - 0.5 * sigma * sigma) * t
    denom = sigma * math.sqrt(t)
    return float(numer / denom)


def safety_score(financials_history, config: dict) -> dict:
    """Tổng hợp điểm Safety. Đọc config['fundamental_filter']['safety_merton_dd']['enabled']
    để quyết định có tính DD hay không — xem mục 11.4 (fallback khi thiếu dữ liệu).
    """
    merton_cfg = (
        (config or {}).get("fundamental_filter", {}).get("safety_merton_dd", {})
        if config
        else {}
    )
    merton_enabled = bool(merton_cfg.get("enabled", False))

    if isinstance(financials_history, dict):
        score = financials_history.get("score", financials_history.get("safety_score"))
        headline = financials_history.get("headline") or {
            "metric": "net_debt_to_ebitda",
            "value": financials_history.get("net_debt_to_ebitda"),
        }
        supporting = dict(financials_history.get("supporting") or {})
    elif financials_history is None:
        raise ValueError("financials_history is required")
    else:
        score = float(financials_history)
        headline = {"metric": "net_debt_to_ebitda"}
        supporting = {}

    # Mục 11.4: missing advanced metric → omit, do not zero-penalize
    supporting["merton_dd"] = None
    if merton_enabled:
        try:
            supporting["merton_dd"] = merton_distance_to_default(
                float(financials_history.get("equity_value")),
                float(financials_history.get("equity_vol")),
                float(financials_history.get("debt_face_value")),
                float(financials_history.get("risk_free_rate", 0.05)),
                float(financials_history.get("horizon_years", 1.0)),
            )
            supporting["merton_dd_status"] = "computed_naive_bs2008"
        except (TypeError, ValueError, AttributeError):
            supporting["merton_dd_status"] = "enabled_but_inputs_missing"
    else:
        supporting["merton_dd_status"] = "disabled"

    return {"score": score, "headline": headline, "supporting": supporting}
