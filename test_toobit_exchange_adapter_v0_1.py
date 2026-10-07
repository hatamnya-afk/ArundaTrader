"""Focused tests for the read-only Toobit exchange adapter."""

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
    result = ToobitExchangeAdapter().cancel_order()
    assert result.allowed is False
    assert result.reason == "EXECUTION_DISABLED_ORDER_CANCELLATION_NOT_IMPLEMENTED"
