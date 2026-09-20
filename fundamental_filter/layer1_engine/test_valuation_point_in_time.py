import unittest
from unittest.mock import Mock, patch

import pandas as pd

from .dnse_price import get_close_price
from .ratios_valuation import (
    aggregate_ttm,
    get_valuation,
    select_latest_published_financial,
)
from .shares_data import get_shares_outstanding


class ValuationPointInTimeTests(unittest.TestCase):
    def setUp(self):
        self.financial_data = {
            "eps": 2_000,
            "equity": 50_000_000,
            "short_term_debt": 5_000_000,
            "long_term_debt": 5_000_000,
            "cash": 3_000_000,
            "ebitda": 10_000_000,
            "cfo": 8_000_000,
            "capex": 2_000_000,
        }

    def test_a_historical_price_never_uses_a_later_close(self):
        quote = Mock()
        quote.history.return_value = pd.DataFrame(
            {
                "time": ["2024-06-27", "2024-06-28", "2024-07-01"],
                "close": [55.0, 56.24, 999.0],
            }
        )
        with (
            patch(
                "fundamental_filter.layer1_engine.dnse_price.Quote",
                return_value=quote,
            ),
            patch(
                "fundamental_filter.layer1_engine.dnse_price.get_live_close_price"
            ) as live_price_mock,
        ):
            result = get_close_price(
                "VNM", "2024-06-30", return_metadata=True
            )

        live_price_mock.assert_not_called()
        self.assertEqual(result["price_date"], "2024-06-28")
        self.assertEqual(result["price"], 56_240)
        self.assertEqual(result["price_adjustment"], "ADJUSTED")

    def test_b_financial_record_requires_publication_by_cutoff(self):
        records = [
            {
                "period_end": "2024-03-31",
                "publication_date": "2024-04-25",
                "eps": 10,
            }
        ]
        self.assertIsNone(
            select_latest_published_financial(records, "2024-04-10")
        )
        self.assertIs(
            select_latest_published_financial(records, "2024-04-26"),
            records[0],
        )

    @patch(
        "fundamental_filter.layer1_engine.financial_data.get_latest_reported_financial_data"
    )
    @patch(
        "fundamental_filter.layer1_engine.shares_data.get_shares_outstanding"
    )
    @patch("fundamental_filter.layer1_engine.dnse_price.get_close_price")
    def test_c_live_valuation_uses_live_price_and_latest_reported_basis(
        self, price_mock, shares_mock, financial_mock
    ):
        price_mock.return_value = {
            "price": 60_000,
            "price_date": "2026-09-18",
            "price_source": "DNSE close",
            "price_adjustment": "UNADJUSTED",
            "point_in_time_safe": True,
            "warning": None,
        }
        shares_mock.return_value = {
            "shares_outstanding": 1_000,
            "date": "2026-09-18",
            "source": "KBS company profile via vnstock",
            "historical_fallback_used": False,
            "point_in_time_safe": True,
            "warning": None,
        }
        financial_mock.return_value = {
            "data": self.financial_data,
            "financial_period": "2025",
            "period_end_date": "2025-12-31",
            "financial_publication_date": None,
            "earnings_basis": "FY_FALLBACK",
            "publication_date_missing": True,
            "point_in_time_safe": False,
            "warning": "FY fallback",
        }

        result = get_valuation("vnm")

        self.assertEqual(result["valuation_mode"], "LIVE")
        self.assertEqual(result["price"], 60_000)
        self.assertEqual(result["pe"], 30)
        self.assertEqual(result["financial_period"], "2025")
        self.assertEqual(result["earnings_basis"], "FY_FALLBACK")

    def test_d_ttm_uses_four_consecutive_published_quarters(self):
        records = []
        for period, publication in [
            ("2023-09-30", "2023-10-25"),
            ("2023-12-31", "2024-01-25"),
            ("2024-03-31", "2024-04-25"),
            ("2024-06-30", "2024-07-25"),
        ]:
            records.append(
                {
                    "period_end": period,
                    "publication_date": publication,
                    "eps": 1,
                    "ebitda": 2,
                    "cfo": 3,
                    "capex": 1,
                    "equity": 10,
                    "short_term_debt": 2,
                    "long_term_debt": 3,
                    "cash": 1,
                }
            )

        result = aggregate_ttm(records, "2024-07-26")

        self.assertEqual(result["eps"], 4)
        self.assertEqual(result["ebitda"], 8)
        self.assertEqual(result["cfo"], 12)
        self.assertEqual(result["capex"], 4)
        self.assertEqual(result["fcf"], 8)
        self.assertEqual(result["earnings_basis"], "TTM")

    @patch(
        "fundamental_filter.layer1_engine.financial_data.get_latest_reported_financial_data"
    )
    @patch(
        "fundamental_filter.layer1_engine.shares_data.get_shares_outstanding"
    )
    @patch("fundamental_filter.layer1_engine.dnse_price.get_close_price")
    def test_e_fy_fallback_is_explicit_and_does_not_crash(
        self, price_mock, shares_mock, financial_mock
    ):
        price_mock.return_value = {
            "price": 60_000,
            "price_date": "2026-09-18",
            "price_source": "DNSE close",
            "price_adjustment": "UNADJUSTED",
            "point_in_time_safe": True,
        }
        shares_mock.return_value = {
            "shares_outstanding": 1_000,
            "date": "2026-09-18",
            "source": "KBS",
            "historical_fallback_used": False,
            "point_in_time_safe": True,
        }
        financial_mock.return_value = {
            "data": self.financial_data,
            "financial_period": "2025",
            "period_end_date": "2025-12-31",
            "financial_publication_date": None,
            "earnings_basis": "FY_FALLBACK",
            "publication_date_missing": True,
            "point_in_time_safe": False,
            "warning": "FY fallback",
        }

        result = get_valuation("VNM")

        self.assertEqual(result["earnings_basis"], "FY_FALLBACK")
        self.assertFalse(result["point_in_time_safe"])
        self.assertIsNotNone(result["pe"])

    @patch("fundamental_filter.layer1_engine.shares_data.get_kbs_company_data")
    def test_f_historical_shares_never_fall_back_to_current(self, company_mock):
        result = get_shares_outstanding("VNM", "2024-06-30")

        company_mock.assert_not_called()
        self.assertIsNone(result["shares_outstanding"])
        self.assertFalse(result["historical_fallback_used"])
        self.assertFalse(result["point_in_time_safe"])

    def test_legacy_integer_year_is_rejected(self):
        with self.assertRaises(TypeError):
            get_valuation("VNM", 2025)


if __name__ == "__main__":
    unittest.main()
