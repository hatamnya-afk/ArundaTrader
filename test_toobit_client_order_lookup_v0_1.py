from exchange_execution_order_reconciliation_contract_v0_1 import (
    ProviderOrderLookup,
    evaluate_order_reconciliation,
)
from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter


def test_direct_futures_lookup_returns_found_only_for_matching_complete_identity():
    def transport(*, method, path, params, headers, base_url):
        assert method == "GET"
        assert path == "/api/v2/futures/order"
        assert params["origClientOrderId"] == "AR-CLIENT-001"
        assert params["category"] == "USDT"
        assert headers["X-BB-APIKEY"] == "test-key"
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "orderId": "EX-123",
                "clientOrderId": "AR-CLIENT-001",
                "status": "NEW",
            },
        }

    result = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    ).lookup_futures_order_by_client_order_id("AR-CLIENT-001")

    assert result == ProviderOrderLookup(
        state="FOUND",
        client_order_id="AR-CLIENT-001",
        exchange_order_id="EX-123",
        provider_status="NEW",
        detail_code="TOOBIT_DIRECT_ORDER_LOOKUP",
    )


def test_explicit_provider_no_such_order_is_not_found_but_does_not_authorize_retry():
    def transport(*, method, path, params, headers, base_url):
        assert method == "GET"
        assert path == "/api/v2/futures/order"
        return {"code": -2013, "msg": "Order does not exist."}

    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    )
    result = adapter.lookup_futures_order_by_client_order_id("AR-CLIENT-002")
    assert result.state == "NOT_FOUND"
    assert result.detail_code == "TOOBIT_NO_SUCH_ORDER"

    decision = evaluate_order_reconciliation(
        expected_client_order_id="AR-CLIENT-002",
        prior_attempt="PRIOR_ATTEMPT_FOUND",
        lookup=result,
    )
    assert decision.state == "RECONCILIATION_REQUIRED"
    assert decision.may_submit is False
    assert decision.retry_allowed is False


def test_transport_timeout_remains_error_not_not_found():
    def transport(**kwargs):
        raise TimeoutError("synthetic timeout")

    result = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    ).lookup_futures_order_by_client_order_id("AR-CLIENT-003")

    assert result.state == "ERROR"
    assert result.detail_code == "TOOBIT_LOOKUP_ERROR:TimeoutError"


def test_malformed_or_mismatched_provider_identity_fails_closed():
    def transport(**kwargs):
        return {
            "code": 200,
            "msg": "success",
            "data": {
                "orderId": "EX-404",
                "clientOrderId": "DIFFERENT-ID",
                "status": "NEW",
            },
        }

    result = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    ).lookup_futures_order_by_client_order_id("AR-CLIENT-004")

    assert result.state == "ERROR"
    assert result.detail_code == "TOOBIT_ORDER_LOOKUP_IDENTITY_INVALID"


def test_missing_credentials_or_transport_fail_closed_without_network_fallback():
    result = ToobitExchangeAdapter().lookup_futures_order_by_client_order_id(
        "AR-CLIENT-005"
    )
    assert result.state == "ERROR"
    assert result.detail_code == "TOOBIT_LOOKUP_ERROR:RuntimeError"
