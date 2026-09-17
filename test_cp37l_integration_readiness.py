from pathlib import Path
import json
import requests
import pytest

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


def _response(payload, status_code=200):
    response = requests.Response()
    response.status_code = status_code
    response._content = json.dumps(payload).encode("utf-8")
    response.headers["Content-Type"] = "application/json"
    response.url = "https://api.toobit.com/api/v1/futures/positions"
    return response


def _position(symbol="BTC-SWAP-USDT", side="LONG", quantity="2", notional="50000"):
    return {
        "symbol": symbol,
        "side": side,
        "avgPrice": "24000",
        "position": quantity,
        "markPrice": "25000",
        "positionValue": notional,
        "unrealizedPnL": "2000",
        "realizedPnL": "10",
    }


def _reader_for(payload, calls=None):
    adapter = ToobitTradingAdapter(api_key="TEST_ONLY", api_secret="TEST_ONLY")

    def fake_signed_get(endpoint, params=None):
        if calls is not None:
            calls.append((endpoint, params))
        return _response(payload)

    adapter._signed_get = fake_signed_get
    return build_toobit_position_reader(adapter)


def test_cp37l_successful_real_response_chain():
    calls = []
    reader = _reader_for({"positions": [_position()]}, calls)

    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=reader,
        portfolio_id="CP37-L",
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


def test_cp37l_empty_valid_payload():
    reader = _reader_for({"positions": []})

    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=reader,
        portfolio_id="CP37-L",
    )

    assert observation.positions == ()
    assert observation.total_exposure is None
    assert observation.exposure_source is None
    assert "EXPOSURE_NOT_AVAILABLE" in observation.gaps


@pytest.mark.parametrize(
    "payload",
    [
        {"positions": "not-a-list"},
        {"unexpected": []},
        {"positions": [None]},
        {"positions": [{"symbol": "BTC-SWAP-USDT"}]},
        "invalid-top-level-payload",
    ],
)
def test_cp37l_malformed_payload_fails_closed(payload):
    reader = _reader_for(payload)

    with pytest.raises(RuntimeError):
        reader()


def test_cp37l_http_failure_fails_closed():
    adapter = ToobitTradingAdapter(api_key="TEST_ONLY", api_secret="TEST_ONLY")

    def fake_signed_get(endpoint, params=None):
        return _response({"error": "unauthorized"}, status_code=401)

    adapter._signed_get = fake_signed_get
    reader = build_toobit_position_reader(adapter)

    with pytest.raises(RuntimeError, match="HTTP 401"):
        reader()


def test_cp37l_provenance_failure_fails_closed():
    payload = {
        "positions": [_position()],
        "source_id": "TOOBIT",
        "source_type": "CEX_PRIVATE_API",
        "source_timestamp": None,
    }

    reader = _reader_for(payload)

    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=reader,
        portfolio_id="CP37-L",
    )

    assert observation.positions[0].source_id == "TOOBIT"
    assert observation.positions[0].source_type == "CEX_PRIVATE_API"
    assert observation.positions[0].source_timestamp is None


def test_cp37l_dynamic_positions_and_arbitrary_assets():
    payload = {
        "positions": [
            _position("ARBITRARY-AAA", "LONG", "3", "300"),
            _position("ARBITRARY-BBB", "SHORT", "4", "700"),
            _position("NON_LEGACY_ASSET", "LONG", "1", "125"),
        ]
    }

    reader = _reader_for(payload)
    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=reader,
        portfolio_id="CP37-L",
    )

    assert [p.symbol for p in observation.positions] == [
        "ARBITRARY-AAA",
        "ARBITRARY-BBB",
        "NON_LEGACY_ASSET",
    ]
    assert len(observation.positions) == 3
    assert observation.total_exposure == 1125.0


def test_cp37l_deterministic_output():
    payload = {
        "positions": [
            _position("AAA-1", "LONG", "2", "100"),
            _position("BBB-2", "SHORT", "5", "250"),
        ]
    }

    reader1 = _reader_for(payload)
    reader2 = _reader_for(payload)

    observation1 = build_portfolio_observation(
        _account_balance(),
        position_reader=reader1,
        portfolio_id="CP37-L",
    )
    observation2 = build_portfolio_observation(
        _account_balance(),
        position_reader=reader2,
        portfolio_id="CP37-L",
    )

    assert observation1 == observation2


def test_cp37l_no_capital_leakage():
    account = _account_balance()
    reader = _reader_for({"positions": [_position(notional="500")]})

    observation = build_portfolio_observation(
        account,
        position_reader=reader,
        portfolio_id="CP37-L",
    )

    assert observation.balances == ()
    assert observation.total_exposure == 500.0
    assert "TEST_CAPITAL" not in repr(observation)
    assert "PRODUCTION_CAPITAL" not in repr(observation)


def test_cp37l_no_side_effects():
    calls = []
    reader = _reader_for({"positions": [_position()]}, calls)

    observation = build_portfolio_observation(
        _account_balance(),
        position_reader=reader,
        portfolio_id="CP37-L",
    )

    assert len(calls) == 1
    assert calls[0] == (POSITION_ENDPOINT, {})
    assert observation.positions[0].symbol == "BTC-SWAP-USDT"


def test_cp37l_provider_neutral_portfolio_boundary():
    source = Path("portfolio_observation_v0_1.py").read_text(encoding="utf-8")

    assert "ToobitTradingAdapter" not in source
    assert "TOOBIT" not in source
    assert "requests" not in source
    assert "POSITION_ENDPOINT" not in source


def test_cp37l_fixed_15_safety():
    position_reader_source = Path(
        "toobit_position_reader_v0_1.py"
    ).read_text(encoding="utf-8")
    portfolio_source = Path(
        "portfolio_observation_v0_1.py"
    ).read_text(encoding="utf-8")

    assert "EXPECTED_ASSETS" not in position_reader_source
    assert "EXPECTED_ASSETS" not in portfolio_source
    assert "range(15)" not in position_reader_source
    assert "range(15)" not in portfolio_source


def test_cp37l_no_production_write_or_execution_path():
    sources = "\n".join(
        Path(name).read_text(encoding="utf-8")
        for name in (
            "toobit_position_reader_v0_1.py",
            "portfolio_observation_v0_1.py",
        )
    )

    forbidden = (
        "INSERT",
        "UPDATE",
        "DELETE",
        "commit(",
        "place_order",
        "cancel_order",
        "withdraw",
        "OrderIntent",
    )

    for token in forbidden:
        assert token not in sources
