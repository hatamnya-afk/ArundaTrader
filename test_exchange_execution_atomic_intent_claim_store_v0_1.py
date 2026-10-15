"""Provider-neutral invariant tests for durable single-attempt claims.

All storage is temporary and isolated; no production DB or provider is used.
"""
import ast
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


    def test_attempt_boundary_has_one_submit_call_after_durable_claim_fence(self):
        source = Path(__file__).with_name("exchange_execution_order_attempt_boundary_v0_1.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "attempt_prepared_order")
        submit_calls = [node for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "submit_prepared_order"]
        claim_calls = [node for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "claim"]
        fence_calls = [node for node in ast.walk(function) if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "transition"]
        self.assertEqual(len(submit_calls), 1)
        self.assertEqual(len(claim_calls), 1)
        self.assertGreaterEqual(len(fence_calls), 2)
        self.assertLess(claim_calls[0].lineno, submit_calls[0].lineno)
        self.assertLess(min(node.lineno for node in fence_calls), submit_calls[0].lineno)
        self.assertTrue(any(node.lineno > submit_calls[0].lineno for node in fence_calls))
        self.assertIn("PROVIDER_ACCEPTED", source)
        self.assertIn("PROVIDER_REJECTED", source)

    def test_attempt_boundary_requires_stable_client_id_and_claim_store(self):
        source = Path(__file__).with_name("exchange_execution_order_attempt_boundary_v0_1.py").read_text(encoding="utf-8")
        self.assertIn("DURABLE_INTENT_CLAIM_STORE_REQUIRED", source)
        self.assertIn("STABLE_CLIENT_ORDER_ID_REQUIRED", source)
        self.assertIn("INTENT_ALREADY_CLAIMED_NO_RESUBMIT", source)
        self.assertIn("SUBMISSION_OUTCOME_UNKNOWN", source)


if __name__ == "__main__":
    unittest.main()
