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


def _management_observation(decision="AUTHORIZED"):
    return {
        "decision": decision,
        "mandate_id": "REAL-PROD-MANDATE-001",
        "authorized_by": "MANAGEMENT",
        "authorization_source": "MANAGEMENT_PHASE_ENTRY",
        "environment": "REAL_PRODUCTION",
        "issued_at": "2026-10-10T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "allowed_markets": ["SPOT", "FUTURES"],
        "provider": "FAKE_PROVIDER_NEUTRAL",
        "capital_policy": "ZERO_INITIAL_CAPITAL_PROVIDER_FEEDBACK_THEN_PROGRESSIVE_SCALING",
        "evidence_required_before": ["canonical_order_path", "provider_readiness"],
        "evidence_required_after": ["provider_response", "fill_or_not_filled", "outcome"],
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


def test_final_attempt_runs_management_producer_then_technical_authorization():
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        management_observation=_management_observation(),
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )
    assert result.status == "PROVIDER_REJECTED"
    assert result.error_code == "TEST_PROVIDER_REJECTION"


def test_final_attempt_keeps_trade_identity_outside_management_scope():
    request = _request()
    observation = _management_observation()
    assert "attempt_id" not in observation
    assert "asset" not in observation
    assert hasattr(request, "intent_id")
    assert hasattr(request, "snapshot_id")


def test_final_attempt_fails_closed_without_valid_management_mandate():
    observation = _management_observation()
    observation["authorization_source"] = ""
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        management_observation=observation,
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "FINAL_EXECUTION_ATTEMPT_CONTRACT_FAILED"


def test_final_attempt_fails_closed_when_mandate_provider_does_not_match_adapter():
    observation = _management_observation()
    observation["provider"] = "OTHER_PROVIDER"
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        management_observation=observation,
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "AUTHORIZATION_PROVIDER_MISMATCH"


def test_final_attempt_fails_closed_when_mandate_provider_is_missing():
    observation = _management_observation()
    observation.pop("provider")
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        management_observation=observation,
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "FINAL_EXECUTION_ATTEMPT_CONTRACT_FAILED"


def test_final_attempt_denied_management_decision_never_reaches_adapter():
    class NoPrepareAdapter(_FakeAdapter):
        def prepare_order(self, request, *, venue, execution_instrument):
            raise AssertionError("adapter must not be reached for denied phase entry")

    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        management_observation=_management_observation("DENIED"),
        adapter=NoPrepareAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "FINAL_EXECUTION_ATTEMPT_CONTRACT_FAILED"


def test_final_attempt_rejects_handcrafted_technical_authorization_as_management_input():
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        management_observation={
            "execution_authorization": "AUTHORIZED",
            "authorization_validation": "VALID",
            "authorization_mode": "STANDING_MANDATE",
        },
        adapter=_FakeAdapter(),
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "FINAL_EXECUTION_ATTEMPT_CONTRACT_FAILED"
