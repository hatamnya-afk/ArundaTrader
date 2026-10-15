"""Focused tests for strict Decision/Risk/Trade-Gate -> canonical request production."""
import unittest
from canonical_request_runtime_producer_v0_1 import produce_canonical_requests_from_runtime_outputs


def snapshots():
    decision = {
        "asset": "BTC", "direction": "LONG", "entry_price": 100.0,
        "reference_price": 100.0, "intent_id": "INTENT-1",
        "decision_id": "DECISION-BIRTH-1", "snapshot_id": "SNAPSHOT-1",
        "timestamp": "2026-10-15T12:00:00+00:00",
    }
    risk = {
        "risk_status": "APPROVED", "position_quantity": 0.01,
        "quantity_unit": "BASE_ASSET", "quantity_source": "RISK.position_quantity",
        "stop_price": 95.0, "stop_distance": 5.0, "exposure": 1.0,
        "policy_version": "test-policy", "provenance": "REAL_MARKET",
        "observed_at": "2026-10-15T12:00:00+00:00",
    }
    gate = {"trade_gate_state": "TRADE_READY"}
    return {"BTC": decision}, {"BTC": risk}, {"BTC": gate}


class CanonicalRequestRuntimeProducerTests(unittest.TestCase):
    def test_uses_existing_upstream_values_without_resizing_or_identity_invention(self):
        decision, risk, gate = snapshots()
        result = produce_canonical_requests_from_runtime_outputs(
            decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate
        )
        record = result["BTC"]
        request = record["request"]
        self.assertEqual(request.quantity, risk["BTC"]["position_quantity"])
        self.assertEqual(request.intent_id, decision["BTC"]["intent_id"])
        self.assertEqual(request.decision_id, decision["BTC"]["decision_id"])
        self.assertEqual(request.snapshot_id, decision["BTC"]["snapshot_id"])
        self.assertEqual(record["execution_ready_package"]["package_validation"], "VALID")

    def test_missing_intent_identity_fails_closed_instead_of_fabricating_one(self):
        decision, risk, gate = snapshots()
        decision["BTC"].pop("intent_id")
        with self.assertRaisesRegex(ValueError, "ORDER_INTENT_IDENTITY_MISSING"):
            produce_canonical_requests_from_runtime_outputs(
                decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate
            )

    def test_non_trade_ready_asset_produces_no_request(self):
        decision, risk, gate = snapshots()
        gate["BTC"]["trade_gate_state"] = "REJECTED"
        result = produce_canonical_requests_from_runtime_outputs(
            decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate
        )
        self.assertEqual(result, {})

    def test_quantity_provenance_must_be_explicit(self):
        decision, risk, gate = snapshots()
        risk["BTC"].pop("quantity_source")
        with self.assertRaisesRegex(ValueError, "RISK_QUANTITY_SOURCE_MISSING"):
            produce_canonical_requests_from_runtime_outputs(
                decision_snapshot=decision, risk_snapshot=risk, trade_gate_snapshot=gate
            )


if __name__ == "__main__":
    unittest.main()
