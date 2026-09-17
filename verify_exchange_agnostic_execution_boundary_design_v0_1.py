"""
ARUNDA TRADER
EXCHANGE-AGNOSTIC EXECUTION BOUNDARY DESIGN
CONTRACT VERIFICATION v0.1

READ-ONLY / CONTRACT-ONLY.
NO NETWORK.
NO EXCHANGE WRITE.
NO DATABASE WRITE.
NO ORDER SUBMISSION.
NO EXECUTION.
"""

import ast
import inspect

import exchange_execution_contract as contract


def source_has_forbidden_write_surface() -> bool:
    source = inspect.getsource(contract)
    forbidden = (
        "requests.post(",
        "requests.put(",
        "requests.delete(",
        "requests.patch(",
        "sqlite3.connect(",
        "INSERT INTO",
        "UPDATE ",
        "DELETE FROM",
    )
    return any(marker in source for marker in forbidden)


def verify_contract() -> dict[str, bool]:
    risk = {
        "position_quantity": "AUTHORITATIVE_RISK_VALUE",
    }

    request = contract.build_order_request(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        risk=risk,
        entry_price=None,
        reference_price="REFERENCE_PRICE",
        intent_id="TEST-INTENT",
        snapshot_id="TEST-SNAPSHOT",
        timestamp="TEST-TIMESTAMP",
    )

    valid, reason = contract.validate_order_request(request)

    blocked = contract.blocked_execution_result(
        asset=request.asset,
        direction=request.direction,
        adapter="TEST_ADAPTER",
    )

    safety = contract.safety_contract()

    checks = {
        "canonical_order_request": isinstance(
            request,
            contract.CanonicalOrderRequest,
        ),
        "quantity_provenance": (
            request.quantity_source
            == "RISK.position_quantity"
        ),
        "quantity_not_recomputed": (
            request.quantity == risk["position_quantity"]
        ),
        "quantity_unit_canonical": (
            request.quantity_unit == "BASE_ASSET"
        ),
        "order_request_validation": (
            valid and reason == "VALID"
        ),
        "canonical_execution_result": isinstance(
            blocked,
            contract.CanonicalExecutionResult,
        ),
        "fail_closed": (
            blocked.accepted is False
            and blocked.status == "FAIL_CLOSED"
            and blocked.exchange_order_id is None
        ),
        "execution_disabled": (
            safety["EXECUTION_ENABLED"] is False
        ),
        "order_submission_disabled": (
            safety["ORDER_SUBMISSION_ENABLED"] is False
        ),
        "order_cancellation_disabled": (
            safety["ORDER_CANCELLATION_ENABLED"] is False
        ),
        "withdrawal_disabled": (
            safety["WITHDRAWAL_ENABLED"] is False
        ),
        "exchange_write_disabled": (
            safety["EXCHANGE_WRITE_ENABLED"] is False
        ),
        "database_write_disabled": (
            safety["DATABASE_WRITE_ENABLED"] is False
        ),
        "no_write_surface": (
            source_has_forbidden_write_surface() is False
        ),
    }

    return checks


def main() -> int:
    print("=" * 78)
    print("ARUNDA TRADER — EXCHANGE-AGNOSTIC EXECUTION BOUNDARY")
    print("CONTRACT VERIFICATION v0.1")
    print("=" * 78)
    print()
    print("NETWORK CALLS              : NONE")
    print("ORDER SUBMISSION           : NONE")
    print("EXCHANGE WRITE             : NONE")
    print("DATABASE WRITE             : NONE")
    print("EXECUTION                  : FALSE")
    print()

    checks = verify_contract()

    for name, passed in checks.items():
        print(f"{name:<34}: {'PASS' if passed else 'FAIL'}")

    print()
    print("=" * 78)
    print(
        "OVERALL RESULT             : "
        + ("PASS" if all(checks.values()) else "BLOCKED")
    )
    print("=" * 78)

    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
