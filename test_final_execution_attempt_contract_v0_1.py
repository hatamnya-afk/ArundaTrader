from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
)
from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from final_execution_attempt_contract_v0_1 import run_final_execution_attempt_contract


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
        "provider": "TOOBIT",
        "authorization_id": "REAL-PROD-MANDATE-001",
        "mandate_id": "REAL-PROD-MANDATE-001",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "environment": "REAL_PRODUCTION",
        "allowed_markets": ("SPOT", "FUTURES"),
    }


class _FakeAdapter:
    adapter_name = "TOOBIT"

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


def test_final_attempt_fails_closed_when_mandate_provider_does_not_match_adapter():
    authorization = _standing_mandate()
    authorization["provider"] = "OTHER_PROVIDER"
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        authorization_observation=authorization,
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "AUTHORIZATION_PROVIDER_MISMATCH"
    assert "does not match" in result.error_message


def test_final_attempt_fails_closed_when_mandate_provider_is_missing():
    authorization = _standing_mandate()
    authorization.pop("provider")
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        authorization_observation=authorization,
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "AUTHORIZATION_PROVIDER_MISMATCH"
    assert "does not match" in result.error_message