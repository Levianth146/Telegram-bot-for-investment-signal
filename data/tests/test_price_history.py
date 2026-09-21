"""OHLCV helper unit tests (no network)."""

from __future__ import annotations

import pandas as pd
import pytest

from data.ingest import price_history
from data.ingest.price_history import cache_ohlcv, request_delay_seconds, to_close_series


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


def test_request_delay_seconds_default():
    assert request_delay_seconds({"data_sources": {"price": {}}}) == 0.25
    assert request_delay_seconds({"data_sources": {"price": {"request_delay_ms": 0}}}) == 0.0
    assert request_delay_seconds({"data_sources": {"price": {"request_delay_ms": 100}}}) == 0.1


def test_fetch_universe_ohlcv_throttles(monkeypatch):
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def fake_fetch(ticker, start, end, config=None):
        return pd.DataFrame({"date": ["2024-01-02"], "close": [1.0], "volume": [1]})

    monkeypatch.setattr(price_history.time, "sleep", fake_sleep)
    monkeypatch.setattr(price_history, "fetch_ohlcv", fake_fetch)
    cfg = {"data_sources": {"price": {"request_delay_ms": 100}}}
    out = price_history.fetch_universe_ohlcv(
        ["AAA", "BBB", "CCC"], "2024-01-01", "2024-01-31", cfg
    )
    assert set(out) == {"AAA", "BBB", "CCC"}
    assert sleeps == [0.1, 0.1]


def test_fetch_universe_ohlcv_no_sleep_when_delay_zero(monkeypatch):
    sleeps: list[float] = []
    monkeypatch.setattr(price_history.time, "sleep", lambda s: sleeps.append(s))
    monkeypatch.setattr(
        price_history,
        "fetch_ohlcv",
        lambda *a, **k: pd.DataFrame(
            {"date": ["2024-01-02"], "close": [1.0], "volume": [1]}
        ),
    )
    cfg = {"data_sources": {"price": {"request_delay_ms": 0}}}
    price_history.fetch_universe_ohlcv(["AAA", "BBB"], "2024-01-01", "2024-01-31", cfg)
    assert sleeps == []
