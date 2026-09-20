CURATED_PEERS = {}

PEER_SELECTION_CONFIG = {
    "min_primary_peers": 5,
    "min_percentile_peers": 5,
    "size_ratio_min": 0.30,
    "size_ratio_max": 3.00,
}

PEER_QUALITY_MULTIPLIERS = {
    "HIGH": 1.00,
    "MEDIUM": 0.75,
    "LOW": 0.50,
    "UNAVAILABLE": 0.00,
}

GROWTH_QUALITY_COMPONENT_WEIGHTS = {
    "peer": 0.65,
    "trend": 0.35,
}

VALUATION_COMPONENT_WEIGHTS = {
    "peer": 0.50,
    "historical": 0.35,
    "fundamental_context": 0.15,
}

VALUATION_METRIC_WEIGHTS = {
    "pe": 0.25,
    "pb": 0.10,
    "ev_to_ebitda": 0.30,
    "fcf_yield": 0.35,
}

SAFETY_ANCHORS = {
    "debt_to_equity": [
        (0.0, 100), (0.3, 90), (0.6, 75), (1.0, 55),
        (1.5, 30), (2.0, 10), (3.0, 0),
    ],
    "net_debt_to_ebitda": [
        (0.0, 100), (1.0, 90), (2.0, 75), (3.0, 55),
        (4.0, 35), (6.0, 10), (8.0, 0),
    ],
    "interest_coverage": [
        (0.0, 0), (1.0, 10), (1.5, 25), (2.0, 40),
        (3.0, 60), (5.0, 80), (8.0, 90), (12.0, 100),
    ],
    "cfo_to_debt": [
        (-0.20, 0), (0.00, 10), (0.10, 30), (0.20, 50),
        (0.35, 70), (0.50, 85), (0.75, 95), (1.00, 100),
    ],
}

ABSOLUTE_SAFETY_WEIGHTS = {
    "debt_to_equity": 0.10,
    "net_debt_to_ebitda": 0.35,
    "interest_coverage": 0.30,
    "cfo_to_debt": 0.25,
}

FINAL_SAFETY_WEIGHTS = {
    "absolute_safety_score": 0.60,
    "peer_relative_score": 0.25,
    "safety_trend_score": 0.15,
}

SAFETY_GATE_THRESHOLDS = {
    "critical_interest_coverage": 1.0,
    "high_risk_net_debt_to_ebitda": 4.0,
    "high_risk_debt_to_equity": 2.0,
    "high_risk_cfo_to_debt": 0.10,
    "high_risk_interest_coverage": 2.0,
    "high_risk_condition_count": 2,
}

MODULE_METRIC_WEIGHTS = {
    # CURRENT YoY share weight; CAGR carries sustainability (anti double-count)
    "GROWTH": {
        "revenue_growth_yoy": 0.15,
        "npat_growth_yoy": 0.15,
        "eps_growth_yoy": 0.15,
        "revenue_cagr_3_year": 0.20,
        "eps_cagr_3_year": 0.35,
    },
    "QUALITY": {
        "operating_margin": 0.20,
        "roe": 0.25,
        "roic": 0.35,
        "cfo_to_npat": 0.20,  # Cash Conversion (mục 3.4)
    },
    "SAFETY": ABSOLUTE_SAFETY_WEIGHTS.copy(),
    "VALUATION": VALUATION_METRIC_WEIGHTS.copy(),
}

FUNDAMENTAL_MODULE_WEIGHTS = {
    "GROWTH": 0.25,
    "QUALITY": 0.25,
    "SAFETY": 0.25,
    "VALUATION": 0.25,
}

CLASSIFICATION_CONFIG = {
    "min_percentile_universe": 20,
    "pass_percentile": 0.60,
    "watch_percentile": 0.30,
    "absolute_pass_score": 65.0,
    "absolute_watch_score": 45.0,
    "min_module_score_for_pass": 40.0,
}
