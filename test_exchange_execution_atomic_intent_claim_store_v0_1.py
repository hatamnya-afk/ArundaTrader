"""Provider-neutral invariant tests for durable single-attempt claims.

All storage is temporary and isolated; no production DB or provider is used.
"""
import tempfile
import unittest
from pathlib import Path

from exchange_execution_atomic_intent_claim_store_v0_1 import (
    CLAIMED, SUBMISSION_OUTCOME_UNKNOWN, SQLiteIntentClaimStore,
)


class DurableIntentClaimTests(unittest.TestCase):
    def test_only_first_claim_can_authorize_attempt(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "claims.sqlite3"
            first = SQLiteIntentClaimStore(path).claim(
                provider_namespace="ARUNDA-EXECUTION",
                intent_id="INTENT-1",
                client_order_id="CLIENT-1",
            )
            replay = SQLiteIntentClaimStore(path).claim(
                provider_namespace="ARUNDA-EXECUTION",
                intent_id="INTENT-1",
                client_order_id="CLIENT-1",
            )
            self.assertEqual(first.outcome, "CLAIMED")
            self.assertEqual(replay.outcome, "ALREADY_CLAIMED")

    def test_claim_is_durable_across_store_recreation_and_unknown_outcome(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "claims.sqlite3"
            store = SQLiteIntentClaimStore(path)
            store.claim(provider_namespace="ARUNDA-EXECUTION",
                        intent_id="INTENT-2", client_order_id="CLIENT-2")
            store.transition(provider_namespace="ARUNDA-EXECUTION",
                             intent_id="INTENT-2",
                             status=SUBMISSION_OUTCOME_UNKNOWN,
                             detail_code="ATTEMPT_FENCED")
            reopened = SQLiteIntentClaimStore(path)
            self.assertEqual(reopened.get(
                provider_namespace="ARUNDA-EXECUTION", intent_id="INTENT-2"
            ).status, SUBMISSION_OUTCOME_UNKNOWN)
            replay = reopened.claim(provider_namespace="ARUNDA-EXECUTION",
                                    intent_id="INTENT-2",
                                    client_order_id="CLIENT-2")
            self.assertEqual(replay.outcome, "ALREADY_CLAIMED")
            self.assertEqual(replay.status, SUBMISSION_OUTCOME_UNKNOWN)

    def test_same_intent_cannot_change_client_order_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteIntentClaimStore(Path(directory) / "claims.sqlite3")
            store.claim(provider_namespace="ARUNDA-EXECUTION",
                        intent_id="INTENT-3", client_order_id="CLIENT-3")
            result = store.claim(provider_namespace="ARUNDA-EXECUTION",
                                 intent_id="INTENT-3", client_order_id="CLIENT-OTHER")
            self.assertEqual(result.outcome, "IDENTITY_CONFLICT")

    def test_client_order_id_cannot_be_reused_for_another_intent(self):
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteIntentClaimStore(Path(directory) / "claims.sqlite3")
            store.claim(provider_namespace="ARUNDA-EXECUTION",
                        intent_id="INTENT-4", client_order_id="CLIENT-4")
            result = store.claim(provider_namespace="ARUNDA-EXECUTION",
                                 intent_id="INTENT-5", client_order_id="CLIENT-4")
            self.assertEqual(result.outcome, "CLIENT_ORDER_ID_COLLISION")


if __name__ == "__main__":
    unittest.main()
