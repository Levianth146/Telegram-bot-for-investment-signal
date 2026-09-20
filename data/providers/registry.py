"""Build provider chains from ``pipeline/config.yaml``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import FinancialStatementProvider, PriceProvider, SectorProvider
from .chain import call_chain
from .financials_stubs import CafeFFinancials, VietstockFinancials
from .financials_vnfinancialdata import VnFinancialDataStatements
from .financials_vnstock import VnstockFinancials
from .price_dnse import DnsePriceProvider
from .price_stubs import CafeFPriceProvider
from .price_vnstock import VnstockPriceProvider
from .sector_vnstock import VnstockSectorProvider

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_CONFIG = _REPO_ROOT / "pipeline" / "config.yaml"

_PRICE_FACTORIES = {
    "dnse": DnsePriceProvider,
    "vnstock": VnstockPriceProvider,
    "cafef": CafeFPriceProvider,
}

_FS_LIVE_FACTORIES = {
    "vnstock": VnstockFinancials,
    "cafef": CafeFFinancials,
    "vietstock": VietstockFinancials,
    # transitional: annual backtest source also usable for live FY pulls
    "vnfinancialdata": VnFinancialDataStatements,
}

_SECTOR_FACTORIES = {
    "vnstock": VnstockSectorProvider,
}


def load_pipeline_config(config_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(config_path) if config_path else _DEFAULT_CONFIG
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyYAML required to load pipeline/config.yaml") from exc
    if not path.is_file():
        return {}
    with path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return data if isinstance(data, dict) else {}


class _ChainedPrice:
    def __init__(self, providers: list[PriceProvider]):
        self.name = "chain:" + ",".join(p.name for p in providers)
        self._providers = providers

    def get_close(self, ticker: str, as_of_date: str | None = None):
        return call_chain(self._providers, "get_close", ticker, as_of_date)

    def get_ohlcv(self, ticker: str, start: str, end: str):
        return call_chain(self._providers, "get_ohlcv", ticker, start, end)


class _ChainedFinancials:
    def __init__(self, providers: list[FinancialStatementProvider]):
        self.name = "chain:" + ",".join(p.name for p in providers)
        self._providers = providers

    def get_annual(self, ticker: str, year: int):
        return call_chain(self._providers, "get_annual", ticker, year)

    def get_latest(self, ticker: str, as_of_date: str | None = None):
        return call_chain(self._providers, "get_latest", ticker, as_of_date)


class _ChainedSector:
    def __init__(self, providers: list[SectorProvider]):
        self.name = "chain:" + ",".join(p.name for p in providers)
        self._providers = providers

    def get_industry(self, ticker: str):
        return call_chain(self._providers, "get_industry", ticker)


def get_price_provider(config: dict[str, Any] | None = None) -> PriceProvider:
    cfg = config if config is not None else load_pipeline_config()
    names = ((cfg.get("data_sources") or {}).get("price") or {}).get("chain") or [
        "dnse",
        "vnstock",
        "cafef",
    ]
    providers: list[PriceProvider] = []
    for name in names:
        factory = _PRICE_FACTORIES.get(str(name).lower())
        if factory is None:
            continue
        providers.append(factory())
    if not providers:
        raise ValueError("No price providers configured")
    return _ChainedPrice(providers)


def get_financial_statement_provider(
    config: dict[str, Any] | None = None,
    *,
    mode: str = "live",
) -> FinancialStatementProvider:
    """``mode='live'`` uses financial_statements_live.chain;
    ``mode='backtest'`` uses financial_statements_backtest.primary first.
    """
    cfg = config if config is not None else load_pipeline_config()
    sources = cfg.get("data_sources") or {}
    providers: list[FinancialStatementProvider] = []

    if mode == "backtest":
        primary = (sources.get("financial_statements_backtest") or {}).get(
            "primary", "vnfinancialdata"
        )
        factory = _FS_LIVE_FACTORIES.get(str(primary).lower())
        if factory:
            providers.append(factory())
    else:
        names = (sources.get("financial_statements_live") or {}).get("chain") or [
            "vnstock",
            "cafef",
            "vietstock",
        ]
        for name in names:
            factory = _FS_LIVE_FACTORIES.get(str(name).lower())
            if factory:
                providers.append(factory())
        # Always allow annual vnfinancialdata as last-resort until live APIs land
        if "vnfinancialdata" not in {p.name for p in providers}:
            providers.append(VnFinancialDataStatements())

    if not providers:
        raise ValueError("No financial-statement providers configured")
    return _ChainedFinancials(providers)


def get_sector_provider(config: dict[str, Any] | None = None) -> SectorProvider:
    cfg = config if config is not None else load_pipeline_config()
    source = (cfg.get("sector_classification") or {}).get("source", "vnstock")
    factory = _SECTOR_FACTORIES.get(str(source).lower(), VnstockSectorProvider)
    return _ChainedSector([factory()])
