"""Ví dụ test cho module Growth — mỗi PR thêm logic mới cần test tương tự."""
import pytest
from fundamental_filter import growth


def test_revenue_growth_yoy_not_implemented_yet():
    # TODO(P6 - fundamental): xóa test này khi đã implement, thay bằng test thật
    with pytest.raises(NotImplementedError):
        growth.revenue_growth_yoy(120, 100)
