from datetime import date, datetime

from kbs_company_data import get_kbs_company_data


def get_shares_outstanding(ticker, as_of_date=None):
    """Return live shares; never substitute them into a historical valuation."""
    ticker = ticker.strip().upper()
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
            "ticker": ticker,
            "shares_outstanding": None,
            "date": None,
            "source": None,
            "requested_as_of_date": requested_date.isoformat(),
            "historical_fallback_used": False,
            "point_in_time_safe": False,
            "warning": (
                "Historical shares are unavailable from the configured source; "
                "current shares were not used."
            ),
        }

    company_data = get_kbs_company_data(ticker)
    if company_data is None:
        return None

    shares = company_data["shares_outstanding"]
    if shares is None:
        return None

    return {
        "ticker": ticker,
        "shares_outstanding": shares,
        "date": company_data["shares_date"],
        "source": "KBS company profile via vnstock",
        "requested_as_of_date": None,
        "historical_fallback_used": False,
        "point_in_time_safe": True,
        "warning": None,
    }


if __name__ == "__main__":
    result = get_shares_outstanding("VNM")

    if result is None:
        print("Không lấy được dữ liệu VNM.")
    else:
        print("ticker:", result["ticker"])
        print("shares_outstanding:", result["shares_outstanding"])
        print("date:", result["date"])
        print("source:", result["source"])
