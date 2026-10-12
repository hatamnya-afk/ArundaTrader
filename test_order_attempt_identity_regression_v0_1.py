"""Focused regression tests for authoritative order-attempt identity.

Only fake adapters and pytest temporary files are used; no provider/network calls.
"""
import json
from pathlib import Path

from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
)
from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from exchange_execution_order_attempt_boundary_v0_1 import attempt_prepared_order
from mcp01_trade_event_identity_v0_1 import validate_trade_event_id


def request():
    return CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET",
        quantity=1, quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100, reference_price=100, intent_id="INTENT-1",
        snapshot_id="SNAP-1", timestamp="2026-10-08T00:00:00Z",
        decision_id="DECISION-1",
    )


def readiness():
    return {
        "readiness_state": "READY", "readiness_validation": "VALID",
        "asset": "BTC", "quantity": 1, "entry_price": 100, "notional": 100,
        "venue": "SPOT",
    }


def authorization():
    return {
        "execution_authorization": "AUTHORIZED",
        "authorization_validation": "VALID",
        "authorization_source": "MANAGEMENT_PHASE_ENTRY",
        "authorization_mode": "STANDING_MANDATE",
        "authorization_id": "REAL-PROD-MANDATE-001",
        "mandate_id": "REAL-PROD-MANDATE-001",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "environment": "REAL_PRODUCTION",
        "allowed_markets": ("SPOT", "FUTURES"),
    }


class FakeAdapter:
    adapter_name = "FAKE_PROVIDER"

    def __init__(self, evidence_path: Path | None = None, raises=False):
        self.evidence_path = evidence_path
        self.raises = raises
        self.submit_called = False
        self.attempt_evidence_seen_before_submit = False

    def capabilities(self):
        return ExchangeAdapterCapabilities(
            venue_discovery=False, instrument_resolution=True,
            constraint_read=True, account_read=True, order_state_read=True,
            order_submission=True, order_cancellation=False,
        )

    def prepare_order(self, request, *, venue, execution_instrument):
        return AdapterOrderPreparation(
            ready=True, reason="READY", adapter_name=self.adapter_name,
            venue=venue, request={"instrument": execution_instrument},
        )

    def submit_prepared_order(self, preparation, *, canonical_request):
        self.submit_called = True
        if self.evidence_path and self.evidence_path.exists():
            rows = [json.loads(line) for line in self.evidence_path.read_text(encoding="utf-8").splitlines()]
            self.attempt_evidence_seen_before_submit = (
                len(rows) == 1 and rows[0]["event_type"] == "ORDER_ATTEMPTED"
            )
        if self.raises:
            raise TimeoutError("simulated timeout")
        return CanonicalExecutionResult(
            accepted=False, exchange_order_id=None, status="PROVIDER_REJECTED",
            asset=canonical_request.asset, direction=canonical_request.direction,
            executed_quantity=None, executed_price=None,
            timestamp=canonical_request.timestamp, adapter=self.adapter_name,
            error_code="FAKE_REJECT", error_message="fake response",
            trade_event_id="PROVIDER-CONTROLLED-ID",
        )

    def submit_order(self, request):
        raise AssertionError("direct submit must not be used")

    def cancel_order(self, *, asset, exchange_order_id):
        raise AssertionError("cancel must not be used")


def _run(adapter, evidence_path=None):
    return attempt_prepared_order(
        request=request(), readiness_observation=readiness(),
        authorization_observation=authorization(), adapter=adapter,
        venue="SPOT", execution_instrument="BTCUSDT",
        evidence_stream_path=evidence_path,
    )


def test_attempt_id_is_local_and_attempt_evidence_precedes_provider_call(tmp_path):
    stream = tmp_path / "events.jsonl"
    adapter = FakeAdapter(evidence_path=stream)
    result = _run(adapter, stream)
    rows = [json.loads(line) for line in stream.read_text(encoding="utf-8").splitlines()]
    assert result.status == "PROVIDER_REJECTED"
    assert validate_trade_event_id(result.trade_event_id)
    assert result.trade_event_id != "PROVIDER-CONTROLLED-ID"
    assert adapter.submit_called
    assert adapter.attempt_evidence_seen_before_submit
    assert [row["event_type"] for row in rows] == ["ORDER_ATTEMPTED", "PROVIDER_RESULT"]
    assert all(row["trade_event_id"] == result.trade_event_id for row in rows)


def test_submission_exception_is_unknown_and_both_events_are_recorded(tmp_path):
    stream = tmp_path / "events.jsonl"
    adapter = FakeAdapter(evidence_path=stream, raises=True)
    result = _run(adapter, stream)
    rows = [json.loads(line) for line in stream.read_text(encoding="utf-8").splitlines()]
    assert result.status == "SUBMISSION_OUTCOME_UNKNOWN"
    assert result.error_code == "ADAPTER_SUBMIT_PREPARED_FAILED"
    assert validate_trade_event_id(result.trade_event_id)
    assert adapter.attempt_evidence_seen_before_submit
    assert [row["event_type"] for row in rows] == ["ORDER_ATTEMPTED", "PROVIDER_RESULT"]
    assert rows[1]["status"] == "SUBMISSION_OUTCOME_UNKNOWN"


def test_missing_evidence_path_blocks_before_provider_call():
    adapter = FakeAdapter()
    result = _run(adapter)
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "EXECUTION_ATTEMPT_EVIDENCE_PATH_REQUIRED"
    assert not adapter.submit_called


def test_pre_submit_evidence_write_failure_blocks_adapter_call(tmp_path, monkeypatch):
    import mcp01_execution_attempt_evidence_v0_1 as evidence

    def fail_write(event, stream_path):
        raise OSError("simulated evidence disk failure")

    monkeypatch.setattr(evidence, "append_event_idempotent", fail_write)
    adapter = FakeAdapter(evidence_path=tmp_path / "events.jsonl")
    result = _run(adapter, tmp_path / "events.jsonl")

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "ORDER_ATTEMPT_EVIDENCE_PERSISTENCE_FAILED"
    assert validate_trade_event_id(result.trade_event_id)
    assert not adapter.submit_called


def test_provider_result_evidence_failure_surfaces_reconciliation_error(tmp_path, monkeypatch):
    import mcp01_execution_attempt_evidence_v0_1 as evidence

    original_append = evidence.append_event_idempotent

    def fail_only_provider_result(event, stream_path):
        if event.event_type == "PROVIDER_RESULT":
            raise OSError("simulated provider-result evidence failure")
        return original_append(event, stream_path)

    monkeypatch.setattr(evidence, "append_event_idempotent", fail_only_provider_result)
    stream = tmp_path / "events.jsonl"
    adapter = FakeAdapter(evidence_path=stream)
    result = _run(adapter, stream)

    assert adapter.submit_called
    assert result.status == "PROVIDER_REJECTED"
    assert result.error_code == "PROVIDER_RESULT_EVIDENCE_PERSISTENCE_FAILED"
    assert validate_trade_event_id(result.trade_event_id)
    rows = [json.loads(line) for line in stream.read_text(encoding="utf-8").splitlines()]
    assert [row["event_type"] for row in rows] == ["ORDER_ATTEMPTED"]
