"""ARUNDA TRADER — EXCHANGE-AGNOSTIC ADAPTER CONTRACT v0.2.

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
from typing import Any, Protocol, runtime_checkable

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


@dataclass(frozen=True)
class AdapterOrderPreparation:
    """Provider-neutral envelope around an adapter-owned order request.

    The request field is intentionally opaque to Core. Only the selected
    adapter may interpret or submit it. This keeps provider symbols,
    transport fields and authentication details outside the Core contract.
    """

    ready: bool
    reason: str
    adapter_name: str
    venue: str
    request: Any = None


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

    def prepare_order(
        self,
        request: CanonicalOrderRequest,
        *,
        venue: str,
        execution_instrument: Any,
    ) -> AdapterOrderPreparation:
        ...

    def submit_prepared_order(
        self,
        preparation: AdapterOrderPreparation,
        *,
        canonical_request: CanonicalOrderRequest,
    ) -> CanonicalExecutionResult:
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
    prepare = getattr(adapter, "prepare_order", None)
    submit_prepared = getattr(adapter, "submit_prepared_order", None)
    submit = getattr(adapter, "submit_order", None)
    cancel = getattr(adapter, "cancel_order", None)

    if not callable(capabilities):
        return False, "ADAPTER_CAPABILITIES_MISSING"
    if not callable(prepare):
        return False, "ADAPTER_PREPARE_MISSING"
    if not callable(submit_prepared):
        return False, "ADAPTER_PREPARED_SUBMIT_MISSING"
    if not callable(submit):
        return False, "ADAPTER_SUBMIT_MISSING"
    if not callable(cancel):
        return False, "ADAPTER_CANCEL_MISSING"

    return True, "VALID"


__all__ = [
    "AdapterOrderPreparation",
    "ExchangeAdapterCapabilities",
    "ExchangeExecutionAdapter",
    "validate_adapter_contract",
]
