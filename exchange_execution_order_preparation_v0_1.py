"""ARUNDA TRADER — EXCHANGE-AGNOSTIC ORDER PREPARATION BOUNDARY v0.1.

Turns an already-authoritative CanonicalOrderRequest into an opaque,
adapter-owned order request. Core never interprets provider fields.

NO NETWORK IN CORE.
NO DATABASE WRITE.
NO EXCHANGE WRITE.
NO EXECUTION AUTHORIZATION.
"""

from __future__ import annotations

from typing import Any

from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    validate_adapter_contract,
)
from exchange_execution_contract import (
    CanonicalOrderRequest,
    validate_order_request,
)


def prepare_order_for_adapter(
    *,
    request: CanonicalOrderRequest,
    adapter: Any,
    venue: str,
    execution_instrument: Any,
) -> AdapterOrderPreparation:
    """Fail-closed handoff to the selected replaceable adapter.

    The boundary validates only provider-neutral state. The returned
    request is opaque and adapter-owned; Core must not inspect it.
    """

    valid, reason = validate_order_request(request)
    if not valid:
        return AdapterOrderPreparation(
            ready=False,
            reason=reason,
            adapter_name=str(getattr(adapter, "adapter_name", "")),
            venue=str(venue).strip().upper(),
        )

    contract_valid, contract_reason = validate_adapter_contract(adapter)
    if not contract_valid:
        return AdapterOrderPreparation(
            ready=False,
            reason=contract_reason,
            adapter_name=str(getattr(adapter, "adapter_name", "")),
            venue=str(venue).strip().upper(),
        )

    normalized_venue = str(venue).strip().upper()
    if normalized_venue not in {"SPOT", "FUTURES"}:
        return AdapterOrderPreparation(
            ready=False,
            reason="VENUE_INVALID",
            adapter_name=adapter.adapter_name,
            venue=normalized_venue,
        )

    try:
        prepared = adapter.prepare_order(
            request,
            venue=normalized_venue,
            execution_instrument=execution_instrument,
        )
    except Exception as exc:
        return AdapterOrderPreparation(
            ready=False,
            reason=f"ADAPTER_PREPARE_FAILED:{exc}",
            adapter_name=adapter.adapter_name,
            venue=normalized_venue,
        )

    if not isinstance(prepared, AdapterOrderPreparation):
        return AdapterOrderPreparation(
            ready=False,
            reason="ADAPTER_PREPARE_RESULT_INVALID",
            adapter_name=adapter.adapter_name,
            venue=normalized_venue,
        )

    if prepared.adapter_name != adapter.adapter_name:
        return AdapterOrderPreparation(
            ready=False,
            reason="ADAPTER_IDENTITY_MISMATCH",
            adapter_name=adapter.adapter_name,
            venue=normalized_venue,
        )

    if prepared.venue != normalized_venue:
        return AdapterOrderPreparation(
            ready=False,
            reason="ADAPTER_VENUE_MISMATCH",
            adapter_name=adapter.adapter_name,
            venue=normalized_venue,
        )

    return prepared


__all__ = ["prepare_order_for_adapter"]
