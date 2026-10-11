"""Build the complete, provider-neutral context for the final attempt boundary.

This module only validates and assembles existing authoritative inputs. It
never invents stop/risk values, chooses a venue implicitly, reads credentials,
contacts a provider, submits an order, or mutates persistent state.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from execution_ready_package_v0_1 import build_execution_ready_package
from execution_instrument_policy_v0_1 import build_execution_instrument_specification
from exchange_execution_contract import CanonicalOrderRequest, validate_order_request


def build_production_final_attempt_context(
    *,
    request: CanonicalOrderRequest,
    pre_execution_readiness: Mapping[str, Any],
    management_observation: Mapping[str, Any],
    adapter: Any,
    venue: str,
) -> dict[str, Any]:
    """Validate authoritative readiness and produce the exact dispatcher context.

    `pre_execution_readiness` must come from the existing pre-execution
    readiness contract. Missing stop, sizing, risk, gate, provenance or
    timestamp fields fail closed; this function does not derive or fill them.
    Provider instrument metadata remains an adapter-owned authoritative read
    and is intentionally not simulated by this pure context assembler.
    """
    if not isinstance(request, CanonicalOrderRequest):
        raise ValueError("CANONICAL_ORDER_REQUEST_INVALID")
    valid, reason = validate_order_request(request)
    if not valid:
        raise ValueError(reason)
    if not isinstance(pre_execution_readiness, Mapping):
        raise ValueError("PRE_EXECUTION_READINESS_MISSING")
    if not isinstance(management_observation, Mapping):
        raise ValueError("MANAGEMENT_MANDATE_MISSING")
    if adapter is None or not isinstance(getattr(adapter, "adapter_name", None), str):
        raise ValueError("EXECUTION_ADAPTER_INVALID")
    if not isinstance(venue, str) or venue.strip().upper() not in {"SPOT", "FUTURES"}:
        raise ValueError("EXECUTION_VENUE_INVALID")

    readiness = dict(pre_execution_readiness)
    # The canonical request is the identity/quantity authority at this boundary.
    aligned = {
        "asset": request.asset,
        "direction": request.direction,
        "entry_price": request.entry_price,
        "quantity": request.quantity,
    }
    for field, expected in aligned.items():
        if readiness.get(field) != expected:
            raise ValueError(f"PRE_EXECUTION_REQUEST_MISMATCH:{field}")

    package = build_execution_ready_package(readiness)
    instrument = build_execution_instrument_specification(
        asset=request.asset,
        venue=venue.strip().upper(),
    )
    return {
        "execution_ready_package": package,
        "management_observation": dict(management_observation),
        "adapter": adapter,
        "venue": venue.strip().upper(),
        "execution_instrument": instrument,
    }


__all__ = ["build_production_final_attempt_context"]
