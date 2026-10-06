"""Focused MCP-01.1 contract tests."""
from __future__ import annotations
import json
import tempfile
from pathlib import Path
from mcp01_compact_event_evidence_v0_1 import *

def test_selected_requires_decision():
    e=build_event(event_id="EV-1",event_type=EVENT_SELECTED,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d1",asset="BTC",direction="LONG",stage="DECISION")
    assert e.validate()

def test_identities_are_distinct():
    e=build_event(event_id="EV-2",event_type=EVENT_TRADE_READY,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d1",case_id="case1",stage="TRADE_GATE")
    assert e.decision_id != e.case_id

def test_order_requires_trade_identity():
    e=build_event(event_id="EV-3",event_type=EVENT_ORDER_ATTEMPTED,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d1",trade_event_id="t1",stage="ORDER")
    assert e.trade_event_id == "t1"

def test_provider_result_requires_provider():
    e=build_event(event_id="EV-4",event_type=EVENT_PROVIDER_RESULT,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",trade_event_id="t1",provider="TOOBIT",stage="EXECUTION")
    assert e.validate()

def test_data_quality_event():
    e=build_event(event_id="EV-5",event_type=EVENT_DATA_QUALITY,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",stage="DATA_QUALITY",reason_code="FUTURE_DATED_INPUT")
    assert e.validate()

def test_append_jsonl():
    e=build_event(event_id="EV-6",event_type=EVENT_SELECTED,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d1",stage="DECISION")
    with tempfile.TemporaryDirectory() as d:
        p=append_event(e,Path(d)/"events.jsonl")
        row=json.loads(p.read_text(encoding="utf-8").splitlines()[0])
        assert row["schema"]==MCP01_SCHEMA and row["schema_version"]==MCP01_SCHEMA_VERSION

def test_event_id_is_evidence_identity_only():
    x=deterministic_event_id(event_type=EVENT_SELECTED,cycle_id="c1",decision_id="d1")
    assert x.startswith("EV-") and x!="d1"

def test_invalid_order_rejected():
    try:
        build_event(event_id="EV-X",event_type=EVENT_ORDER_ATTEMPTED,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",stage="ORDER")
    except ValueError:
        return
    raise AssertionError("invalid order evidence accepted")


def test_idempotent_append_does_not_duplicate_identical_event():
    e=build_event(event_id="EV-IDEMP-1",event_type=EVENT_SELECTED,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d1",stage="DECISION")
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"events.jsonl"
        append_event_idempotent(e,p)
        append_event_idempotent(e,p)
        assert len(p.read_text(encoding="utf-8").splitlines()) == 1


def test_idempotent_append_rejects_conflicting_event_id():
    e=build_event(event_id="EV-IDEMP-2",event_type=EVENT_SELECTED,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d1",stage="DECISION")
    conflict=build_event(event_id="EV-IDEMP-2",event_type=EVENT_SELECTED,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d2",stage="DECISION")
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/"events.jsonl"
        append_event_idempotent(e,p)
        try:
            append_event_idempotent(conflict,p)
        except ValueError as exc:
            assert "event_id conflict" in str(exc)
        else:
            raise AssertionError("conflicting event_id was accepted")


def test_persistence_failure_isolated_and_inputs_unchanged():
    e1=build_event(event_id="EV-ISO-1",event_type=EVENT_SELECTED,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d1",stage="DECISION")
    e2=build_event(event_id="EV-ISO-2",event_type=EVENT_TRADE_READY,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d2",stage="TRADE_GATE")
    events=[e1,e2]
    before=[event.to_dict() for event in events]
    calls=[]

    def failing_append(event):
        calls.append(event.event_id)
        raise OSError("simulated evidence I/O failure")

    persisted, failures=persist_events_isolated(events, failing_append)
    assert persisted == 0
    assert [event.to_dict() for event in events] == before
    assert calls == ["EV-ISO-1", "EV-ISO-2"]
    assert [row["event_id"] for row in failures] == ["EV-ISO-1", "EV-ISO-2"]
    assert all(row["error_type"].endswith(".OSError") for row in failures)


def test_persistence_failure_isolated_per_event():
    e1=build_event(event_id="EV-ISO-3",event_type=EVENT_SELECTED,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d1",stage="DECISION")
    e2=build_event(event_id="EV-ISO-4",event_type=EVENT_SELECTED,event_timestamp="2026-10-05T00:00:00+00:00",cycle_id="c1",decision_id="d2",stage="DECISION")
    calls=[]

    def fail_first(event):
        calls.append(event.event_id)
        if event.event_id == "EV-ISO-3":
            raise OSError("first event failed")

    persisted, failures=persist_events_isolated([e1,e2], fail_first)
    assert persisted == 1
    assert len(failures) == 1
    assert failures[0]["event_id"] == "EV-ISO-3"
    assert calls == ["EV-ISO-3", "EV-ISO-4"]


if __name__=="__main__":
    tests=[v for n,v in sorted(globals().items()) if n.startswith("test_") and callable(v)]
    for test in tests: test()
    print(f"MCP-01.1 EVIDENCE CONTRACT TESTS PASS: {len(tests)}/{len(tests)}")
