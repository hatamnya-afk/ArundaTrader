"""CP46-F Toobit Futures read-boundary tests."""

from toobit_trading_adapter import ToobitTradingAdapter


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def _constraints_result():
    from toobit_trading_adapter import AdapterResult
    return AdapterResult(
        status="PASS",
        allowed=True,
        operation="futures_trading_constraints",
        reason="ok",
        data={"symbol": "BTC-SWAP-USDT"},
    )


def test_futures_duplicate_check_uses_v2_data_wrapped_reads(monkeypatch):
    adapter = ToobitTradingAdapter(api_key="k", api_secret="s")
    monkeypatch.setattr(
        adapter,
        "futures_trading_constraints",
        lambda asset: _constraints_result(),
    )

    responses = iter([
        _Response(200, {"code": 200, "msg": "success", "data": [
            {"clientOrderId": "OPEN-1", "symbol": "BTC-SWAP-USDT"},
        ]}),
        _Response(200, {"code": 200, "msg": "success", "data": [
            {"clientOrderId": "RECENT-1", "symbol": "BTC-SWAP-USDT"},
        ]}),
    ])
    calls = []

    def signed_get(endpoint, params=None):
        calls.append((endpoint, params))
        return next(responses)

    monkeypatch.setattr(adapter, "_signed_get", signed_get)
    result = adapter.futures_duplicate_check("BTC")

    assert result.allowed is True
    assert result.data["open_order_client_ids"] == frozenset({"OPEN-1"})
    assert result.data["recent_order_client_ids"] == frozenset({"RECENT-1"})
    assert calls[0][0] == "/api/v2/futures/open-orders"
    assert calls[1][0] == "/api/v2/futures/history-orders"
    assert all(call[1]["category"] == "USDT" for call in calls)


def test_futures_duplicate_check_fail_closes_on_invalid_v2_data(monkeypatch):
    adapter = ToobitTradingAdapter(api_key="k", api_secret="s")
    monkeypatch.setattr(
        adapter,
        "futures_trading_constraints",
        lambda asset: _constraints_result(),
    )
    monkeypatch.setattr(
        adapter,
        "_signed_get",
        lambda endpoint, params=None: _Response(200, {"code": 200, "data": {}}),
    )

    result = adapter.futures_duplicate_check("BTC")
    assert result.allowed is False
    assert result.status == "ERROR"
