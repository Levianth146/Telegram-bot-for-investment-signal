"""Universe CSV loader tests (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from data.universe import load_universe_tickers, resolve_tickers


def test_load_universe_tickers_sample():
    path = Path("data/universe/vn30_sample.csv")
    tickers = load_universe_tickers(path)
    assert "FPT" in tickers
    assert "VNM" in tickers
    assert len(tickers) >= 20
    assert len(tickers) == len(set(tickers))


def test_load_universe_tickers_comments(tmp_path):
    path = tmp_path / "u.csv"
    path.write_text("# comment\nticker\nAAA\n\nbbb\nAAA\n", encoding="utf-8")
    assert load_universe_tickers(path) == ["AAA", "BBB"]


def test_resolve_tickers_prefers_cli():
    assert resolve_tickers(tickers_csv="vnm,fpt", universe_file="missing.csv") == [
        "VNM",
        "FPT",
    ]


def test_load_universe_missing_file():
    with pytest.raises(FileNotFoundError):
        load_universe_tickers("data/universe/does_not_exist.csv")
