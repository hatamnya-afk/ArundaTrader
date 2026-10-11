"""Focused regression tests for authoritative order-attempt identity.

All adapters are fakes; no provider/network calls occur.
"""
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

    def __init__(self, raises=False):
        self.raises = raises

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


def _run(adapter):
    return attempt_prepared_order(
        request=request(), readiness_observation=readiness(),
        authorization_observation=authorization(), adapter=adapter,
        venue="SPOT", execution_instrument="BTCUSDT",
    )


def test_attempt_id_is_issued_locally_and_overrides_provider_identity():
    result = _run(FakeAdapter())
    assert result.status == "PROVIDER_REJECTED"
    assert validate_trade_event_id(result.trade_event_id)
    assert result.trade_event_id != "PROVIDER-CONTROLLED-ID"


def test_submission_exception_is_unknown_not_assumed_rejected():
    result = _run(FakeAdapter(raises=True))
    assert result.status == "SUBMISSION_OUTCOME_UNKNOWN"
    assert result.error_code == "ADAPTER_SUBMIT_PREPARED_FAILED"
    assert validate_trade_event_id(result.trade_event_id)
