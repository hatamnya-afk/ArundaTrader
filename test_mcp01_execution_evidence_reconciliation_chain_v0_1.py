from __future__ import annotations

import unittest
from dataclasses import asdict

from exchange_execution_contract import CanonicalExecutionResult

from mcp01_compact_event_evidence_v0_1 import (
    EVENT_DATA_QUALITY,
    EVENT_FILL_OUTCOME,
    EVENT_ORDER_ATTEMPTED,
    EVENT_PROVIDER_RESULT,
    EVENT_TRADE_READY,
)
from mcp01_outcome_reconciliation_v0_1 import reconcile_outcomes
from mcp01_trader_evidence_bridge_v0_1 import build_runtime_evidence_events


class ExecutionEvidenceReconciliationChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decisions = {
            "BTC": {"decision_id": "DECISION-1", "decision": "TRADE"}
        }
        self.gates = {
            "BTC": {
                "decision_id": "DECISION-1",
                "trade_gate_status": "TRADE_READY",
                "direction": "LONG",
            }
        }
        self.base = {
            "cycle_id": "CYCLE-1",
            "emitted_at": "2026-10-09T00:00:00+00:00",
            "decision_snapshot": self.decisions,
            "trade_gate_snapshot": self.gates,
            "trade_ready_assets": ["BTC"],
        }

    def _events(self, execution_results):
        return build_runtime_evidence_events(
            **self.base,
            execution_results=execution_results,
        )

    def test_authoritative_attempt_identity_reaches_complete_reconciliation(self) -> None:
        trade_event_id = "TRADE-EVENT-TEST-1"
        events = self._events({
            "BTC": {
                "trade_event_id": trade_event_id,
                "decision_id": "DECISION-1",
                "status": "ACCEPTED",
                "adapter": "CONTROLLED_TEST_ADAPTER",
                "direction": "LONG",
                "fill_outcome": "FILLED",
            }
        })

        trade_events = [
            event for event in events
            if event["event_type"] in {
                EVENT_ORDER_ATTEMPTED,
                EVENT_PROVIDER_RESULT,
                EVENT_FILL_OUTCOME,
            }
        ]
        self.assertEqual(
            {event["event_type"] for event in trade_events},
            {EVENT_ORDER_ATTEMPTED, EVENT_PROVIDER_RESULT, EVENT_FILL_OUTCOME},
        )
        self.assertEqual(
            {event["trade_event_id"] for event in trade_events},
            {trade_event_id},
        )
        self.assertTrue(
            all(event["decision_id"] == "DECISION-1" for event in trade_events)
        )

        reconciled = reconcile_outcomes(events)
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0]["trade_event_id"], trade_event_id)
        self.assertEqual(reconciled[0]["decision_id"], "DECISION-1")
        self.assertEqual(reconciled[0]["fill_outcome"], "FILLED")
        self.assertTrue(reconciled[0]["complete"])

    def test_missing_attempt_identity_is_data_quality_not_invented_order(self) -> None:
        events = self._events({
            "BTC": {
                "decision_id": "DECISION-1",
                "status": "ACCEPTED",
                "adapter": "CONTROLLED_TEST_ADAPTER",
                "direction": "LONG",
                "fill_outcome": "FILLED",
            }
        })

        self.assertTrue(any(
            event["event_type"] == EVENT_DATA_QUALITY
            and event.get("reason_code") == "TRADE_EVENT_ID_MISSING_AT_EXECUTION_RESULT"
            for event in events
        ))
        self.assertFalse(any(
            event["event_type"] in {
                EVENT_ORDER_ATTEMPTED,
                EVENT_PROVIDER_RESULT,
                EVENT_FILL_OUTCOME,
            }
            for event in events
        ))

        reconciled = reconcile_outcomes(events)
        self.assertEqual(len(reconciled), 1)
        self.assertIsNone(reconciled[0]["trade_event_id"])
        self.assertFalse(reconciled[0]["complete"])

    def test_absent_fill_outcome_never_marks_reconciliation_complete(self) -> None:
        trade_event_id = "TRADE-EVENT-TEST-2"
        events = self._events({
            "BTC": {
                "trade_event_id": trade_event_id,
                "decision_id": "DECISION-1",
                "status": "ACCEPTED",
                "adapter": "CONTROLLED_TEST_ADAPTER",
                "direction": "LONG",
            }
        })

        self.assertTrue(any(event["event_type"] == EVENT_TRADE_READY for event in events))
        self.assertFalse(any(event["event_type"] == EVENT_FILL_OUTCOME for event in events))

        reconciled = reconcile_outcomes(events)
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0]["trade_event_id"], trade_event_id)
        self.assertIsNone(reconciled[0]["fill_outcome"])
        self.assertFalse(reconciled[0]["complete"])



    def test_canonical_execution_result_preserves_explicit_fill_outcome(self) -> None:
        result = CanonicalExecutionResult(
            accepted=True,
            exchange_order_id="EXCHANGE-ORDER-1",
            status="ACCEPTED",
            asset="BTC",
            direction="LONG",
            executed_quantity="0.01",
            executed_price="100000",
            timestamp="2026-10-09T00:00:00+00:00",
            adapter="CONTROLLED_TEST_ADAPTER",
            error_code=None,
            error_message=None,
            trade_event_id="TRADE-EVENT-CANONICAL-1",
            decision_id="DECISION-1",
            fill_outcome="FILLED",
            fill_reason_code="PROVIDER_CONFIRMED_TERMINAL_FILL",
        )
        events = self._events({"BTC": asdict(result)})

        fill_events = [
            event for event in events
            if event["event_type"] == EVENT_FILL_OUTCOME
        ]
        self.assertEqual(len(fill_events), 1)
        self.assertEqual(fill_events[0]["status"], "FILLED")
        self.assertEqual(
            fill_events[0]["reason_code"],
            "PROVIDER_CONFIRMED_TERMINAL_FILL",
        )
        reconciled = reconcile_outcomes(events)
        self.assertEqual(len(reconciled), 1)
        self.assertEqual(reconciled[0]["fill_outcome"], "FILLED")
        self.assertTrue(reconciled[0]["complete"])

    def test_missing_result_decision_id_is_data_quality_only(self) -> None:
        events = self._events({
            "BTC": {
                "trade_event_id": "TRADE-EVENT-MISSING-DECISION",
                "status": "ACCEPTED",
                "adapter": "CONTROLLED_TEST_ADAPTER",
                "direction": "LONG",
                "fill_outcome": "FILLED",
            }
        })
        self.assertTrue(any(
            event["event_type"] == EVENT_DATA_QUALITY
            and event.get("reason_code") == "EXECUTION_RESULT_DECISION_ID_MISSING"
            for event in events
        ))
        self.assertFalse(any(
            event["event_type"] in {
                EVENT_ORDER_ATTEMPTED, EVENT_PROVIDER_RESULT, EVENT_FILL_OUTCOME
            }
            for event in events
        ))

    def test_mismatched_result_decision_id_is_data_quality_only(self) -> None:
        events = self._events({
            "BTC": {
                "decision_id": "OTHER-DECISION",
                "trade_event_id": "TRADE-EVENT-WRONG-DECISION",
                "status": "ACCEPTED",
                "adapter": "CONTROLLED_TEST_ADAPTER",
                "direction": "LONG",
                "fill_outcome": "FILLED",
            }
        })
        self.assertTrue(any(
            event["event_type"] == EVENT_DATA_QUALITY
            and event.get("reason_code") == "EXECUTION_RESULT_DECISION_ID_MISMATCH"
            for event in events
        ))
        self.assertFalse(any(
            event["event_type"] in {
                EVENT_ORDER_ATTEMPTED, EVENT_PROVIDER_RESULT, EVENT_FILL_OUTCOME
            }
            for event in events
        ))

if __name__ == "__main__":
    unittest.main()
