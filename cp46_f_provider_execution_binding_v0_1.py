"""CP46-F provider execution transport binding contract.

Provider-neutral, immutable binding between a verified CP46-E eligibility
result and the provider-specific ProviderOrderRequest produced by CP46-C/D.

No network, database, exchange write, order submission, execution, quantity
conversion, rounding, estimation, or mutation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cp46_d_provider_execution_handoff_v0_1 import (
    ProviderExecutionHandoffResult,
)
from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from provider_order_translation_v0_1 import ProviderOrderRequest


class BindingStatus:
    PASS = "PASS"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ProviderExecutionBindingResult:
    status: str
    reason: str
    message: str
    canonical_request: object | None = None
    provider_request: Optional[ProviderOrderRequest] = None


def _block(reason: str, message: str) -> ProviderExecutionBindingResult:
    return ProviderExecutionBindingResult(
        status=BindingStatus.BLOCK,
        reason=reason,
        message=message,
    )


def build_provider_execution_binding(
    eligibility: ExecutionEligibilityResult,
    handoff: ProviderExecutionHandoffResult,
) -> ProviderExecutionBindingResult:
    """Bind CP46-E eligibility to its exact provider request.

    This function validates identity/provenance only. It never changes either
    request and never performs provider I/O.
    """

    if not isinstance(eligibility, ExecutionEligibilityResult):
        return _block(
            "ELIGIBILITY_INVALID",
            "CP46-E execution eligibility result is required.",
        )

    if eligibility.status != EligibilityStatus.PASS:
        return _block(
            "ELIGIBILITY_NOT_PASS",
            "CP46-E execution eligibility must be PASS.",
        )

    canonical = eligibility.canonical_request
    if canonical is None:
        return _block(
            "CANONICAL_REQUEST_MISSING",
            "Successful eligibility has no canonical request.",
        )

    if not isinstance(handoff, ProviderExecutionHandoffResult):
        return _block(
            "HANDOFF_INVALID",
            "CP46-D provider execution handoff is required.",
        )

    if handoff.status != "PASS":
        return _block(
            "HANDOFF_NOT_PASS",
            "CP46-D provider execution handoff must be PASS.",
        )

    provider = handoff.provider_request
    if not isinstance(provider, ProviderOrderRequest):
        return _block(
            "PROVIDER_REQUEST_MISSING",
            "A valid ProviderOrderRequest is required.",
        )

    preflight = handoff.preflight
    if preflight is None or getattr(preflight, "status", None) != "PASS":
        return _block(
            "PREFLIGHT_NOT_PASS",
            "Provider preflight PASS is required.",
        )

    if provider.intent_id != canonical.intent_id:
        return _block(
            "INTENT_ID_MISMATCH",
            "Provider and canonical intent identity do not match.",
        )

    if provider.snapshot_id != canonical.snapshot_id:
        return _block(
            "SNAPSHOT_ID_MISMATCH",
            "Provider and canonical snapshot identity do not match.",
        )

    if provider.timestamp != canonical.timestamp:
        return _block(
            "TIMESTAMP_MISMATCH",
            "Provider and canonical timestamp identity do not match.",
        )

    if canonical.direction not in {"LONG", "SHORT"}:
        return _block(
            "CANONICAL_DIRECTION_INVALID",
            "Canonical direction must be LONG or SHORT.",
        )

    venue = str(provider.venue).upper().strip()
    side = str(provider.side).upper().strip()
    position_side = (
        str(provider.position_side).upper().strip()
        if provider.position_side is not None
        else None
    )

    if venue not in {"SPOT", "FUTURES"}:
        return _block(
            "VENUE_INVALID",
            "Provider venue must be SPOT or FUTURES.",
        )

    if venue == "SPOT":
        if canonical.direction != "LONG" or side != "BUY":
            return _block(
                "SPOT_DIRECTION_MISMATCH",
                "Spot binding requires canonical LONG mapped to BUY.",
            )
    else:
        expected_side = "BUY" if canonical.direction == "LONG" else "SELL"
        expected_position = canonical.direction

        if side != expected_side or position_side != expected_position:
            return _block(
                "FUTURES_DIRECTION_MISMATCH",
                "Futures side and positionSide do not match canonical direction.",
            )

    if not isinstance(provider.symbol, str) or not provider.symbol.strip():
        return _block(
            "PROVIDER_SYMBOL_INVALID",
            "Provider symbol is required.",
        )

    if provider.quantity is None:
        return _block(
            "PROVIDER_QUANTITY_MISSING",
            "Provider quantity is required and must remain exact.",
        )

    if not isinstance(provider.quantity_unit, str) or not provider.quantity_unit.strip():
        return _block(
            "PROVIDER_QUANTITY_UNIT_INVALID",
            "Provider quantity unit is required.",
        )

    return ProviderExecutionBindingResult(
        status=BindingStatus.PASS,
        reason="PROVIDER_EXECUTION_BINDING_VALID",
        message="CP46-E eligibility is deterministically bound to the provider request.",
        canonical_request=canonical,
        provider_request=provider,
    )


__all__ = [
    "BindingStatus",
    "ProviderExecutionBindingResult",
    "build_provider_execution_binding",
]
