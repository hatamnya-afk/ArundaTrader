from __future__ import annotations

import json

from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
    QUANTITY_SOURCE_RISK_POSITION,
    QUANTITY_UNIT_BASE_ASSET,
)
from execution_attempt_outcome_capture_v0_1 import capture_execution_attempt_outcome


def request():
    return CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity="0.01",
        quantity_unit=QUANTITY_UNIT_BASE_ASSET,
        quantity_source=QUANTITY_SOURCE_RISK_POSITION,
        entry_price=None, reference_price=None, intent_id="INT-1",
        snapshot_id="SNAP-1", timestamp="2026-10-15T08:00:00Z",
        decision_id="DEC-1",
    )


def result(**overrides):
    values = dict(
        accepted=True, exchange_order_id="EX-1", status="FILLED",
        asset="BTC", direction="LONG", executed_quantity="0.01",
        executed_price="60000", timestamp="2026-10-15T08:01:00Z",
        adapter="TOOBIT", error_code=None, error_message=None,
        trade_event_id="TE-1",
    )
    values.update(overrides)
    return CanonicalExecutionResult(**values)


def test_real_canonical_provider_result_is_persisted_with_authoritative_ids(tmp_path):
    path = tmp_path / "private" / "outcomes.jsonl"
    outcome = capture_execution_attempt_outcome(
        request=request(), result=result(), stream_path=path
    )
    assert outcome.capture_state == "PERSISTED"
    assert outcome.execution_result.status == "FILLED"
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["decision_id"] == "DEC-1"
    assert row["intent_id"] == "INT-1"
    assert row["trade_event_id"] == "TE-1"
    assert row["client_order_id"] == "INT-1"
    assert row["outcome_state"] == "FILLED"
    assert row["fill_inferred"] is False


def test_duplicate_same_provider_observation_is_idempotent(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    args = dict(request=request(), result=result(), stream_path=path)
    first = capture_execution_attempt_outcome(**args)
    second = capture_execution_attempt_outcome(**args)
    assert first.event_id == second.event_id
    assert first.capture_state == "PERSISTED"
    assert second.capture_state == "ALREADY_PERSISTED"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_fail_closed_boundary_result_is_not_misrepresented_as_provider_evidence(tmp_path):
    outcome = capture_execution_attempt_outcome(
        request=request(),
        result=result(accepted=False, status="FAIL_CLOSED", exchange_order_id=None,
                      timestamp=None, trade_event_id=None, executed_quantity=None,
                      executed_price=None, error_code="EXECUTION_DISABLED"),
        stream_path=tmp_path / "outcomes.jsonl",
    )
    assert outcome.capture_state == "NOT_CAPTURED"
    assert outcome.reason == "NO_PROVIDER_RESPONSE_FAIL_CLOSED_BOUNDARY_RESULT"
    assert not (tmp_path / "outcomes.jsonl").exists()


def test_missing_authoritative_decision_id_is_not_persisted(tmp_path):
    req = request()
    req = CanonicalOrderRequest(
        asset=req.asset, direction=req.direction, order_type=req.order_type,
        quantity=req.quantity, quantity_unit=req.quantity_unit,
        quantity_source=req.quantity_source, entry_price=req.entry_price,
        reference_price=req.reference_price, intent_id=req.intent_id,
        snapshot_id=req.snapshot_id, timestamp=req.timestamp, decision_id=None,
    )
    path = tmp_path / "outcomes.jsonl"
    outcome = capture_execution_attempt_outcome(
        request=req, result=result(), stream_path=path
    )
    assert outcome.capture_state == "NOT_CAPTURED"
    assert outcome.reason == "AUTHORITATIVE_DECISION_ID_MISSING"
    assert not path.exists()
