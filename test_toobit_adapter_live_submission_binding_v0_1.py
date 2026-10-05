from exchange_execution_contract import CanonicalOrderRequest
from toobit_trading_adapter import ToobitTradingAdapter
from toobit_spot_order_live_transport_v0_1 import (
    SpotLiveOrderResult,
)
from provider_order_translation_v0_1 import ProviderOrderRequest

class FakeLiveTransport:
    def submit(self, request):
        return SpotLiveOrderResult(
            accepted=False,
            status="HTTP_ERROR",
            http_status=400,
            response_body={"code": -2010, "msg": "insufficient balance"},
            error_code="HTTP_ERROR",
            error_message="400",
            submitted_to_matching_engine=True,
        )


def make_request():
    return CanonicalOrderRequest(
        asset="BTCUSDT",
        direction="LONG",
        order_type="LIMIT",
        quantity="1",
        quantity_unit="BASE_ASSET",
        quantity_source="RESEARCH_PREDEFINED",
        entry_price="40000",
        reference_price="40000",
        intent_id="LAB-ADAPTER-001",
        snapshot_id="RS-LAB-001",
        timestamp="1700000000000",
    )


def test_toobit_adapter_exposes_order_submission_capability_only_when_explicitly_enabled():
    adapter = ToobitTradingAdapter(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        live_order_transport=FakeLiveTransport(),
    )

    assert adapter.capabilities().get("ORDER_SUBMISSION") is False

    adapter.execution_enabled = True
    adapter.order_submission_enabled = True
    adapter.exchange_write_enabled = True
    adapter.live_order_transport_enabled = True

    assert adapter.capabilities().get("ORDER_SUBMISSION") is True


def test_toobit_adapter_submit_order_projects_provider_quantity_and_returns_exchange_rejection():
    adapter = ToobitTradingAdapter(
        api_key="TEST_KEY",
        api_secret="TEST_SECRET",
        live_order_transport=FakeLiveTransport(),
    )

    adapter.execution_enabled = True
    adapter.order_submission_enabled = True
    adapter.exchange_write_enabled = True
    adapter.live_order_transport_enabled = True

    request = make_request()
    original_quantity = request.quantity

    provider_request = ProviderOrderRequest(
        venue="TOOBIT",
        symbol="BTCUSDT",
        side="BUY",
        position_side=None,
        order_type="LIMIT",
        quantity="123.456789",
        quantity_unit="BASE_ASSET",
        entry_price="40000",
        intent_id=request.intent_id,
        snapshot_id=request.snapshot_id,
        timestamp=request.timestamp,
        decision_id="DEC-1",
    )

    adapter._cp46g_provider_request = provider_request
    adapter._get_server_timestamp_ms = lambda: 1791120705000

    result = adapter.submit_order(request)

    assert result.accepted is False
    assert result.error_code == "HTTP_ERROR"
    assert result.exchange_order_id is None
    assert request.quantity == original_quantity
    assert provider_request.quantity == "123.456789"