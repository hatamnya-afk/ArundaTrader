"""Runtime producers for the final execution-attempt context.

Consumes only upstream-produced values. It never creates an order request,
manufactures timestamps, chooses an expiry, or enables provider submission.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from execution_ready_package_v0_1 import build_execution_ready_package
from execution_attempt_readiness_contract_v0_1 import evaluate_execution_attempt_readiness
from management_execution_authorization_v0_1 import evaluate_management_phase_entry
from exchange_execution_contract import CanonicalOrderRequest


def produce_final_execution_attempt_context(
    *,
    readiness: Mapping[str, Any],
    management_observation: Mapping[str, Any],
    request: CanonicalOrderRequest,
    venue: str,
    execution_instrument: Any,
) -> dict[str, Any]:
    """Produce a validated package and active standing-mandate observation.

    All timestamps and policy values must originate from the caller's
    authoritative records. Missing/incomplete/expired mandate data fails closed.
    """
    if not isinstance(readiness, Mapping):
        raise ValueError("EXECUTION_READY_SOURCE_MISSING")
    if not isinstance(management_observation, Mapping):
        raise ValueError("ACTIVE_STANDING_MANDATE_SOURCE_MISSING")
    if not isinstance(request, CanonicalOrderRequest):
        raise ValueError("CANONICAL_ORDER_REQUEST_SOURCE_MISSING")
    if not isinstance(venue, str) or not venue.strip():
        raise ValueError("EXECUTION_VENUE_SOURCE_MISSING")
    if execution_instrument is None or (
        isinstance(execution_instrument, str) and not execution_instrument.strip()
    ):
        raise ValueError("EXECUTION_INSTRUMENT_SOURCE_MISSING")

    package = build_execution_ready_package(readiness)
    management = evaluate_management_phase_entry(management_observation)
    authorization = management.get("authorization_observation")
    if not isinstance(authorization, Mapping):
        raise ValueError("ACTIVE_STANDING_MANDATE_NOT_AUTHORIZED")

    readiness_observation = evaluate_execution_attempt_readiness(
        execution_ready_package=package,
        request=request,
    )
    readiness_observation = dict(readiness_observation)
    readiness_observation["venue"] = venue.strip().upper()
    readiness_observation["execution_instrument"] = execution_instrument

    # Return the validated observations only; the provider adapter remains
    # unbound and no attempt/submission is made by this producer.
    return {
        "execution_ready_package": package,
        "authorization_observation": dict(authorization),
        "readiness_observation": readiness_observation,
        "venue": venue.strip().upper(),
        "execution_instrument": execution_instrument,
        "management_mandate_id": management["mandate_id"],
        "provider": management["provider"],
        "provider_binding": "DEFERRED",
        "execution_authorized": False,
        "execution_submitted": False,
    }


__all__ = ["produce_final_execution_attempt_context"]
