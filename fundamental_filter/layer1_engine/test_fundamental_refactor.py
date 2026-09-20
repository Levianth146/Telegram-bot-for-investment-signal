import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd

from fundamental_engine import score_current_universe, write_run_outputs


BASE_DIR = Path(__file__).resolve().parent
FIXTURE_DIR = BASE_DIR / "tests" / "fixtures"
BASELINE_FILE = FIXTURE_DIR / "fundamental_baseline.json"


class FundamentalRefactorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = json.loads(BASELINE_FILE.read_text(encoding="utf-8"))
        cls.frames = {
            ticker: pd.read_csv(
                FIXTURE_DIR / f"scoring_input_{ticker.lower()}_2021_2025.csv"
            )
            for ticker in cls.baseline["tickers"]
        }

    def run_frozen(self):
        with redirect_stdout(io.StringIO()):
            return score_current_universe(self.frames, 2021, 2025)

    def test_regression_matches_frozen_baseline_without_network(self):
        results, _, _ = self.run_frozen()
        actual = results.set_index("ticker")
        tolerance = self.baseline["tolerance"]
        numeric_fields = [
            "growth_score",
            "quality_score",
            "safety_score",
            "valuation_score",
            "fundamental_score",
            "absolute_safety_score",
            "peer_relative_score",
            "safety_trend_score",
            "fundamental_percentile",
        ]
        text_fields = [
            "safety_gate_status",
            "peer_quality",
            "classification_mode",
            "classification",
            "classification_reason",
        ]
        for ticker, expected in self.baseline["tickers"].items():
            for field in numeric_fields:
                actual_value = actual.loc[ticker, field]
                expected_value = expected[field]
                if expected_value is None:
                    self.assertTrue(pd.isna(actual_value), f"{ticker}.{field}")
                else:
                    self.assertTrue(
                        math.isclose(
                            float(actual_value), expected_value,
                            rel_tol=0.0, abs_tol=tolerance,
                        ),
                        f"{ticker}.{field}: {actual_value} != {expected_value}",
                    )
            for field in text_fields:
                self.assertEqual(actual.loc[ticker, field], expected[field])

    def test_stale_csv_cannot_change_current_run(self):
        before, _, _ = self.run_frozen()
        with tempfile.TemporaryDirectory() as temporary_directory:
            fake = Path(temporary_directory) / "fundamental_score_zzz_2021_2025.csv"
            pd.DataFrame([{"ticker": "ZZZ", "fundamental_score": 100}]).to_csv(
                fake, index=False
            )
            after, _, _ = self.run_frozen()
        pd.testing.assert_frame_equal(before, after)

    def test_same_input_is_deterministic(self):
        first_results, first_metrics, _ = self.run_frozen()
        second_results, second_metrics, _ = self.run_frozen()
        pd.testing.assert_frame_equal(first_results, second_results)
        pd.testing.assert_frame_equal(first_metrics, second_metrics)

    def test_cfo_growth_does_not_change_growth_score(self):
        baseline = {ticker: frame.copy() for ticker, frame in self.frames.items()}
        changed = {ticker: frame.copy() for ticker, frame in self.frames.items()}
        changed["VNM"].loc[
            changed["VNM"]["metric"].eq("cfo_growth_yoy"),
            ["raw_value", "peer_percentile", "trend_score"],
        ] = [5.0, 100.0, 100.0]
        first = self.run_frozen()[0].set_index("ticker").loc["VNM", "growth_score"]
        second = score_current_universe(changed, 2021, 2025)[0].set_index("ticker").loc["VNM", "growth_score"]
        self.assertEqual(first, second)

    def test_missing_cfo_growth_does_not_make_growth_score_nan(self):
        frames = {ticker: frame.copy() for ticker, frame in self.frames.items()}
        frames["VNM"] = frames["VNM"].loc[
            ~frames["VNM"]["metric"].eq("cfo_growth_yoy")
        ].copy()
        result = score_current_universe(frames, 2021, 2025)[0].set_index("ticker")
        self.assertFalse(pd.isna(result.loc["VNM", "growth_score"]))

    def test_growth_metrics_and_raw_cfo_remain_available(self):
        result, metrics, _ = self.run_frozen()
        growth = metrics.loc[
            metrics["ticker"].eq("VNM")
            & metrics["module"].eq("GROWTH")
            & metrics["metric"].ne("cfo_growth_yoy")
        ]
        self.assertEqual(set(growth["metric"]), {
            "revenue_growth_yoy", "revenue_cagr_3_year", "eps_cagr_3_year"
        })
        raw_input = self.frames["VNM"].loc[
            self.frames["VNM"]["metric"].eq("cfo_growth_yoy"), "raw_value"
        ]
        self.assertFalse(raw_input.empty)
        self.assertFalse(pd.isna(raw_input.iloc[0]))

    def test_debug_false_writes_only_two_final_outputs(self):
        results, metrics, stages = self.run_frozen()
        with tempfile.TemporaryDirectory() as temporary_directory:
            write_run_outputs(
                results, metrics, temporary_directory, debug=False,
                debug_frames=stages,
            )
            files = sorted(
                path.relative_to(temporary_directory).as_posix()
                for path in Path(temporary_directory).rglob("*.csv")
            )
        self.assertEqual(
            files, ["fundamental_metrics.csv", "fundamental_results.csv"]
        )

    def test_debug_true_isolated_under_one_run_directory(self):
        results, metrics, stages = self.run_frozen()
        with tempfile.TemporaryDirectory() as temporary_directory:
            debug_dir = write_run_outputs(
                results, metrics, temporary_directory, debug=True,
                debug_frames=stages,
            )
            debug_files = list(debug_dir.rglob("*.csv"))
            self.assertTrue(debug_files)
            self.assertEqual(debug_dir.parent.name, "debug")
            root_csvs = sorted(
                path.name for path in Path(temporary_directory).glob("*.csv")
            )
        self.assertEqual(
            root_csvs, ["fundamental_metrics.csv", "fundamental_results.csv"]
        )


if __name__ == "__main__":
    unittest.main()
