"""Focused tests for runtime OrderIntent + management-mandate canonical request production."""
import unittest
from canonical_request_runtime_producer_v0_1 import produce_canonical_requests_from_runtime_outputs


def snapshots():
    decision = {"asset": "BTC", "direction": "LONG", "decision_id": "DECISION-BIRTH-1"}
    risk = {
        "risk_status": "APPROVED", "position_quantity": 0.01,
        "quantity_unit": "BASE_ASSET", "quantity_source": "RISK.position_quantity",
        "stop_price": 95.0, "stop_distance": 5.0, "exposure": 1.0,
        "policy_version": "test-policy", "provenance": "REAL_MARKET",
        "observed_at": "2026-10-15T12:00:00+00:00",
    }
    gate = {"trade_gate_state": "TRADE_READY"}
    intent = {
        "asset": "BTC", "direction": "LONG", "entry_price": 100.0,
        "reference_price": 100.0, "intent_id": "OI-DECISION-BIRTH-1",
        "decision_id": "DECISION-BIRTH-1", "snapshot_id": "SNAPSHOT-1",
        "timestamp": "2026-10-15T12:00:00+00:00", "quantity": 0.01,
        "quantity_unit": "BASE_ASSET", "quantity_source": "RISK.position_quantity",
    }
    return {"BTC": decision}, {"BTC": risk}, {"BTC": gate}, {"BTC": intent}, {
        "decision": "AUTHORIZED", "mandate_id": "TEST-ONLY", "issued_at": "test",
        "expires_at": "test", "environment": "REAL_PRODUCTION",
    }


class CanonicalRequestRuntimeProducerTests(unittest.TestCase):
    def test_uses_authoritative_order_intent_and_risk_quantity_unchanged(self):
        decision, risk, gate, intents, mandate = snapshots()
        result = produce_canonical_requests_from_runtime_outputs(
            decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate,
            order_intents=intents, management_observation=mandate,
        )
        record = result["BTC"]
        request = record["request"]
        self.assertEqual(request.quantity, risk["BTC"]["position_quantity"])
        self.assertEqual(request.intent_id, intents["BTC"]["intent_id"])
        self.assertEqual(request.decision_id, decision["BTC"]["decision_id"])
        self.assertEqual(request.snapshot_id, intents["BTC"]["snapshot_id"])
        self.assertEqual(record["execution_ready_package"]["package_validation"], "VALID")
        self.assertEqual(record["management_observation"], mandate)

    def test_missing_authoritative_order_intent_fails_closed(self):
        decision, risk, gate, _, mandate = snapshots()
        with self.assertRaisesRegex(ValueError, "AUTHORITATIVE_ORDER_INTENT_MISSING"):
            produce_canonical_requests_from_runtime_outputs(
                decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate,
                order_intents={}, management_observation=mandate,
            )

    def test_intent_decision_birth_mismatch_fails_closed(self):
        decision, risk, gate, intents, mandate = snapshots()
        intents["BTC"]["decision_id"] = "OTHER-DECISION"
        with self.assertRaisesRegex(ValueError, "ORDER_INTENT_DECISION_BIRTH_MISMATCH"):
            produce_canonical_requests_from_runtime_outputs(
                decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate,
                order_intents=intents, management_observation=mandate,
            )

    def test_non_trade_ready_asset_produces_no_request(self):
        decision, risk, gate, intents, mandate = snapshots()
        gate["BTC"]["trade_gate_state"] = "REJECTED"
        intents.clear()
        result = produce_canonical_requests_from_runtime_outputs(
            decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate,
            order_intents=intents, management_observation=mandate,
        )
        self.assertEqual(result, {})

    def test_quantity_provenance_must_be_explicit(self):
        decision, risk, gate, intents, mandate = snapshots()
        risk["BTC"].pop("quantity_source")
        with self.assertRaisesRegex(ValueError, "RISK_QUANTITY_SOURCE_INVALID"):
            produce_canonical_requests_from_runtime_outputs(
                decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate,
                order_intents=intents, management_observation=mandate,
            )


if __name__ == "__main__":
    unittest.main()
