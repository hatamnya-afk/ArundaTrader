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


def _authorization():
    return {
        "execution_authorization": "AUTHORIZED",
        "authorization_validation": "VALID",
        "authorization_source": "EXPLICIT_USER_AUTHORIZATION",
    }


class FakeAdapter:
    adapter_name = "REPLACEABLE"

    def __init__(self):
        self.submit_called = False

    def capabilities(self):
        return ExchangeAdapterCapabilities(
            venue_discovery=True,
            instrument_resolution=True,
            constraint_read=True,
            account_read=True,
            order_state_read=True,
            order_submission=True,
            order_cancellation=True,
        )

    def prepare_order(self, request, *, venue, execution_instrument):
        return AdapterOrderPreparation(
            ready=True,
            reason="READY",
            adapter_name=self.adapter_name,
            venue=venue,
            request={"opaque": "provider-payload"},
        )

    def submit_prepared_order(self, preparation, *, canonical_request):
        self.submit_called = True
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="FAIL_CLOSED",
            asset=canonical_request.asset,
            direction=canonical_request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=None,
            adapter=self.adapter_name,
            error_code="TEST_EXECUTION_DISABLED",
            error_message="test adapter remains fail-closed",
        )

    def submit_order(self, request):
        raise AssertionError("legacy submit path must not be used")

    def cancel_order(self, *, asset, exchange_order_id):
        raise AssertionError("cancel path must not be used")


def test_final_contract_blocks_without_explicit_authorization():
    adapter = FakeAdapter()
    authorization = {}
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        authorization_observation=authorization,
        adapter=adapter,
        venue="SPOT",
        execution_instrument=object(),
    )
    assert result.accepted is False
    assert result.error_code == "AUTHORIZATION_INVALID"
    assert adapter.submit_called is False


def test_final_contract_reaches_replaceable_adapter_after_explicit_authorization():
    adapter = FakeAdapter()
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        authorization_observation=_authorization(),
        adapter=adapter,
        venue="SPOT",
        execution_instrument=object(),
    )
    assert result.accepted is False
    assert result.error_code == "TEST_EXECUTION_DISABLED"
    assert adapter.submit_called is True


def test_final_contract_rejects_invalid_package_before_adapter():
    adapter = FakeAdapter()
    package = _package()
    package["quantity"] = 2
    result = run_final_execution_attempt_contract(
        execution_ready_package=package,
        request=_request(),
        authorization_observation=_authorization(),
        adapter=adapter,
        venue="SPOT",
        execution_instrument=object(),
    )
    assert result.accepted is False
    assert result.error_code == "READINESS_REQUEST_QUANTITY_MISMATCH"
    assert adapter.submit_called is False
