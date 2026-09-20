from kbs_company_data import get_kbs_company_data


def get_financial_exchange(ticker):
    ticker = ticker.strip().upper()
    company_data = get_kbs_company_data(ticker)

    if company_data is None:
        return None

    source_exchange = company_data["exchange"]
    if not isinstance(source_exchange, str) or not source_exchange.strip():
        return None

    source_exchange = source_exchange.strip().upper()
    exchange_mapping = {"HOSE": "HSX", "HNX": "HNX"}
    financial_exchange = exchange_mapping.get(source_exchange)

    return {
        "ticker": ticker,
        "source_exchange": source_exchange,
        "financial_exchange": financial_exchange,
        "supported": financial_exchange is not None,
    }


if __name__ == "__main__":
    for ticker in ["VNM", "BCF", "MCH"]:
        print(get_financial_exchange(ticker))
