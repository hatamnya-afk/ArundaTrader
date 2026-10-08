"""ARUNDA TRADER — EXPLICIT EXECUTION-ATTEMPT READINESS CONTRACT v0.1.

Provider-neutral, pure contract verification for the final execution gate.

This module does NOT authorize execution, select an exchange, contact a
provider, mutate state, or submit an order. It establishes whether the
canonical request and execution-ready package are internally aligned and
eligible to reach the technical authorization boundary backed by the active
standing management mandate.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from exchange_execution_contract import CanonicalOrderRequest, validate_order_request

READY = "READY"
NOT_READY = "NOT_READY"
VALID = "VALID"


def evaluate_execution_attempt_readiness(
    *,
    execution_ready_package: Mapping[str, Any],
    request: CanonicalOrderRequest,
) -> dict[str, Any]:
    """Return a pure readiness observation for the technical authorization boundary."""
    if not isinstance(execution_ready_package, Mapping):
        raise ValueError("EXECUTION_READY_PACKAGE_INVALID")

    valid, reason = validate_order_request(request)
    if not valid:
        raise ValueError(reason)

    if execution_ready_package.get("package_state") != "EXECUTION_READY_PACKAGE":
        raise ValueError("EXECUTION_READY_PACKAGE_STATE_INVALID")
    if execution_ready_package.get("package_validation") != VALID:
        raise ValueError("EXECUTION_READY_PACKAGE_VALIDATION_INVALID")
    if execution_ready_package.get("execution_authorized") is not False:
        raise ValueError("EXECUTION_AUTHORIZATION_MUST_REMAIN_EXPLICIT")

    if execution_ready_package.get("provider_binding") != "DEFERRED":
        raise ValueError("PROVIDER_BINDING_MUST_REMAIN_DEFERRED")

    asset = execution_ready_package.get("asset")
    direction = execution_ready_package.get("direction")
    quantity = execution_ready_package.get("quantity")
    entry_price = execution_ready_package.get("entry_price")
    exposure = execution_ready_package.get("exposure")

    if asset != request.asset:
        raise ValueError("READINESS_REQUEST_ASSET_MISMATCH")
    if direction != request.direction:
        raise ValueError("READINESS_REQUEST_DIRECTION_MISMATCH")
    if quantity != request.quantity:
        raise ValueError("READINESS_REQUEST_QUANTITY_MISMATCH")
    if entry_price != request.entry_price:
        raise ValueError("READINESS_REQUEST_ENTRY_PRICE_MISMATCH")

    if not isinstance(exposure, (int, float)) or isinstance(exposure, bool) or exposure <= 0:
        raise ValueError("READINESS_EXPOSURE_INVALID")

    return {
        "readiness_state": READY,
        "readiness_validation": VALID,
        "asset": request.asset,
        "direction": request.direction,
        "quantity": request.quantity,
        "entry_price": request.entry_price,
        "notional": exposure,
        "provider_binding": "DEFERRED",
        "execution_authorized": False,
    }


__all__ = ["READY", "NOT_READY", "VALID", "evaluate_execution_attempt_readiness"]
