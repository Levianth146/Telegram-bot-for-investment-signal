"""Tests for display-only TA reference (§9.7)."""

from __future__ import annotations

from bot.ta_reference import ta_indicators_from_closes


def test_ta_from_closes_rsi_and_ma():
    closes = [
        {"date": f"2024-01-{i:02d}", "close": 50.0 + i * 0.5, "volume": 1_000_000 + i * 1000}
        for i in range(1, 60)
    ]
    ta = ta_indicators_from_closes(closes)
    assert "rsi_14" in ta
    assert 0 <= float(ta["rsi_14"]) <= 100
    assert "ma_trend" in ta
    assert "volume_over_ma20" in ta


def test_ta_empty_when_too_short():
    assert ta_indicators_from_closes([{"date": "2024-01-01", "close": 1.0}]) == {}
