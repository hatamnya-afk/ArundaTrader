from dataclasses import dataclass

from toobit_raw_position_observation_producer_v0_1 import (
    build_toobit_raw_position_observation,
)


@dataclass
class AdapterResult:
    allowed: bool
    reason: str
    data: dict | None = None


def test_preserves_raw_positions_but_blocks_portfolio_risk():
    rows = [{"symbol": "BTC-SWAP-USDT", "side": "LONG", "positionAmt": "0.01"}]
    result = build_toobit_raw_position_observation(
        adapter_result=AdapterResult(True, "OK", {"position_state_known": True, "positions": rows}),
        observed_at="2026-10-14T18:00:00Z",
        account_scope="TOOBIT:FUTURES:ACCOUNT",
        requested_asset="BTC-SWAP-USDT",
        provenance="signed GET /api/v1/futures/positions; captured by caller",
    )
    assert result["observation_state"] == "AVAILABLE"
    assert result["positions"] == rows
    assert result["portfolio_state"] == "BLOCKED"
    assert result["allocated_risk"] is None
    assert result["concurrent_positions"] is None


def test_missing_timestamp_blocks_without_inventing_one():
    result = build_toobit_raw_position_observation(
        adapter_result=AdapterResult(True, "OK", {"position_state_known": True, "positions": []}),
        observed_at="",
        account_scope="TOOBIT:FUTURES:ACCOUNT",
        requested_asset="BTC-SWAP-USDT",
        provenance="signed GET",
    )
    assert result["observation_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "TOOBIT_POSITION_OBSERVATION_TIMESTAMP_MISSING"


def test_provider_failure_blocks():
    result = build_toobit_raw_position_observation(
        adapter_result=AdapterResult(False, "TOOBIT_FUTURES_POSITION_STATE_INVALID"),
        observed_at="2026-10-14T18:00:00Z",
        account_scope="TOOBIT:FUTURES:ACCOUNT",
        requested_asset="BTC-SWAP-USDT",
        provenance="signed GET",
    )
    assert result["observation_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "TOOBIT_FUTURES_POSITION_STATE_INVALID"


def test_symbol_scope_mismatch_blocks():
    result = build_toobit_raw_position_observation(
        adapter_result=AdapterResult(True, "OK", {"position_state_known": True, "positions": [
            {"symbol": "ETH-SWAP-USDT", "side": "LONG", "positionAmt": "1"}
        ]}),
        observed_at="2026-10-14T18:00:00Z",
        account_scope="TOOBIT:FUTURES:ACCOUNT",
        requested_asset="BTC-SWAP-USDT",
        provenance="signed GET",
    )
    assert result["observation_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "TOOBIT_POSITION_SYMBOL_SCOPE_MISMATCH"


def test_malformed_position_side_blocks():
    result = build_toobit_raw_position_observation(
        adapter_result=AdapterResult(True, "OK", {"position_state_known": True, "positions": [
            {"symbol": "BTC-SWAP-USDT", "side": "BOTH"}
        ]}),
        observed_at="2026-10-14T18:00:00Z",
        account_scope="TOOBIT:FUTURES:ACCOUNT",
        requested_asset="BTC-SWAP-USDT",
        provenance="signed GET",
    )
    assert result["observation_state"] == "BLOCKED"
    assert result["portfolio_block_reason"] == "TOOBIT_POSITION_SIDE_INVALID"
