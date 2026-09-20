import sys
from datetime import date, datetime

import truststore

truststore.inject_into_ssl()

import pandas as pd
import vnfinancialdata as vnf

from exchange_data import get_financial_exchange


sys.stdout.reconfigure(encoding="utf-8")


def get_value(df, item_code):
    rows = df[df["item_code"] == item_code]

    if rows.empty:
        return None

    return rows["value"].iloc[0]


def get_financial_data(ticker, year):
    exchange_data = get_financial_exchange(ticker)

    if exchange_data is None or not exchange_data["supported"]:
        return None

    financial_exchange = exchange_data["financial_exchange"]

    income_statement = vnf.get(
        ticker=ticker,
        exchange=financial_exchange,
        statement="income_statement",
        start=year,
        end=year,
    )

    balance_sheet = vnf.get(
        ticker=ticker,
        exchange=financial_exchange,
        statement="balance_sheet",
        start=year,
        end=year,
    )

    cash_flow = vnf.get(
        ticker=ticker,
        exchange=financial_exchange,
        statement="cash_flow",
        start=year,
        end=year,
    )

    capex = get_value(
        cash_flow, "cf_tien_mua_tai_san_co_dinh_va_cac_tai_san_dai_han_khac"
    )
    tax_expense = get_value(
        income_statement, "is_chi_phi_thue_thu_nhap_doanh_nghiep"
    )
    interest_expense = get_value(
        income_statement, "is_trong_do_chi_phi_lai_vay"
    )

    if capex is not None:
        capex = abs(capex)

    if tax_expense is not None:
        tax_expense = abs(tax_expense)

    if interest_expense is not None:
        interest_expense = abs(interest_expense)

    return {
        "revenue": get_value(income_statement, "is_doanh_so_thuan"),
        "gross_profit": get_value(income_statement, "is_lai_gop"),
        "ebit": get_value(income_statement, "is_ebit"),
        "ebitda": get_value(income_statement, "is_ebitda"),
        "npat_parent": get_value(
            income_statement, "is_loi_nhuan_cua_co_dong_cua_cong_ty_me"
        ),
        "eps": get_value(income_statement, "is_lai_co_ban_tren_co_phieu"),
        "pretax_profit": get_value(
            income_statement, "is_lai_lo_rong_truoc_thue"
        ),
        "tax_expense": tax_expense,
        "interest_expense": interest_expense,
        "cash": get_value(balance_sheet, "bs_tien_va_tuong_duong_tien"),
        "receivables": get_value(balance_sheet, "bs_phai_thu_khach_hang"),
        "inventory": get_value(balance_sheet, "bs_hang_ton_kho"),
        "current_assets": get_value(balance_sheet, "bs_tai_san_ngan_han"),
        "current_liabilities": get_value(balance_sheet, "bs_no_ngan_han"),
        "short_term_debt": get_value(balance_sheet, "bs_vay_ngan_han"),
        "long_term_debt": get_value(balance_sheet, "bs_vay_dai_han"),
        "total_assets": get_value(balance_sheet, "bs_tong_tai_san"),
        "equity": get_value(balance_sheet, "bs_von_chu_so_huu_4d280b22"),
        "cfo": get_value(
            cash_flow,
            "cf_luu_chuyen_tien_thuan_tu_cac_hoat_dong_san_xuat_kinh_doanh",
        ),
        "capex": capex,
    }


VALUATION_FINANCIAL_FIELDS = [
    "eps",
    "equity",
    "short_term_debt",
    "long_term_debt",
    "cash",
    "ebitda",
    "cfo",
    "capex",
]


def get_latest_reported_financial_data(ticker, as_of_date=None, lookback_years=5):
    """Return auditable financial input for valuation.

    The configured annual source does not expose publication dates. Live mode may
    therefore use the latest completed FY as an explicitly labelled fallback.
    Historical mode refuses to infer a publication date and returns no data.
    """
    if as_of_date is not None:
        if isinstance(as_of_date, datetime):
            requested_date = as_of_date.date()
        elif isinstance(as_of_date, date):
            requested_date = as_of_date
        elif isinstance(as_of_date, str):
            requested_date = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        else:
            raise TypeError("as_of_date must be YYYY-MM-DD, date, datetime, or None")

        return {
            "data": None,
            "financial_period": None,
            "period_end_date": None,
            "financial_publication_date": None,
            "earnings_basis": None,
            "publication_date_missing": True,
            "point_in_time_safe": False,
            "warning": (
                "Historical financial statements cannot be selected safely because "
                "the configured source has no publication date."
            ),
            "requested_as_of_date": requested_date.isoformat(),
        }

    latest_completed_year = date.today().year - 1
    for financial_year in range(
        latest_completed_year, latest_completed_year - lookback_years, -1
    ):
        data = get_financial_data(ticker, financial_year)
        if data is None:
            continue
        if not all(data.get(field) is not None for field in VALUATION_FINANCIAL_FIELDS):
            continue

        return {
            "data": data,
            "financial_period": str(financial_year),
            "period_end_date": f"{financial_year}-12-31",
            "financial_publication_date": None,
            "earnings_basis": "FY_FALLBACK",
            "publication_date_missing": True,
            "point_in_time_safe": False,
            "warning": (
                "Quarterly publication-dated data is unavailable; latest complete "
                "FY is used and labelled FY_FALLBACK."
            ),
            "requested_as_of_date": None,
        }

    return {
        "data": None,
        "financial_period": None,
        "period_end_date": None,
        "financial_publication_date": None,
        "earnings_basis": None,
        "publication_date_missing": True,
        "point_in_time_safe": False,
        "warning": "No complete FY valuation input was found.",
        "requested_as_of_date": None,
    }


if __name__ == "__main__":
    years = [2021, 2022, 2023, 2024, 2025]
    all_years = [get_financial_data("VNM", year) for year in years]

    result = pd.DataFrame(all_years, index=years)
    result.index.name = "year"

    print(result.to_string())
