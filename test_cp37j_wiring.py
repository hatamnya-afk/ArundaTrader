from account_balance_observation_v0_1 import (
    AccountBalanceObservation,
    AccountObservation,
)
from toobit_position_reader_v0_1 import (
    POSITION_ENDPOINT,
)
from toobit_trading_adapter import (
    ToobitTradingAdapter,
    build_toobit_portfolio_observation,
)


def _account_balance() -> AccountBalanceObservation:
    return AccountBalanceObservation(
        account=AccountObservation(
            account_id="TEST-ACCOUNT",
            account_type="CEX",
            environment="TEST",
            source_id="TOOBIT",
            source_type="CEX_PRIVATE_API",
            source_timestamp="2026-09-16T00:00:00+00:00",
            retrieved_at="2026-09-16T00:00:01+00:00",
            status="PASS",
        ),
        balances=(),
    )


def test_cp37j_real_toobit_adapter_wiring_chain():
    adapter = ToobitTradingAdapter(
        api_key="TEST_ONLY",
        api_secret="TEST_ONLY",
    )

    calls = []

    def fake_signed_get(endpoint, params=None):
        calls.append((endpoint, params))
        return type(
            "Result",
            (),
            {
                "allowed": True,
                "status": "PASS",
                "reason": "",
                "data": {
                    "positions": [
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
                    ],
                    "source_id": "TOOBIT",
                    "source_type": "CEX_PRIVATE_API",
                    "source_timestamp": "2026-09-16T00:00:00+00:00",
                    "retrieved_at": "2026-09-16T00:00:01+00:00",
                },
            },
        )()

    adapter._signed_get = fake_signed_get

    observation = build_toobit_portfolio_observation(
        adapter,
        _account_balance(),
        portfolio_id="TEST-PORTFOLIO",
    )

    assert calls == [(POSITION_ENDPOINT, {})]

    assert len(observation.positions) == 1

    position = observation.positions[0]

    assert position.symbol == "BTC-SWAP-USDT"
    assert position.side == "LONG"
    assert position.quantity == "2"
    assert position.entry_price == "24000"
    assert position.mark_price == "25000"
    assert position.notional == "50000"

    assert position.source_id == "TOOBIT"
    assert position.source_type == "CEX_PRIVATE_API"

    assert observation.total_exposure == 50000.0
    assert observation.exposure_source == "POSITION_NOTIONAL"


def test_cp37j_uses_same_adapter_instance_for_position_reader():
    adapter = ToobitTradingAdapter(
        api_key="TEST_ONLY",
        api_secret="TEST_ONLY",
    )

    seen = []

    def fake_signed_get(endpoint, params=None):
        seen.append(adapter)
        return type(
            "Result",
            (),
            {
                "allowed": True,
                "status": "PASS",
                "reason": "",
                "data": {
                    "positions": [],
                    "source_id": "TOOBIT",
                    "source_type": "CEX_PRIVATE_API",
                    "source_timestamp": "2026-09-16T00:00:00+00:00",
                    "retrieved_at": "2026-09-16T00:00:01+00:00",
                },
            },
        )()

    adapter._signed_get = fake_signed_get

    observation = build_toobit_portfolio_observation(
        adapter,
        _account_balance(),
        portfolio_id="TEST-PORTFOLIO",
    )

    assert seen == [adapter]
    assert observation.positions == ()
    assert observation.total_exposure is None