"""Offline tests for durable reconciliation; no provider calls or production DB."""
import tempfile
import unittest
from pathlib import Path

from exchange_execution_atomic_intent_claim_store_v0_1 import (
    PROVIDER_ACCEPTED, RECONCILIATION_REQUIRED, SUBMISSION_OUTCOME_UNKNOWN,
    SQLiteIntentClaimStore,
)
from execution_order_reconciliation_v0_1 import reconcile_order_attempt
from toobit_exchange_adapter_v0_1 import ToobitAdapterResult


class _FakeAdapter:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def query_order_by_client_order_id(self, **kwargs):
        self.calls += 1
        assert kwargs["client_order_id"] == "A123"
        return self.result


def _claim(path):
    store = SQLiteIntentClaimStore(path)
    store.claim(provider_namespace="ARUNDA-EXECUTION",
                intent_id="intent-1", client_order_id="A123")
    store.transition(provider_namespace="ARUNDA-EXECUTION",
                     intent_id="intent-1", status=SUBMISSION_OUTCOME_UNKNOWN,
                     trade_event_id="trade-1", decision_id="decision-1",
                     detail_code="POST_BOUNDARY_ENTERED")
    return store


class ReconciliationTests(unittest.TestCase):
    def test_positive_identity_matched_lookup_persists_outcome_and_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            store = _claim(Path(directory) / "claims.sqlite3")
            adapter = _FakeAdapter(ToobitAdapterResult(True, "ORDER_FOUND", {
                "state_known": True, "reconciliation_state": "ORDER_FOUND",
                "client_order_id": "A123", "symbol": "BTCUSDT",
                "exchange_order_id": "exchange-1", "provider_status": "FILLED",
                "executed_quantity": "0.01", "executed_price": "65000",
                "timestamp": "1792000000000",
            }))
            result = reconcile_order_attempt(claim_store=store, adapter=adapter,
                intent_id="intent-1", venue="SPOT", symbol="BTCUSDT")
            self.assertTrue(result["allowed"])
            self.assertEqual(result["claim_status"], PROVIDER_ACCEPTED)
            claim = store.get(provider_namespace="ARUNDA-EXECUTION", intent_id="intent-1")
            self.assertEqual(claim.exchange_order_id, "exchange-1")
            evidence = store.list_reconciliation_evidence(
                provider_namespace="ARUNDA-EXECUTION", intent_id="intent-1")
            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0]["executed_quantity"], "0.01")
            self.assertEqual(evidence[0]["executed_price"], "65000")
            self.assertEqual(adapter.calls, 1)
            self.assertFalse(result["resubmit_allowed"])

    def test_negative_lookup_is_evidence_of_uncertainty_not_non_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            store = _claim(Path(directory) / "claims.sqlite3")
            adapter = _FakeAdapter(ToobitAdapterResult(False, "ORDER_LOOKUP_UNRESOLVED", {
                "state_known": False,
                "reconciliation_state": "UNRESOLVED_KEEP_QUARANTINED",
                "client_order_id": "A123", "symbol": "BTCUSDT",
                "resubmit_allowed": False, "detail": "order not found",
            }))
            result = reconcile_order_attempt(claim_store=store, adapter=adapter,
                intent_id="intent-1", venue="SPOT", symbol="BTCUSDT")
            self.assertFalse(result["allowed"])
            self.assertEqual(result["claim_status"], RECONCILIATION_REQUIRED)
            self.assertFalse(result["resubmit_allowed"])
            claim = store.get(provider_namespace="ARUNDA-EXECUTION", intent_id="intent-1")
            self.assertEqual(claim.status, RECONCILIATION_REQUIRED)
            evidence = store.list_reconciliation_evidence(
                provider_namespace="ARUNDA-EXECUTION", intent_id="intent-1")
            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0]["reconciliation_state"], "UNRESOLVED_KEEP_QUARANTINED")
            self.assertEqual(adapter.calls, 1)

    def test_claim_in_wrong_state_never_queries_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteIntentClaimStore(Path(directory) / "claims.sqlite3")
            store.claim(provider_namespace="ARUNDA-EXECUTION",
                        intent_id="intent-1", client_order_id="A123")
            adapter = _FakeAdapter(ToobitAdapterResult(False, "NOT_FOUND", {}))
            result = reconcile_order_attempt(claim_store=store, adapter=adapter,
                intent_id="intent-1", venue="SPOT", symbol="BTCUSDT")
            self.assertEqual(result["reason"], "CLAIM_NOT_RECONCILABLE")
            self.assertEqual(adapter.calls, 0)


if __name__ == "__main__":
    unittest.main()
