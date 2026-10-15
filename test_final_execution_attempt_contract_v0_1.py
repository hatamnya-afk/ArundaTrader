from unittest.mock import patch
import exchange_execution_contract as execution_contract
from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
)
from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from final_execution_attempt_contract_v0_1 import run_final_execution_attempt_contract


def _request():
    return CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity=1,
        quantity_unit="BASE_ASSET", quantity_source="RISK.position_quantity",
        entry_price=100, reference_price=100, intent_id="intent-001",
        snapshot_id="snapshot-001", timestamp="2026-10-08T00:00:00+00:00",
        decision_id="decision-001",
    )


def _package():
    return {
        "package_state": "EXECUTION_READY_PACKAGE", "package_validation": "VALID",
        "execution_authorized": False, "execution_submitted": False,
        "provider_binding": "DEFERRED", "asset": "BTC", "direction": "LONG",
        "entry_price": 100, "stop_price": 99, "stop_distance": 1, "quantity": 1,
        "exposure": 100, "risk_state": "APPROVED", "trade_gate_state": "APPROVED",
        "policy_version": "POLICY-1", "provenance": "REAL_MARKET",
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
        "expires_at": "2099-01-01T00:00:00+00:00",
        "environment": "REAL_PRODUCTION",
        "allowed_markets": ("SPOT", "FUTURES"),
    }


def _revocation_controlled_mandate():
    value = _standing_mandate()
    value.pop("expires_at")
    value["mandate_expiry_policy"] = "REVOCATION_CONTROLLED_NO_CALENDAR_EXPIRY"
    return value


def _active_mandate_status():
    from datetime import datetime, timezone
    return {
        "mandate_id": "REAL-PROD-MANDATE-001",
        "status": "ACTIVE",
        "source": "MANAGEMENT_MANDATE_REGISTRY",
        "record_id": "mandate-status-record-001",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "max_age_seconds": 60,
        "freshness_policy_id": "management-status-freshness-v1",
    }


class _FakeClaim:
    outcome = "CLAIMED"


class _FakeClaimStore:
    """In-memory test double; never touches production state or a database."""

    def claim(self, **kwargs):
        return _FakeClaim()

    def transition(self, **kwargs):
        return None


class _FakeAdapter:
    adapter_name = "FAKE_PROVIDER_NEUTRAL"

    def capabilities(self):
        return ExchangeAdapterCapabilities(
            venue_discovery=False, instrument_resolution=True, constraint_read=True,
            account_read=True, order_state_read=True, order_submission=True,
            order_cancellation=False,
        )

    def prepare_order(self, request, *, venue, execution_instrument):
        return AdapterOrderPreparation(
            ready=True, reason="READY", adapter_name=self.adapter_name, venue=venue,
            request={"instrument": execution_instrument, "request": request},
            client_order_id=f"fake-{request.intent_id}",
        )

    def submit_prepared_order(self, preparation, *, canonical_request):
        return CanonicalExecutionResult(
            accepted=False, exchange_order_id=None, status="PROVIDER_REJECTED",
            asset=canonical_request.asset, direction=canonical_request.direction,
            executed_quantity=None, executed_price=None, timestamp=canonical_request.timestamp,
            adapter=self.adapter_name, error_code="TEST_PROVIDER_REJECTION",
            error_message="Provider rejection is evidence.",
        )

    def submit_order(self, request):
        return CanonicalExecutionResult(
            accepted=False, exchange_order_id=None, status="FAIL_CLOSED",
            asset=request.asset, direction=request.direction, executed_quantity=None,
            executed_price=None, timestamp=request.timestamp, adapter=self.adapter_name,
            error_code="DIRECT_SUBMIT_NOT_ALLOWED",
            error_message="Not used by this contract test.",
        )

    def cancel_order(self, *, asset, exchange_order_id):
        return CanonicalExecutionResult(
            accepted=False, exchange_order_id=exchange_order_id, status="FAIL_CLOSED",
            asset=asset, direction=None, executed_quantity=None, executed_price=None,
            timestamp=None, adapter=self.adapter_name, error_code="CANCEL_NOT_ALLOWED",
            error_message="Not used by this contract test.",
        )


def _run(authorization, safety=None):
    if safety is None:
        safety = {
            "EXECUTION_ENABLED": True,
            "ORDER_SUBMISSION_ENABLED": True,
            "EXCHANGE_WRITE_ENABLED": True,
        }
    with patch.object(execution_contract, "safety_contract", return_value=safety):
        return run_final_execution_attempt_contract(
            execution_ready_package=_package(), request=_request(),
            authorization_observation=authorization, mandate_status_observation=_active_mandate_status(), adapter=_FakeAdapter(),
            venue="SPOT", execution_instrument="BTC-USDT",
            claim_store=_FakeClaimStore(),
        )


def test_final_attempt_accepts_standing_mandate_as_technical_authorization():
    result = _run(_standing_mandate())
    assert result.status == "PROVIDER_REJECTED"
    assert result.error_code == "TEST_PROVIDER_REJECTION"


def test_final_attempt_accepts_explicit_revocation_controlled_mandate_without_expiry():
    result = _run(_revocation_controlled_mandate())
    assert result.status == "PROVIDER_REJECTED"
    assert result.error_code == "TEST_PROVIDER_REJECTION"


def test_final_attempt_rejects_missing_expiry_policy_when_expiry_is_absent():
    authorization = _standing_mandate()
    authorization.pop("expires_at")
    result = _run(authorization)
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "AUTHORIZATION_EXPIRY_POLICY_INVALID"


def test_final_attempt_requires_only_standing_mandate_authorization():
    authorization = _standing_mandate()
    assert "attempt_id" not in authorization
    result = _run(authorization)
    assert result.status == "PROVIDER_REJECTED"
    assert result.error_code == "TEST_PROVIDER_REJECTION"


def test_final_attempt_fails_closed_without_standing_mandate():
    authorization = _standing_mandate()
    authorization.pop("authorization_mode")
    result = _run(authorization)
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "AUTHORIZATION_MODE_INVALID"


def test_final_attempt_keeps_attempt_identity_outside_management_authorization():
    request = _request()
    authorization = _standing_mandate()
    assert "attempt_id" not in authorization
    assert hasattr(request, "intent_id")
    assert hasattr(request, "snapshot_id")


def test_final_attempt_blocks_when_any_global_execution_gate_is_closed():
    for flag in ("EXECUTION_ENABLED", "ORDER_SUBMISSION_ENABLED", "EXCHANGE_WRITE_ENABLED"):
        safety = {
            "EXECUTION_ENABLED": True,
            "ORDER_SUBMISSION_ENABLED": True,
            "EXCHANGE_WRITE_ENABLED": True,
        }
        safety[flag] = False
        result = _run(_standing_mandate(), safety=safety)
        assert result.status == "FAIL_CLOSED"
        assert result.error_code == "GLOBAL_EXECUTION_SAFETY_GATE_CLOSED"


def test_final_attempt_rejects_exposure_not_reconciled_to_quantity_times_entry():
    package = _package()
    package["exposure"] = 99
    safety = {
        "EXECUTION_ENABLED": True,
        "ORDER_SUBMISSION_ENABLED": True,
        "EXCHANGE_WRITE_ENABLED": True,
    }
    with patch.object(execution_contract, "safety_contract", return_value=safety):
        result = run_final_execution_attempt_contract(
            execution_ready_package=package, request=_request(),
            authorization_observation=_standing_mandate(), mandate_status_observation=_active_mandate_status(), adapter=_FakeAdapter(),
            venue="SPOT", execution_instrument="BTC-USDT",
            claim_store=_FakeClaimStore(),
        )
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "READINESS_EXPOSURE_ARITHMETIC_MISMATCH"


def test_final_attempt_fails_closed_when_mandate_status_missing_or_revoked():
    with patch.object(execution_contract, "safety_contract", return_value={
        "EXECUTION_ENABLED": True, "ORDER_SUBMISSION_ENABLED": True, "EXCHANGE_WRITE_ENABLED": True,
    }):
        missing = run_final_execution_attempt_contract(
            execution_ready_package=_package(), request=_request(),
            authorization_observation=_standing_mandate(), adapter=_FakeAdapter(),
            venue="SPOT", execution_instrument="BTC-USDT", claim_store=_FakeClaimStore(),
        )
        revoked = run_final_execution_attempt_contract(
            execution_ready_package=_package(), request=_request(),
            authorization_observation=_standing_mandate(),
            mandate_status_observation={**_active_mandate_status(), "status": "REVOKED"},
            adapter=_FakeAdapter(), venue="SPOT", execution_instrument="BTC-USDT",
            claim_store=_FakeClaimStore(),
        )
    assert missing.status == "FAIL_CLOSED"
    assert missing.error_code == "MANDATE_REVOCATION_OBSERVATION_MISSING"
    assert revoked.status == "FAIL_CLOSED"
    assert revoked.error_code == "MANDATE_REVOKED"
