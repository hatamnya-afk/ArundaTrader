from pathlib import Path

from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from mcp01_execution_attempt_evidence_v0_1 import (
    build_execution_attempt_events,
    persist_execution_attempt_events,
)
from mcp01_outcome_reconciliation_v0_1 import reconcile_outcomes
from mcp01_trade_event_identity_v0_1 import issue_trade_event_id


def test_attempt_evidence_is_correlatable_and_persisted_idempotently(tmp_path: Path):
    request = CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity=1,
        quantity_unit="BASE_ASSET", quantity_source="RISK.position_quantity",
        entry_price=100, reference_price=100, intent_id="I-1", snapshot_id="S-1",
        timestamp="2026-10-08T00:00:00Z", decision_id="D-1",
    )
    result = CanonicalExecutionResult(
        accepted=False, exchange_order_id=None, status="PROVIDER_REJECTED",
        asset="BTC", direction="LONG", executed_quantity=None, executed_price=None,
        timestamp="2026-10-08T00:00:01Z", adapter="FAKE_PROVIDER",
        error_code="FAKE_REJECT", error_message="synthetic unit-test response",
        trade_event_id=issue_trade_event_id(),
    )
    events = build_execution_attempt_events(request=request, result=result)
    assert [event.event_type for event in events] == ["ORDER_ATTEMPTED", "PROVIDER_RESULT"]
    assert all(event.trade_event_id == result.trade_event_id for event in events)

    stream = tmp_path / "events.jsonl"
    first = persist_execution_attempt_events(events, stream_path=stream)
    second = persist_execution_attempt_events(events, stream_path=stream)
    assert first["persistence_state"] == "PERSISTED"
    assert second["persistence_state"] == "PERSISTED"
    assert len(stream.read_text(encoding="utf-8").splitlines()) == 2

    reconciled = reconcile_outcomes([
        {"event_type": "TRADE_READY", "decision_id": "D-1",
         "asset": "BTC", "direction": "LONG"},
        *[event.to_dict() for event in events],
    ])
    assert len(reconciled) == 1
    assert reconciled[0]["trade_event_id"] == result.trade_event_id
    assert reconciled[0]["provider_status"] == "PROVIDER_REJECTED"


def test_event_builder_rejects_missing_authoritative_attempt_identity():
    request = CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity=1,
        quantity_unit="BASE_ASSET", quantity_source="RISK.position_quantity",
        entry_price=100, reference_price=100, intent_id="I-1", snapshot_id="S-1",
        timestamp="2026-10-08T00:00:00Z", decision_id="D-1",
    )
    result = CanonicalExecutionResult(
        accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
        asset="BTC", direction="LONG", executed_quantity=None, executed_price=None,
        timestamp=None, adapter="FAKE_PROVIDER", error_code="BLOCKED",
        error_message="not submitted", trade_event_id=None,
    )
    try:
        build_execution_attempt_events(request=request, result=result)
    except ValueError as exc:
        assert str(exc) == "AUTHORITATIVE_TRADE_EVENT_ID_REQUIRED"
    else:
        raise AssertionError("missing attempt identity must fail closed")
