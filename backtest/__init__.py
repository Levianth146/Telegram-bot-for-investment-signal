"""Backtest package — shared FF + Quant path (ARCHITECTURE invariant #2)."""

from __future__ import annotations

from typing import Any

__all__ = [
    "run_backtest",
    "run_walk_forward",
    "walk_forward_windows",
    "run_ablation",
    "compute_metrics",
]


def __getattr__(name: str) -> Any:
    if name == "run_ablation":
        from .ablation import run_ablation

        return run_ablation
    if name == "run_backtest":
        from .engine import run_backtest

        return run_backtest
    if name == "compute_metrics":
        from .metrics import compute_metrics

        return compute_metrics
    if name == "run_walk_forward":
        from .walk_forward import run_walk_forward

        return run_walk_forward
    if name == "walk_forward_windows":
        from .walk_forward import walk_forward_windows

        return walk_forward_windows
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
