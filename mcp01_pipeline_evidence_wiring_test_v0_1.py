"""Static wiring verification for MCP-01 Trader evidence flow.

No runtime, network, exchange, database, or production execution is used.
"""

from pathlib import Path


PIPELINE = Path(__file__).resolve().parent / "arunda_pipeline.py"


def test_evidence_boundary_is_after_execution_results_and_outside_execution_quality_block():
    source = PIPELINE.read_text(encoding="utf-8-sig")

    execution_results_pos = source.index("execution_results = {}")
    execution_quality_pos = source.index("if execution_quality_ready_assets:")
    evidence_pos = source.index("mcp01_events = deduplicate_events(")
    cp69_pos = source.index("# 13. CP69 CANONICAL RUNTIME OBSERVATION")

    assert execution_results_pos < evidence_pos
    assert execution_quality_pos < evidence_pos < cp69_pos

    evidence_line = next(
        line for line in source.splitlines()
        if "mcp01_events = deduplicate_events(" in line
    )
    assert len(evidence_line) - len(evidence_line.lstrip()) == 8


def test_pipeline_preserves_authoritative_trade_event_id_in_execution_result_mapping():
    source = PIPELINE.read_text(encoding="utf-8-sig")

    mapping_start = source.index("execution_results[asset] = {")
    mapping_end = source.index("}", mapping_start)
    mapping = source[mapping_start:mapping_end]

    assert '"trade_event_id": result.trade_event_id' in mapping
    assert '"exchange_order_id": result.exchange_order_id' in mapping


def test_evidence_call_uses_authoritative_runtime_inputs():
    source = PIPELINE.read_text(encoding="utf-8-sig")

    start = source.index("mcp01_events = deduplicate_events(")
    end = source.index("# ------------------------------------------------------------------", start)
    block = source[start:end]

    for required in (
        "cycle_id=runtime_cycle_id",
        "decision_snapshot=decision_snapshot",
        "trade_gate_snapshot=trade_gate_snapshot",
        "trade_ready_assets=trade_ready_assets",
        "execution_results=execution_results",
    ):
        assert required in block

    assert "exchange_order_id" not in block


def test_evidence_persistence_is_isolated_from_pipeline_control_flow():
    source = PIPELINE.read_text(encoding="utf-8-sig")

    evidence_pos = source.index("mcp01_events = deduplicate_events(")
    persistence_pos = source.index("persist_events_isolated(", evidence_pos)
    cp69_pos = source.index("# 13. CP69 CANONICAL RUNTIME OBSERVATION")

    assert evidence_pos < persistence_pos < cp69_pos
    assert "append_event_idempotent(" not in source[evidence_pos:cp69_pos]
    assert "MCP01_EVIDENCE_PERSISTENCE_FAILURES=" in source[persistence_pos:cp69_pos]


def main():
    tests = (
        test_evidence_boundary_is_after_execution_results_and_outside_execution_quality_block,
        test_pipeline_preserves_authoritative_trade_event_id_in_execution_result_mapping,
        test_evidence_call_uses_authoritative_runtime_inputs,
        test_evidence_persistence_is_isolated_from_pipeline_control_flow,
    )
    for test in tests:
        test()
    print("MCP01_PIPELINE_EVIDENCE_WIRING_TESTS=4/4 PASS")


if __name__ == "__main__":
    main()
