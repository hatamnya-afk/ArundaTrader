"""Offline contract tests for opt-in Toobit submission; no real transport is used."""

import unittest

from exchange_execution_adapter_contract_v0_1 import AdapterOrderPreparation
from exchange_execution_contract import CanonicalOrderRequest
from execution_instrument_contract_v0_1 import ExecutionInstrumentSpecification
from toobit_exchange_adapter_v0_1 import ToobitAdapterResult, ToobitExchangeAdapter


def _request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=0.001,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100000,
        reference_price=100000,
        intent_id="decision-birth-opaque-001",
        snapshot_id="snapshot-fixture",
        timestamp="2026-10-15T00:00:00+00:00",
        decision_id="decision-birth-opaque-001",
    )


def _preparation(adapter, request):
    return adapter.prepare_order(
        request,
        venue="SPOT",
        execution_instrument=ExecutionInstrumentSpecification(
            asset="BTC", venue="SPOT", settlement_asset="USDT",
            instrument_type="SPOT", selection_source="TEST_FIXTURE",
            policy_version="test-only",
        ),
    )


def test_submission_is_disabled_by_default():
    adapter = ToobitExchangeAdapter(
        transport=lambda **_: (_ for _ in ()).throw(AssertionError("no call expected")),
        api_key="test-key",
        secret_key="test-secret",
    )
    assert adapter.capabilities().order_submission is False
    result = adapter.submit_order(_request())
    assert result.accepted is False
    assert result.error_code == "PREPARED_ORDER_REQUIRED"


def test_opt_in_spot_submit_sends_once_and_validates_provider_response():
    calls = []
    def transport(*, method, path, params, headers, base_url):
        calls.append((method, path, dict(params), dict(headers), base_url))
        if method == "GET" and path == "/api/v1/exchangeInfo":
            return {"symbols": [{
                "symbol": "BTCUSDT", "status": "TRADING",
                "baseAsset": "BTC", "quoteAsset": "USDT",
                "filters": [{"filterType": "LOT_SIZE", "minQty": "0.00001",
                             "maxQty": "100000", "stepSize": "0.00001"}],
            }], "contracts": []}
        assert method == "POST"
        assert path == "/api/v1/spot/order"
        assert params["symbol"] == "BTCUSDT"
        assert params["side"] == "BUY"
        assert params["type"] == "MARKET"
        assert params["newClientOrderId"].startswith("A")
        assert len(params["newClientOrderId"]) == 32
        assert "signature" in params
        assert headers["X-BB-APIKEY"] == "test-key"
        return {
            "symbol": "BTCUSDT",
            "orderId": "order-123",
            "clientOrderId": params["newClientOrderId"],
            "status": "NEW",
            "executedQty": "0",
            "avgPrice": "0",
            "transactTime": "1792022400000",
        }

    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret",
        enable_order_submission=True,
    )
    request = _request()
    prep = _preparation(adapter, request)
    assert prep.ready is True
    assert prep.client_order_id == prep.request["newClientOrderId"]
    assert adapter.capabilities().order_submission is True

    result = adapter.submit_prepared_order(prep, canonical_request=request)
    assert result.accepted is True
    assert result.exchange_order_id == "order-123"
    assert result.status == "NEW"
    assert len([call for call in calls if call[0] == "POST"]) == 1


def test_client_order_id_is_stable_for_same_canonical_intent():
    adapter = ToobitExchangeAdapter(transport=lambda **_: {})
    first = adapter._stable_client_order_id("same-intent")
    second = adapter._stable_client_order_id("same-intent")
    assert first == second
    assert len(first) == 32
    assert first.isalnum()


def test_transport_exception_is_ambiguous_and_never_retried():
    calls = []
    def transport(**kwargs):
        calls.append(kwargs)
        if kwargs["method"] == "GET" and kwargs["path"] == "/api/v1/exchangeInfo":
            return {"symbols": [{
                "symbol": "BTCUSDT", "status": "TRADING",
                "baseAsset": "BTC", "quoteAsset": "USDT",
                "filters": [{"filterType": "LOT_SIZE", "minQty": "0.00001",
                             "maxQty": "100000", "stepSize": "0.00001"}],
            }], "contracts": []}
        raise TimeoutError("fixture timeout after request boundary")
    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret",
        enable_order_submission=True,
    )
    request = _request()
    prep = _preparation(adapter, request)
    result = adapter.submit_prepared_order(prep, canonical_request=request)
    assert result.accepted is False
    assert result.status == "SUBMISSION_OUTCOME_UNKNOWN"
    assert result.error_code == "SUBMISSION_OUTCOME_UNKNOWN"
    assert len([call for call in calls if call["method"] == "POST"]) == 1


def test_response_identity_mismatch_is_not_reported_as_acceptance():
    def transport(*, method, path, params, **kwargs):
        if method == "GET" and path == "/api/v1/exchangeInfo":
            return {"symbols": [{
                "symbol": "BTCUSDT", "status": "TRADING",
                "baseAsset": "BTC", "quoteAsset": "USDT",
                "filters": [{"filterType": "LOT_SIZE", "minQty": "0.00001",
                             "maxQty": "100000", "stepSize": "0.00001"}],
            }], "contracts": []}
        return {
            "symbol": "BTCUSDT", "orderId": "order-123",
            "clientOrderId": "different-client-id", "status": "NEW",
        }
    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret",
        enable_order_submission=True,
    )
    request = _request()
    prep = _preparation(adapter, request)
    result = adapter.submit_prepared_order(prep, canonical_request=request)
    assert result.accepted is False
    assert result.status == "SUBMISSION_OUTCOME_UNKNOWN"
    assert result.error_code == "SUBMISSION_OUTCOME_UNKNOWN"


def test_explicit_provider_rejection_is_not_reported_as_acceptance():
    def transport(*, method, path, params, **kwargs):
        if method == "GET" and path == "/api/v1/exchangeInfo":
            return {"symbols": [{
                "symbol": "BTCUSDT", "status": "TRADING",
                "baseAsset": "BTC", "quoteAsset": "USDT",
                "filters": [{"filterType": "LOT_SIZE", "minQty": "0.00001",
                             "maxQty": "100000", "stepSize": "0.00001"}],
            }], "contracts": []}
        return {
            "symbol": "BTCUSDT", "orderId": "order-rejected-1",
            "clientOrderId": params["newClientOrderId"], "status": "REJECTED",
            "executedQty": "0", "avgPrice": "0",
        }

    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret",
        enable_order_submission=True,
    )
    request = _request()
    prep = _preparation(adapter, request)
    result = adapter.submit_prepared_order(prep, canonical_request=request)
    assert result.accepted is False
    assert result.status == "PROVIDER_REJECTED"
    assert result.error_code == "TOOBIT_PROVIDER_REJECTED"


class ToobitSubmitAdapterTests(unittest.TestCase):
    def test_submission_is_disabled_by_default(self):
        test_submission_is_disabled_by_default()

    def test_opt_in_spot_submit_sends_once_and_validates_provider_response(self):
        test_opt_in_spot_submit_sends_once_and_validates_provider_response()

    def test_client_order_id_is_stable_for_same_canonical_intent(self):
        test_client_order_id_is_stable_for_same_canonical_intent()

    def test_transport_exception_is_ambiguous_and_never_retried(self):
        test_transport_exception_is_ambiguous_and_never_retried()

    def test_response_identity_mismatch_is_not_reported_as_acceptance(self):
        test_response_identity_mismatch_is_not_reported_as_acceptance()

    def test_explicit_provider_rejection_is_not_reported_as_acceptance(self):
        test_explicit_provider_rejection_is_not_reported_as_acceptance()


if __name__ == "__main__":
    unittest.main()


def test_read_only_client_id_reconciliation_finds_exact_spot_order_without_post():
    calls = []
    def transport(*, method, path, params, **kwargs):
        calls.append((method, path, dict(params)))
        assert method == "GET"
        assert path == "/api/v1/spot/order"
        return {
            "symbol": "BTCUSDT",
            "orderId": "reconcile-order-7",
            "clientOrderId": params["origClientOrderId"],
            "status": "FILLED",
            "executedQty": "0.001",
            "avgPrice": "65000",
            "time": "1792000000000",
        }

    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    )
    result = adapter.query_order_by_client_order_id(
        venue="SPOT",
        symbol="BTCUSDT",
        client_order_id="A0123456789abcdefghijklmnopqrstuv",
    )
    assert result.allowed is True
    assert result.reason == "ORDER_FOUND"
    assert result.data["state_known"] is True
    assert result.data["exchange_order_id"] == "reconcile-order-7"
    assert result.data["provider_status"] == "FILLED"
    assert len(calls) == 1
    assert all(method == "GET" for method, _, _ in calls)


def test_read_only_client_id_reconciliation_keeps_missing_order_unresolved():
    calls = []
    def transport(*, method, path, params, **kwargs):
        calls.append((method, path, dict(params)))
        raise RuntimeError("TOOBIT_PROVIDER_ERROR:-2013:Order does not exist")

    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    )
    result = adapter.query_order_by_client_order_id(
        venue="SPOT",
        symbol="BTCUSDT",
        client_order_id="A0123456789abcdefghijklmnopqrstuv",
    )
    assert result.allowed is False
    assert result.reason == "ORDER_LOOKUP_UNRESOLVED"
    assert result.data["state_known"] is False
    assert result.data["reconciliation_state"] == "UNRESOLVED_KEEP_QUARANTINED"
    assert result.data["resubmit_allowed"] is False
    assert len(calls) == 1
    assert calls[0][0] == "GET"


def test_read_only_client_id_reconciliation_uses_documented_futures_query_endpoint():
    from execution_instrument_contract_v0_1 import ExecutionInstrumentSpecification

    calls = []
    def transport(*, method, path, params, **kwargs):
        calls.append((method, path, dict(params)))
        assert method == "GET"
        assert path == "/api/v2/futures/order"
        assert params["category"] == "USDT"
        return {
            "symbol": "BTC-SWAP-USDT",
            "orderId": "futures-reconcile-1",
            "clientOrderId": params["origClientOrderId"],
            "status": "PARTIALLY_FILLED",
            "executedQty": "1",
            "avgPrice": "65000",
            "updateTime": "1792000000000",
        }

    class _ResolvedAdapter(ToobitExchangeAdapter):
        def resolve_futures_instrument(self, specification):
            return ToobitAdapterResult(True, "RESOLVED", {"symbol": "BTC-SWAP-USDT"})

    adapter = _ResolvedAdapter(transport=transport, api_key="test-key", secret_key="test-secret")
    instrument = ExecutionInstrumentSpecification(
        asset="BTC", venue="FUTURES", settlement_asset="USDT",
        instrument_type="PERPETUAL", selection_source="POLICY",
        policy_version="test-policy",
    )
    result = adapter.query_order_by_client_order_id(
        venue="FUTURES", symbol="BTC-SWAP-USDT",
        client_order_id="A0123456789abcdefghijklmnopqrstuv",
        execution_instrument=instrument,
    )
    assert result.allowed is True
    assert result.reason == "ORDER_FOUND"
    assert result.data["provider_status"] == "PARTIALLY_FILLED"
    assert len(calls) == 1
    assert calls[0][0] == "GET"
