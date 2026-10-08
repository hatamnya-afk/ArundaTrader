from dataclasses import dataclass

from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    ExchangeAdapterCapabilities,
)
from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from exchange_execution_order_attempt_boundary_v0_1 import attempt_prepared_order


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


def _readiness():
    return {
        "readiness_state": "READY",
        "readiness_validation": "VALID",
        "asset": "BTC",
        "quantity": 1,
        "entry_price": 100,
        "notional": 100,
    }


def _authorized():
    return {
        "execution_authorization": "AUTHORIZED",
        "authorization_validation": "VALID",
        "authorization_source": "EXPLICIT_USER_AUTHORIZATION",
    }


class FakeAdapter:
    adapter_name = "REPLACEABLE"

    def __init__(self):
        self.submit_called = False
        self.prepared_request = None

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
        self.prepared_request = {"opaque": "provider-payload"}
        return AdapterOrderPreparation(
            ready=True,
            reason="READY",
            adapter_name=self.adapter_name,
            venue=venue,
            request=self.prepared_request,
        )

    def submit_prepared_order(self, preparation, *, canonical_request):
        self.submit_called = True
        assert preparation.request is self.prepared_request
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


def test_order_attempt_blocks_without_explicit_authorization():
    adapter = FakeAdapter()
    result = attempt_prepared_order(
        request=_request(),
        readiness_observation=_readiness(),
        authorization_observation={},
        adapter=adapter,
        venue="SPOT",
        execution_instrument=object(),
    )
    assert result.accepted is False
    assert result.error_code == "AUTHORIZATION_INVALID"
    assert adapter.submit_called is False


def test_order_attempt_reaches_replaceable_adapter_only_after_authorization():
    adapter = FakeAdapter()
    result = attempt_prepared_order(
        request=_request(),
        readiness_observation=_readiness(),
        authorization_observation=_authorized(),
        adapter=adapter,
        venue="SPOT",
        execution_instrument=object(),
    )
    assert result.accepted is False
    assert result.error_code == "TEST_EXECUTION_DISABLED"
    assert adapter.submit_called is True
