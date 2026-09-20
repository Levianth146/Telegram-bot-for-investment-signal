"""Quant Regime Engine — Tầng 2 (daily).

Pure modules (no network): ``regime``, ``alpha``, ``risk``, ``portfolio``,
``signal_engine.generate_signals``. Pipeline prepares prices via ``data/``.
"""

from __future__ import annotations

from .signal_engine import generate_signals

__all__ = ["generate_signals"]
