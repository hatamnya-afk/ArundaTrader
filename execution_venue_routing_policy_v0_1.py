"""
ARUNDA TRADER — CP46-A3
PROVIDER QUANTITY SEMANTICS / VENUE ROUTING POLICY v0.1

Scope:
- Deterministic venue routing contract only.
- No exchange transport.
- No HTTP/API.
- No database write.
- No quantity conversion.
- No quantity mutation.
- No execution.

Canonical quantity semantics remain owned by the canonical
order request / risk boundary. Provider-specific quantity
translation is intentionally outside this router.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Venue(str, Enum):
    SPOT = "SPOT"
    FUTURES = "FUTURES"
    BOTH = "BOTH"
    NONE = "NONE"


class RoutingReason(str, Enum):
    LONG_SPOT = "LONG_SPOT"
    LONG_FUTURES_REQUIRED = "LONG_FUTURES_REQUIRED"
    LONG_BOTH_AUTHORIZED = "LONG_BOTH_AUTHORIZED"
    SHORT_FUTURES = "SHORT_FUTURES"
    SHORT_FUTURES_UNAVAILABLE = "SHORT_FUTURES_UNAVAILABLE"
    SPOT_UNAVAILABLE = "SPOT_UNAVAILABLE"
    FUTURES_UNAVAILABLE = "FUTURES_UNAVAILABLE"
    BOTH_NOT_READY = "BOTH_NOT_READY"
    HARD_BLOCK = "HARD_BLOCK"
    INVALID_DIRECTION = "INVALID_DIRECTION"
    INVALID_ROUTING_STATE = "INVALID_ROUTING_STATE"


@dataclass(frozen=True)
class VenueRoutingRequest:
    """
    Provider-neutral routing inputs.

    Important:
    - This contract does NOT contain canonical order quantity.
    - This contract does NOT calculate risk.
    - This contract does NOT translate BASE_ASSET to CONTRACTS
      or QUOTE_ASSET.
    - Eligibility/readiness must be established by the appropriate
      upstream gate/preflight layer.
    """

    direction: str

    spot_ready: bool
    futures_ready: bool

    derivative_required: bool = False

    # Explicit authorization for two independently authorized
    # exposures. This is NOT inferred from confidence or signal strength.
    both_authorized: bool = False

    # Explicit permission to use Futures for a LONG when Futures is
    # not required by the strategy but Spot is unavailable.
    #
    # Default False prevents silent derivative fallback.
    futures_fallback_authorized: bool = False

    # Global/local hard safety block.
    hard_block: bool = False


@dataclass(frozen=True)
class VenueRoutingDecision:
    venue: Venue
    reason: RoutingReason


def route_venue(request: VenueRoutingRequest) -> VenueRoutingDecision:
    """
    Deterministic fail-closed venue router.

    Policy:

    1. Any hard block -> NONE.

    2. Direction must be exactly LONG or SHORT.

    3. SHORT -> FUTURES ONLY.
       Spot SELL is never interpreted as SHORT.

    4. LONG:
       a) BOTH only when both venues are ready AND an explicit
          two-exposure authorization exists.
       b) If derivative/leverage is required -> FUTURES.
       c) Otherwise -> SPOT when Spot is ready.
       d) Futures may be used as a LONG fallback only when:
          - Spot is unavailable,
          - Futures is ready,
          - explicit futures_fallback_authorized=True.
       e) Otherwise -> NONE.

    5. No quantity conversion or mutation occurs here.
    """

    if request.hard_block:
        return VenueRoutingDecision(
            venue=Venue.NONE,
            reason=RoutingReason.HARD_BLOCK,
        )

    if request.direction not in {"LONG", "SHORT"}:
        return VenueRoutingDecision(
            venue=Venue.NONE,
            reason=RoutingReason.INVALID_DIRECTION,
        )

    if not isinstance(request.spot_ready, bool):
        return VenueRoutingDecision(
            venue=Venue.NONE,
            reason=RoutingReason.INVALID_ROUTING_STATE,
        )

    if not isinstance(request.futures_ready, bool):
        return VenueRoutingDecision(
            venue=Venue.NONE,
            reason=RoutingReason.INVALID_ROUTING_STATE,
        )

    if not isinstance(request.derivative_required, bool):
        return VenueRoutingDecision(
            venue=Venue.NONE,
            reason=RoutingReason.INVALID_ROUTING_STATE,
        )

    if not isinstance(request.both_authorized, bool):
        return VenueRoutingDecision(
            venue=Venue.NONE,
            reason=RoutingReason.INVALID_ROUTING_STATE,
        )

    if not isinstance(request.futures_fallback_authorized, bool):
        return VenueRoutingDecision(
            venue=Venue.NONE,
            reason=RoutingReason.INVALID_ROUTING_STATE,
        )

    # ---------------------------------------------------------
    # SHORT
    # ---------------------------------------------------------
    #
    # Spot SELL is ownership disposition, not a short position.
    # Therefore SHORT has no Spot route.
    #
    if request.direction == "SHORT":
        if request.futures_ready:
            return VenueRoutingDecision(
                venue=Venue.FUTURES,
                reason=RoutingReason.SHORT_FUTURES,
            )

        return VenueRoutingDecision(
            venue=Venue.NONE,
            reason=RoutingReason.SHORT_FUTURES_UNAVAILABLE,
        )

    # ---------------------------------------------------------
    # LONG
    # ---------------------------------------------------------

    # BOTH requires explicit authorization for two independent
    # exposures. It is never inferred.
    if request.both_authorized:
        if request.spot_ready and request.futures_ready:
            return VenueRoutingDecision(
                venue=Venue.BOTH,
                reason=RoutingReason.LONG_BOTH_AUTHORIZED,
            )

        # If two-exposure authorization exists but both venues are
        # not ready, do not silently manufacture BOTH.
        #
        # A single venue can still be selected when the policy
        # independently permits it below.
        if request.derivative_required:
            if request.futures_ready:
                return VenueRoutingDecision(
                    venue=Venue.FUTURES,
                    reason=RoutingReason.LONG_FUTURES_REQUIRED,
                )

            return VenueRoutingDecision(
                venue=Venue.NONE,
                reason=RoutingReason.BOTH_NOT_READY,
            )

        if request.spot_ready:
            return VenueRoutingDecision(
                venue=Venue.SPOT,
                reason=RoutingReason.LONG_SPOT,
            )

    # Derivative/leverage requirement is explicit.
    # Never silently downgrade to Spot.
    if request.derivative_required:
        if request.futures_ready:
            return VenueRoutingDecision(
                venue=Venue.FUTURES,
                reason=RoutingReason.LONG_FUTURES_REQUIRED,
            )

        return VenueRoutingDecision(
            venue=Venue.NONE,
            reason=RoutingReason.FUTURES_UNAVAILABLE,
        )

    # Normal LONG path: Spot is primary.
    if request.spot_ready:
        return VenueRoutingDecision(
            venue=Venue.SPOT,
            reason=RoutingReason.LONG_SPOT,
        )

    # No silent Futures fallback.
    # A Futures fallback requires explicit authorization.
    if request.futures_ready and request.futures_fallback_authorized:
        return VenueRoutingDecision(
            venue=Venue.FUTURES,
            reason=RoutingReason.LONG_FUTURES_REQUIRED,
        )

    return VenueRoutingDecision(
        venue=Venue.NONE,
        reason=RoutingReason.SPOT_UNAVAILABLE,
    )


__all__ = [
    "Venue",
    "RoutingReason",
    "VenueRoutingRequest",
    "VenueRoutingDecision",
    "route_venue",
]
