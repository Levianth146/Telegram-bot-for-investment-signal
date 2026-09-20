"""Provider interfaces + fallback chains for price / BCTC / sector.

Pipeline loads providers via ``get_price_provider(config)`` etc. — never hardcode
vendor names outside ``pipeline/config.yaml`` and this package.
"""

from .base import (
    FinancialStatementProvider,
    PriceProvider,
    ProviderError,
    SectorProvider,
)
from .registry import (
    get_financial_statement_provider,
    get_price_provider,
    get_sector_provider,
    load_pipeline_config,
)

__all__ = [
    "FinancialStatementProvider",
    "PriceProvider",
    "ProviderError",
    "SectorProvider",
    "get_financial_statement_provider",
    "get_price_provider",
    "get_sector_provider",
    "load_pipeline_config",
]
