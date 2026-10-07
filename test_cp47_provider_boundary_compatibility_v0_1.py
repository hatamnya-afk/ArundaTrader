"""
CP46-A3 — Venue Routing Policy Contract Tests v0.1

No HTTP.
No API.
No database.
No exchange.
No execution.
"""

from execution_venue_routing_policy_v0_1 import (
    RoutingReason,
    Venue,
    VenueRoutingRequest,
    route_venue,
)


def test_short_routes_to_futures_only():
    result = route_venue(
        VenueRoutingRequest(
            direction="SHORT",
            spot_ready=True,
            futures_ready=True,
        )
    )

    assert result.venue is Venue.FUTURES
    assert result.reason is RoutingReason.SHORT_FUTURES


def test_short_does_not_fallback_to_spot():
    result = route_venue(
        VenueRoutingRequest(
            direction="SHORT",
            spot_ready=True,
            futures_ready=False,
        )
    )

    assert result.venue is Venue.NONE
    assert result.reason is RoutingReason.SHORT_FUTURES_UNAVAILABLE


def test_long_without_derivative_requirement_routes_to_spot():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=True,
            futures_ready=True,
            derivative_required=False,
        )
    )

    assert result.venue is Venue.SPOT
    assert result.reason is RoutingReason.LONG_SPOT


def test_long_derivative_requirement_routes_to_futures():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=True,
            futures_ready=True,
            derivative_required=True,
        )
    )

    assert result.venue is Venue.FUTURES
    assert result.reason is RoutingReason.LONG_FUTURES_REQUIRED


def test_long_derivative_requirement_never_downgrades_to_spot():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=True,
            futures_ready=False,
            derivative_required=True,
        )
    )

    assert result.venue is Venue.NONE
    assert result.reason is RoutingReason.FUTURES_UNAVAILABLE


def test_both_requires_explicit_authorization():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=True,
            futures_ready=True,
            both_authorized=False,
        )
    )

    assert result.venue is Venue.SPOT
    assert result.reason is RoutingReason.LONG_SPOT


def test_both_requires_both_venues_ready():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=True,
            futures_ready=False,
            both_authorized=True,
        )
    )

    assert result.venue is Venue.SPOT
    assert result.reason is RoutingReason.LONG_SPOT


def test_both_is_selected_only_with_two_exposure_authorization():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=True,
            futures_ready=True,
            both_authorized=True,
        )
    )

    assert result.venue is Venue.BOTH
    assert result.reason is RoutingReason.LONG_BOTH_AUTHORIZED


def test_both_does_not_override_derivative_requirement_when_futures_unavailable():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=True,
            futures_ready=False,
            derivative_required=True,
            both_authorized=True,
        )
    )

    assert result.venue is Venue.NONE
    assert result.reason is RoutingReason.BOTH_NOT_READY


def test_long_spot_unavailable_does_not_silently_use_futures():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=False,
            futures_ready=True,
            derivative_required=False,
            futures_fallback_authorized=False,
        )
    )

    assert result.venue is Venue.NONE
    assert result.reason is RoutingReason.SPOT_UNAVAILABLE


def test_long_futures_fallback_requires_explicit_authorization():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=False,
            futures_ready=True,
            derivative_required=False,
            futures_fallback_authorized=True,
        )
    )

    assert result.venue is Venue.FUTURES
    assert result.reason is RoutingReason.LONG_FUTURES_REQUIRED


def test_hard_block_always_returns_none():
    result = route_venue(
        VenueRoutingRequest(
            direction="SHORT",
            spot_ready=True,
            futures_ready=True,
            hard_block=True,
        )
    )

    assert result.venue is Venue.NONE
    assert result.reason is RoutingReason.HARD_BLOCK


def test_invalid_direction_fails_closed():
    result = route_venue(
        VenueRoutingRequest(
            direction="BUY",
            spot_ready=True,
            futures_ready=True,
        )
    )

    assert result.venue is Venue.NONE
    assert result.reason is RoutingReason.INVALID_DIRECTION


def test_lowercase_direction_is_not_silently_normalized():
    result = route_venue(
        VenueRoutingRequest(
            direction="short",
            spot_ready=True,
            futures_ready=True,
        )
    )

    assert result.venue is Venue.NONE
    assert result.reason is RoutingReason.INVALID_DIRECTION


def test_invalid_boolean_state_fails_closed():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=1,
            futures_ready=True,
        )
    )

    assert result.venue is Venue.NONE
    assert result.reason is RoutingReason.INVALID_ROUTING_STATE


def test_no_venue_ready_returns_none():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=False,
            futures_ready=False,
        )
    )

    assert result.venue is Venue.NONE
    assert result.reason is RoutingReason.SPOT_UNAVAILABLE


def test_short_with_spot_only_is_none():
    result = route_venue(
        VenueRoutingRequest(
            direction="SHORT",
            spot_ready=True,
            futures_ready=False,
        )
    )

    assert result.venue is Venue.NONE


def test_quantity_is_not_part_of_routing_contract():
    request = VenueRoutingRequest(
        direction="LONG",
        spot_ready=True,
        futures_ready=True,
    )

    result = route_venue(request)

    assert result.venue is Venue.SPOT
    assert not hasattr(request, "quantity")
    assert not hasattr(result, "quantity")
    assert not hasattr(result, "converted_quantity")


def test_router_is_deterministic():
    request = VenueRoutingRequest(
        direction="SHORT",
        spot_ready=True,
        futures_ready=True,
    )

    first = route_venue(request)
    second = route_venue(request)

    assert first == second
    assert first.venue is Venue.FUTURES
    assert first.reason is RoutingReason.SHORT_FUTURES


def test_execution_semantics_are_not_created_by_router():
    result = route_venue(
        VenueRoutingRequest(
            direction="LONG",
            spot_ready=True,
            futures_ready=True,
        )
    )

    assert result.venue is Venue.SPOT
    assert not hasattr(result, "order_id")
    assert not hasattr(result, "exchange_order_id")
    assert not hasattr(result, "executed_quantity")
    assert not hasattr(result, "executed_price")
    assert not hasattr(result, "submitted")


def test_all_declared_venues_are_first_class():
    assert Venue.SPOT.value == "SPOT"
    assert Venue.FUTURES.value == "FUTURES"
    assert Venue.BOTH.value == "BOTH"
    assert Venue.NONE.value == "NONE"
