"""Ví dụ test cho module Regime."""
import pytest
from quant_engine import regime


def test_filtered_regime_probability_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        regime.filtered_regime_probability(model=None, returns_up_to_t=None)
