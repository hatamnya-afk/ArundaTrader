"""Focused static/unit verification for CP49 first-execution activation wiring.

No production runtime, network call, exchange call, or database I/O.
"""
import unittest

import exchange_execution_contract
from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from cp49_first_execution_contract_v0_1 import (
    AttemptState,
    ExecutionSafetyGate,
)
from exchange_execution_boundary import execute_order
from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
)
from toobit_trading_adapter import ToobitTradingAdapter


class FakeTransport:
    transport_enabled = False
    execution_enabled = False
    order_submission_enabled = False
    exchange_write_enabled = False


class FakeAdapter:
    def __init__(self):
        self.activated = False
        self.submitted_quantity = None

    def authorize_first_execution(self, gate):
        if gate.validate() is not AttemptState.READY:
            return False
        self.activated = True
        return True

    def capabilities(self):
        return {"ORDER_SUBMISSION": self.activated}

    def submit_order(self, request):
        self.submitted_quantity = request.quantity
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="TEST_NO_NETWORK",
            asset=request.asset,
            direction=request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=request.timestamp,
            adapter="TEST",
            error_code="TEST_NO_NETWORK",
            error_message="Focused test adapter; no exchange I/O.",
        )


def ready_gate():
    return ExecutionSafetyGate(
        management_authorized=True,
        implementation_verified=True,
        prior_attempt_exists=False,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
        automatic_retry_enabled=False,
    )


def blocked_gate():
    return ExecutionSafetyGate(
        management_authorized=False,
        implementation_verified=True,
        prior_attempt_exists=False,
        execution_enabled=False,
        order_submission_enabled=False,
        exchange_write_enabled=False,
        automatic_retry_enabled=False,
    )


def request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="LIMIT",
        quantity=0.001,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100000,
        reference_price=100000,
        intent_id="intent-test",
        snapshot_id="snapshot-test",
        timestamp="2026-09-29T00:00:00+00:00",
    )


def eligibility_for(req):
    return ExecutionEligibilityResult(
        status=EligibilityStatus.PASS,
        reason="PASS",
        message="focused test eligibility",
        canonical_request=req,
    )


class CP49ActivationWiringTests(unittest.TestCase):
    def test_global_safety_defaults_remain_fail_closed(self):
        safety = exchange_execution_contract.safety_contract()
        self.assertTrue(all(value is False for value in safety.values()))

    def test_adapter_default_is_disabled(self):
        transport = FakeTransport()
        adapter = ToobitTradingAdapter(
            live_order_transport=transport,
        )
        self.assertFalse(adapter.execution_enabled)
        self.assertFalse(adapter.order_submission_enabled)
        self.assertFalse(adapter.exchange_write_enabled)
        self.assertFalse(adapter.live_order_transport_enabled)
        self.assertFalse(transport.transport_enabled)

    def test_blocked_gate_cannot_activate_adapter(self):
        transport = FakeTransport()
        adapter = ToobitTradingAdapter(
            live_order_transport=transport,
        )
        self.assertFalse(adapter.authorize_first_execution(blocked_gate()))
        self.assertFalse(adapter.execution_enabled)
        self.assertFalse(adapter.live_order_transport_enabled)
        self.assertFalse(transport.transport_enabled)

    def test_ready_gate_activates_existing_adapter_and_transport(self):
        transport = FakeTransport()
        adapter = ToobitTradingAdapter(
            live_order_transport=transport,
        )
        self.assertTrue(adapter.authorize_first_execution(ready_gate()))
        self.assertTrue(adapter.execution_enabled)
        self.assertTrue(adapter.order_submission_enabled)
        self.assertTrue(adapter.exchange_write_enabled)
        self.assertTrue(adapter.live_order_transport_enabled)
        self.assertTrue(transport.transport_enabled)
        self.assertTrue(transport.execution_enabled)
        self.assertTrue(transport.order_submission_enabled)
        self.assertTrue(transport.exchange_write_enabled)

    def test_boundary_requires_cp49_gate(self):
        req = request()
        adapter = FakeAdapter()
        result = execute_order(
            request=req,
            adapter=adapter,
            eligibility=eligibility_for(req),
        )
        self.assertEqual(result.error_code, "CP49_SAFETY_GATE_REQUIRED")
        self.assertFalse(adapter.activated)

    def test_boundary_blocks_non_ready_cp49_gate(self):
        req = request()
        adapter = FakeAdapter()
        result = execute_order(
            request=req,
            adapter=adapter,
            eligibility=eligibility_for(req),
            safety_gate=blocked_gate(),
        )
        self.assertEqual(result.error_code, "CP49_SAFETY_GATE_BLOCKED")
        self.assertFalse(adapter.activated)

    def test_ready_gate_reaches_existing_boundary_without_network(self):
        req = request()
        adapter = FakeAdapter()
        result = execute_order(
            request=req,
            adapter=adapter,
            eligibility=eligibility_for(req),
            safety_gate=ready_gate(),
        )
        self.assertTrue(adapter.activated)
        self.assertEqual(result.error_code, "TEST_NO_NETWORK")
        self.assertEqual(adapter.submitted_quantity, req.quantity)


if __name__ == "__main__":
    unittest.main()
