from toobit_account_wide_futures_observation_producer_v0_1 import build_toobit_account_wide_futures_observation
from toobit_exchange_adapter_v0_1 import ToobitAdapterResult


def test_normalizes_both_account_wide_futures_categories_without_inventing_risk():
    positions = ToobitAdapterResult(True, "OK", {
        "coverage_scope": "ACCOUNT_WIDE", "categories_queried": ["USDT", "USDC"],
        "positions_by_category": {
            "USDT": [{"symbol": "BTC-SWAP-USDT", "side": "LONG", "position": "1"}],
            "USDC": [{"symbol": "ETH-SWAP-USDC", "side": "SHORT", "position": "2"}],
        },
    })
    balances = ToobitAdapterResult(True, "OK", {
        "coverage_scope": "ACCOUNT_WIDE", "categories_queried": ["USDT", "USDC"],
        "balances_by_category": {
            "USDT": [{"asset": "USDT", "total_amount": 100.0, "usable_amount": 80.0, "category": "USDT"}],
            "USDC": [{"asset": "USDC", "total_amount": 50.0, "usable_amount": 40.0, "category": "USDC"}],
        },
    })
    result = build_toobit_account_wide_futures_observation(
        positions_adapter_result=positions, balances_adapter_result=balances,
        observed_at="2026-10-14T18:00:00Z", cycle_id="fixture-cycle",
        account_scope="TOOBIT:fixture", provenance="synthetic fixture only",
    )
    assert result["observation_state"] == "AVAILABLE"
    assert result["positions_coverage"] == "ACCOUNT_WIDE"
    assert len(result["positions"]) == 2
    assert result["coverage_validation"]["coverage_state"] == "AVAILABLE"
    assert result["portfolio_capital"] is None
    assert result["allocated_risk"] is None


def test_account_wide_futures_observation_blocks_when_one_market_category_missing():
    positions = ToobitAdapterResult(True, "OK", {
        "coverage_scope": "ACCOUNT_WIDE", "categories_queried": ["USDT"],
        "positions_by_category": {"USDT": []},
    })
    balances = ToobitAdapterResult(True, "OK", {
        "coverage_scope": "ACCOUNT_WIDE", "categories_queried": ["USDT", "USDC"],
        "balances_by_category": {"USDT": [], "USDC": []},
    })
    result = build_toobit_account_wide_futures_observation(
        positions_adapter_result=positions, balances_adapter_result=balances,
        observed_at="2026-10-14T18:00:00Z", cycle_id="fixture-cycle",
        account_scope="TOOBIT:fixture", provenance="synthetic fixture only",
    )
    assert result["observation_state"] == "BLOCKED"
