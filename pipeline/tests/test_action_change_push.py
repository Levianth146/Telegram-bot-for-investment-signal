"""Tests diff action + ưu tiên push đổi trạng thái."""

from __future__ import annotations

from pipeline.daily_job import diff_signal_actions


def test_diff_signal_actions_detects_changes():
    prev = [
        {"ticker": "FPT", "action": "WATCH"},
        {"ticker": "GAS", "action": "BUY"},
        {"ticker": "VNM", "action": "SELL"},
    ]
    cur = [
        {"ticker": "FPT", "action": "BUY", "date": "2026-09-22", "score": 1.0},
        {"ticker": "GAS", "action": "BUY", "date": "2026-09-22"},
        {"ticker": "VNM", "action": "WATCH", "date": "2026-09-22"},
    ]
    changes = diff_signal_actions(prev, cur)
    tickers = {c["ticker"] for c in changes}
    assert tickers == {"FPT", "VNM"}
    by = {c["ticker"]: c for c in changes}
    assert by["FPT"]["from_action"] == "WATCH"
    assert by["FPT"]["to_action"] == "BUY"
