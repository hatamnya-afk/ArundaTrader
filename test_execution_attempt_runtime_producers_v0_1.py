"""Focused tests for authentic final-attempt context producers.

Fixtures are isolated unit-test data; no production runtime or provider is called.
"""
from datetime import datetime, timedelta, timezone
import unittest

from exchange_execution_contract import CanonicalOrderRequest
from execution_attempt_runtime_producers_v0_1 import produce_final_execution_attempt_context


def valid_readiness():
    return {
        "readiness_state": "PRE_EXECUTION_READY",
        "readiness_validation": "VALID",
        "asset": "BTC",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_price": 95.0,
        "stop_distance": 5.0,
        "quantity": 0.01,
        "exposure": 1.0,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": "unit-test-policy",
        "provenance": "REAL_MARKET",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "provider_binding": "DEFERRED",
    }


def valid_mandate():
    now = datetime.now(timezone.utc)
    return {
        "decision": "AUTHORIZED",
        "mandate_id": "UNIT-MANDATE",
        "authorized_by": "unit-test",
        "authorization_source": "MANAGEMENT_PHASE_ENTRY_DECISION",
        "environment": "REAL_PRODUCTION",
        "issued_at": (now - timedelta(minutes=1)).isoformat(),
        "expires_at": (now + timedelta(minutes=5)).isoformat(),
        "allowed_markets": ["SPOT", "FUTURES"],
        "provider": "TOOBIT",
        "capital_policy": "PROGRESSIVE_AFTER_REAL_OUTCOME_REVIEW",
        "evidence_required_before": ["technical-gate"],
        "evidence_required_after": ["provider-outcome"],
    }


def valid_request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=0.01,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100.0,
        reference_price=100.0,
        intent_id="UNIT-INTENT",
        snapshot_id="UNIT-SNAPSHOT",
        timestamp=datetime.now(timezone.utc).isoformat(),
        decision_id="UNIT-DECISION-BIRTH",
    )


class RuntimeProducerTests(unittest.TestCase):
    def test_produces_package_and_time_bounded_standing_mandate(self):
        result = produce_final_execution_attempt_context(
            readiness=valid_readiness(),
            management_observation=valid_mandate(),
            request=valid_request(),
            venue="SPOT",
            execution_instrument="BTC-USDT",
        )
        self.assertEqual(result["execution_ready_package"]["package_validation"], "VALID")
        self.assertEqual(result["authorization_observation"]["authorization_mode"], "STANDING_MANDATE")
        self.assertEqual(result["authorization_observation"]["environment"], "REAL_PRODUCTION")
        self.assertEqual(result["venue"], "SPOT")
        self.assertEqual(result["provider_binding"], "DEFERRED")
        self.assertIs(result["execution_authorized"], False)
        self.assertIs(result["execution_submitted"], False)

    def test_missing_expiry_fails_closed_without_inventing_time(self):
        mandate = valid_mandate()
        mandate.pop("expires_at")
        with self.assertRaisesRegex(ValueError, "MANAGEMENT_EXPIRY_INVALID"):
            produce_final_execution_attempt_context(
                readiness=valid_readiness(),
                management_observation=mandate,
                request=valid_request(),
                venue="SPOT",
                execution_instrument="BTC-USDT",
            )

    def test_package_rejects_missing_upstream_risk_field(self):
        readiness = valid_readiness()
        readiness.pop("stop_price")
        with self.assertRaises(ValueError):
            produce_final_execution_attempt_context(
                readiness=readiness,
                management_observation=valid_mandate(),
                request=valid_request(),
                venue="SPOT",
                execution_instrument="BTC-USDT",
            )

    def test_request_readiness_mismatch_fails_closed(self):
        request = valid_request()
        request = CanonicalOrderRequest(
            asset=request.asset, direction=request.direction,
            order_type=request.order_type, quantity=0.02,
            quantity_unit=request.quantity_unit, quantity_source=request.quantity_source,
            entry_price=request.entry_price, reference_price=request.reference_price,
            intent_id=request.intent_id, snapshot_id=request.snapshot_id,
            timestamp=request.timestamp, decision_id=request.decision_id,
        )
        with self.assertRaisesRegex(ValueError, "READINESS_REQUEST_QUANTITY_MISMATCH"):
            produce_final_execution_attempt_context(
                readiness=valid_readiness(),
                management_observation=valid_mandate(),
                request=request,
                venue="SPOT",
                execution_instrument="BTC-USDT",
            )

    def test_pipeline_verifier_calls_real_context_producer(self):
        from pathlib import Path
        import ast
        tree = ast.parse(Path(__file__).with_name("arunda_pipeline.py").read_text(encoding="utf-8-sig"))
        verifier = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "verify_execution_boundary_integration")
        called = {
            node.func.id for node in ast.walk(verifier)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertIn("produce_final_execution_attempt_context", called)


if __name__ == "__main__":
    unittest.main()
