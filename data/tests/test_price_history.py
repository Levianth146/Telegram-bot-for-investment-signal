"""OHLCV helper unit tests (no network)."""

from __future__ import annotations

import pandas as pd
import pytest

from data.ingest import price_history
from data.ingest.price_history import (
    cache_ohlcv,
    cache_ohlcv_enabled,
    load_cached_ohlcv,
    request_delay_seconds,
    to_close_series,
)


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


def test_cache_ohlcv_enabled_default():
    assert cache_ohlcv_enabled({"data_sources": {"price": {}}}) is True
    assert cache_ohlcv_enabled({"data_sources": {"price": {"cache_ohlcv": False}}}) is False


def test_fetch_universe_ohlcv_throttles(monkeypatch):
    sleeps: list[float] = []

    def fake_sleep(seconds: float) -> None:
        sleeps.append(seconds)

    def fake_fetch(ticker, start, end, config=None):
        return pd.DataFrame({"date": ["2024-01-02"], "close": [1.0], "volume": [1]})

    monkeypatch.setattr(price_history.time, "sleep", fake_sleep)
    monkeypatch.setattr(price_history, "fetch_ohlcv", fake_fetch)
    cfg = {
        "data_sources": {
            "price": {"request_delay_ms": 100, "cache_ohlcv": False}
        }
    }
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
    cfg = {
        "data_sources": {"price": {"request_delay_ms": 0, "cache_ohlcv": False}}
    }
    price_history.fetch_universe_ohlcv(["AAA", "BBB"], "2024-01-01", "2024-01-31", cfg)
    assert sleeps == []


def test_fetch_ohlcv_uses_disk_cache(tmp_path, monkeypatch):
    frame = pd.DataFrame(
        {"date": ["2024-01-02"], "close": [42.0], "volume": [3], "open": [40], "high": [43], "low": [39]}
    )
    cache_ohlcv(frame, "VNM", tmp_path, start="2024-01-01", end="2024-01-31")

    def boom(*_a, **_k):
        raise AssertionError("provider must not be called on cache hit")

    monkeypatch.setattr(
        price_history,
        "get_price_provider",
        lambda config=None: type("P", (), {"get_ohlcv": staticmethod(boom)})(),
    )
    cfg = {
        "data_sources": {
            "price": {
                "cache_ohlcv": True,
                "cache_dir": str(tmp_path),
                "request_delay_ms": 0,
            }
        }
    }
    loaded = price_history.fetch_ohlcv("VNM", "2024-01-01", "2024-01-31", cfg)
    assert float(loaded.iloc[0]["close"]) == 42.0


def test_fetch_universe_skips_throttle_on_cache_hit(tmp_path, monkeypatch):
    frame = pd.DataFrame({"date": ["2024-01-02"], "close": [1.0], "volume": [1]})
    for ticker in ("AAA", "BBB"):
        cache_ohlcv(frame, ticker, tmp_path, start="2024-01-01", end="2024-01-31")

    sleeps: list[float] = []
    calls: list[str] = []
    monkeypatch.setattr(price_history.time, "sleep", lambda s: sleeps.append(s))

    def fake_fetch(ticker, start, end, config=None):
        calls.append(ticker)
        return frame

    monkeypatch.setattr(price_history, "fetch_ohlcv", fake_fetch)
    cfg = {
        "data_sources": {
            "price": {
                "cache_ohlcv": True,
                "cache_dir": str(tmp_path),
                "request_delay_ms": 100,
            }
        }
    }
    out = price_history.fetch_universe_ohlcv(
        ["AAA", "BBB"], "2024-01-01", "2024-01-31", cfg
    )
    assert set(out) == {"AAA", "BBB"}
    assert calls == []
    assert sleeps == []
    assert load_cached_ohlcv("AAA", "2024-01-01", "2024-01-31", tmp_path) is not None
