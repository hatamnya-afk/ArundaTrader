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


def test_stable_client_order_id_binding_replaces_intent_id_in_prepared_payload():
    from exchange_execution_adapter_contract_v0_1 import AdapterOrderPreparation

    adapter = ToobitExchangeAdapter()
    prepared = AdapterOrderPreparation(
        ready=True,
        reason="READY",
        adapter_name="TOOBIT",
        venue="FUTURES",
        request={"symbol": "BTCUSDT", "newClientOrderId": "INTENT-OLD", "quantity": "1"},
    )

    bound = adapter.bind_stable_client_order_id(prepared, "AR-STABLE-001")

    assert bound.ready is True
    assert bound.request["newClientOrderId"] == "AR-STABLE-001"
    assert bound.request["symbol"] == "BTCUSDT"
    assert prepared.request["newClientOrderId"] == "INTENT-OLD"


def test_stable_client_order_id_binding_rejects_missing_id_and_invalid_payload():
    from exchange_execution_adapter_contract_v0_1 import AdapterOrderPreparation

    adapter = ToobitExchangeAdapter()
    prepared = AdapterOrderPreparation(
        ready=True, reason="READY", adapter_name="TOOBIT", venue="SPOT", request={}
    )
    missing = adapter.bind_stable_client_order_id(prepared, "  ")
    invalid = adapter.bind_stable_client_order_id(
        AdapterOrderPreparation(
            ready=True, reason="READY", adapter_name="TOOBIT", venue="SPOT", request=None
        ),
        "AR-STABLE-002",
    )

    assert missing.ready is False
    assert missing.reason == "STABLE_CLIENT_ORDER_ID_REQUIRED"
    assert invalid.ready is False
    assert invalid.reason == "TOOBIT_ORDER_PAYLOAD_INVALID"


def test_toobit_policy_records_confirmed_id_constraints_but_keeps_submission_unapproved():
    policy = ToobitExchangeAdapter().stable_client_order_id_policy()
    assert policy["verified"] is False
    assert policy["client_id_constraints_verified"] is True
    assert policy["provider_max_length"] == 255
    assert policy["max_length"] == 64
    assert policy["allowed_pattern"] == r"^[A-Za-z0-9_-]{1,64}$"
    assert policy["submission_enabled"] is False
    assert policy["verification_blocker"] == "TOOBIT_AMBIGUOUS_TIMEOUT_RECOVERY_UNSPECIFIED"
