import unittest

import numpy as np
import pandas as pd

from .metric_score import calculate_metric_scores
from .safety_scoring import (
    ABSOLUTE_SAFETY_WEIGHTS,
    FINAL_SAFETY_WEIGHTS,
    calculate_absolute_metric_score,
    calculate_safety_components,
    get_safety_gate_status,
    validate_safety_weights,
)


class SafetyScoringTests(unittest.TestCase):
    def setUp(self):
        self.safe_raw = {
            "debt_to_equity": 0.30,
            "net_debt_to_ebitda": 0.70,
            "interest_coverage": 25.0,
            "cfo_to_debt": 0.80,
        }
        self.risky_raw = {
            "debt_to_equity": 1.80,
            "net_debt_to_ebitda": 4.50,
            "interest_coverage": 2.0,
            "cfo_to_debt": 0.15,
        }

    def components(self, raw, peer_value, trend_value):
        peer = {metric: peer_value for metric in ABSOLUTE_SAFETY_WEIGHTS}
        trend = {metric: trend_value for metric in ABSOLUTE_SAFETY_WEIGHTS}
        return calculate_safety_components(raw, peer, trend)

    def test_a_safe_but_deteriorating_remains_supported_by_absolute_strength(self):
        result = self.components(self.safe_raw, peer_value=50, trend_value=0)
        self.assertGreaterEqual(result["absolute_safety_score"], 90)
        self.assertGreaterEqual(result["safety_score"], 60)

    def test_b_risky_but_improving_does_not_beat_safe_company(self):
        safe = self.components(self.safe_raw, peer_value=50, trend_value=0)
        risky = self.components(self.risky_raw, peer_value=50, trend_value=100)
        self.assertLess(risky["absolute_safety_score"], 50)
        self.assertLess(risky["safety_score"], safe["safety_score"])

    def test_c_bad_industry_cannot_be_rescued_by_top_peer_rank(self):
        raw = {
            "debt_to_equity": 2.50,
            "net_debt_to_ebitda": 7.0,
            "interest_coverage": 1.2,
            "cfo_to_debt": 0.05,
        }
        result = self.components(raw, peer_value=100, trend_value=100)
        self.assertLess(result["absolute_safety_score"], 25)
        self.assertLess(result["safety_score"], 60)

    def test_d_strong_company_keeps_high_absolute_score_in_strong_industry(self):
        raw = {
            "debt_to_equity": 0.40,
            "net_debt_to_ebitda": 0.60,
            "interest_coverage": 20.0,
            "cfo_to_debt": 0.80,
        }
        result = self.components(raw, peer_value=0, trend_value=0)
        self.assertGreaterEqual(result["absolute_safety_score"], 90)

    def test_e_absolute_metric_scores_are_monotonic(self):
        checks = [
            ("debt_to_equity", [0.0, 0.3, 1.0, 2.0, 3.0], False),
            ("net_debt_to_ebitda", [-1.0, 0.0, 2.0, 4.0, 8.0], False),
            ("interest_coverage", [0.0, 1.0, 3.0, 8.0, 20.0], True),
            ("cfo_to_debt", [-0.2, 0.0, 0.2, 0.75, 2.0], True),
        ]
        for metric, values, increasing in checks:
            scores = [calculate_absolute_metric_score(metric, value) for value in values]
            comparisons = zip(scores, scores[1:])
            if increasing:
                self.assertTrue(all(left <= right for left, right in comparisons))
            else:
                self.assertTrue(all(left >= right for left, right in comparisons))

    def test_f_historical_percentile_is_not_a_safety_score_input(self):
        rows = []
        for metric, raw in self.safe_raw.items():
            rows.append(
                {
                    "module": "SAFETY",
                    "metric": metric,
                    "raw_value": raw,
                    "peer_percentile": 50.0,
                    "historical_percentile": 0.0,
                    "trend_score": 50.0,
                    "equity": 100.0,
                }
            )
        first = calculate_metric_scores(pd.DataFrame(rows))
        changed = pd.DataFrame(rows)
        changed["historical_percentile"] = 100.0
        second = calculate_metric_scores(changed)
        np.testing.assert_allclose(first["metric_score"], second["metric_score"])

    def test_g_growth_quality_and_valuation_follow_current_formulas(self):
        rows = pd.DataFrame(
            [
                {
                    "module": "GROWTH",
                    "metric": "revenue_growth_yoy",
                    "raw_value": 1.0,
                    "peer_percentile": 60.0,
                    "historical_percentile": 40.0,
                    "trend_score": np.nan,
                    "equity": 100.0,
                },
                {
                    "module": "QUALITY",
                    "metric": "roe",
                    "raw_value": 1.0,
                    "peer_percentile": 60.0,
                    "historical_percentile": 40.0,
                    "trend_score": 20.0,
                    "equity": 100.0,
                },
                {
                    "module": "VALUATION",
                    "metric": "pe",
                    "raw_value": 1.0,
                    "peer_percentile": 60.0,
                    "historical_percentile": np.nan,
                    "trend_score": np.nan,
                    "equity": 100.0,
                },
            ]
        )
        result = calculate_metric_scores(rows).set_index("module")
        self.assertEqual(result.loc["GROWTH", "metric_score"], 60.0)
        self.assertEqual(result.loc["QUALITY", "metric_score"], 46.0)
        self.assertEqual(result.loc["VALUATION", "metric_score"], 60.0)

    def test_gate_rules_and_weight_totals(self):
        validate_safety_weights()
        self.assertAlmostEqual(sum(ABSOLUTE_SAFETY_WEIGHTS.values()), 1.0)
        self.assertAlmostEqual(sum(FINAL_SAFETY_WEIGHTS.values()), 1.0)
        self.assertEqual(get_safety_gate_status(self.safe_raw, 100), "NORMAL")
        self.assertEqual(
            get_safety_gate_status({**self.safe_raw, "interest_coverage": 0.9}, 100),
            "CRITICAL",
        )
        self.assertEqual(get_safety_gate_status(self.safe_raw, 0), "CRITICAL")
        high_risk = {
            "debt_to_equity": 2.1,
            "net_debt_to_ebitda": 4.1,
            "interest_coverage": 3.0,
            "cfo_to_debt": 0.2,
        }
        self.assertEqual(get_safety_gate_status(high_risk, 100), "HIGH_RISK")
        # Levered + non-positive EBITDA sentinel (99) trips ND/EBITDA high-risk alone
        # when combined with another condition — here D/E also high.
        levered_bad_ebitda = {
            "debt_to_equity": 2.1,
            "net_debt_to_ebitda": 99.0,
            "interest_coverage": 5.0,
            "cfo_to_debt": 0.5,
        }
        self.assertEqual(get_safety_gate_status(levered_bad_ebitda, 100), "HIGH_RISK")

    def test_missing_input_is_not_filled_or_renormalized(self):
        raw = {**self.safe_raw, "cfo_to_debt": np.nan}
        result = self.components(raw, peer_value=50, trend_value=50)
        self.assertTrue(np.isnan(result["absolute_safety_score"]))
        self.assertTrue(np.isnan(result["safety_score"]))


if __name__ == "__main__":
    unittest.main()
