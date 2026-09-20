"""OHLCV helper unit tests (no network)."""

from __future__ import annotations

import pandas as pd
import pytest

from data.ingest.price_history import cache_ohlcv, to_close_series


def test_to_close_series():
    frame = pd.DataFrame(
        {"date": ["2024-01-02", "2024-01-03"], "close": [10.0, 11.0], "volume": [1, 2]}
    )
    series = to_close_series(frame)
    assert list(series.index) == ["2024-01-02", "2024-01-03"]
    assert series.iloc[-1] == 11.0


def test_cache_ohlcv(tmp_path):
    frame = pd.DataFrame({"date": ["2024-01-02"], "close": [10.0], "volume": [1]})
    path = cache_ohlcv(frame, "VNM", tmp_path)
    assert path.exists()
    loaded = pd.read_csv(path)
    assert loaded.iloc[0]["close"] == 10.0


def test_to_close_series_requires_columns():
    with pytest.raises(ValueError):
        to_close_series(pd.DataFrame({"x": [1]}))
