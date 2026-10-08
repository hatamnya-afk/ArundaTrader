"""ARUNDA TRADER — EXCHANGE-AGNOSTIC ADAPTER CONTRACT v0.1.

Defines the replaceable execution-adapter boundary without naming or importing
any exchange. Provider-specific translation, transport, authentication and
symbol semantics remain inside the selected adapter.

NO NETWORK.
NO DATABASE WRITE.
NO EXCHANGE WRITE.
NO EXECUTION.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable

from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
)


@dataclass(frozen=True)
class ExchangeAdapterCapabilities:
    """Provider-neutral capabilities advertised by a replaceable adapter."""

    venue_discovery: bool
    instrument_resolution: bool
    constraint_read: bool
    account_read: bool
    order_state_read: bool
    order_submission: bool
    order_cancellation: bool


@runtime_checkable
class ExchangeExecutionAdapter(Protocol):
    """Minimal provider-neutral execution adapter boundary.

    The Core sees only this contract. Concrete adapters may use any exchange,
    API, authentication scheme, symbol format, or transport internally.
    """

    @property
    def adapter_name(self) -> str:
        ...

    def capabilities(self) -> ExchangeAdapterCapabilities:
        ...

    def submit_order(
        self,
        request: CanonicalOrderRequest,
    ) -> CanonicalExecutionResult:
        ...

    def cancel_order(
        self,
        *,
        asset: str,
        exchange_order_id: str,
    ) -> CanonicalExecutionResult:
        ...


def validate_adapter_contract(adapter: Any) -> tuple[bool, str]:
    """Pure structural validation; never calls provider methods."""

    if adapter is None:
        return False, "ADAPTER_MISSING"

    name = getattr(adapter, "adapter_name", None)
    if not isinstance(name, str) or not name.strip():
        return False, "ADAPTER_NAME_INVALID"

    capabilities = getattr(adapter, "capabilities", None)
    submit = getattr(adapter, "submit_order", None)
    cancel = getattr(adapter, "cancel_order", None)

    if not callable(capabilities):
        return False, "ADAPTER_CAPABILITIES_MISSING"
    if not callable(submit):
        return False, "ADAPTER_SUBMIT_MISSING"
    if not callable(cancel):
        return False, "ADAPTER_CANCEL_MISSING"

    return True, "VALID"


__all__ = [
    "ExchangeAdapterCapabilities",
    "ExchangeExecutionAdapter",
    "validate_adapter_contract",
]
