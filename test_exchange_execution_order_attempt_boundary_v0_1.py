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


def _authorized(provider="TOOBIT"):
    return {
        "execution_authorization": "AUTHORIZED",
        "authorization_validation": "VALID",
        "authorization_source": "MANAGEMENT_PHASE_ENTRY",
        "authorization_mode": "STANDING_MANDATE",
        "provider": provider,
        "authorization_id": "REAL-PROD-MANDATE-001",
        "mandate_id": "REAL-PROD-MANDATE-001",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "environment": "REAL_PRODUCTION",
        "allowed_markets": ("SPOT", "FUTURES"),
    }


class _TrackingAdapter:
    adapter_name = "TOOBIT"

    def __init__(self):
        self.prepare_calls = 0
        self.submit_prepared_calls = 0
        self.submit_calls = 0

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
        self.prepare_calls += 1
        return AdapterOrderPreparation(
            ready=True,
            reason="READY",
            adapter_name=self.adapter_name,
            venue=venue,
            request={"symbol": execution_instrument},
        )

    def submit_prepared_order(self, preparation, *, canonical_request):
        self.submit_prepared_calls += 1
        return CanonicalExecutionResult(
            accepted=True,
            exchange_order_id="fake-order",
            status="ACCEPTED",
            asset=canonical_request.asset,
            direction=canonical_request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=canonical_request.timestamp,
            adapter=self.adapter_name,
            error_code=None,
            error_message=None,
        )

    def submit_order(self, request):
        self.submit_calls += 1
        raise AssertionError("Direct submit_order must not be called by this boundary.")

    def cancel_order(self, *, asset, exchange_order_id):
        raise AssertionError("Cancellation is outside this test.")


def _attempt(adapter, authorization):
    return attempt_prepared_order(
        request=_request(),
        readiness_observation=_readiness(),
        authorization_observation=authorization,
        adapter=adapter,
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )


def test_provider_mismatch_blocks_before_adapter_preparation_or_submission():
    adapter = _TrackingAdapter()

    result = _attempt(adapter, _authorized(provider="OTHER_PROVIDER"))

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "AUTHORIZATION_PROVIDER_MISMATCH"
    assert adapter.prepare_calls == 0
    assert adapter.submit_prepared_calls == 0
    assert adapter.submit_calls == 0


def test_missing_provider_blocks_before_adapter_preparation_or_submission():
    adapter = _TrackingAdapter()
    authorization = _authorized()
    authorization.pop("provider")

    result = _attempt(adapter, authorization)

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "AUTHORIZATION_PROVIDER_MISMATCH"
    assert adapter.prepare_calls == 0
    assert adapter.submit_prepared_calls == 0
    assert adapter.submit_calls == 0

def test_missing_decision_id_blocks_before_adapter_preparation_or_submission():
    from dataclasses import replace

    adapter = _TrackingAdapter()
    request = replace(_request(), decision_id=None)

    result = attempt_prepared_order(
        request=request,
        readiness_observation=_readiness(),
        authorization_observation=_authorized(),
        adapter=adapter,
        venue="SPOT",
        execution_instrument="BTC-USDT",
    )

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "DECISION_ID_MISSING"
    assert result.trade_event_id is None
    assert adapter.prepare_calls == 0
    assert adapter.submit_prepared_calls == 0
    assert adapter.submit_calls == 0


def test_successful_attempt_carries_boundary_owned_attempt_and_decision_ids():
    adapter = _TrackingAdapter()

    result = _attempt(adapter, _authorized())

    assert result.decision_id == "decision-001"
    assert isinstance(result.trade_event_id, str)
    assert result.trade_event_id.strip()
    assert adapter.prepare_calls == 1
    assert adapter.submit_prepared_calls == 1
    assert adapter.submit_calls == 0


def test_submit_exception_preserves_decision_and_attempt_identity():
    class _RaisingAdapter(_TrackingAdapter):
        def submit_prepared_order(self, preparation, *, canonical_request):
            self.submit_prepared_calls += 1
            raise RuntimeError("controlled test exception")

    adapter = _RaisingAdapter()
    result = _attempt(adapter, _authorized())

    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "ADAPTER_SUBMIT_PREPARED_FAILED"
    assert result.decision_id == "decision-001"
    assert isinstance(result.trade_event_id, str)
    assert result.trade_event_id.strip()
    assert result.fill_outcome is None
    assert adapter.prepare_calls == 1
    assert adapter.submit_prepared_calls == 1
    assert adapter.submit_calls == 0
