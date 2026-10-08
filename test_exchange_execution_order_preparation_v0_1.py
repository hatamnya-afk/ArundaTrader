from exchange_execution_contract import CanonicalOrderRequest
from exchange_execution_order_preparation_v0_1 import prepare_order_for_adapter
from execution_instrument_policy_v0_1 import build_execution_instrument_specification
from toobit_exchange_adapter_v0_1 import ToobitExchangeAdapter


def _request(direction="LONG", quantity=1):
    return CanonicalOrderRequest(
        asset="BTC",
        direction=direction,
        order_type="MARKET",
        quantity=quantity,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=None,
        reference_price=100000,
        intent_id="intent-001",
        snapshot_id="snapshot-001",
        timestamp="2026-10-08T00:00:00+00:00",
        decision_id="decision-001",
    )


def _transport(*, method, path, params, headers, base_url):
    assert method == "GET"
    assert path == "/api/v1/exchangeInfo"
    return {
        "symbols": [
            {
                "symbol": "BTCUSDT",
                "baseAsset": "BTC",
                "quoteAsset": "USDT",
                "status": "TRADING",
                "filters": [],
            },
        ],
        "contracts": [
            {
                "symbol": "BTC-SWAP-USDT",
                "underlying": "BTC",
                "marginToken": "USDT",
                "status": "TRADING",
                "contractMultiplier": "0.001",
                "filters": [
                    {
                        "filterType": "LOT_SIZE",
                        "minQty": "1",
                        "maxQty": "1000000",
                        "stepSize": "1",
                    },
                ],
            },
        ],
    }


def test_toobit_prepare_futures_translates_base_quantity_to_contracts():
    adapter = ToobitExchangeAdapter(transport=_transport)
    spec = build_execution_instrument_specification(
        asset="BTC", venue="FUTURES"
    )
    prepared = prepare_order_for_adapter(
        request=_request("SHORT", quantity=0.005),
        adapter=adapter,
        venue="FUTURES",
        execution_instrument=spec,
    )
    assert prepared.ready is True
    assert prepared.reason == "READY"
    assert prepared.adapter_name == "TOOBIT"
    assert prepared.venue == "FUTURES"
    assert prepared.request["symbol"] == "BTC-SWAP-USDT"
    assert prepared.request["side"] == "SELL"
    assert prepared.request["positionSide"] == "SHORT"
    assert prepared.request["quantity"] == "5"
    assert prepared.request["category"] == "USDT"


def test_toobit_prepare_spot_market_buy_uses_quote_amount_translation():
    adapter = ToobitExchangeAdapter(transport=_transport)
    spec = build_execution_instrument_specification(
        asset="BTC", venue="SPOT"
    )
    prepared = prepare_order_for_adapter(
        request=_request("LONG", quantity=0.001),
        adapter=adapter,
        venue="SPOT",
        execution_instrument=spec,
    )
    assert prepared.ready is True
    assert prepared.request["symbol"] == "BTCUSDT"
    assert prepared.request["side"] == "BUY"
    assert prepared.request["type"] == "MARKET"
    assert prepared.request["quantity"] == "100"


def test_toobit_prepare_rejects_mismatched_instrument():
    adapter = ToobitExchangeAdapter(transport=_transport)
    spec = build_execution_instrument_specification(
        asset="BTC", venue="FUTURES"
    )
    prepared = prepare_order_for_adapter(
        request=_request("LONG"),
        adapter=adapter,
        venue="SPOT",
        execution_instrument=spec,
    )
    assert prepared.ready is False
    assert prepared.reason == "EXECUTION_INSTRUMENT_REQUEST_MISMATCH"
