from toobit_account_wide_spot_observation_producer_v0_1 import build_toobit_account_wide_spot_observation
from toobit_exchange_adapter_v0_1 import ToobitAdapterResult


def test_spot_balance_normalization_preserves_total_and_usable_amounts():
    raw = ToobitAdapterResult(True, "OK", {
        "state_known": True,
        "balances": [
            {"asset": "USDT", "free": "90.25", "locked": "10.00"},
            {"asset": "BTC", "free": "0.01", "locked": "0.002"},
        ],
    })
    result = build_toobit_account_wide_spot_observation(
        adapter_result=raw, observed_at="2026-10-14T18:00:00Z",
        cycle_id="fixture-cycle", account_scope="TOOBIT:fixture",
        provenance="synthetic fixture only",
    )
    assert result["observation_state"] == "AVAILABLE"
    assert result["coverage_scope"] == "ACCOUNT_WIDE"
    assert result["balances"][0]["total_amount"] == 100.25
    assert result["balances"][0]["usable_amount"] == 90.25
    assert result["balances"][1]["total_amount"] == 0.012
    assert result["available_capital"] is None


def test_spot_balance_normalization_blocks_duplicate_assets():
    raw = ToobitAdapterResult(True, "OK", {
        "state_known": True,
        "balances": [
            {"asset": "USDT", "free": "1", "locked": "0"},
            {"asset": "usdt", "free": "2", "locked": "0"},
        ],
    })
    result = build_toobit_account_wide_spot_observation(
        adapter_result=raw, observed_at="2026-10-14T18:00:00Z",
        cycle_id="fixture-cycle", account_scope="TOOBIT:fixture",
        provenance="synthetic fixture only",
    )
    assert result["observation_state"] == "BLOCKED"
    assert result["observation_block_reason"] == "SPOT_PROVIDER_BALANCE_ASSET_DUPLICATE:USDT"
