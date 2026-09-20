import unittest

import numpy as np
import pandas as pd

import trend_analysis
from fundamental_config import MODULE_METRIC_WEIGHTS
from scoring_input import CORE_METRICS
from fundamental_classification import classify_fundamental_universe
from metric_score import calculate_metric_scores
from peer_selector import select_peer_universe
from scoring_utils import normalize_available_weights
from valuation_scoring import (
    calculate_historical_valuation_score,
    calculate_valuation_components,
    is_point_in_time_observation,
)


class PeerSelectionTests(unittest.TestCase):
    def candidates(self):
        return pd.DataFrame(
            [
                {"ticker": ticker, "coverage_eligible": True, "market_cap": cap,
                 "sub_industry": sub}
                for ticker, cap, sub in [
                    ("AAA", 80, "MILK"), ("BBB", 90, "MILK"),
                    ("CCC", 100, "MILK"), ("DDD", 110, "MILK"),
                    ("EEE", 120, "MILK"), ("FFF", 900, "FOOD"),
                ]
            ]
        )

    def test_a1_curated_override_has_priority(self):
        selected, meta = select_peer_universe(
            "TGT", self.candidates(), curated_peers=["AAA", "BBB", "CCC", "DDD", "EEE"]
        )
        self.assertEqual(meta["peer_method"], "CURATED")
        self.assertEqual(selected, ["AAA", "BBB", "CCC", "DDD", "EEE"])

    def test_a2_sub_industry_and_size_are_preferred(self):
        selected, meta = select_peer_universe(
            "TGT", self.candidates(), target_market_cap=100,
            target_sub_industry="MILK", curated_peers=[]
        )
        self.assertEqual(meta["peer_method"], "SUB_INDUSTRY_SIZE")
        self.assertNotIn("FFF", selected)

    def test_a3_industry_fallback_is_low_quality(self):
        selected, meta = select_peer_universe(
            "TGT", self.candidates().drop(columns="sub_industry"),
            target_market_cap=None, curated_peers=[]
        )
        self.assertEqual(meta["peer_method"], "INDUSTRY_FALLBACK")
        self.assertEqual(meta["peer_quality"], "LOW")
        self.assertTrue(meta["fallback_used"])

    def test_a4_missing_peer_reweights_without_zero_fill(self):
        score, weights, _ = normalize_available_weights(
            {"peer": 0.65, "trend": 0.35},
            {"peer": np.nan, "trend": 80.0},
        )
        self.assertEqual(score, 80.0)
        self.assertEqual(weights, {"peer": 0.0, "trend": 1.0})

    def test_a5_target_is_never_its_own_peer(self):
        candidates = pd.concat(
            [self.candidates(), pd.DataFrame([{"ticker": "TGT", "coverage_eligible": True,
                                               "market_cap": 100, "sub_industry": "MILK"}])]
        )
        selected, _ = select_peer_universe(
            "TGT", candidates, target_market_cap=100,
            target_sub_industry="MILK", curated_peers=[]
        )
        self.assertNotIn("TGT", selected)
        self.assertEqual(len(selected), len(set(selected)))


class HistoricalPercentileExclusionTests(unittest.TestCase):
    @staticmethod
    def row(module, metric, historical):
        return {
            "module": module,
            "metric": metric,
            "raw_value": 1.0,
            "peer_percentile": 60.0,
            "historical_percentile": historical,
            "trend_score": 20.0,
            "equity": 100.0,
            "peer_quality": "HIGH",
        }

    def test_b1_growth_weights_exclude_cfo_and_sum_to_one(self):
        growth_weights = MODULE_METRIC_WEIGHTS["GROWTH"]
        self.assertNotIn("cfo_growth_yoy", growth_weights)
        self.assertAlmostEqual(sum(growth_weights.values()), 1.0)
        self.assertEqual(CORE_METRICS["GROWTH"], list(growth_weights))

    def test_b2_quality_ignores_historical_percentile(self):
        low = calculate_metric_scores(pd.DataFrame([self.row("QUALITY", "roe", 0)]))
        high = calculate_metric_scores(pd.DataFrame([self.row("QUALITY", "roe", 100)]))
        self.assertEqual(low.iloc[0]["metric_score"], high.iloc[0]["metric_score"])

    def test_b3_cfo_growth_is_diagnostic_only(self):
        row = self.row("GROWTH", "cfo_growth_yoy", 0)
        result = calculate_metric_scores(pd.DataFrame([row])).iloc[0]
        self.assertEqual(row["raw_value"], 1.0)
        self.assertTrue(pd.isna(result["peer_percentile"]))
        self.assertTrue(pd.isna(result["trend_score"]))
        self.assertTrue(pd.isna(result["metric_score"]))
        self.assertEqual(result["score_reweight_reason"], "diagnostic_only")

    def test_b4_growth_raw_metrics_remain_available_to_trend(self):
        for metric in ("revenue_growth_yoy", "revenue_cagr_3_year", "eps_cagr_3_year"):
            self.assertIn(metric, trend_analysis.HIGHER_IS_BETTER)

    def test_b5_safety_and_valuation_do_not_use_historical_percentile(self):
        safety = self.row("SAFETY", "debt_to_equity", 0)
        safety["raw_value"] = 0.3
        valuation = self.row("VALUATION", "pe", 0)
        first = calculate_metric_scores(pd.DataFrame([safety, valuation]))
        safety["historical_percentile"] = 100
        valuation["historical_percentile"] = 100
        second = calculate_metric_scores(pd.DataFrame([safety, valuation]))
        np.testing.assert_allclose(first["metric_score"], second["metric_score"])


class ValuationHybridTests(unittest.TestCase):
    def observations(self, score_shift=0):
        values = [10, 12, 14, 16]
        rows = []
        for index, pe in enumerate(values, start=1):
            rows.append({
                "observation_date": f"2024-0{index}-28",
                "price_date": f"2024-0{index}-27",
                "shares_date": f"2024-0{index}-20",
                "financial_publication_date": f"2024-0{index}-15",
                "point_in_time_safe": True,
                "pe": pe + score_shift, "pb": pe / 5, "ev_to_ebitda": pe / 2,
                "fcf_yield": 0.02 + index * 0.01,
            })
        return rows

    def test_c1_safe_historical_valuation_is_used(self):
        score, _, count = calculate_historical_valuation_score(
            {"pe": 11, "pb": 2.1, "ev_to_ebitda": 5.5, "fcf_yield": 0.05},
            self.observations(), "2024-12-31"
        )
        self.assertFalse(np.isnan(score))
        self.assertEqual(count, 4)

    def test_c2_unsafe_history_is_unavailable_and_weights_normalize(self):
        rows = self.observations()
        for row in rows:
            row["point_in_time_safe"] = False
        score, _, _ = calculate_historical_valuation_score(
            {"pe": 11, "pb": 2, "ev_to_ebitda": 5, "fcf_yield": 0.05}, rows, "2024-12-31"
        )
        self.assertTrue(np.isnan(score))
        result = calculate_valuation_components(70, score, np.nan)
        self.assertEqual(result["valuation_score"], 70)
        self.assertFalse(result["historical_valuation_available"])

    def test_c3_peer_component_changes_final_score(self):
        low = calculate_valuation_components(20, 50, 50)["valuation_score"]
        high = calculate_valuation_components(80, 50, 50)["valuation_score"]
        self.assertGreater(high, low)

    def test_c4_historical_component_changes_final_score(self):
        low = calculate_valuation_components(50, 20, 50)["valuation_score"]
        high = calculate_valuation_components(50, 80, 50)["valuation_score"]
        self.assertGreater(high, low)

    def test_c5_context_cannot_exceed_its_configured_influence(self):
        low = calculate_valuation_components(50, 50, 0)["valuation_score"]
        high = calculate_valuation_components(50, 50, 100)["valuation_score"]
        self.assertLessEqual(high - low, 15.0 + 1e-12)

    def test_c6_future_publication_is_rejected(self):
        record = self.observations()[0]
        record["financial_publication_date"] = "2024-02-01"
        record["observation_date"] = "2024-01-28"
        self.assertFalse(is_point_in_time_observation(record, "2024-12-31"))


class ClassificationTests(unittest.TestCase):
    @staticmethod
    def row(ticker, fundamental_score, safety_gate="NORMAL", **overrides):
        row = {
            "ticker": ticker,
            "year": 2025,
            "growth_score": 70.0,
            "quality_score": 70.0,
            "safety_score": 70.0,
            "valuation_score": 70.0,
            "fundamental_score": fundamental_score,
            "safety_gate_status": safety_gate,
            "critical_data_quality_flag": False,
            "data_quality_flags": "",
        }
        row.update(overrides)
        return row

    @classmethod
    def small_universe(cls, target_score=57.0, size=2):
        rows = [cls.row("TARGET", target_score)]
        rows.extend(
            cls.row(f"PEER{index:02d}", 50.0 + index)
            for index in range(1, size)
        )
        return pd.DataFrame(rows)

    @classmethod
    def large_universe(cls):
        return pd.DataFrame(
            [cls.row(f"T{index:02d}", 40.0 + index) for index in range(20)]
        )

    def classify(self, data):
        return classify_fundamental_universe(data, "2025-12-31").set_index("ticker")

    def test_a_small_universe_uses_absolute_watch_not_low_percentile_fail(self):
        data = self.small_universe(target_score=57.0, size=2)
        data.loc[data.ticker.eq("PEER01"), "fundamental_score"] = 70.0
        result = self.classify(data)
        target = result.loc["TARGET"]
        self.assertEqual(target["classification_mode"], "ABSOLUTE_FALLBACK")
        self.assertEqual(target["classification"], "WATCH")
        self.assertEqual(target["classification_reason"], "ABSOLUTE_WATCH_RANGE")
        self.assertFalse(target["percentile_used_for_classification"])
        self.assertEqual(target["fundamental_percentile"], 0.0)

    def test_b_small_universe_strong_company_passes(self):
        result = self.classify(self.small_universe(target_score=70.0, size=5))
        self.assertEqual(result.loc["TARGET", "classification"], "PASS")

    def test_c_small_universe_weak_company_fails(self):
        result = self.classify(self.small_universe(target_score=40.0, size=5))
        self.assertEqual(result.loc["TARGET", "classification"], "FAIL")
        self.assertEqual(
            result.loc["TARGET", "classification_reason"],
            "BELOW_ABSOLUTE_WATCH_SCORE",
        )

    def test_d_large_universe_uses_percentile_rules(self):
        result = self.classify(self.large_universe())
        self.assertEqual(result.loc["T00", "classification_mode"], "PERCENTILE")
        self.assertTrue(result.loc["T00", "percentile_used_for_classification"])
        self.assertEqual(result.loc["T00", "classification"], "FAIL")
        self.assertEqual(result.loc["T10", "classification"], "WATCH")
        self.assertEqual(result.loc["T19", "classification"], "PASS")

    def test_e_safety_critical_always_fails(self):
        data = self.small_universe(target_score=90.0, size=5)
        data.loc[data.ticker.eq("TARGET"), "safety_gate_status"] = "CRITICAL"
        result = self.classify(data)
        self.assertEqual(result.loc["TARGET", "classification"], "FAIL")
        self.assertEqual(result.loc["TARGET", "classification_reason"], "SAFETY_CRITICAL")
        self.assertFalse(result.loc["TARGET", "percentile_used_for_classification"])

    def test_f_safety_high_risk_cannot_pass(self):
        data = self.small_universe(target_score=80.0, size=5)
        data.loc[data.ticker.eq("TARGET"), "safety_gate_status"] = "HIGH_RISK"
        result = self.classify(data)
        self.assertEqual(result.loc["TARGET", "classification"], "WATCH")
        self.assertEqual(result.loc["TARGET", "classification_reason"], "SAFETY_HIGH_RISK")

    def test_g_module_floor_blocks_absolute_pass(self):
        data = self.small_universe(target_score=70.0, size=5)
        data.loc[data.ticker.eq("TARGET"), "growth_score"] = 35.0
        result = self.classify(data)
        self.assertEqual(result.loc["TARGET", "classification"], "WATCH")
        self.assertEqual(result.loc["TARGET", "classification_reason"], "MODULE_FLOOR_NOT_MET")

    def test_h_missing_critical_data_is_watch(self):
        data = self.small_universe(target_score=80.0, size=5)
        data.loc[data.ticker.eq("TARGET"), "quality_score"] = np.nan
        result = self.classify(data)
        self.assertEqual(result.loc["TARGET", "classification"], "WATCH")
        self.assertEqual(result.loc["TARGET", "classification_reason"], "INSUFFICIENT_DATA")
        self.assertFalse(result.loc["TARGET", "percentile_used_for_classification"])

    def test_critical_data_quality_flag_blocks_pass(self):
        data = self.small_universe(target_score=80.0, size=5)
        data.loc[data.ticker.eq("TARGET"), "critical_data_quality_flag"] = True
        result = self.classify(data)
        self.assertEqual(result.loc["TARGET", "classification"], "WATCH")
        self.assertEqual(result.loc["TARGET", "classification_reason"], "INSUFFICIENT_DATA")

    def test_critical_cases_are_excluded_from_eligible_universe(self):
        data = self.small_universe(target_score=90.0, size=5)
        data.loc[data.ticker.eq("TARGET"), "safety_gate_status"] = "CRITICAL"
        result = self.classify(data)
        self.assertTrue(np.isnan(result.loc["TARGET", "fundamental_percentile"]))
        self.assertEqual(result.loc["PEER01", "classification_universe_size"], 4)


if __name__ == "__main__":
    unittest.main()
