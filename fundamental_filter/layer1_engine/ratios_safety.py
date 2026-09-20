import pandas as pd

from financial_data import get_financial_data


def current_ratio(current_assets, current_liabilities):
    if current_assets is None or current_liabilities is None:
        return None
    if current_liabilities == 0:
        return None
    return current_assets / current_liabilities


def quick_ratio(current_assets, inventory, current_liabilities):
    if current_assets is None or inventory is None or current_liabilities is None:
        return None
    if current_liabilities == 0:
        return None
    return (current_assets - inventory) / current_liabilities


def total_debt(short_term_debt, long_term_debt):
    if short_term_debt is None or long_term_debt is None:
        return None
    return short_term_debt + long_term_debt


def debt_to_equity(debt, equity):
    if debt is None or equity is None or equity <= 0:
        return None
    return debt / equity


def net_debt(debt, cash):
    if debt is None or cash is None:
        return None
    return debt - cash


def net_debt_to_ebitda(current_net_debt, ebitda):
    if current_net_debt is None or ebitda is None or ebitda <= 0:
        return None
    return current_net_debt / ebitda


def interest_coverage(ebit, interest_expense):
    if ebit is None or interest_expense is None or interest_expense <= 0:
        return None
    return ebit / interest_expense


def cfo_to_debt(cfo, debt):
    if cfo is None or debt is None or debt <= 0:
        return None
    return cfo / debt


if __name__ == "__main__":
    years = [2021, 2022, 2023, 2024, 2025]
    safety_rows = []

    for year in years:
        data = get_financial_data("VNM", year)
        debt = total_debt(data["short_term_debt"], data["long_term_debt"])
        current_net_debt = net_debt(debt, data["cash"])

        safety_rows.append(
            {
                "current_ratio": current_ratio(
                    data["current_assets"], data["current_liabilities"]
                ),
                "quick_ratio": quick_ratio(
                    data["current_assets"],
                    data["inventory"],
                    data["current_liabilities"],
                ),
                "debt_to_equity": debt_to_equity(debt, data["equity"]),
                "net_debt_to_ebitda": net_debt_to_ebitda(
                    current_net_debt, data["ebitda"]
                ),
                "interest_coverage": interest_coverage(
                    data["ebit"], data["interest_expense"]
                ),
                "cfo_to_debt": cfo_to_debt(data["cfo"], debt),
            }
        )

    result = pd.DataFrame(safety_rows, index=years)
    result.index.name = "year"

    print(result.to_string(na_rep="None"))
