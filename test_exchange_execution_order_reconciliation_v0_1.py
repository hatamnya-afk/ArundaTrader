import tempfile
import unittest
from pathlib import Path

from exchange_execution_atomic_intent_claim_store_v0_1 import (
    RECONCILIATION_REQUIRED,
    SUBMISSION_OUTCOME_UNKNOWN,
    PROVIDER_ACCEPTED,
    SQLiteIntentClaimStore,
)
from exchange_execution_order_reconciliation_v0_1 import reconcile_ambiguous_order
from toobit_exchange_adapter_v0_1 import ToobitAdapterResult


class FakeAdapter:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def query_order_by_client_order_id(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


def make_store(path):
    store = SQLiteIntentClaimStore(path)
    store.claim(
        provider_namespace="ARUNDA-EXECUTION",
        intent_id="INTENT-RECON-1",
        client_order_id="A0123456789abcdefghijklmnopqrstuv",
    )
    store.transition(
        provider_namespace="ARUNDA-EXECUTION",
        intent_id="INTENT-RECON-1",
        status=SUBMISSION_OUTCOME_UNKNOWN,
        trade_event_id="trade-event-1",
        decision_id="decision-birth-1",
        evidence_event_id="trade-event-1:provider-response",
        detail_code="POST_OUTCOME_UNKNOWN",
    )
    return store


class AmbiguousOrderReconciliationTests(unittest.TestCase):
    def test_positive_identity_match_persists_evidence_and_resolves_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            store = make_store(Path(directory) / "claims.sqlite3")
            adapter = FakeAdapter(ToobitAdapterResult(True, "ORDER_FOUND", {
                "state_known": True,
                "reconciliation_state": "ORDER_FOUND",
                "client_order_id": "A0123456789abcdefghijklmnopqrstuv",
                "symbol": "BTCUSDT",
                "exchange_order_id": "exchange-77",
                "provider_status": "FILLED",
                "executed_quantity": "0.001",
                "executed_price": "65000",
                "timestamp": "1792000000000",
                "raw_order": {"orderId": "exchange-77", "status": "FILLED"},
            }))
            result = reconcile_ambiguous_order(
                claim_store=store, adapter=adapter,
                provider_namespace="ARUNDA-EXECUTION",
                intent_id="INTENT-RECON-1", venue="SPOT", symbol="BTCUSDT",
            )
            self.assertEqual(result["state"], "ORDER_FOUND")
            self.assertFalse(result["resubmit_allowed"])
            claim = store.get(provider_namespace="ARUNDA-EXECUTION", intent_id="INTENT-RECON-1")
            self.assertEqual(claim.status, PROVIDER_ACCEPTED)
            self.assertEqual(claim.exchange_order_id, "exchange-77")
            evidence = store.list_reconciliation_evidence(
                provider_namespace="ARUNDA-EXECUTION", intent_id="INTENT-RECON-1"
            )
            self.assertEqual(len(evidence), 1)
            self.assertEqual(evidence[0]["provider_status"], "FILLED")
            self.assertEqual(adapter.calls[0]["client_order_id"], claim.client_order_id)

    def test_negative_lookup_persists_quarantine_and_never_reopens_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            store = make_store(Path(directory) / "claims.sqlite3")
            adapter = FakeAdapter(ToobitAdapterResult(False, "ORDER_LOOKUP_UNRESOLVED", {
                "state_known": False,
                "reconciliation_state": "UNRESOLVED_KEEP_QUARANTINED",
                "client_order_id": "A0123456789abcdefghijklmnopqrstuv",
                "detail": "provider order not found",
                "resubmit_allowed": False,
            }))
            result = reconcile_ambiguous_order(
                claim_store=store, adapter=adapter,
                provider_namespace="ARUNDA-EXECUTION",
                intent_id="INTENT-RECON-1", venue="SPOT", symbol="BTCUSDT",
            )
            self.assertEqual(result["state"], "UNRESOLVED_KEEP_QUARANTINED")
            self.assertFalse(result["resubmit_allowed"])
            claim = store.get(provider_namespace="ARUNDA-EXECUTION", intent_id="INTENT-RECON-1")
            self.assertEqual(claim.status, RECONCILIATION_REQUIRED)
            replay = store.claim(
                provider_namespace="ARUNDA-EXECUTION",
                intent_id="INTENT-RECON-1",
                client_order_id=claim.client_order_id,
            )
            self.assertEqual(replay.outcome, "ALREADY_CLAIMED")
            evidence = store.list_reconciliation_evidence(
                provider_namespace="ARUNDA-EXECUTION", intent_id="INTENT-RECON-1"
            )
            self.assertEqual(evidence[0]["reconciliation_state"], "UNRESOLVED_KEEP_QUARANTINED")

    def test_mismatched_provider_identity_is_treated_as_unresolved(self):
        with tempfile.TemporaryDirectory() as directory:
            store = make_store(Path(directory) / "claims.sqlite3")
            adapter = FakeAdapter(ToobitAdapterResult(True, "ORDER_FOUND", {
                "state_known": True,
                "client_order_id": "SOMEONE_ELSES_ORDER",
                "symbol": "BTCUSDT",
                "exchange_order_id": "exchange-88",
                "provider_status": "FILLED",
            }))
            result = reconcile_ambiguous_order(
                claim_store=store, adapter=adapter,
                provider_namespace="ARUNDA-EXECUTION",
                intent_id="INTENT-RECON-1", venue="SPOT", symbol="BTCUSDT",
            )
            self.assertEqual(result["state"], "UNRESOLVED_KEEP_QUARANTINED")
            self.assertFalse(result["resubmit_allowed"])
            self.assertEqual(
                store.get(provider_namespace="ARUNDA-EXECUTION", intent_id="INTENT-RECON-1").status,
                RECONCILIATION_REQUIRED,
            )


    def test_existing_terminal_exchange_order_id_cannot_be_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            store = make_store(Path(directory) / "claims.sqlite3")
            store.transition(
                provider_namespace="ARUNDA-EXECUTION",
                intent_id="INTENT-RECON-1",
                status=PROVIDER_ACCEPTED,
                trade_event_id="trade-event-1",
                decision_id="decision-birth-1",
                exchange_order_id="original-order",
                provider_status="FILLED",
                evidence_event_id="trade-event-1:provider-response",
                detail_code="ORIGINAL_ACCEPTANCE",
            )
            adapter = FakeAdapter(ToobitAdapterResult(True, "ORDER_FOUND", {
                "state_known": True,
                "client_order_id": "A0123456789abcdefghijklmnopqrstuv",
                "symbol": "BTCUSDT",
                "exchange_order_id": "different-order",
                "provider_status": "FILLED",
            }))
            result = reconcile_ambiguous_order(
                claim_store=store, adapter=adapter,
                provider_namespace="ARUNDA-EXECUTION",
                intent_id="INTENT-RECON-1", venue="SPOT", symbol="BTCUSDT",
            )
            self.assertEqual(result["state"], "UNRESOLVED_KEEP_QUARANTINED")
            self.assertFalse(result["resubmit_allowed"])
            claim = store.get(provider_namespace="ARUNDA-EXECUTION", intent_id="INTENT-RECON-1")
            self.assertEqual(claim.status, PROVIDER_ACCEPTED)
            self.assertEqual(claim.exchange_order_id, "original-order")


if __name__ == "__main__":
    unittest.main()
