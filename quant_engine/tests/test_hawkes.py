"""Tests for Hawkes crowding overlay (no network)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from quant_engine.probabilistic.hawkes import (
    branching_ratio,
    crowding_size_multiplier,
    fit_hawkes,
    fit_hawkes_from_returns,
)


def test_branching_and_multiplier():
    assert branching_ratio(0.45, 0.5) == 0.9
    assert crowding_size_multiplier(0.0) == 1.0
    assert crowding_size_multiplier(0.9) == 0.0
    assert 0.0 < crowding_size_multiplier(0.45) < 1.0


def test_fit_hawkes_sparse_and_dense():
    sparse = fit_hawkes([1.0, 2.0])
    assert sparse["n_events"] == 2
    dense = fit_hawkes(list(range(20)))
    assert dense["alpha"] >= 0
    assert dense["beta"] > 0


def test_fit_hawkes_from_returns():
    rng = np.random.default_rng(0)
    rets = pd.Series(rng.normal(0, 0.01, size=200))
    rets.iloc[50] = 0.08
    rets.iloc[51] = -0.07
    rets.iloc[52] = 0.06
    fitted = fit_hawkes_from_returns(rets, spike_z=2.0)
    assert "branching_ratio" in fitted
    assert 0.0 <= fitted["branching_ratio"] <= 1.0
