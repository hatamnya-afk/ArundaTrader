from __future__ import annotations

import json

from exchange_execution_contract import (
    CanonicalOrderRequest,
    QUANTITY_SOURCE_RISK_POSITION,
    QUANTITY_UNIT_BASE_ASSET,
)
from toobit_ambiguous_submission_reconciliation_v0_1 import reconcile_ambiguous_submission
from toobit_ambiguous_submission_outcome_bridge_v0_1 import capture_reconciled_toobit_outcome


def request():
    return CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity="0.01",
        quantity_unit=QUANTITY_UNIT_BASE_ASSET,
        quantity_source=QUANTITY_SOURCE_RISK_POSITION,
        entry_price=None, reference_price=None, intent_id="INT-1",
        snapshot_id="SNAP-1", timestamp="2026-10-15T08:00:00Z",
        decision_id="DEC-1",
    )


def test_found_exact_match_flows_to_read_only_evidence_without_inventing_fill(tmp_path):
    row = {
        "symbol": "BTCUSDT", "clientOrderId": "INT-1", "orderId": "EX-1",
        "status": "FILLED", "executedQty": "0.01", "price": "60000",
    }
    reconciliation = reconcile_ambiguous_submission(
        client_order_id="INT-1", open_orders=[], recent_orders=[row]
    )
    result = capture_reconciled_toobit_outcome(
        request=request(), reconciliation=reconciliation, trade_event_id="TE-1",
        observed_at="2026-10-15T08:01:00Z", stream_path=tmp_path / "outcomes.jsonl",
    )
    assert result["reconciliation_state"] == "FOUND"
    assert result["capture_state"] == "PERSISTED"
    assert result["safe_to_retry"] is False
    persisted = json.loads((tmp_path / "outcomes.jsonl").read_text(encoding="utf-8"))
    assert persisted["source_kind"] == "READ_ONLY_LOOKUP"
    assert persisted["decision_id"] == "DEC-1"
    assert persisted["trade_event_id"] == "TE-1"
    assert persisted["executed_quantity"] == "0.01"
    assert persisted["executed_price"] is None
    assert persisted["fill_inferred"] is False


def test_not_found_remains_unresolved_and_does_not_persist(tmp_path):
    reconciliation = reconcile_ambiguous_submission(
        client_order_id="INT-1", open_orders=[], recent_orders=[]
    )
    path = tmp_path / "outcomes.jsonl"
    result = capture_reconciled_toobit_outcome(
        request=request(), reconciliation=reconciliation, trade_event_id="TE-1",
        observed_at="2026-10-15T08:01:00Z", stream_path=path,
    )
    assert result["reconciliation_state"] == "NOT_FOUND_UNRESOLVED"
    assert result["capture_state"] == "NOT_CAPTURED"
    assert result["safe_to_retry"] is False
    assert not path.exists()


def test_conflict_does_not_choose_or_persist_either_order(tmp_path):
    reconciliation = reconcile_ambiguous_submission(
        client_order_id="INT-1",
        open_orders=[{"clientOrderId": "INT-1", "orderId": "EX-1", "status": "NEW"}],
        recent_orders=[{"clientOrderId": "INT-1", "orderId": "EX-2", "status": "FILLED"}],
    )
    path = tmp_path / "outcomes.jsonl"
    result = capture_reconciled_toobit_outcome(
        request=request(), reconciliation=reconciliation, trade_event_id="TE-1",
        observed_at="2026-10-15T08:01:00Z", stream_path=path,
    )
    assert result["reconciliation_state"] == "CONFLICT"
    assert result["capture_state"] == "NOT_CAPTURED"
    assert result["safe_to_retry"] is False
    assert not path.exists()


def test_found_state_without_fail_closed_retry_policy_is_rejected(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    result = capture_reconciled_toobit_outcome(
        request=request(),
        reconciliation={"state": "FOUND", "order": {"clientOrderId": "INT-1"}, "safe_to_retry": True},
        trade_event_id="TE-1", observed_at="2026-10-15T08:01:00Z", stream_path=path,
    )
    assert result["reconciliation_state"] == "INVALID_OBSERVATION"
    assert result["capture_state"] == "NOT_CAPTURED"
    assert result["safe_to_retry"] is False
    assert not path.exists()


def test_evidence_persistence_failure_is_explicit_and_never_retryable(tmp_path):
    row = {
        "symbol": "BTCUSDT", "clientOrderId": "INT-1", "orderId": "EX-1",
        "status": "NEW",
    }
    reconciliation = reconcile_ambiguous_submission(
        client_order_id="INT-1", open_orders=[row], recent_orders=[]
    )
    path = tmp_path / "directory-instead-of-file"
    path.mkdir()
    result = capture_reconciled_toobit_outcome(
        request=request(), reconciliation=reconciliation, trade_event_id="TE-1",
        observed_at="2026-10-15T08:01:00Z", stream_path=path,
    )
    assert result["reconciliation_state"] == "FOUND"
    assert result["capture_state"] == "PERSISTENCE_FAILED"
    assert result["reason"].startswith("IsADirectoryError:")
    assert result["safe_to_retry"] is False
