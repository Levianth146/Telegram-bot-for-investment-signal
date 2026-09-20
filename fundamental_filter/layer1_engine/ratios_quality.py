import pandas as pd


def gross_margin(gross_profit, revenue):
    if gross_profit is None or revenue is None or revenue == 0:
        return None
    return gross_profit / revenue


def operating_margin(ebit, revenue):
    if ebit is None or revenue is None or revenue == 0:
        return None
    return ebit / revenue


def roe(npat_parent, current_equity, previous_equity):
    if npat_parent is None or current_equity is None or previous_equity is None:
        return None

    average_equity = (current_equity + previous_equity) / 2

    if average_equity == 0:
        return None

    return npat_parent / average_equity


def cfo_to_npat(cfo, npat_parent):
    if cfo is None or npat_parent is None or npat_parent == 0:
        return None
    return cfo / npat_parent


def tax_rate(tax_expense, pretax_profit):
    if tax_expense is None or pretax_profit is None or pretax_profit <= 0:
        return None
    return tax_expense / pretax_profit


def nopat(ebit, current_tax_rate):
    if ebit is None or current_tax_rate is None:
        return None
    return ebit * (1 - current_tax_rate)


def total_debt(short_term_debt, long_term_debt):
    if short_term_debt is None or long_term_debt is None:
        return None
    return short_term_debt + long_term_debt


def invested_capital(equity, debt, cash):
    if equity is None or debt is None or cash is None:
        return None
    return equity + debt - cash


def average_invested_capital(current, previous):
    if current is None or previous is None:
        return None
    return (current + previous) / 2


def roic(current_nopat, average_capital):
    if current_nopat is None or average_capital is None or average_capital == 0:
        return None
    return current_nopat / average_capital


if __name__ == "__main__":
    from .financial_data import get_financial_data

    years = [2021, 2022, 2023, 2024, 2025]
    financial_data = {year: get_financial_data("VNM", year) for year in years}
    roic_data = {}
    quality_rows = []

    for year in years:
        current = financial_data[year]
        current_tax_rate = tax_rate(
            current["tax_expense"], current["pretax_profit"]
        )
        current_nopat = nopat(current["ebit"], current_tax_rate)
        current_debt = total_debt(
            current["short_term_debt"], current["long_term_debt"]
        )
        current_invested_capital = invested_capital(
            current["equity"], current_debt, current["cash"]
        )

        roic_data[year] = {
            "nopat": current_nopat,
            "invested_capital": current_invested_capital,
        }

    for year in years:
        current = financial_data[year]
        previous = financial_data.get(year - 1)
        previous_roic_data = roic_data.get(year - 1)
        average_capital = average_invested_capital(
            roic_data[year]["invested_capital"],
            previous_roic_data["invested_capital"] if previous_roic_data else None,
        )

        quality_rows.append(
            {
                "gross_margin": gross_margin(
                    current["gross_profit"], current["revenue"]
                ),
                "operating_margin": operating_margin(
                    current["ebit"], current["revenue"]
                ),
                "roe": roe(
                    current["npat_parent"],
                    current["equity"],
                    previous["equity"] if previous else None,
                ),
                "roic": roic(roic_data[year]["nopat"], average_capital),
                "cfo_to_npat": cfo_to_npat(
                    current["cfo"], current["npat_parent"]
                ),
            }
        )

    result = pd.DataFrame(quality_rows, index=years)
    result.index.name = "year"

    print(result.to_string(na_rep="None"))
