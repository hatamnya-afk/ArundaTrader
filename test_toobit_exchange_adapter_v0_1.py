"""Focused tests for Toobit read, preparation, and gated-write contracts."""

from execution_instrument_contract_v0_1 import ExecutionInstrumentSpecification
from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter


def test_spot_constraints_use_authoritative_symbol():
    def transport(*, method, path, params, headers, base_url):
        assert method == "GET"
        assert path == "/api/v1/exchangeInfo"
        return {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "status": "TRADING",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "filters": [
                        {"filterType": "LOT_SIZE", "minQty": "0.001", "maxQty": "10", "stepSize": "0.001"},
                    ],
                }
            ],
            "contracts": [],
        }

    result = ToobitExchangeAdapter(transport=transport).trading_constraints("BTC")
    assert result.allowed is True
    assert result.data["symbol"] == "BTCUSDT"


def test_futures_constraints_preserve_provider_contract_metadata():
    def transport(*, method, path, params, headers, base_url):
        assert path == "/api/v1/exchangeInfo"
        return {
            "symbols": [],
            "contracts": [
                {
                    "symbol": "BTC-SWAP-USDT",
                    "status": "TRADING",
                    "underlying": "BTC",
                    "contractMultiplier": "0.001",
                    "filters": [
                        {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.001",
                            "maxQty": "1000",
                            "stepSize": "0.001",
                        }
                    ],
                }
            ],
        }

    result = ToobitExchangeAdapter(transport=transport).futures_trading_constraints("BTC")
    assert result.allowed is True
    assert result.data["symbol"] == "BTC-SWAP-USDT"
    assert result.data["contractMultiplier"] == "0.001"


def test_missing_transport_fails_closed():
    result = ToobitExchangeAdapter().get_server_time()
    assert result.allowed is False
    assert result.reason == "TOOBIT_TRANSPORT_NOT_CONFIGURED"


def test_order_submission_is_explicitly_disabled():
    result = ToobitExchangeAdapter().order_submission()
    assert result.allowed is False
    assert result.reason == "EXECUTION_WRITE_GATES_CLOSED"


def test_cancel_is_explicitly_disabled():
    result = ToobitExchangeAdapter().cancel_order(
        asset="BTC", exchange_order_id="test-order-id"
    )
    assert result.accepted is False
    assert result.error_code == "EXECUTION_DISABLED_ORDER_CANCELLATION_NOT_IMPLEMENTED"


def test_futures_account_state_preserves_provider_position_state_without_inference():
    def transport(*, method, path, params, headers, base_url):
        if path == "/api/v1/exchangeInfo":
            return {
                "symbols": [],
                "contracts": [
                    {
                        "symbol": "BTC-SWAP-USDT",
                        "status": "TRADING",
                        "underlying": "BTC",
                        "contractMultiplier": "0.001",
                        "filters": [],
                    }
                ],
            }
        if path == "/api/v1/futures/balance":
            return [{"asset": "USDT", "available": "100"}]
        if path == "/api/v1/futures/accountLeverage":
            return [{"symbolId": "BTC-SWAP-USDT", "leverage": "5", "marginType": "CROSS"}]
        if path == "/api/v1/futures/positions":
            return [{"symbol": "BTC-SWAP-USDT", "side": "LONG", "positionAmt": "2"}]
        raise AssertionError("unexpected path: " + path)

    result = ToobitExchangeAdapter(
        transport=transport,
        api_key="test-key",
        secret_key="test-secret",
    ).futures_account_state("BTC")

    assert result.allowed is True
    assert result.data["position_state_known"] is True
    assert result.data["margin_state_known"] is True
    assert result.data["margin_type"] == "CROSS"
    assert result.data["positions"] == [
        {"symbol": "BTC-SWAP-USDT", "side": "LONG", "positionAmt": "2"}
    ]
    assert "position_conflict" not in result.data


def test_futures_account_state_blocks_without_provider_native_margin_type():
    def transport(*, method, path, params, headers, base_url):
        if path == "/api/v1/exchangeInfo":
            return {
                "symbols": [],
                "contracts": [
                    {
                        "symbol": "BTC-SWAP-USDT",
                        "status": "TRADING",
                        "underlying": "BTC",
                        "contractMultiplier": "0.001",
                        "filters": [],
                    }
                ],
            }
        if path == "/api/v1/futures/balance":
            return [{"asset": "USDT", "available": "100"}]
        if path == "/api/v1/futures/accountLeverage":
            return [{"symbolId": "BTC-SWAP-USDT", "leverage": "5"}]
        if path == "/api/v1/futures/positions":
            raise AssertionError("position read must not follow unknown margin state")
        raise AssertionError("unexpected path: " + path)

    result = ToobitExchangeAdapter(
        transport=transport,
        api_key="test-key",
        secret_key="test-secret",
    ).futures_account_state("BTC")

    assert result.allowed is False
    assert result.reason == "TOOBIT_FUTURES_MARGIN_STATE_UNAVAILABLE"


def test_futures_instrument_resolution_uses_authoritative_settlement_metadata():
    def transport(*, method, path, params, headers, base_url):
        assert path == "/api/v1/exchangeInfo"
        return {
            "symbols": [],
            "contracts": [
                {
                    "symbol": "BTC-SWAP-USDT",
                    "status": "TRADING",
                    "underlying": "BTC",
                    "marginToken": "USDT",
                    "quoteAsset": "USDT",
                    "filters": [],
                },
                {
                    "symbol": "BTC-SWAP-USDC",
                    "status": "TRADING",
                    "underlying": "BTC",
                    "marginToken": "USDC",
                    "quoteAsset": "USDC",
                    "filters": [],
                },
            ],
        }

    specification = ExecutionInstrumentSpecification(
        asset="BTC",
        venue="FUTURES",
        settlement_asset="USDT",
        instrument_type="PERPETUAL",
        selection_source="EXECUTION_POLICY",
        policy_version="v0.1",
    )

    result = ToobitExchangeAdapter(
        transport=transport,
    ).resolve_futures_instrument(specification)

    assert result.allowed is True
    assert result.data["symbol"] == "BTC-SWAP-USDT"


def test_futures_instrument_resolution_blocks_ambiguous_same_settlement_contracts():
    def transport(*, method, path, params, headers, base_url):
        return {
            "symbols": [],
            "contracts": [
                {
                    "symbol": "BTC-SWAP-USDT-A",
                    "status": "TRADING",
                    "underlying": "BTC",
                    "marginToken": "USDT",
                    "quoteAsset": "USDT",
                },
                {
                    "symbol": "BTC-SWAP-USDT-B",
                    "status": "TRADING",
                    "underlying": "BTC",
                    "marginToken": "USDT",
                    "quoteAsset": "USDT",
                },
            ],
        }

    specification = ExecutionInstrumentSpecification(
        asset="BTC",
        venue="FUTURES",
        settlement_asset="USDT",
        instrument_type="PERPETUAL",
        selection_source="EXECUTION_POLICY",
        policy_version="v0.1",
    )

    result = ToobitExchangeAdapter(
        transport=transport,
    ).resolve_futures_instrument(specification)

    assert result.allowed is False
    assert result.reason == "AUTHORITATIVE_PROVIDER_INSTRUMENT_AMBIGUOUS"



def test_discover_tradable_assets_is_dynamic_for_spot_and_futures():
    def transport(*, method, path, params, headers, base_url):
        assert path == "/api/v1/exchangeInfo"
        return {
            "symbols": [
                {"symbol": "ETHUSDT", "status": "TRADING", "baseAsset": "ETH", "quoteAsset": "USDT"},
                {"symbol": "SOLUSDT", "status": "TRADING", "baseAsset": "SOL", "quoteAsset": "USDT"},
                {"symbol": "BTCUSDT", "status": "BREAK", "baseAsset": "BTC", "quoteAsset": "USDT"},
                {"symbol": "XRPUSDC", "status": "TRADING", "baseAsset": "XRP", "quoteAsset": "USDC"},
            ],
            "contracts": [
                {"symbol": "ETH-SWAP-USDT", "status": "TRADING", "underlying": "ETH"},
                {"symbol": "SOL-SWAP-USDT", "status": "TRADING", "underlying": "SOL"},
                {"symbol": "BTC-SWAP-USDT", "status": "BREAK", "underlying": "BTC"},
                {"symbol": "XRP-SWAP-USDC", "status": "TRADING", "underlying": "XRP"},
            ],
        }
    adapter = ToobitExchangeAdapter(transport=transport)
    spot = adapter.discover_tradable_assets(venue="SPOT")
    futures = adapter.discover_tradable_assets(venue="FUTURES")
    assert spot.allowed is True
    assert spot.data["assets"] == ["ETH", "SOL"]
    assert futures.allowed is True
    assert futures.data["assets"] == ["ETH", "SOL", "XRP"]


def test_discover_tradable_assets_rejects_invalid_venue():
    result = ToobitExchangeAdapter(transport=lambda **_: {}).discover_tradable_assets(venue="OPTIONS")
    assert result.allowed is False
    assert result.reason == "EXECUTION_INSTRUMENT_VENUE_INVALID"



def test_toobit_conforms_to_replaceable_exchange_adapter_contract():
    from exchange_execution_adapter_contract_v0_1 import (
        ExchangeExecutionAdapter,
        validate_adapter_contract,
    )
    adapter = ToobitExchangeAdapter(transport=lambda **_: {})
    assert isinstance(adapter, ExchangeExecutionAdapter)
    assert validate_adapter_contract(adapter) == (True, "VALID")
    assert adapter.capabilities().order_submission is True
    assert adapter.capabilities().order_cancellation is False


def _canonical_spot_request():
    from exchange_execution_contract import build_order_request
    return build_order_request(
        asset="BTC", direction="LONG", order_type="MARKET",
        risk={"position_quantity": "0.001"},
        entry_price=None, reference_price="50000",
        intent_id="intent-test-001", snapshot_id="snapshot-test-001",
        timestamp="2026-10-10T00:00:00Z", decision_id="decision-test-001",
    )


def test_futures_base_quantity_converts_to_contracts_using_provider_multiplier():
    from exchange_execution_contract import build_order_request

    def transport(*, method, path, params, headers, base_url):
        assert method == "GET"
        assert path == "/api/v1/exchangeInfo"
        return {
            "symbols": [],
            "contracts": [{
                "symbol": "BTC-SWAP-USDT",
                "status": "TRADING",
                "underlying": "BTC",
                "marginToken": "USDT",
                "quoteAsset": "USDT",
                "contractMultiplier": "0.001",
                "filters": [{
                    "filterType": "LOT_SIZE",
                    "minQty": "1",
                    "maxQty": "1000",
                    "stepSize": "1",
                }],
            }],
        }

    request = build_order_request(
        asset="BTC", direction="LONG", order_type="MARKET",
        risk={"position_quantity": "0.003"},
        entry_price=None, reference_price="50000",
        intent_id="futures-intent-001", snapshot_id="birth-BTC-001",
        timestamp="2026-10-10T00:00:00Z", decision_id="birth-decision-001",
    )
    specification = ExecutionInstrumentSpecification(
        asset="BTC", venue="FUTURES", settlement_asset="USDT",
        instrument_type="PERPETUAL", selection_source="EXECUTION_POLICY",
        policy_version="v0.1",
    )
    result = ToobitExchangeAdapter(transport=transport).prepare_order(
        request, venue="FUTURES", execution_instrument=specification,
    )
    assert result.ready is True
    # Toobit futures quantity is contracts: 0.003 BTC / 0.001 BTC per contract = 3.
    assert result.request["quantity"] == "3"
    assert result.request["symbol"] == "BTC-SWAP-USDT"
    assert result.request["side"] == "BUY_OPEN"
    assert result.request["type"] == "LIMIT"
    assert result.request["priceType"] == "MARKET"


def test_spot_market_buy_validates_base_lot_and_sends_quote_amount():
    def transport(*, method, path, params, headers, base_url):
        assert method == "GET"
        assert path == "/api/v1/exchangeInfo"
        return {
            "symbols": [{
                "symbol": "BTCUSDT", "status": "TRADING",
                "baseAsset": "BTC", "quoteAsset": "USDT",
                "filters": [{
                    "filterType": "LOT_SIZE", "minQty": "0.0001",
                    "maxQty": "0.01", "stepSize": "0.0001",
                }],
            }],
            "contracts": [],
        }

    adapter = ToobitExchangeAdapter(transport=transport)
    specification = ExecutionInstrumentSpecification(
        asset="BTC", venue="SPOT", settlement_asset="USDT",
        instrument_type=None, selection_source="EXECUTION_POLICY",
        policy_version="v0.1",
    )
    result = adapter.prepare_order(
        _canonical_spot_request(), venue="SPOT",
        execution_instrument=specification,
    )
    assert result.ready is True
    # Canonical quantity is 0.001 BTC; Toobit Spot MARKET BUY takes 50 USDT.
    assert result.request["quantity"] == "50"
    assert result.request["symbol"] == "BTCUSDT"


def test_submission_stays_closed_and_never_calls_transport(monkeypatch):
    import exchange_execution_contract as contract
    from exchange_execution_adapter_contract_v0_1 import AdapterOrderPreparation

    monkeypatch.setattr(contract, "EXECUTION_ENABLED", False)
    monkeypatch.setattr(contract, "ORDER_SUBMISSION_ENABLED", True)
    monkeypatch.setattr(contract, "EXCHANGE_WRITE_ENABLED", True)
    calls = []
    adapter = ToobitExchangeAdapter(transport=lambda **kwargs: calls.append(kwargs))
    prep = AdapterOrderPreparation(
        ready=True, reason="READY", adapter_name="TOOBIT", venue="SPOT",
        request={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET",
                 "newClientOrderId": "intent-test-001", "quantity": "50"},
    )
    result = adapter.submit_prepared_order(prep, canonical_request=_canonical_spot_request())
    assert result.accepted is False
    assert result.error_code == "EXECUTION_WRITE_GATES_CLOSED"
    assert calls == []


def test_submission_reconciles_provider_confirmed_fill_when_gates_explicitly_open(monkeypatch):
    import exchange_execution_contract as contract
    from exchange_execution_adapter_contract_v0_1 import AdapterOrderPreparation

    monkeypatch.setattr(contract, "EXECUTION_ENABLED", True)
    monkeypatch.setattr(contract, "ORDER_SUBMISSION_ENABLED", True)
    monkeypatch.setattr(contract, "EXCHANGE_WRITE_ENABLED", True)
    calls = []

    def transport(*, method, path, params, headers, base_url):
        calls.append((method, path, params, headers))
        assert method == "POST"
        assert path == "/api/v1/spot/order"
        assert params["newClientOrderId"] == "intent-test-001"
        assert params["signature"]
        assert headers["X-BB-APIKEY"] == "test-key"
        return {
            "symbol": "BTCUSDT", "clientOrderId": "intent-test-001",
            "orderId": "provider-order-001", "status": "FILLED",
            "executedQty": "0.001", "price": "50000",
            "transactTime": "1791596700000",
        }

    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    )
    prep = AdapterOrderPreparation(
        ready=True, reason="READY", adapter_name="TOOBIT", venue="SPOT",
        request={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET",
                 "newClientOrderId": "intent-test-001", "quantity": "50"},
    )
    result = adapter.submit_prepared_order(prep, canonical_request=_canonical_spot_request())
    assert len(calls) == 1
    assert result.accepted is True
    assert result.exchange_order_id == "provider-order-001"
    assert result.fill_outcome == "FILLED"
    assert result.executed_quantity == "0.001"
    assert result.executed_price == "50000"
    assert result.decision_id == "decision-test-001"


def test_submission_ambiguous_transport_failure_is_unknown_without_retry(monkeypatch):
    import exchange_execution_contract as contract
    from exchange_execution_adapter_contract_v0_1 import AdapterOrderPreparation

    monkeypatch.setattr(contract, "EXECUTION_ENABLED", True)
    monkeypatch.setattr(contract, "ORDER_SUBMISSION_ENABLED", True)
    monkeypatch.setattr(contract, "EXCHANGE_WRITE_ENABLED", True)
    calls = []

    def transport(**kwargs):
        calls.append(kwargs)
        if kwargs["method"] == "POST":
            raise TimeoutError("timeout after send")
        raise TimeoutError("reconciliation temporarily unavailable")

    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    )
    prep = AdapterOrderPreparation(
        ready=True, reason="READY", adapter_name="TOOBIT", venue="SPOT",
        request={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET",
                 "newClientOrderId": "intent-test-001", "quantity": "50"},
    )
    result = adapter.submit_prepared_order(prep, canonical_request=_canonical_spot_request())
    assert [call["method"] for call in calls] == ["POST", "GET"]
    assert result.status == "UNKNOWN"
    assert result.fill_outcome == "UNKNOWN"
    assert result.fill_reason_code == "RECONCILIATION_REQUIRED"
    assert "reconciliation=ORDER_RECONCILIATION_FAILED" in result.error_message


def test_submission_timeout_reconciles_matching_provider_order_without_retry(monkeypatch):
    import exchange_execution_contract as contract
    from exchange_execution_adapter_contract_v0_1 import AdapterOrderPreparation

    monkeypatch.setattr(contract, "EXECUTION_ENABLED", True)
    monkeypatch.setattr(contract, "ORDER_SUBMISSION_ENABLED", True)
    monkeypatch.setattr(contract, "EXCHANGE_WRITE_ENABLED", True)
    calls = []

    def transport(*, method, path, params, headers, base_url):
        calls.append((method, path, params))
        if method == "POST":
            raise TimeoutError("response lost after accepted request")
        assert method == "GET"
        assert path == "/api/v1/spot/order"
        assert params["origClientOrderId"] == "intent-test-001"
        return {
            "symbol": "BTCUSDT", "clientOrderId": "intent-test-001",
            "orderId": "provider-order-reconciled", "status": "FILLED",
            "executedQty": "0.001", "avgPrice": "0", "price": "50000",
            "transactTime": "1791596700000",
        }

    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    )
    prep = AdapterOrderPreparation(
        ready=True, reason="READY", adapter_name="TOOBIT", venue="SPOT",
        request={"symbol": "BTCUSDT", "side": "BUY", "type": "MARKET",
                 "newClientOrderId": "intent-test-001", "quantity": "50"},
    )
    result = adapter.submit_prepared_order(prep, canonical_request=_canonical_spot_request())
    assert [call[0] for call in calls] == ["POST", "GET"]
    assert result.status == "FILLED"
    assert result.exchange_order_id == "provider-order-reconciled"
    assert result.fill_outcome == "FILLED"
    assert result.executed_quantity == "0.001"
    assert result.executed_price == "50000"


def test_order_reconciliation_reads_by_client_id_without_submission():
    calls = []

    def transport(*, method, path, params, headers, base_url):
        calls.append((method, path, params))
        assert method == "GET"
        assert path == "/api/v1/futures/order"
        assert params["origClientOrderId"] == "intent-test-001"
        assert params["symbol"] == "BTC-SWAP-USDT"
        assert params["category"] == "USDT"
        return {
            "symbol": "BTC-SWAP-USDT", "clientOrderId": "intent-test-001",
            "orderId": "provider-order-001", "status": "FILLED",
            "executedQty": "5", "avgPrice": "50000",
        }

    adapter = ToobitExchangeAdapter(
        transport=transport, api_key="test-key", secret_key="test-secret"
    )
    result = adapter.query_order_by_client_id(
        venue="FUTURES", symbol="BTC-SWAP-USDT",
        client_order_id="intent-test-001",
    )
    assert result.allowed is True
    assert result.reason == "PROVIDER_ORDER_STATE_CONFIRMED"
    assert result.data["status"] == "FILLED"
    assert len(calls) == 1


def test_futures_duplicate_check_fails_closed_on_malformed_order_collection():
    def transport(*, method, path, params, headers, base_url):
        if path == "/api/v1/exchangeInfo":
            return {
                "symbols": [],
                "contracts": [
                    {
                        "symbol": "BTC-SWAP-USDT",
                        "status": "TRADING",
                        "underlying": "BTC",
                        "contractMultiplier": "0.001",
                        "marginToken": "USDT",
                    }
                ],
            }
        if path == "/api/v2/futures/open-orders":
            return {"unexpected": "not-a-list"}
        if path == "/api/v1/futures/historyOrders":
            return []
        raise AssertionError("unexpected path: " + path)

    result = ToobitExchangeAdapter(
        transport=transport,
        api_key="test-key",
        secret_key="test-secret",
    ).futures_duplicate_check("BTC")

    assert result.allowed is False
    assert result.reason == "TOOBIT_FUTURES_ORDER_STATE_INVALID"


def test_futures_duplicate_check_fails_closed_on_order_without_client_identity():
    def transport(*, method, path, params, headers, base_url):
        if path == "/api/v1/exchangeInfo":
            return {
                "symbols": [],
                "contracts": [
                    {
                        "symbol": "BTC-SWAP-USDT",
                        "status": "TRADING",
                        "underlying": "BTC",
                        "contractMultiplier": "0.001",
                        "marginToken": "USDT",
                    }
                ],
            }
        if path == "/api/v2/futures/open-orders":
            return [{"orderId": "exchange-order-without-client-id"}]
        if path == "/api/v1/futures/historyOrders":
            return []
        raise AssertionError("unexpected path: " + path)

    result = ToobitExchangeAdapter(
        transport=transport,
        api_key="test-key",
        secret_key="test-secret",
    ).futures_duplicate_check("BTC")

    assert result.allowed is False
    assert result.reason == "TOOBIT_FUTURES_ORDER_CLIENT_ID_UNAVAILABLE"


def test_spot_preparation_fails_closed_when_authoritative_lot_filter_is_missing():
    def transport(*, method, path, params, headers, base_url):
        return {
            "symbols": [{
                "symbol": "BTCUSDT", "status": "TRADING",
                "baseAsset": "BTC", "quoteAsset": "USDT", "filters": [],
            }],
            "contracts": [],
        }

    specification = ExecutionInstrumentSpecification(
        asset="BTC", venue="SPOT", settlement_asset="USDT",
        instrument_type=None, selection_source="EXECUTION_POLICY",
        policy_version="v0.1",
    )
    result = ToobitExchangeAdapter(transport=transport).prepare_order(
        _canonical_spot_request(), venue="SPOT",
        execution_instrument=specification,
    )
    assert result.ready is False
    assert result.reason == "SPOT_LOT_SIZE_UNAVAILABLE"


def test_futures_preparation_fails_closed_when_authoritative_lot_filter_is_missing():
    def transport(*, method, path, params, headers, base_url):
        return {
            "symbols": [],
            "contracts": [{
                "symbol": "BTC-SWAP-USDT", "status": "TRADING",
                "underlying": "BTC", "marginToken": "USDT",
                "contractMultiplier": "0.001", "filters": [],
            }],
        }

    specification = ExecutionInstrumentSpecification(
        asset="BTC", venue="FUTURES", settlement_asset="USDT",
        instrument_type="PERPETUAL", selection_source="EXECUTION_POLICY",
        policy_version="v0.1",
    )
    from dataclasses import replace

    result = ToobitExchangeAdapter(transport=transport).prepare_order(
        replace(_canonical_spot_request(), quantity=0.003), venue="FUTURES",
        execution_instrument=specification,
    )
    assert result.ready is False
    assert result.reason == "FUTURES_LOT_SIZE_UNAVAILABLE"
