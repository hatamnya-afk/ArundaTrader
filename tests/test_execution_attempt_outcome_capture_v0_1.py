from __future__ import annotations

import json

from standing_mandate_lifecycle_store_v0_1 import append_lifecycle_event

from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
    QUANTITY_SOURCE_RISK_POSITION,
    QUANTITY_UNIT_BASE_ASSET,
)
from execution_attempt_outcome_capture_v0_1 import (
    capture_execution_attempt_outcome,
    run_final_execution_attempt_with_outcome_capture,
)


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



def test_final_attempt_composition_preserves_fail_closed_and_does_not_fake_provider_evidence(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    outcome = run_final_execution_attempt_with_outcome_capture(
        execution_ready_package={},
        request=request(),
        authorization_observation={},
        adapter=object(),
        venue="SPOT",
        execution_instrument=None,
        stream_path=path,
    )
    assert outcome.execution_result.status == "FAIL_CLOSED"
    assert outcome.capture_state == "NOT_CAPTURED"
    assert outcome.reason == "NO_PROVIDER_RESPONSE_FAIL_CLOSED_BOUNDARY_RESULT"
    assert not path.exists()


def test_final_attempt_boundary_identity_flows_into_outcome_capture(tmp_path, monkeypatch):
    lifecycle_path = tmp_path / "mandate-lifecycle.jsonl"
    append_lifecycle_event(lifecycle_path, {
        "event_id": "activate-test-only",
        "event_type": "ACTIVATE",
        "mandate_id": "TEST-ONLY",
        "authority": "MANAGEMENT",
    })
    monkeypatch.setenv("ARUNDA_MANDATE_LIFECYCLE_PATH", str(lifecycle_path))
    from exchange_execution_adapter_contract_v0_1 import (
        AdapterOrderPreparation, ExchangeAdapterCapabilities,
    )
    import exchange_execution_order_attempt_boundary_v0_1 as boundary

    class ProviderAdapter:
        adapter_name = "FAKE"
        def capabilities(self):
            return ExchangeAdapterCapabilities(True, True, True, True, True, True, False)
        def prepare_order(self, request, *, venue, execution_instrument):
            return AdapterOrderPreparation(True, "READY", "FAKE", venue, {"symbol": "BTCUSDT"})
        def submit_prepared_order(self, preparation, *, canonical_request):
            return result(adapter="FAKE", trade_event_id="PROVIDER-CANNOT-OWN-ID")
        def submit_order(self, request):
            raise AssertionError("direct submission bypass")
        def cancel_order(self, *, asset, exchange_order_id):
            raise AssertionError("cancel must not be called")

    monkeypatch.setattr(boundary, "evaluate_execution_attempt_readiness", lambda **kwargs: {
        "readiness_state": "READY", "readiness_validation": "VALID",
        "asset": "BTC", "direction": "LONG", "quantity": "0.01",
        "entry_price": None, "notional": 600, "provider_binding": "DEFERRED",
        "execution_authorized": False,
    })
    monkeypatch.setattr(boundary, "evaluate_execution_authorization", lambda *args: {
        "authorization_state": "AUTHORIZED",
    })
    monkeypatch.setattr(boundary, "prepare_order_for_adapter", lambda **kwargs:
        AdapterOrderPreparation(True, "READY", "FAKE", "SPOT", {"symbol": "BTCUSDT"}))

    path = tmp_path / "outcomes.jsonl"
    outcome = run_final_execution_attempt_with_outcome_capture(
        execution_ready_package={"package_state": "EXECUTION_READY_PACKAGE"},
        request=request(),
        authorization_observation={"mandate_id": "TEST-ONLY"},
        adapter=ProviderAdapter(),
        venue="SPOT",
        execution_instrument=None,
        stream_path=path,
    )
    assert outcome.execution_result.status == "FILLED"
    assert outcome.execution_result.trade_event_id.startswith("TE-")
    assert outcome.execution_result.trade_event_id != "PROVIDER-CANNOT-OWN-ID"
    assert outcome.capture_state == "PERSISTED"
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["trade_event_id"] == outcome.execution_result.trade_event_id
    assert row["decision_id"] == "DEC-1"
    assert row["fill_inferred"] is False


def test_submission_unknown_without_provider_timestamp_is_persisted_with_local_capture_time(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    outcome = capture_execution_attempt_outcome(
        request=request(),
        result=result(
            accepted=False, exchange_order_id=None, status="SUBMISSION_UNKNOWN",
            timestamp=None, executed_quantity=None, executed_price=None,
            error_code="PROVIDER_SUBMISSION_OUTCOME_AMBIGUOUS",
        ),
        stream_path=path,
    )
    assert outcome.capture_state == "PERSISTED"
    row = json.loads(path.read_text(encoding="utf-8").strip())
    assert row["trade_event_id"] == "TE-1"
    assert row["decision_id"] == "DEC-1"
    assert row["client_order_id"] == "INT-1"
    assert row["provider_status"] == "SUBMISSION_UNKNOWN"
    assert row["outcome_state"] == "UNKNOWN"
    assert row["observed_at"] is None
    assert row["provider_timestamp_known"] is False
    assert row["captured_at"]
    assert row["executed_quantity"] is None
    assert row["executed_price"] is None
    assert row["fill_inferred"] is False
    replay = capture_execution_attempt_outcome(
        request=request(),
        result=result(
            accepted=False, exchange_order_id=None, status="SUBMISSION_UNKNOWN",
            timestamp=None, executed_quantity=None, executed_price=None,
            error_code="PROVIDER_SUBMISSION_OUTCOME_AMBIGUOUS",
        ),
        stream_path=path,
    )
    assert replay.capture_state == "ALREADY_PERSISTED"
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_persistence_failure_is_reported_explicitly(tmp_path):
    path = tmp_path / "outcomes.jsonl"
    path.mkdir()
    outcome = capture_execution_attempt_outcome(
        request=request(), result=result(), stream_path=path
    )
    assert outcome.capture_state == "PERSISTENCE_FAILED"
    assert outcome.reason.startswith("IsADirectoryError:")
    assert path.is_dir()
