import os
import pytest

from standing_mandate_lifecycle_store_v0_1 import append_lifecycle_event

from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
)
from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from final_execution_attempt_contract_v0_1 import run_final_execution_attempt_contract


@pytest.fixture(autouse=True)
def _durable_mandate_journal(tmp_path, monkeypatch):
    journal = tmp_path / "standing-mandate.jsonl"
    append_lifecycle_event(
        journal,
        {
            "event_id": "PHASE_ENTRY_ACTIVATE:REAL-PROD-MANDATE-001",
            "event_type": "ACTIVATE",
            "mandate_id": "REAL-PROD-MANDATE-001",
            "authority": "MANAGEMENT",
        },
    )
    monkeypatch.setenv("ARUNDA_MANDATE_LIFECYCLE_PATH", str(journal))
    return journal


def _request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100,
        reference_price=100,
        intent_id="intent-001",
        snapshot_id="snapshot-001",
        timestamp="2026-10-08T00:00:00+00:00",
        decision_id="decision-001",
    )


def _package():
    return {
        "package_state": "EXECUTION_READY_PACKAGE",
        "package_validation": "VALID",
        "execution_authorized": False,
        "execution_submitted": False,
        "provider_binding": "DEFERRED",
        "asset": "BTC",
        "direction": "LONG",
        "entry_price": 100,
        "stop_price": 99,
        "stop_distance": 1,
        "quantity": 1,
        "exposure": 100,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": "POLICY-1",
        "provenance": "REAL_MARKET",
        "observed_at": "2026-10-08T00:00:00+00:00",
    }


def _standing_mandate():
    return {
        "execution_authorization": "AUTHORIZED",
        "authorization_validation": "VALID",
        "authorization_source": "MANAGEMENT_PHASE_ENTRY",
        "authorization_mode": "STANDING_MANDATE",
        "authorization_id": "REAL-PROD-MANDATE-001",
        "mandate_id": "REAL-PROD-MANDATE-001",
        "mandate_lifecycle_events": (
            {
                "event_id": "PHASE_ENTRY_ACTIVATE:REAL-PROD-MANDATE-001",
                "event_type": "ACTIVATE",
                "mandate_id": "REAL-PROD-MANDATE-001",
                "authority": "MANAGEMENT",
            },
        ),
        "expires_at": None,
        "environment": "REAL_PRODUCTION",
        "allowed_markets": ("SPOT", "FUTURES"),
    }


class _FakeAdapter:
    adapter_name = "FAKE_PROVIDER_NEUTRAL"

    def capabilities(self):
        return ExchangeAdapterCapabilities(
            venue_discovery=False,
            instrument_resolution=True,
            constraint_read=True,
            account_read=True,
            order_state_read=True,
            order_submission=True,
            order_cancellation=False,
        )

    def prepare_order(self, request, *, venue, execution_instrument):
        return AdapterOrderPreparation(
            ready=True,
            reason="READY",
            adapter_name=self.adapter_name,
            venue=venue,
            request={"instrument": execution_instrument, "request": request},
        )

    def submit_prepared_order(self, preparation, *, canonical_request):
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="PROVIDER_REJECTED",
            asset=canonical_request.asset,
            direction=canonical_request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=canonical_request.timestamp,
            adapter=self.adapter_name,
            error_code="TEST_PROVIDER_REJECTION",
            error_message="Provider rejection is evidence.",
        )

    def submit_order(self, request):
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="FAIL_CLOSED",
            asset=request.asset,
            direction=request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=request.timestamp,
            adapter=self.adapter_name,
            error_code="DIRECT_SUBMIT_NOT_ALLOWED",
            error_message="Not used by this contract test.",
        )

    def cancel_order(self, *, asset, exchange_order_id):
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=exchange_order_id,
            status="FAIL_CLOSED",
            asset=asset,
            direction=None,
            executed_quantity=None,
            executed_price=None,
            timestamp=None,
            adapter=self.adapter_name,
            error_code="CANCEL_NOT_ALLOWED",
            error_message="Not used by this contract test.",
        )


def test_final_attempt_accepts_standing_mandate_as_technical_authorization():
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        authorization_observation=_standing_mandate(),
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )

    assert result.status == "PROVIDER_REJECTED"
    assert result.error_code == "TEST_PROVIDER_REJECTION"


def test_final_attempt_requires_only_standing_mandate_authorization():
    authorization = _standing_mandate()
    assert "attempt_id" not in authorization
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        authorization_observation=authorization,
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )

    assert result.status == "PROVIDER_REJECTED"
    assert result.error_code == "TEST_PROVIDER_REJECTION"


def test_final_attempt_fails_closed_without_standing_mandate():
    authorization = _standing_mandate()
    authorization.pop("authorization_mode")
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        authorization_observation=authorization,
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "AUTHORIZATION_MODE_INVALID"


def test_final_attempt_keeps_attempt_identity_outside_management_authorization():
    request = _request()
    authorization = _standing_mandate()

    assert "attempt_id" not in authorization
    assert hasattr(request, "intent_id")
    assert hasattr(request, "snapshot_id")


def test_final_attempt_rereads_durable_lifecycle_and_blocks_after_revocation(
    _durable_mandate_journal,
):
    append_lifecycle_event(
        _durable_mandate_journal,
        {
            "event_id": "MANAGEMENT_REVOKE:REAL-PROD-MANDATE-001",
            "event_type": "REVOKE",
            "mandate_id": "REAL-PROD-MANDATE-001",
            "authority": "MANAGEMENT",
        },
    )
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        authorization_observation=_standing_mandate(),
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "MANDATE_NOT_ACTIVE"


def test_final_attempt_fails_closed_if_durable_journal_path_is_unconfigured(monkeypatch):
    monkeypatch.delenv("ARUNDA_MANDATE_LIFECYCLE_PATH", raising=False)
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        authorization_observation=_standing_mandate(),
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "FINAL_EXECUTION_ATTEMPT_CONTRACT_FAILED"
    assert "MANDATE_LIFECYCLE_STORE_PATH_REQUIRED" in (result.error_message or "")
