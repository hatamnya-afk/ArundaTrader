"""Focused tests for the MCP-01 Trader evidence bridge."""

from mcp01_trader_evidence_bridge_v0_1 import (
    build_runtime_evidence_events,
    deduplicate_events,
)


def snapshots():
    decisions = {
        "BTC": {"decision_id": "DEC-BTC-1", "decision": "BUY"},
        "ETH": {"decision_id": "DEC-ETH-1", "decision": "HOLD"},
    }
    gates = {
        "BTC": {"decision_id": "DEC-BTC-1", "direction": "LONG", "trade_gate_status": "TRADE_READY"},
        "ETH": {"decision_id": "DEC-ETH-1", "direction": "LONG", "trade_gate_status": "HOLD"},
    }
    return decisions, gates


def test_selection_and_trade_ready_preserve_authoritative_decision_id():
    decisions, gates = snapshots()
    events = build_runtime_evidence_events(
        cycle_id="RC-1",
        emitted_at="2026-10-06T00:00:00+00:00",
        decision_snapshot=decisions,
        trade_gate_snapshot=gates,
        trade_ready_assets={"BTC"},
    )
    selected = [e for e in events if e["event_type"] == "SELECTED"]
    ready = [e for e in events if e["event_type"] == "TRADE_READY"]
    assert {e["decision_id"] for e in selected} == {"DEC-BTC-1", "DEC-ETH-1"}
    assert len(ready) == 1
    assert ready[0]["decision_id"] == "DEC-BTC-1"


def test_missing_trade_event_id_is_data_quality_not_synthetic_identity():
    decisions, gates = snapshots()
    events = build_runtime_evidence_events(
        cycle_id="RC-2",
        emitted_at="2026-10-06T00:01:00+00:00",
        decision_snapshot=decisions,
        trade_gate_snapshot=gates,
        trade_ready_assets={"BTC"},
        execution_results={
            "BTC": {
                "status": "REJECTED",
                "adapter": "TOOBIT",
                "error_code": "-1157",
                "direction": "LONG",
                "exchange_order_id": None,
            }
        },
    )
    dq = [e for e in events if e["event_type"] == "DATA_QUALITY_EVENT"]
    assert len(dq) == 1
    assert dq[0]["reason_code"] == "TRADE_EVENT_ID_MISSING_AT_EXECUTION_RESULT"
    assert all(e.get("trade_event_id") is None for e in dq)


def test_authoritative_trade_event_id_produces_order_and_provider_events():
    decisions, gates = snapshots()
    events = build_runtime_evidence_events(
        cycle_id="RC-3",
        emitted_at="2026-10-06T00:02:00+00:00",
        decision_snapshot=decisions,
        trade_gate_snapshot=gates,
        trade_ready_assets={"BTC"},
        execution_results={
            "BTC": {
                "status": "REJECTED",
                "adapter": "TOOBIT",
                "error_code": "-1157",
                "direction": "LONG",
                "trade_event_id": "TE-BTC-1",
            }
        },
    )
    order = [e for e in events if e["event_type"] == "ORDER_ATTEMPTED"]
    provider = [e for e in events if e["event_type"] == "PROVIDER_RESULT"]
    assert len(order) == 1
    assert len(provider) == 1
    assert order[0]["trade_event_id"] == "TE-BTC-1"
    assert provider[0]["trade_event_id"] == "TE-BTC-1"
    assert provider[0]["reason_code"] == "-1157"


def test_exchange_order_id_never_substitutes_trade_event_id():
    decisions, gates = snapshots()
    events = build_runtime_evidence_events(
        cycle_id="RC-4",
        emitted_at="2026-10-06T00:03:00+00:00",
        decision_snapshot=decisions,
        trade_gate_snapshot=gates,
        trade_ready_assets={"BTC"},
        execution_results={
            "BTC": {
                "status": "REJECTED",
                "adapter": "TOOBIT",
                "error_code": "-1157",
                "direction": "LONG",
                "exchange_order_id": "EXCHANGE-123",
            }
        },
    )
    assert any(
        e["event_type"] == "DATA_QUALITY_EVENT"
        and e["reason_code"] == "TRADE_EVENT_ID_MISSING_AT_EXECUTION_RESULT"
        for e in events
    )
    assert not any(e["event_type"] == "ORDER_ATTEMPTED" for e in events)


def test_identity_conflict_is_rejected():
    decisions, gates = snapshots()
    bad_gates = dict(gates)
    bad_gates["BTC"] = {
        **gates["BTC"],
        "decision_id": "WRONG-ID",
    }
    try:
        build_runtime_evidence_events(
            cycle_id="RC-5",
            emitted_at="2026-10-06T00:04:00+00:00",
            decision_snapshot=decisions,
            trade_gate_snapshot=bad_gates,
            trade_ready_assets={"BTC"},
        )
    except ValueError as exc:
        assert "decision_id lineage mismatch" in str(exc)
    else:
        raise AssertionError("decision lineage conflict was not rejected")


def test_deduplication_is_identity_based_and_stable():
    decisions, gates = snapshots()
    events = build_runtime_evidence_events(
        cycle_id="RC-6",
        emitted_at="2026-10-06T00:05:00+00:00",
        decision_snapshot=decisions,
        trade_gate_snapshot=gates,
        trade_ready_assets={"BTC"},
    )
    duplicated = events + events[:3]
    result = deduplicate_events(duplicated)
    assert len(result) == len(events)
    assert [e["event_id"] for e in result] == [e["event_id"] for e in events]


def main():
    tests = (
        test_selection_and_trade_ready_preserve_authoritative_decision_id,
        test_missing_trade_event_id_is_data_quality_not_synthetic_identity,
        test_authoritative_trade_event_id_produces_order_and_provider_events,
        test_exchange_order_id_never_substitutes_trade_event_id,
        test_identity_conflict_is_rejected,
        test_deduplication_is_identity_based_and_stable,
    )
    for test in tests:
        test()
    print("MCP01_TRADER_EVIDENCE_BRIDGE_TESTS=6/6 PASS")


if __name__ == "__main__":
    main()
