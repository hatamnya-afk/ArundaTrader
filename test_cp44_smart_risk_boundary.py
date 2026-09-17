"""Focused CP44 tests for dynamic Risk and Smart Risk boundaries.

These tests are side-effect free and do not execute the trading pipeline.
"""

from dynamic_risk_contract_boundary_v0_1 import build_dynamic_risk
from dynamic_smart_risk_contract_boundary_v0_1 import build_dynamic_smart_risk


POLICY = {
    "policy_version": "CP44-SMART-RISK-v0.1",
    "policy_validation": "VALID",
    "max_concurrent_positions": 8,
}


def observation(asset: str, direction: str, allocation_fraction: float, capital: float):
    return {
        "asset": asset,
        "capital_state": "REAL_CAPITAL",
        "direction": direction,
        "entry_price": 100.0,
        "invalidation_price": 95.0 if direction == "LONG" else 105.0,
        "portfolio_capital": capital,
        "usable_capital": capital,
        "allocation_fraction": allocation_fraction,
        "concurrent_positions": 0,
    }


def test_dynamic_risk_fails_closed_without_real_capital_context():
    result = build_dynamic_risk(
        "BTC/USDT",
        {
            "asset": "BTC/USDT",
            "state": "ACTIONABLE",
            "direction": "LONG",
        },
    )

    assert result["risk_state"] == "BLOCKED"
    assert result["reason"] == "REAL_CAPITAL_BOUNDARY_UNAVAILABLE"


def test_dynamic_risk_preserves_dynamic_asset_identity():
    result = build_dynamic_risk(
        "NEWASSET/USDT",
        {
            "asset": "NEWASSET/USDT",
            "state": "ACTIONABLE",
            "direction": "LONG",
        },
    )

    assert result["asset"] == "NEWASSET/USDT"
    assert result["dynamic_universe"] is True
    assert result["fixed_15_used"] is False


def test_long_allocation_sizes_from_explicit_invalidation():
    result = build_dynamic_smart_risk(
        "ALPHA/USDT",
        {"state": "ACTIONABLE", "direction": "LONG"},
        observation("ALPHA/USDT", "LONG", 0.50, 1_000_000),
        POLICY,
    )
    assert result.risk_state == "APPROVED"
    assert result.invalidation_price == 95.0
    assert result.allocated_capital == 500_000.0
    assert result.exposure == 500_000.0
    assert result.position_size == 5_000.0
    assert result.risk_budget == 25_000.0


def test_short_allocation_uses_directional_invalidation():
    result = build_dynamic_smart_risk(
        "BETA/USDT",
        {"state": "ACTIONABLE", "direction": "SHORT"},
        observation("BETA/USDT", "SHORT", 0.25, 200_000),
        POLICY,
    )
    assert result.risk_state == "APPROVED"
    assert result.invalidation_price == 105.0
    assert result.allocated_capital == 50_000.0
    assert result.exposure == 50_000.0
    assert result.risk_budget == 2_500.0


def test_full_allocation_is_allowed_when_validated():
    result = build_dynamic_smart_risk(
        "GAMMA/USDT",
        {"state": "ACTIONABLE", "direction": "LONG"},
        observation("GAMMA/USDT", "LONG", 1.0, 75_000),
        POLICY,
    )
    assert result.risk_state == "APPROVED"
    assert result.allocation_fraction == 1.0
    assert result.allocated_capital == 75_000.0


def test_capital_scale_does_not_change_allocation_logic():
    small = build_dynamic_smart_risk(
        "DELTA/USDT",
        {"state": "ACTIONABLE", "direction": "LONG"},
        observation("DELTA/USDT", "LONG", 0.40, 10_000),
        POLICY,
    )
    large = build_dynamic_smart_risk(
        "DELTA/USDT",
        {"state": "ACTIONABLE", "direction": "LONG"},
        observation("DELTA/USDT", "LONG", 0.40, 10_000_000),
        POLICY,
    )
    assert small.risk_state == "APPROVED"
    assert large.risk_state == "APPROVED"
    assert small.allocation_fraction == large.allocation_fraction == 0.40
    assert small.position_size / large.position_size == 0.001


def test_invalid_long_invalidation_fails_closed():
    data = observation("EPSILON/USDT", "LONG", 0.50, 1_000_000)
    data["invalidation_price"] = 105.0
    result = build_dynamic_smart_risk(
        "EPSILON/USDT",
        {"state": "ACTIONABLE", "direction": "LONG"},
        data,
        POLICY,
    )
    assert result.risk_state == "BLOCKED"
    assert result.reason == "LONG_INVALIDATION_MUST_BE_BELOW_ENTRY"


def test_zero_allocation_fails_closed():
    result = build_dynamic_smart_risk(
        "ZETA/USDT",
        {"state": "ACTIONABLE", "direction": "LONG"},
        observation("ZETA/USDT", "LONG", 0.0, 1_000_000),
        POLICY,
    )
    assert result.risk_state == "BLOCKED"
    assert result.reason == "ALLOCATION_IS_ZERO"


if __name__ == "__main__":
    test_dynamic_risk_fails_closed_without_real_capital_context()
    test_dynamic_risk_preserves_dynamic_asset_identity()
    test_long_allocation_sizes_from_explicit_invalidation()
    test_short_allocation_uses_directional_invalidation()
    test_full_allocation_is_allowed_when_validated()
    test_capital_scale_does_not_change_allocation_logic()
    test_invalid_long_invalidation_fails_closed()
    test_zero_allocation_fails_closed()
    print("CP44 SMART-RISK BOUNDARY TESTS: PASS")
