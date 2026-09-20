import pandas as pd

from dnse_price import get_close_price
from exchange_data import get_financial_exchange
from financial_data import get_financial_data
from shares_data import get_shares_outstanding


def get_error_message(error):
    message = str(error).strip()
    return message.splitlines()[0] if message else type(error).__name__


def check_peer_coverage(ticker, year):
    ticker = ticker.strip().upper()
    result = {
        "ticker": ticker,
        "exchange": None,
        "financial_ok": False,
        "missing_financial_fields": None,
        "price_ok": False,
        "price": None,
        "shares_ok": False,
        "shares_outstanding": None,
        "market_cap": None,
        "eligible": False,
        "reason": "",
    }

    try:
        exchange_data = get_financial_exchange(ticker)
    except (Exception, SystemExit) as error:
        result["reason"] = f"Exchange error: {get_error_message(error)}"
        return result

    if exchange_data is None:
        result["reason"] = "Không lấy được exchange"
        return result

    result["exchange"] = (
        exchange_data["financial_exchange"] or exchange_data["source_exchange"]
    )

    if not exchange_data["supported"]:
        result["reason"] = "Exchange không được vnfinancialdata hỗ trợ"
        return result

    reasons = []

    try:
        financial_data = get_financial_data(ticker, year)
        if financial_data is None:
            reasons.append("Không lấy được financial data")
        else:
            missing_fields = [
                name for name, value in financial_data.items() if value is None
            ]
            result["missing_financial_fields"] = len(missing_fields)
            result["financial_ok"] = len(missing_fields) < len(financial_data)

            if missing_fields:
                reasons.append("Thiếu: " + ", ".join(missing_fields))
    except (Exception, SystemExit) as error:
        reasons.append(f"Financial data error: {get_error_message(error)}")

    try:
        price = get_close_price(ticker)
        result["price"] = price
        result["price_ok"] = price is not None and price > 0
        if not result["price_ok"]:
            reasons.append("Giá không hợp lệ")
    except (Exception, SystemExit) as error:
        reasons.append(f"Price error: {get_error_message(error)}")

    try:
        shares_data = get_shares_outstanding(ticker)
        shares = None if shares_data is None else shares_data["shares_outstanding"]
        result["shares_outstanding"] = shares
        result["shares_ok"] = shares is not None and shares > 0
        if not result["shares_ok"]:
            reasons.append("Shares outstanding không hợp lệ")
    except (Exception, SystemExit) as error:
        reasons.append(f"Shares error: {get_error_message(error)}")

    result["eligible"] = (
        result["financial_ok"]
        and result["missing_financial_fields"] == 0
        and result["price_ok"]
        and result["shares_ok"]
    )
    if result["price_ok"] and result["shares_ok"]:
        result["market_cap"] = result["price"] * result["shares_outstanding"]
    result["reason"] = "OK" if result["eligible"] else "; ".join(reasons)
    return result


if __name__ == "__main__":
    tickers = ["AFX", "ANT", "BAF", "BCF", "BHN"]
    rows = [check_peer_coverage(ticker, 2025) for ticker in tickers]
    print(pd.DataFrame(rows).to_string(index=False))
