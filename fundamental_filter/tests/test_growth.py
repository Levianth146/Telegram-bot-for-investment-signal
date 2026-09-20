"""Ví dụ test cho module Growth — mỗi PR thêm logic mới cần test tương tự."""
from fundamental_filter import growth


def test_revenue_growth_yoy():
    assert abs(growth.revenue_growth_yoy(120, 100) - 0.2) < 1e-12


def test_growth_spread():
    assert growth.growth_spread(0.25, 0.10) == 0.15


def test_eps_cagr():
    # (1.331 / 1.0)^(1/3) - 1 = 0.1
    assert abs(growth.eps_cagr(1.331, 1.0, 3) - 0.1) < 1e-9


def test_positive_growth_ratio():
    assert growth.positive_growth_ratio([0.1, -0.2, 0.05, 0.0]) == 0.5
