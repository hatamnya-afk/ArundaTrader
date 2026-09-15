from __future__ import annotations

from dataclasses import dataclass

import pytest

from portfolio_observation_v0_1 import build_portfolio_observation
from account_balance_observation_v0_1 import (
    AccountBalanceObservation,
    AccountObservation,
    BalanceObservation,
)
from toobit_position_reader_v0_1 import (
    POSITION_ENDPOINT,
    build_toobit_position_reader,
)


@dataclass
class Result:
    allowed: bool
    data: dict
    status: str = "PASS"
    reason: str = ""


class FakeAdapter:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def _signed_get(self, endpoint, params=None):
        self.calls.append((endpoint, params))
        return self.result


def account_balance():
    account = AccountObservation(
        account_id="acct-1",
        account_type="FUTURES",
        environment="PRODUCTION",
        source_id="TOOBIT",
        source_type="CEX_PRIVATE_API",
        source_timestamp="2026-09-16T00:00:00+00:00",
        retrieved_at="2026-09-16T00:00:01+00:00",
        status="PASS",
    )
    return AccountBalanceObservation(account=account, balances=tuple())


def valid_payload():
    return {
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
            },
            {
                "symbol": "ETH-SWAP-USDT",
                "side": "SHORT",
                "avgPrice": "2000",
                "position": "3",
                "markPrice": "1900",
                "positionValue": "5700",
                "unrealizedPnL": "300",
                "realizedPnL": "5",
            },
        ],
        "source_id": "TOOBIT",
        "source_type": "CEX_PRIVATE_API",
        "source_timestamp": "2026-09-16T00:00:00+00:00",
        "retrieved_at": "2026-09-16T00:00:01+00:00",
    }


def test_reader_uses_real_position_endpoint_without_write():
    adapter = FakeAdapter(Result(True, valid_payload()))
    reader = build_toobit_position_reader(adapter)
    result = reader()
    assert result.allowed is True
    assert adapter.calls == [(POSITION_ENDPOINT, {})]


def test_reader_maps_dynamic_positions():
    adapter = FakeAdapter(Result(True, valid_payload()))
    result = build_toobit_position_reader(adapter)()
    rows = result.data["positions"]
    assert len(rows) == 2
    assert rows[0]["symbol"] == "BTC-SWAP-USDT"
    assert rows[0]["side"] == "LONG"
    assert rows[0]["quantity"] == "2"
    assert rows[0]["notional"] == "50000"


def test_reader_allows_empty_dynamic_position_set():
    payload = valid_payload()
    payload["positions"] = []
    result = build_toobit_position_reader(FakeAdapter(Result(True, payload)))()
    assert result.allowed is True
    assert result.data["positions"] == []


def test_reader_fail_closed_when_adapter_denies():
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(False, {})))()


@pytest.mark.parametrize("field", ["symbol", "side", "avgPrice", "position", "markPrice"])
def test_reader_fail_closed_missing_required_position_field(field):
    payload = valid_payload()
    del payload["positions"][0][field]
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(True, payload)))()


def test_reader_fail_closed_invalid_numeric():
    payload = valid_payload()
    payload["positions"][0]["positionValue"] = "NaN"
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(True, payload)))()


def test_reader_fail_closed_invalid_provenance():
    payload = valid_payload()
    payload["source_type"] = ""
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(True, payload)))()


def test_reader_preserves_provenance():
    result = build_toobit_position_reader(FakeAdapter(Result(True, valid_payload())))()
    row = result.data["positions"][0]
    assert row["source_id"] == "TOOBIT"
    assert row["source_type"] == "CEX_PRIVATE_API"
    assert row["source_timestamp"] == "2026-09-16T00:00:00+00:00"


def test_portfolio_observation_normalizes_canonical_positions_and_exposure():
    adapter = FakeAdapter(Result(True, valid_payload()))
    portfolio = build_portfolio_observation(
        account_balance(),
        position_reader=build_toobit_position_reader(adapter),
    )
    assert portfolio.positions is not None
    assert portfolio.positions[0].symbol == "BTC-SWAP-USDT"
    assert portfolio.total_exposure == 55700.0
    assert portfolio.exposure_source == "POSITION_NOTIONAL"


def test_portfolio_observation_remains_capital_unavailable():
    portfolio = build_portfolio_observation(
        account_balance(),
        position_reader=build_toobit_position_reader(FakeAdapter(Result(True, valid_payload()))),
    )
    assert not hasattr(portfolio, "usable_capital")
    assert not hasattr(portfolio, "risk_budget")
    assert not hasattr(portfolio, "position_size")


def test_no_fixed_asset_dependency():
    payload = valid_payload()
    payload["positions"] = [payload["positions"][0]]
    portfolio = build_portfolio_observation(
        account_balance(),
        position_reader=build_toobit_position_reader(FakeAdapter(Result(True, payload))),
    )
    assert len(portfolio.positions) == 1


def test_exposure_unavailable_if_notional_missing():
    payload = valid_payload()
    payload["positions"][0]["positionValue"] = None
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(True, payload)))()


def test_reader_rejects_non_mapping_payload():
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(True, {"positions": "bad"})))()


def test_reader_does_not_call_write_methods():
    adapter = FakeAdapter(Result(True, valid_payload()))
    build_toobit_position_reader(adapter)()
    assert all(call[0] == POSITION_ENDPOINT for call in adapter.calls)
