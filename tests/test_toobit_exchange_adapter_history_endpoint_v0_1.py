from __future__ import annotations

from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter


def test_futures_duplicate_check_uses_v2_open_and_history_read_routes():
    calls = []

    def transport(**kwargs):
        calls.append(kwargs)
        path = kwargs["path"]
        if path == "/api/v1/exchangeInfo":
            return {"code": 200, "data": {"contracts": [{
                "symbol": "BTC-SWAP-USDT",
                "underlying": "BTC",
                "status": "TRADING",
                "marginToken": "USDT",
            }]}}
        if path in {
            "/api/v2/futures/open-orders",
            "/api/v2/futures/history-orders",
        }:
            return {"code": 200, "data": []}
        raise AssertionError(f"Unexpected Toobit route: {path}")

    adapter = ToobitExchangeAdapter(
        transport=transport,
        api_key="test-key",
        secret_key="test-secret",
    )

    result = adapter.futures_duplicate_check("BTC")

    assert result.allowed is True
    assert result.reason == "OK"
    assert [call["path"] for call in calls] == [
        "/api/v1/exchangeInfo",
        "/api/v2/futures/open-orders",
        "/api/v2/futures/history-orders",
    ]
    assert all(call["method"] == "GET" for call in calls)
    assert all(call["path"] != "/api/v1/futures/historyOrders" for call in calls)
