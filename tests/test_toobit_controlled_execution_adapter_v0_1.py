from __future__ import annotations

from exchange_execution_adapter_contract_v0_1 import AdapterOrderPreparation
from exchange_execution_contract import (
    CanonicalOrderRequest,
    QUANTITY_SOURCE_RISK_POSITION,
    QUANTITY_UNIT_BASE_ASSET,
)
from toobit_controlled_execution_adapter_v0_1 import ToobitControlledExecutionAdapter


def request():
    return CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity="0.01",
        quantity_unit=QUANTITY_UNIT_BASE_ASSET,
        quantity_source=QUANTITY_SOURCE_RISK_POSITION,
        entry_price=None, reference_price="60000", intent_id="INT-1",
        snapshot_id="SNAP-1", timestamp="2026-10-15T08:00:00Z",
        decision_id="DEC-1",
    )


def preparation(venue="SPOT"):
    return AdapterOrderPreparation(
        ready=True, reason="READY", adapter_name="TOOBIT", venue=venue,
        request={
            "symbol": "BTCUSDT" if venue == "SPOT" else "BTC-SWAP-USDT",
            "side": "BUY", "type": "MARKET", "newClientOrderId": "INT-1",
            "quantity": "0.01",
        },
    )


def test_submission_disabled_by_default_and_no_transport_call():
    calls = []
    adapter = ToobitControlledExecutionAdapter(
        transport=lambda **kwargs: calls.append(kwargs) or {"orderId": "unexpected"},
        api_key="key", secret_key="secret",
    )
    result = adapter.submit_prepared_order(preparation(), canonical_request=request())
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "ORDER_SUBMISSION_OPT_IN_REQUIRED"
    assert adapter.capabilities().order_submission is False
    assert calls == []


def test_opt_in_spot_uses_single_signed_post_and_only_explicit_fill_fields():
    calls = []
    def transport(**kwargs):
        calls.append(kwargs)
        return {"code": 200, "data": {
            "orderId": "EX-1", "clientOrderId": "INT-1", "symbol": "BTCUSDT",
            "status": "NEW", "price": "60000", "executedQty": "0",
            "updateTime": 1792051200000,
        }}
    adapter = ToobitControlledExecutionAdapter(
        allow_order_submission=True, transport=transport,
        api_key="key", secret_key="secret",
    )
    result = adapter.submit_prepared_order(preparation(), canonical_request=request())
    assert len(calls) == 1
    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/api/v1/spot/order"
    assert calls[0]["headers"]["X-BB-APIKEY"] == "key"
    assert result.exchange_order_id == "EX-1"
    assert result.status == "NEW"
    assert result.executed_price is None  # order price is not fill price
    assert result.executed_quantity == "0"


def test_ambiguous_transport_error_is_unknown_and_never_retried():
    calls = []
    def transport(**kwargs):
        calls.append(kwargs)
        raise TimeoutError("simulated timeout after request dispatch")
    adapter = ToobitControlledExecutionAdapter(
        allow_order_submission=True, transport=transport,
        api_key="key", secret_key="secret",
    )
    result = adapter.submit_prepared_order(preparation(), canonical_request=request())
    assert len(calls) == 1
    assert result.status == "SUBMISSION_UNKNOWN"
    assert result.error_code == "PROVIDER_SUBMISSION_OUTCOME_AMBIGUOUS"
    assert "do not retry" in result.error_message


def test_wrong_client_order_id_is_blocked_before_transport():
    calls = []
    adapter = ToobitControlledExecutionAdapter(
        allow_order_submission=True,
        transport=lambda **kwargs: calls.append(kwargs) or {},
        api_key="key", secret_key="secret",
    )
    prepared = preparation()
    prepared = AdapterOrderPreparation(
        ready=True, reason="READY", adapter_name="TOOBIT", venue="SPOT",
        request={**prepared.request, "newClientOrderId": "OTHER"},
    )
    result = adapter.submit_prepared_order(prepared, canonical_request=request())
    assert result.status == "FAIL_CLOSED"
    assert result.error_code == "CLIENT_ORDER_ID_MISMATCH"
    assert calls == []


def test_futures_uses_documented_v2_route():
    calls = []
    adapter = ToobitControlledExecutionAdapter(
        allow_order_submission=True,
        transport=lambda **kwargs: calls.append(kwargs) or {"code": 200, "data": {
            "orderId": "FUT-1", "status": "NEW",
        }},
        api_key="key", secret_key="secret",
    )
    result = adapter.submit_prepared_order(preparation("FUTURES"), canonical_request=request())
    assert len(calls) == 1
    assert calls[0]["method"] == "POST"
    assert calls[0]["path"] == "/api/v2/futures/order"
    assert result.exchange_order_id == "FUT-1"
