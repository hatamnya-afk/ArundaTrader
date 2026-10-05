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

if __name__=="__main__":
    tests=[v for n,v in sorted(globals().items()) if n.startswith("test_") and callable(v)]
    for test in tests: test()
    print(f"MCP-01.1 EVIDENCE CONTRACT TESTS PASS: {len(tests)}/{len(tests)}")
