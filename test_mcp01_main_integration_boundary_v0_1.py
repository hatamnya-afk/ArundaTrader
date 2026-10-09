from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mcp01_main_integration_boundary_v0_1 as boundary
from exchange_execution_contract import CanonicalExecutionResult
from mcp01_compact_event_evidence_v0_1 import (
    EVENT_FILL_OUTCOME,
    EVENT_ORDER_ATTEMPTED,
    EVENT_PROVIDER_RESULT,
    EVENT_SELECTED,
    append_event_idempotent,
    build_event,
    persist_events_isolated,
)
from mcp01_outcome_reconciliation_v0_1 import reconcile_outcomes


class EmitMcp01EvidenceExecutionResultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.decisions = {
            "BTC": {"decision_id": "DECISION-1", "decision": "TRADE"}
        }
        self.gates = {
            "BTC": {"decision_id": "DECISION-1", "trade_gate_status": "HOLD"}
        }

    @patch.object(boundary, "persist_events_isolated", return_value=(0, []))
    @patch.object(boundary, "deduplicate_events", side_effect=lambda events: events)
    @patch.object(boundary, "build_runtime_evidence_events", return_value=[])
    def test_forwards_authoritative_execution_results_unchanged(
        self, build_events, _deduplicate, _persist
    ) -> None:
        execution_results = {
            "BTC": {
                "trade_event_id": "TE-1",
                "status": "REJECTED",
                "adapter": "provider-adapter",
            }
        }

        boundary.emit_mcp01_evidence(
            cycle_id="CYCLE-1",
            decision_snapshot=self.decisions,
            trade_gate_snapshot=self.gates,
            trade_ready_assets=[],
            execution_results=execution_results,
        )

        self.assertIs(
            build_events.call_args.kwargs["execution_results"],
            execution_results,
        )

    @patch.object(boundary, "persist_events_isolated", return_value=(0, []))
    @patch.object(boundary, "deduplicate_events", side_effect=lambda events: events)
    @patch.object(boundary, "build_runtime_evidence_events", return_value=[])
    def test_omitted_execution_results_remains_none(
        self, build_events, _deduplicate, _persist
    ) -> None:
        boundary.emit_mcp01_evidence(
            cycle_id="CYCLE-2",
            decision_snapshot=self.decisions,
            trade_gate_snapshot=self.gates,
            trade_ready_assets=[],
        )

        self.assertIsNone(build_events.call_args.kwargs["execution_results"])

    def test_explicit_canonical_fill_outcome_reaches_persisted_evidence(self) -> None:
        captured_events = []
        result = CanonicalExecutionResult(
            accepted=True,
            exchange_order_id="EXCHANGE-ORDER-2",
            status="ACCEPTED",
            asset="BTC",
            direction="LONG",
            executed_quantity=0.1,
            executed_price=50000.0,
            timestamp="2026-10-09T00:00:00+00:00",
            adapter="CONTROLLED_TEST_ADAPTER",
            error_code=None,
            error_message=None,
            trade_event_id="TRADE-EVENT-FILLED-1",
            decision_id="DECISION-1",
            fill_outcome="FILLED",
            fill_reason_code="PROVIDER_CONFIRMED_TERMINAL_FILL",
        )

        with patch.object(
            boundary,
            "persist_events_isolated",
            side_effect=lambda events: (captured_events.extend(events) or (len(events), [])),
        ):
            boundary.emit_mcp01_evidence(
                cycle_id="CYCLE-4",
                decision_snapshot=self.decisions,
                trade_gate_snapshot={
                    "BTC": {
                        "decision_id": "DECISION-1",
                        "trade_gate_status": "TRADE_READY",
                        "direction": "LONG",
                    }
                },
                trade_ready_assets=["BTC"],
                execution_results={"BTC": result},
            )

        fill_events = [
            event for event in captured_events
            if event["event_type"] == EVENT_FILL_OUTCOME
        ]
        self.assertEqual(len(fill_events), 1)
        self.assertEqual(fill_events[0]["trade_event_id"], "TRADE-EVENT-FILLED-1")
        self.assertEqual(fill_events[0]["status"], "FILLED")
        self.assertEqual(
            fill_events[0]["reason_code"],
            "PROVIDER_CONFIRMED_TERMINAL_FILL",
        )
        reconciled = reconcile_outcomes(captured_events)
        trade_chain = next(
            row for row in reconciled
            if row["trade_event_id"] == "TRADE-EVENT-FILLED-1"
        )
        self.assertEqual(trade_chain["fill_outcome"], "FILLED")
        self.assertTrue(trade_chain["complete"])

    def test_canonical_execution_result_reaches_evidence_without_invented_fill(self) -> None:
        captured_events = []
        result = CanonicalExecutionResult(
            accepted=True,
            exchange_order_id="EXCHANGE-ORDER-1",
            status="ACCEPTED",
            asset="BTC",
            direction="LONG",
            executed_quantity=0.1,
            executed_price=50000.0,
            timestamp="2026-10-09T00:00:00+00:00",
            adapter="CONTROLLED_TEST_ADAPTER",
            error_code=None,
            error_message=None,
            trade_event_id="TRADE-EVENT-1",
            decision_id="DECISION-1",
        )

        with patch.object(
            boundary,
            "persist_events_isolated",
            side_effect=lambda events: (captured_events.extend(events) or (len(events), [])),
        ):
            boundary.emit_mcp01_evidence(
                cycle_id="CYCLE-3",
                decision_snapshot=self.decisions,
                trade_gate_snapshot={
                    "BTC": {
                        "decision_id": "DECISION-1",
                        "trade_gate_status": "TRADE_READY",
                        "direction": "LONG",
                    }
                },
                trade_ready_assets=["BTC"],
                execution_results={"BTC": result},
            )

        execution_events = [
            event for event in captured_events
            if event["event_type"] in {
                EVENT_ORDER_ATTEMPTED,
                EVENT_PROVIDER_RESULT,
                EVENT_FILL_OUTCOME,
            }
        ]
        self.assertEqual(
            [event["event_type"] for event in execution_events],
            [EVENT_ORDER_ATTEMPTED, EVENT_PROVIDER_RESULT],
        )
        self.assertEqual(
            {event["trade_event_id"] for event in execution_events},
            {"TRADE-EVENT-1"},
        )
        self.assertTrue(
            all(event["decision_id"] == "DECISION-1" for event in execution_events)
        )

        reconciled = reconcile_outcomes(captured_events)
        trade_chain = next(
            row for row in reconciled
            if row["trade_event_id"] == "TRADE-EVENT-1"
        )
        self.assertIsNone(trade_chain["fill_outcome"])
        self.assertFalse(trade_chain["complete"])

    def test_mapping_events_are_normalized_and_persisted_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stream_path = Path(directory) / "events.jsonl"
            event = build_event(
                event_id="EV-REAL-PERSISTENCE-1",
                event_type=EVENT_SELECTED,
                event_timestamp="2026-10-10T00:00:00+00:00",
                cycle_id="CYCLE-PERSIST-1",
                decision_id="DECISION-PERSIST-1",
                asset="BTC",
                stage="DECISION",
                status="TRADE",
            ).to_dict()
            append = lambda value: append_event_idempotent(value, stream_path=stream_path)

            persisted, failures = persist_events_isolated([event], append_fn=append)
            self.assertEqual((persisted, failures), (1, []))
            rows = [json.loads(line) for line in stream_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["event_id"], "EV-REAL-PERSISTENCE-1")
            self.assertEqual(rows[0]["decision_id"], "DECISION-PERSIST-1")

            persisted_again, failures_again = persist_events_isolated([event], append_fn=append)
            self.assertEqual((persisted_again, failures_again), (1, []))
            rows_again = stream_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(rows_again), 1)

    def test_invalid_mapping_isolated_without_stopping_later_events(self) -> None:
        valid = build_event(
            event_id="EV-VALID-AFTER-INVALID",
            event_type=EVENT_SELECTED,
            event_timestamp="2026-10-10T00:00:00+00:00",
            cycle_id="CYCLE-ISOLATION",
            decision_id="DECISION-ISOLATION",
            asset="BTC",
            stage="DECISION",
            status="TRADE",
        ).to_dict()
        invalid = {**valid, "event_id": "EV-INVALID", "event_type": "UNSUPPORTED"}
        persisted_events = []

        def append(event):
            persisted_events.append(event)

        persisted, failures = persist_events_isolated([invalid, valid], append_fn=append)
        self.assertEqual(persisted, 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["event_id"], "EV-INVALID")
        self.assertEqual(persisted_events[0].event_id, "EV-VALID-AFTER-INVALID")


if __name__ == "__main__":
    unittest.main()
