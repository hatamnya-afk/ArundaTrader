"""Focused execution-boundary test for authoritative trade-event identity.

No network, exchange, database, or real execution is used.
"""

from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from cp49_first_execution_contract_v0_1 import ExecutionSafetyGate
from exchange_execution_boundary import execute_order
from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
)
from mcp01_trade_event_identity_v0_1 import validate_trade_event_id


class FakeAdapter:
    def __init__(self):
        self.live_order_transport_enabled = False
        self.execution_enabled = False
        self.order_submission_enabled = False
        self.exchange_write_enabled = False

    def authorize_first_execution(self, safety_gate):
        assert safety_gate.validate().value == "READY"
        self.live_order_transport_enabled = True
        self.execution_enabled = True
        self.order_submission_enabled = True
        self.exchange_write_enabled = True
        return True

    def capabilities(self):
        return {"ORDER_SUBMISSION": True}

    def submit_order(self, request):
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id="EXCHANGE-123",
            status="REJECTED",
            asset=request.asset,
            direction=request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=request.timestamp,
            adapter="TOOBIT",
            error_code="-1157",
            error_message="provider rejected",
        )


def build_request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="LIMIT",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="AT-INTENT-1",
        snapshot_id="SNAP-1",
        timestamp="2026-10-06T00:00:00+00:00",
        decision_id="DEC-BTC-1",
    )


def build_gate():
    return ExecutionSafetyGate(
        management_authorized=True,
        implementation_verified=True,
        prior_attempt_exists=False,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
        automatic_retry_enabled=False,
    )


def test_trade_event_id_is_issued_at_boundary():
    request = build_request()
    eligibility = ExecutionEligibilityResult(
        status=EligibilityStatus.PASS,
        reason="PASS",
        message="eligible",
        canonical_request=request,
    )
    result = execute_order(
        request=request,
        adapter=FakeAdapter(),
        eligibility=eligibility,
        safety_gate=build_gate(),
    )
    assert validate_trade_event_id(result.trade_event_id) is True
    assert result.trade_event_id != result.exchange_order_id


def test_provider_order_id_is_not_trade_event_id():
    request = build_request()
    eligibility = ExecutionEligibilityResult(
        status=EligibilityStatus.PASS,
        reason="PASS",
        message="eligible",
        canonical_request=request,
    )
    result = execute_order(
        request=request,
        adapter=FakeAdapter(),
        eligibility=eligibility,
        safety_gate=build_gate(),
    )
    assert result.exchange_order_id == "EXCHANGE-123"
    assert result.trade_event_id != "EXCHANGE-123"


def main():
    tests = (
        test_trade_event_id_is_issued_at_boundary,
        test_provider_order_id_is_not_trade_event_id,
    )
    for test in tests:
        test()
    print("MCP01_EXECUTION_BOUNDARY_TRADE_EVENT_TESTS=2/2 PASS")


if __name__ == "__main__":
    main()
