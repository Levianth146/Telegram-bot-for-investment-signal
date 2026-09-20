import pandas as pd

from financial_data import get_financial_data


def revenue_growth_yoy(current, previous):
    if current is None or previous is None or previous == 0:
        return None
    return current / previous - 1


def revenue_cagr_3_year(end_value, start_value):
    if end_value is None or start_value is None:
        return None
    if end_value <= 0 or start_value <= 0:
        return None
    return (end_value / start_value) ** (1 / 3) - 1


def eps_growth_yoy(current, previous):
    if current is None or previous is None or previous == 0:
        return None
    return current / previous - 1


def eps_cagr_3_year(end_value, start_value):
    if end_value is None or start_value is None:
        return None
    if end_value <= 0 or start_value <= 0:
        return None
    return (end_value / start_value) ** (1 / 3) - 1


def cfo_growth_yoy(current, previous):
    if current is None or previous is None or previous == 0:
        return None
    return current / previous - 1


def free_cash_flow(cfo, capex):
    if cfo is None or capex is None:
        return None
    return cfo - capex


if __name__ == "__main__":
    years = [2021, 2022, 2023, 2024, 2025]
    financial_data = {year: get_financial_data("VNM", year) for year in years}
    growth_rows = []

    for year in years:
        current = financial_data[year]
        previous = financial_data.get(year - 1)
        three_years_ago = financial_data.get(year - 3)

        growth_rows.append(
            {
                "revenue_growth_yoy": revenue_growth_yoy(
                    current["revenue"], previous["revenue"] if previous else None
                ),
                "revenue_cagr_3_year": revenue_cagr_3_year(
                    current["revenue"],
                    three_years_ago["revenue"] if three_years_ago else None,
                ),
                "eps_growth_yoy": eps_growth_yoy(
                    current["eps"], previous["eps"] if previous else None
                ),
                "eps_cagr_3_year": eps_cagr_3_year(
                    current["eps"],
                    three_years_ago["eps"] if three_years_ago else None,
                ),
                "cfo_growth_yoy": cfo_growth_yoy(
                    current["cfo"], previous["cfo"] if previous else None
                ),
                "fcf": free_cash_flow(current["cfo"], current["capex"]),
            }
        )

    result = pd.DataFrame(growth_rows, index=years)
    result.index.name = "year"

    print(result.to_string(na_rep="None"))
