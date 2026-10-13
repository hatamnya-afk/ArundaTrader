"""Regression tests for execution-result handoff into MCP-01 evidence."""

from unittest.mock import patch

import pytest

import mcp01_main_integration_boundary_v0_1 as boundary


def test_emit_mcp01_evidence_forwards_canonical_execution_results():
    results = {
        "BTC": {
            "trade_event_id": "TRADE-EVENT-1",
            "status": "SUBMISSION_OUTCOME_UNKNOWN",
            "error_code": "TIMEOUT",
            "adapter": "TOOBIT",
            "direction": "LONG",
        }
    }

    with (
        patch.object(boundary, "build_runtime_evidence_events", return_value=[]) as build,
        patch.object(boundary, "persist_events_isolated", return_value=(0, [])) as persist,
    ):
        result = boundary.emit_mcp01_evidence(
            cycle_id="cycle-1",
            decision_snapshot={"BTC": {"decision_id": "DECISION-1"}},
            trade_gate_snapshot={"BTC": {"trade_gate_status": "HOLD"}},
            trade_ready_assets=(),
            execution_results=results,
        )

    assert result == (0, [])
    assert build.call_args.kwargs["execution_results"] is results
    persist.assert_called_once_with([])


def test_emit_mcp01_evidence_preserves_backward_compatibility_when_results_omitted():
    with (
        patch.object(boundary, "build_runtime_evidence_events", return_value=[]) as build,
        patch.object(boundary, "persist_events_isolated", return_value=(0, [])),
    ):
        boundary.emit_mcp01_evidence(
            cycle_id="cycle-2",
            decision_snapshot={"BTC": {"decision_id": "DECISION-2"}},
            trade_gate_snapshot={"BTC": {"trade_gate_status": "HOLD"}},
            trade_ready_assets=(),
        )

    assert build.call_args.kwargs["execution_results"] is None


def test_emit_mcp01_evidence_rejects_non_mapping_execution_results():
    with pytest.raises(TypeError, match="MCP01_EXECUTION_RESULTS_MUST_BE_MAPPING"):
        boundary.emit_mcp01_evidence(
            cycle_id="cycle-3",
            decision_snapshot={"BTC": {"decision_id": "DECISION-3"}},
            trade_gate_snapshot={"BTC": {"trade_gate_status": "HOLD"}},
            trade_ready_assets=(),
            execution_results=["not", "a", "mapping"],
        )
