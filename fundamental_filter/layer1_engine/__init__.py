"""Fundamental Filter engine (Tầng 1) — package entry.

Pure scoring path (no network): ``score_current_universe``,
``classify_fundamental_universe``, ``to_store_records``, ``load_scoring_config``.

Live / I/O path (transitional — network still inside this package until ``data/``
providers land): ``analyze_fundamental_universe``.

Imports are lazy so ``from fundamental_filter.layer1_engine import ratios_growth``
does not pull DNSE/vnstock.
"""

from __future__ import annotations

__all__ = [
    "classify_fundamental_universe",
    "load_scoring_config",
    "score_current_universe",
    "to_store_records",
]


def __getattr__(name: str):
    if name == "load_scoring_config":
        from .config_loader import load_scoring_config

        return load_scoring_config
    if name == "classify_fundamental_universe":
        from .fundamental_classification import classify_fundamental_universe

        return classify_fundamental_universe
    if name == "score_current_universe":
        from .fundamental_engine import score_current_universe

        return score_current_universe
    if name == "to_store_records":
        from .store_adapter import to_store_records

        return to_store_records
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
