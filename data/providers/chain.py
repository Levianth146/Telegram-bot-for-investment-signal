"""Try providers in config order; skip failures and continue the chain."""

from __future__ import annotations

import logging
from typing import Any, Callable, TypeVar

from .base import ProviderError

logger = logging.getLogger(__name__)

T = TypeVar("T")


def call_chain(
    providers: list[Any],
    method: str,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Call ``provider.method(*args, **kwargs)`` across the chain.

    Skips ``None`` results, ``ProviderError``, and ``NotImplementedError``.
    Raises ``ProviderError`` if every source fails.
    """
    errors: list[str] = []
    for provider in providers:
        name = getattr(provider, "name", type(provider).__name__)
        func: Callable[..., Any] = getattr(provider, method)
        try:
            result = func(*args, **kwargs)
        except NotImplementedError as exc:
            errors.append(f"{name}: not implemented ({exc})")
            logger.info("provider %s.%s not implemented: %s", name, method, exc)
            continue
        except ProviderError as exc:
            errors.append(f"{name}: {exc}")
            logger.warning("provider %s.%s failed: %s", name, method, exc)
            continue
        except Exception as exc:  # noqa: BLE001 — isolate vendor crashes
            errors.append(f"{name}: {type(exc).__name__}: {exc}")
            logger.warning("provider %s.%s error: %s", name, method, exc)
            continue
        if result is None:
            errors.append(f"{name}: returned None")
            continue
        return result
    raise ProviderError(
        f"all providers failed for {method}: " + "; ".join(errors)
    )
