from __future__ import annotations

import json

import pytest

from exchange_execution_contract import (
    CanonicalExecutionResult, CanonicalOrderRequest,
    QUANTITY_UNIT_BASE_ASSET, QUANTITY_SOURCE_RISK_POSITION,
)
from execution_outcome_evidence_contract_v0_1 import (
    build_outcome_record_from_canonical_result,
    append_execution_outcome_record,
    build_execution_outcome_record,
)


def make_record(**overrides):
    values = {
        "provider": "TOOBIT",
        "decision_id": "DEC-1",
        "intent_id": "INT-1",
        "trade_event_id": "TE-1",
        "client_order_id": "CID-1",
        "source_observation_id": "OBS-1",
        "source_kind": "PROVIDER_RESPONSE",
        "provider_status": "NEW",
        "observed_at": "2026-10-15T08:00:00+00:00",
        "exchange_order_id": "EX-1",
    }
    values.update(overrides)
    return build_execution_outcome_record(**values)


def test_acceptance_or_open_status_never_infers_fill():
    record = make_record(provider_status="NEW")
    assert record["outcome_state"] == "OPEN"
    assert record["executed_quantity"] is None
    assert record["executed_price"] is None
    assert record["fill_inferred"] is False


def test_filled_requires_explicit_execution_quantity_and_price():
    record = make_record(provider_status="FILLED")
    assert record["outcome_state"] == "OUTCOME_INCOMPLETE"
    assert record["outcome_reason"] == "FILLED_STATUS_MISSING_EXECUTION_DETAILS"


def test_filled_with_explicit_execution_details_is_recorded():
    record = make_record(
        provider_status="FILLED",
        executed_quantity="0.125000",
        executed_price="67250.50",
    )
    assert record["outcome_state"] == "FILLED"
    assert record["executed_quantity"] == "0.125000"
    assert record["executed_price"] == "67250.50"
    assert record["fill_inferred"] is False


def test_partial_fill_without_details_remains_incomplete():
    record = make_record(provider_status="PARTIALLY_FILLED", executed_quantity="0.01")
    assert record["outcome_state"] == "PARTIAL_FILL_INCOMPLETE"


def test_terminal_status_does_not_claim_zero_fills():
    record = make_record(provider_status="CANCELED")
    assert record["outcome_state"] == "TERMINAL_UNRECONCILED"
    assert "DOES_NOT_PROVE_ZERO_FILL" in record["outcome_reason"]


def test_unknown_provider_status_fails_to_unknown_not_success():
    record = make_record(provider_status="SOME_NEW_STATUS")
    assert record["outcome_state"] == "UNKNOWN"


def test_naive_timestamp_rejected():
    with pytest.raises(ValueError, match="TIMEZONE_REQUIRED"):
        make_record(observed_at="2026-10-15T08:00:00")


def test_execution_quantity_must_be_positive_finite():
    with pytest.raises(ValueError, match="EXECUTED_QUANTITY_INVALID"):
        make_record(provider_status="FILLED", executed_quantity="NaN", executed_price="10")


def test_append_is_idempotent_for_identical_record(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    record = make_record()
    first = append_execution_outcome_record(record, stream_path=path)
    second = append_execution_outcome_record(record, stream_path=path)
    assert first["state"] == "PERSISTED"
    assert second["state"] == "ALREADY_PERSISTED"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert rows == [record]


def test_same_observation_identity_with_conflicting_payload_fails_closed(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    first = make_record(provider_status="NEW")
    append_execution_outcome_record(first, stream_path=path)
    conflict = make_record(provider_status="FILLED", executed_quantity="1", executed_price="10")
    assert conflict["event_id"] == first["event_id"]
    with pytest.raises(ValueError, match="EVENT_ID_CONFLICT"):
        append_execution_outcome_record(conflict, stream_path=path)


def test_source_kind_is_constrained():
    with pytest.raises(ValueError, match="SOURCE_KIND_INVALID"):
        make_record(source_kind="TEST_FIXTURE")



def test_canonical_result_is_bound_to_authoritative_request_identity():
    request = CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity="0.01",
        quantity_unit=QUANTITY_UNIT_BASE_ASSET,
        quantity_source=QUANTITY_SOURCE_RISK_POSITION,
        entry_price=None,
        reference_price=None,
        intent_id="INT-1",
        snapshot_id="SNAP-1",
        timestamp="2026-10-15T08:00:00Z",
        decision_id="DEC-1",
    )
    result = CanonicalExecutionResult(
        accepted=True,
        exchange_order_id="EX-1",
        status="FILLED",
        asset="BTC",
        direction="LONG",
        executed_quantity="0.01",
        executed_price="60000",
        timestamp="2026-10-15T08:01:00Z",
        adapter="TOOBIT",
        error_code=None,
        error_message=None,
        trade_event_id="TE-1",
    )
    record = build_outcome_record_from_canonical_result(
        request=request,
        result=result,
        client_order_id="CID-1",
        source_observation_id="OBS-RESULT-1",
    )
    assert record["decision_id"] == "DEC-1"
    assert record["intent_id"] == "INT-1"
    assert record["trade_event_id"] == "TE-1"
    assert record["outcome_state"] == "FILLED"


def test_canonical_result_asset_mismatch_rejected():
    request = CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity="0.01",
        quantity_unit=QUANTITY_UNIT_BASE_ASSET,
        quantity_source=QUANTITY_SOURCE_RISK_POSITION,
        entry_price=None, reference_price=None, intent_id="INT-1",
        snapshot_id="SNAP-1", timestamp="2026-10-15T08:00:00Z", decision_id="DEC-1",
    )
    result = CanonicalExecutionResult(
        accepted=True, exchange_order_id="EX-1", status="FILLED",
        asset="ETH", direction="LONG", executed_quantity="0.01",
        executed_price="60000", timestamp="2026-10-15T08:01:00Z",
        adapter="TOOBIT", error_code=None, error_message=None, trade_event_id="TE-1",
    )
    with pytest.raises(ValueError, match="PROVIDER_RESULT_ASSET_MISMATCH"):
        build_outcome_record_from_canonical_result(
            request=request, result=result, client_order_id="CID-1",
            source_observation_id="OBS-RESULT-2",
        )


def test_explicit_zero_executed_quantity_is_valid_provider_evidence():
    record = make_record(provider_status="NEW", executed_quantity="0")
    assert record["outcome_state"] == "OPEN"
    assert record["executed_quantity"] == "0"
    assert record["fill_inferred"] is False
