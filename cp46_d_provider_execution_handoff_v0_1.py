"""
ARUNDA TRADER
CP46-D — PROVIDER EXECUTION HANDOFF CONTRACT v0.1

Scope:
    Provider Translation -> Provider Preflight handoff.

NO NETWORK.
NO DATABASE WRITE.
NO EXCHANGE WRITE.
NO ORDER SUBMISSION.
NO EXECUTION.
NO QUANTITY CONVERSION.
NO QUANTITY MUTATION.
NO ROUNDING.

Architecture:

    CanonicalOrderRequest
            |
            v
    CP46-C Provider Translation
            |
            v
    ProviderOrderRequest
            |
            v
    CP46-D Provider Execution Handoff
            |
            v
    CP46-A6 Provider Preflight
            |
        PASS / BLOCK

Important:
    CP46-D does not translate quantity.
    CP46-D does not modify ProviderOrderRequest.
    CP46-D only adapts already-resolved provider semantics
    into the CP46-A6 preflight contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from provider_order_translation_v0_1 import (
    ProviderOrderRequest,
    ProviderTranslationResult,
    TranslationStatus,
)
from provider_preflight_v0_1 import (
    ProviderOrderPreflightRequest,
    ProviderPreflightEvidence,
    ProviderPreflightResult,
    PreflightStatus,
    PreflightReason,
    run_provider_preflight,
)


class HandoffStatus(str):
    PASS = "PASS"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ProviderExecutionHandoffResult:
    status: str
    reason: str
    message: str
    provider_request: Optional[ProviderOrderRequest] = None
    preflight: Optional[ProviderPreflightResult] = None


def _block(
    reason: str,
    message: str,
    *,
    provider_request: Optional[ProviderOrderRequest] = None,
    preflight: Optional[ProviderPreflightResult] = None,
) -> ProviderExecutionHandoffResult:
    return ProviderExecutionHandoffResult(
        status=HandoffStatus.BLOCK,
        reason=reason,
        message=message,
        provider_request=provider_request,
        preflight=preflight,
    )


def _timestamp_to_ms(timestamp: Any) -> Optional[int]:
    """
    Convert an already-canonical timestamp representation to
    provider-preflight milliseconds.

    Accepted forms:
        - positive integer milliseconds
        - numeric string representing milliseconds
        - ISO-8601 timestamp

    No current/local clock is read.
    """

    if isinstance(timestamp, bool):
        return None

    if isinstance(timestamp, int):
        return timestamp if timestamp > 0 else None

    if isinstance(timestamp, float):
        if not timestamp.is_integer() or timestamp <= 0:
            return None
        return int(timestamp)

    if not isinstance(timestamp, str):
        return None

    value = timestamp.strip()

    if not value:
        return None

    # Explicit millisecond representation.
    if value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None

    # Explicit ISO-8601 representation.
    try:
        normalized = value

        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"

        parsed_dt = datetime.fromisoformat(normalized)

        if parsed_dt.tzinfo is None:
            return None

        parsed_dt = parsed_dt.astimezone(timezone.utc)

        timestamp_ms = int(
            parsed_dt.timestamp() * 1000
        )

        return timestamp_ms if timestamp_ms > 0 else None

    except (TypeError, ValueError, OverflowError):
        return None


def build_preflight_request(
    provider_request: ProviderOrderRequest,
) -> Optional[ProviderOrderPreflightRequest]:
    """
    Adapt ProviderOrderRequest to the CP46-A6 preflight request.

    This function does NOT:
        - convert quantity
        - change quantity
        - round quantity
        - calculate notional
        - calculate leverage
        - calculate margin
        - modify provider_request
    """

    if not isinstance(
        provider_request,
        ProviderOrderRequest,
    ):
        return None

    timestamp_ms = _timestamp_to_ms(
        provider_request.timestamp
    )

    if timestamp_ms is None:
        return None

    return ProviderOrderPreflightRequest(
        symbol=provider_request.symbol,
        direction=(
            "LONG"
            if (
                provider_request.venue == "SPOT"
                and provider_request.side == "BUY"
            )
            else (
                provider_request.position_side
                if provider_request.position_side
                in {"LONG", "SHORT"}
                else provider_request.side
            )
        ),
        order_type=provider_request.order_type,
        quantity=provider_request.quantity,
        quantity_unit=provider_request.quantity_unit,
        intent_id=provider_request.intent_id,
        timestamp_ms=timestamp_ms,
        venue=provider_request.venue,
        reference_price=provider_request.entry_price,
    )


def handoff_to_provider_preflight(
    translation_result: ProviderTranslationResult,
    evidence: ProviderPreflightEvidence,
) -> ProviderExecutionHandoffResult:
    """
    CP46-D handoff.

    Translation must PASS before provider preflight can run.

    The translated ProviderOrderRequest is passed to A6 without
    quantity mutation or provider re-translation.
    """

    if not isinstance(
        translation_result,
        ProviderTranslationResult,
    ):
        return _block(
            "TRANSLATION_RESULT_INVALID",
            "Provider translation result type is invalid.",
        )

    if not isinstance(
        evidence,
        ProviderPreflightEvidence,
    ):
        return _block(
            "PREFLIGHT_EVIDENCE_INVALID",
            "Provider preflight evidence type is invalid.",
        )

    if translation_result.status != TranslationStatus.PASS:
        return _block(
            "TRANSLATION_BLOCKED",
            "Provider translation did not pass.",
        )

    provider_request = translation_result.request

    if not isinstance(
        provider_request,
        ProviderOrderRequest,
    ):
        return _block(
            "PROVIDER_REQUEST_MISSING",
            "Successful translation must contain ProviderOrderRequest.",
        )

    preflight_request = build_preflight_request(
        provider_request
    )

    if preflight_request is None:
        return _block(
            "PREFLIGHT_REQUEST_BUILD_FAILED",
            "ProviderOrderRequest could not be adapted to preflight.",
            provider_request=provider_request,
        )

    original_quantity = provider_request.quantity

    preflight_result = run_provider_preflight(
        preflight_request,
        evidence,
    )

    # Provider request must remain immutable from the handoff.
    if provider_request.quantity != original_quantity:
        return _block(
            "QUANTITY_MUTATION",
            "Provider quantity changed during handoff.",
            provider_request=provider_request,
            preflight=preflight_result,
        )

    if preflight_result.status != PreflightStatus.PASS:
        return _block(
            "PREFLIGHT_BLOCKED",
            preflight_result.message,
            provider_request=provider_request,
            preflight=preflight_result,
        )

    return ProviderExecutionHandoffResult(
        status=HandoffStatus.PASS,
        reason=PreflightReason.PASS.value,
        message="Provider translation and preflight handoff passed.",
        provider_request=provider_request,
        preflight=preflight_result,
    )


__all__ = [
    "HandoffStatus",
    "ProviderExecutionHandoffResult",
    "build_preflight_request",
    "handoff_to_provider_preflight",
]