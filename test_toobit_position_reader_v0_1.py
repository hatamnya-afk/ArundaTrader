from dataclasses import dataclass

import pytest

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


def payload():
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


def test_uses_only_read_position_endpoint():
    adapter = FakeAdapter(Result(True, payload()))
    result = build_toobit_position_reader(adapter)()
    assert result.allowed is True
    assert adapter.calls == [(POSITION_ENDPOINT, {})]


def test_maps_dynamic_positions_and_provenance():
    result = build_toobit_position_reader(FakeAdapter(Result(True, payload())))()
    rows = result.data["positions"]
    assert len(rows) == 2
    assert rows[0]["symbol"] == "BTC-SWAP-USDT"
    assert rows[0]["side"] == "LONG"
    assert rows[0]["quantity"] == "2"
    assert rows[0]["entry_price"] == "24000"
    assert rows[0]["mark_price"] == "25000"
    assert rows[0]["notional"] == "50000"
    assert rows[0]["source_id"] == "TOOBIT"
    assert rows[0]["source_type"] == "CEX_PRIVATE_API"


def test_empty_position_set_is_valid_and_dynamic():
    data = payload()
    data["positions"] = []
    result = build_toobit_position_reader(FakeAdapter(Result(True, data)))()
    assert result.allowed is True
    assert result.data["positions"] == []


@pytest.mark.parametrize("field", ["symbol", "side", "avgPrice", "position", "markPrice"])
def test_missing_required_field_fails_closed(field):
    data = payload()
    del data["positions"][0][field]
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(True, data)))()


def test_invalid_numeric_fails_closed():
    data = payload()
    data["positions"][0]["position"] = "NaN"
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(True, data)))()


def test_invalid_provenance_fails_closed():
    data = payload()
    data["source_type"] = ""
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(True, data)))()


def test_adapter_denial_fails_closed():
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(False, {})))()


def test_missing_notional_remains_unavailable_not_inferred():
    data = payload()
    data["positions"][0]["positionValue"] = None
    result = build_toobit_position_reader(FakeAdapter(Result(True, data)))()
    assert result.data["positions"][0]["notional"] is None


def test_non_list_positions_fail_closed():
    data = payload()
    data["positions"] = "invalid"
    with pytest.raises(RuntimeError):
        build_toobit_position_reader(FakeAdapter(Result(True, data)))()
