"""Focused tests for the read-only Toobit exchange adapter."""

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
    assert result.reason == "EXECUTION_DISABLED_ORDER_SUBMISSION_NOT_IMPLEMENTED"


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
    assert adapter.capabilities().order_submission is False
    assert adapter.capabilities().order_cancellation is False
