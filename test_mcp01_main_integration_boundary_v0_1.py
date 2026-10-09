from __future__ import annotations

import unittest
from unittest.mock import patch

import mcp01_main_integration_boundary_v0_1 as boundary


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


if __name__ == "__main__":
    unittest.main()
