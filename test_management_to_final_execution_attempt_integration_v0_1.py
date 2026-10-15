"""Integration contract: management phase-entry mandate -> final attempt gate.

Uses only an in-memory fake adapter. It performs no network, exchange, DB,
runtime, or real order operations.
"""

from management_execution_authorization_v0_1 import (
    DEFERRED,
    DENIED,
    evaluate_management_authorization,
)
from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
)
from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from final_execution_attempt_contract_v0_1 import run_final_execution_attempt_contract


def _management_observation(decision="AUTHORIZED"):
    return {
        "decision": decision,
        "mandate_id": "REAL-PROD-MANDATE-INTEGRATION-001",
        "authorized_by": "MANAGEMENT",
        "authorization_source": "MANAGEMENT_PHASE_ENTRY",
        "environment": "REAL_PRODUCTION",
        "issued_at": "2026-10-08T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "allowed_markets": ["SPOT", "FUTURES"],
        "provider": "TOOBIT",
        "capital_policy": "ZERO_INITIAL_CAPITAL_PROVIDER_FEEDBACK_THEN_PROGRESSIVE_SCALING",
        "evidence_required_before": ["canonical_order_path", "provider_readiness"],
        "evidence_required_after": ["provider_response", "fill_or_not_filled", "outcome"],
    }


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
        intent_id="intent-integration-001",
        snapshot_id="snapshot-integration-001",
        timestamp="2026-10-15T00:00:00+00:00",
        decision_id="decision-integration-001",
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
        "policy_version": "POLICY-TEST",
        "provenance": "REAL_MARKET",
        "observed_at": "2026-10-15T00:00:00+00:00",
    }


class _FakeAdapter:
    """In-memory adapter: never connects to a provider."""

    adapter_name = "IN_MEMORY_TEST_ADAPTER"

    def __init__(self):
        self.submit_calls = 0

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
        self.submit_calls += 1
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="TEST_PROVIDER_REJECTED",
            asset=canonical_request.asset,
            direction=canonical_request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=canonical_request.timestamp,
            adapter=self.adapter_name,
            error_code="IN_MEMORY_TEST_RESULT",
            error_message="In-memory integration-test result only.",
        )

    def submit_order(self, request):
        raise AssertionError("Direct adapter submission must not be used.")

    def cancel_order(self, *, asset, exchange_order_id):
        raise AssertionError("Cancellation must not be used.")


def _run(management_decision):
    management = evaluate_management_authorization(
        _management_observation(management_decision)
    )
    adapter = _FakeAdapter()
    result = run_final_execution_attempt_contract(
        execution_ready_package=_package(),
        request=_request(),
        authorization_observation=management["authorization_observation"] or {},
        adapter=adapter,
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )
    return management, result, adapter


def test_authorized_management_mandate_flows_into_final_attempt_contract():
    management, result, adapter = _run("AUTHORIZED")

    assert management["management_state"] == "AUTHORIZED"
    assert management["authorization_observation"]["authorization_mode"] == "STANDING_MANDATE"
    assert management["authorization_observation"]["allowed_markets"] == ("SPOT", "FUTURES")
    # Reaching this fake adapter is the expected contract boundary; no real
    # provider exists in this test and its result is deliberately a rejection.
    assert result.status == "TEST_PROVIDER_REJECTED"
    assert result.error_code == "IN_MEMORY_TEST_RESULT"
    assert adapter.submit_calls == 1


def test_denied_management_decision_cannot_reach_adapter_submission():
    management, result, adapter = _run(DENIED)

    assert management["authorization_observation"] is None
    assert result.status != "TEST_PROVIDER_REJECTED"
    assert adapter.submit_calls == 0


def test_deferred_management_decision_cannot_reach_adapter_submission():
    management, result, adapter = _run(DEFERRED)

    assert management["authorization_observation"] is None
    assert result.status != "TEST_PROVIDER_REJECTED"
    assert adapter.submit_calls == 0
