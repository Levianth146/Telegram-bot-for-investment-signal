"""Tests for data provider registry + chain (no network required)."""

from __future__ import annotations

import pytest

from data.providers.base import ProviderError
from data.providers.chain import call_chain
from data.providers.registry import (
    get_financial_statement_provider,
    get_price_provider,
    get_sector_provider,
    load_pipeline_config,
)


class _OkClose:
    name = "ok"

    def get_close(self, ticker, as_of_date=None):
        return {"price": 1.0, "ticker": ticker}


class _FailClose:
    name = "fail"

    def get_close(self, ticker, as_of_date=None):
        raise ProviderError("boom")


class _NoneClose:
    name = "none"

    def get_close(self, ticker, as_of_date=None):
        return None


def test_call_chain_skips_failures():
    result = call_chain([_FailClose(), _NoneClose(), _OkClose()], "get_close", "VNM")
    assert result["price"] == 1.0


def test_call_chain_all_fail():
    with pytest.raises(ProviderError):
        call_chain([_FailClose(), _NoneClose()], "get_close", "VNM")


def test_load_pipeline_config_has_data_sources():
    cfg = load_pipeline_config()
    assert "data_sources" in cfg
    assert cfg["data_sources"]["price"]["chain"][0] == "dnse"


def test_provider_registry_builds_chains():
    cfg = load_pipeline_config()
    price = get_price_provider(cfg)
    fs = get_financial_statement_provider(cfg)
    sector = get_sector_provider(cfg)
    assert "dnse" in price.name
    assert "vnstock" in fs.name or "vnfinancialdata" in fs.name
    assert sector.name.startswith("chain:")
