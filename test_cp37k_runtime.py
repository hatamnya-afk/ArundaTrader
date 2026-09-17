from account_balance_observation_v0_1 import AccountBalanceObservation, AccountObservation
from portfolio_observation_v0_1 import build_portfolio_observation
from toobit_position_reader_v0_1 import build_toobit_position_reader, POSITION_ENDPOINT
from toobit_trading_adapter import ToobitTradingAdapter


def _account_balance():
    return AccountBalanceObservation(
        account=AccountObservation(
            account_id="REAL-ACCOUNT",
            account_type="CEX",
            environment="PRODUCTION",
            source_id="TOOBIT",
            source_type="CEX_PRIVATE_API",
            source_timestamp="2026-09-16T00:00:00+00:00",
            retrieved_at="2026-09-16T00:00:01+00:00",
            status="PASS",
        ),
        balances=(),
    )


def _result(positions):
    import requests

    response = requests.Response()
    response.status_code = 200
    response._content = __import__("json").dumps(
        {"positions": positions}
    ).encode("utf-8")
    response.headers["Content-Type"] = "application/json"
    response.url = "https://api.toobit.com/api/v1/futures/positions"
    return response


def test_cp37k_real_position_chain_contract():
    adapter = ToobitTradingAdapter(
        api_key="TEST_ONLY",
        api_secret="TEST_ONLY",
    )

    calls = []

    def fake_signed_get(endpoint, params=None):
        calls.append((endpoint, params))
        return _result(
            [
                {
                    "symbol": "BTC-SWAP-USDT",
                    "side": "LONG",
                    "avgPrice": "24000",
                    "position": "2",
                    "markPrice": "25000",
                    "positionValue": "50000",
                    "unrealizedPnL": "2000",
                    "realizedPnL": "10",
                }
            ]
        )

    adapter._signed_get = fake_signed_get
    reader = build_toobit_position_reader(adapter)

    assert callable(reader)
    assert POSITION_ENDPOINT == "/api/v1/futures/positions"

    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=reader,
        portfolio_id="CP37-K",
    )

    assert calls == [(POSITION_ENDPOINT, {})]
    assert len(observation.positions) == 1
    assert observation.positions[0].symbol == "BTC-SWAP-USDT"
    assert observation.positions[0].side == "LONG"
    assert observation.positions[0].quantity == "2"
    assert observation.positions[0].entry_price == "24000"
    assert observation.positions[0].mark_price == "25000"
    assert observation.positions[0].notional == "50000"
    assert observation.total_exposure == 50000.0
    assert observation.exposure_source == "POSITION_NOTIONAL"
    assert observation.source_status == "AVAILABLE"
    assert observation.portfolio_id == "CP37-K"


def test_cp37k_empty_position_is_not_failure():
    adapter = ToobitTradingAdapter(
        api_key="TEST_ONLY",
        api_secret="TEST_ONLY",
    )

    def fake_signed_get(endpoint, params=None):
        assert endpoint == POSITION_ENDPOINT
        assert params == {}
        return _result([])

    adapter._signed_get = fake_signed_get
    reader = build_toobit_position_reader(adapter)

    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=reader,
        portfolio_id="CP37-K",
    )

    assert observation.positions == ()
    assert observation.total_exposure is None
    assert observation.exposure_source is None
    assert "EXPOSURE_NOT_AVAILABLE" in observation.gaps


def test_cp37ka_raw_requests_response_contract():
    import requests

    adapter = ToobitTradingAdapter(api_key="TEST_ONLY", api_secret="TEST_ONLY")

    response = requests.Response()
    response.status_code = 200
    response._content = (
        b'{"positions":[{"symbol":"BTC-SWAP-USDT","side":"LONG",'
        b'"avgPrice":"24000","position":"2","markPrice":"25000",'
        b'"positionValue":"50000","unrealizedPnL":"2000","realizedPnL":"10"}]}'
    )
    response.headers["Content-Type"] = "application/json"
    response.url = "https://api.toobit.com/api/v1/futures/positions"

    def fake_signed_get(endpoint, params=None):
        assert endpoint == POSITION_ENDPOINT
        assert params == {}
        return response

    adapter._signed_get = fake_signed_get

    reader = build_toobit_position_reader(adapter)
    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=reader,
        portfolio_id="CP37-KA",
    )

    assert len(observation.positions) == 1
    assert observation.positions[0].symbol == "BTC-SWAP-USDT"
    assert observation.positions[0].quantity == "2"
    assert observation.total_exposure == 50000.0
