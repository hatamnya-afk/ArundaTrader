"""
ARUNDA TRADER
CP46-E — PROVIDER PREFLIGHT -> EXECUTION ELIGIBILITY GATE v0.1

Provider-neutral, deterministic eligibility contract.

NO NETWORK.
NO DATABASE WRITE.
NO EXCHANGE WRITE.
NO ORDER SUBMISSION.
NO EXECUTION.
NO QUANTITY CONVERSION.
NO QUANTITY MUTATION.
NO ROUNDING.

Required chain:
    CP46-D PASS
        ->
    ProviderPreflightResult PASS
        ->
    CP46-E ExecutionEligibility PASS
        ->
    Existing Execution Boundary
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from exchange_execution_contract import CanonicalOrderRequest
from cp46_d_provider_execution_handoff_v0_1 import (
    HandoffStatus,
    ProviderExecutionHandoffResult,
)
from provider_preflight_v0_1 import PreflightStatus


class EligibilityStatus(str):
    PASS = "PASS"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ExecutionEligibilityResult:
    status: str
    reason: str
    message: str
    canonical_request: Optional[CanonicalOrderRequest] = None


def _block(reason: str, message: str) -> ExecutionEligibilityResult:
    return ExecutionEligibilityResult(
        status=EligibilityStatus.BLOCK,
        reason=reason,
        message=message,
        canonical_request=None,
    )


def build_execution_eligibility(
    canonical_request: CanonicalOrderRequest,
    handoff: ProviderExecutionHandoffResult,
) -> ExecutionEligibilityResult:
    """
    Prove that a canonical request has a successful CP46-D provider
    preflight predecessor.

    The canonical request is returned unchanged. No provider request
    is produced here and no provider-specific quantity semantics are
    introduced.
    """

    if not isinstance(canonical_request, CanonicalOrderRequest):
        return _block(
            "CANONICAL_REQUEST_INVALID",
            "CanonicalOrderRequest is required.",
        )

    if not isinstance(handoff, ProviderExecutionHandoffResult):
        return _block(
            "HANDOFF_INVALID",
            "CP46-D handoff result is required.",
        )

    if handoff.status != HandoffStatus.PASS:
        return _block(
            "CP46_D_NOT_PASSED",
            "CP46-D provider preflight handoff did not pass.",
        )

    if handoff.preflight is None:
        return _block(
            "PREFLIGHT_RESULT_MISSING",
            "Successful CP46-D handoff must contain preflight result.",
        )

    if handoff.preflight.status != PreflightStatus.PASS:
        return _block(
            "PREFLIGHT_NOT_PASSED",
            "Provider preflight must be PASS.",
        )

    provider_request = handoff.provider_request

    if provider_request is None:
        return _block(
            "PROVIDER_REQUEST_MISSING",
            "Successful CP46-D handoff must contain provider request.",
        )

    if provider_request.intent_id != canonical_request.intent_id:
        return _block(
            "INTENT_ID_MISMATCH",
            "Provider and canonical intent_id do not match.",
        )

    if provider_request.snapshot_id != canonical_request.snapshot_id:
        return _block(
            "SNAPSHOT_ID_MISMATCH",
            "Provider and canonical snapshot_id do not match.",
        )

    if canonical_request.direction not in {"LONG", "SHORT"}:
        return _block(
            "DIRECTION_INVALID",
            "Canonical direction must be LONG or SHORT.",
        )

    provider_direction = (
        "LONG"
        if (
            provider_request.venue == "SPOT"
            and provider_request.side == "BUY"
        )
        else provider_request.position_side
    )

    if provider_direction != canonical_request.direction:
        return _block(
            "DIRECTION_MISMATCH",
            "Provider and canonical direction do not match.",
        )

    # Direct BASE_ASSET quantity must remain exactly identical.
    # Provider-specific translated units (e.g. CONTRACTS) are owned
    # by CP46-C and are therefore not reconverted here.
    if provider_request.quantity_unit == "BASE_ASSET":
        if provider_request.quantity != canonical_request.quantity:
            return _block(
                "QUANTITY_MISMATCH",
                "Provider and canonical BASE_ASSET quantities differ.",
            )

    return ExecutionEligibilityResult(
        status=EligibilityStatus.PASS,
        reason="PASS",
        message=(
            "Provider preflight passed and execution eligibility "
            "is established."
        ),
        canonical_request=canonical_request,
    )


__all__ = [
    "EligibilityStatus",
    "ExecutionEligibilityResult",
    "build_execution_eligibility",
]
