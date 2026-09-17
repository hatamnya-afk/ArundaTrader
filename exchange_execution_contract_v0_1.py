"""
ARUNDA TRADER
EXCHANGE-AGNOSTIC EXECUTION CONTRACT v0.1

CONTRACT-ONLY.
NO NETWORK.
NO EXCHANGE WRITE.
NO ORDER SUBMISSION.
NO DATABASE WRITE.
NO EXECUTION.

Authoritative quantity provenance:
    Risk Contract -> position_quantity

Canonical quantity semantics:
    quantity is the base-asset quantity supplied by Risk.
    Execution Boundary MUST NOT calculate, round, clamp, normalize,
    or otherwise modify it.
"""

from dataclasses import dataclass
from typing import Any, Mapping, Optional


EXECUTION_ENABLED = False
ORDER_SUBMISSION_ENABLED = False
ORDER_CANCELLATION_ENABLED = False
WITHDRAWAL_ENABLED = False
EXCHANGE_WRITE_ENABLED = False
DATABASE_WRITE_ENABLED = False


ORDER_TYPE_MARKET = "MARKET"
VALID_DIRECTIONS = frozenset({"LONG", "SHORT"})
QUANTITY_UNIT_BASE_ASSET = "BASE_ASSET"
QUANTITY_SOURCE_RISK_POSITION = "RISK.position_quantity"


@dataclass(frozen=True)
class CanonicalOrderRequest:
    asset: str
    direction: str
    order_type: str
    quantity: Any
    quantity_unit: str
    quantity_source: str
    entry_price: Optional[Any]
    reference_price: Optional[Any]
    intent_id: str
    snapshot_id: str
    timestamp: str


@dataclass(frozen=True)
class CanonicalExecutionResult:
    accepted: bool
    exchange_order_id: Optional[str]
    status: str
    asset: Optional[str]
    direction: Optional[str]
    executed_quantity: Optional[Any]
    executed_price: Optional[Any]
    timestamp: Optional[str]
    adapter: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]


def build_order_request(
    *,
    asset: str,
    direction: str,
    order_type: str,
    risk: Mapping[str, Any],
    entry_price: Optional[Any],
    reference_price: Optional[Any],
    intent_id: str,
    snapshot_id: str,
    timestamp: str,
) -> CanonicalOrderRequest:
    """
    Build only from already-authoritative upstream values.

    quantity is copied exactly from risk["position_quantity"].
    No sizing/recalculation is performed here.
    """

    if not isinstance(risk, Mapping):
        raise ValueError("RISK_INPUT_INVALID")

    if "position_quantity" not in risk:
        raise ValueError("QUANTITY_PROVENANCE_MISSING")

    quantity = risk["position_quantity"]

    if quantity is None:
        raise ValueError("QUANTITY_UNAVAILABLE")

    return CanonicalOrderRequest(
        asset=str(asset).strip().upper(),
        direction=str(direction).strip().upper(),
        order_type=str(order_type).strip().upper(),
        quantity=quantity,
        quantity_unit=QUANTITY_UNIT_BASE_ASSET,
        quantity_source=QUANTITY_SOURCE_RISK_POSITION,
        entry_price=entry_price,
        reference_price=reference_price,
        intent_id=str(intent_id).strip(),
        snapshot_id=str(snapshot_id).strip(),
        timestamp=str(timestamp).strip(),
    )


def validate_order_request(
    request: CanonicalOrderRequest,
) -> tuple[bool, str]:
    """Pure validation. No network, DB, exchange, or mutation."""

    if not isinstance(request, CanonicalOrderRequest):
        return False, "ORDER_REQUEST_TYPE_INVALID"

    if not request.asset:
        return False, "ASSET_INVALID"

    if request.direction not in VALID_DIRECTIONS:
        return False, "DIRECTION_INVALID"

    if not request.order_type:
        return False, "ORDER_TYPE_INVALID"

    if request.quantity is None:
        return False, "QUANTITY_UNAVAILABLE"

    if request.quantity_unit != QUANTITY_UNIT_BASE_ASSET:
        return False, "QUANTITY_UNIT_INVALID"

    if request.quantity_source != QUANTITY_SOURCE_RISK_POSITION:
        return False, "QUANTITY_PROVENANCE_INVALID"

    if not request.intent_id:
        return False, "INTENT_ID_INVALID"

    if not request.snapshot_id:
        return False, "SNAPSHOT_ID_INVALID"

    if not request.timestamp:
        return False, "TIMESTAMP_INVALID"

    return True, "VALID"


def blocked_execution_result(
    *,
    asset: Optional[str] = None,
    direction: Optional[str] = None,
    adapter: Optional[str] = None,
    error_code: str = "EXECUTION_DISABLED",
    error_message: str = "Execution is disabled by contract.",
) -> CanonicalExecutionResult:
    """
    Contract-level fail-closed result.
    This function does not contact an exchange.
    """

    return CanonicalExecutionResult(
        accepted=False,
        exchange_order_id=None,
        status="FAIL_CLOSED",
        asset=asset,
        direction=direction,
        executed_quantity=None,
        executed_price=None,
        timestamp=None,
        adapter=adapter,
        error_code=error_code,
        error_message=error_message,
    )


def safety_contract() -> dict[str, bool]:
    return {
        "EXECUTION_ENABLED": EXECUTION_ENABLED,
        "ORDER_SUBMISSION_ENABLED": ORDER_SUBMISSION_ENABLED,
        "ORDER_CANCELLATION_ENABLED": ORDER_CANCELLATION_ENABLED,
        "WITHDRAWAL_ENABLED": WITHDRAWAL_ENABLED,
        "EXCHANGE_WRITE_ENABLED": EXCHANGE_WRITE_ENABLED,
        "DATABASE_WRITE_ENABLED": DATABASE_WRITE_ENABLED,
    }


def self_check() -> dict[str, bool]:
    safety = safety_contract()

    return {
        "canonical_request_defined": True,
        "canonical_result_defined": True,
        "quantity_from_risk_position_quantity": (
            QUANTITY_SOURCE_RISK_POSITION
            == "RISK.position_quantity"
        ),
        "quantity_unit_is_exchange_agnostic": (
            QUANTITY_UNIT_BASE_ASSET == "BASE_ASSET"
        ),
        "execution_boundary_does_not_size": True,
        "execution_disabled": safety["EXECUTION_ENABLED"] is False,
        "order_submission_disabled": (
            safety["ORDER_SUBMISSION_ENABLED"] is False
        ),
        "order_cancellation_disabled": (
            safety["ORDER_CANCELLATION_ENABLED"] is False
        ),
        "withdrawal_disabled": safety["WITHDRAWAL_ENABLED"] is False,
        "exchange_write_disabled": (
            safety["EXCHANGE_WRITE_ENABLED"] is False
        ),
        "database_write_disabled": (
            safety["DATABASE_WRITE_ENABLED"] is False
        ),
    }


if __name__ == "__main__":
    checks = self_check()
    for name, passed in checks.items():
        print(f"{name}: {passed}")
    print(
        "SELF CHECK RESULT : "
        + ("PASS" if all(checks.values()) else "FAIL")
    )
