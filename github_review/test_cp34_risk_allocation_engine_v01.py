"""CP34-B RED — Risk Allocation boundary tests."""
from __future__ import annotations

import pytest


def _load_engine():
    try:
        from risk_allocation_engine_v0_1 import build_risk_allocation
        return build_risk_allocation
    except ModuleNotFoundError as exc:
        pytest.fail(f"CP34 RED: Risk Allocation Engine is not implemented yet: {exc}")


def test_cp34_requires_validated_real_capital_before_numeric_allocation():
    build_risk_allocation = _load_engine()
    result = build_risk_allocation({"capital_state": "UNAVAILABLE_CAPITAL"}, None)
    assert result.allocated_risk is None
    assert result.allocation_reason == "REAL_CAPITAL_NOT_AVAILABLE"


def test_cp34_never_uses_legacy_test_capital_or_static_defaults():
    build_risk_allocation = _load_engine()
    result = build_risk_allocation(
        {"capital_state": "TEST_CAPITAL", "available_capital": 1_000_000.0},
        {"risk_per_trade": 0.005},
    )
    assert result.allocated_risk is None
    assert result.trade_risk_capacity is None


def test_cp34_unvalidated_policy_never_creates_risk_numbers():
    build_risk_allocation = _load_engine()
    result = build_risk_allocation(
        {"capital_state": "REAL_CAPITAL", "available_capital": 100_000.0},
        {"risk_per_trade": 0.005},
    )
    assert result.allocated_risk is None
    assert result.trade_risk_capacity is None
    assert result.allocation_reason == "RISK_POLICY_UNVALIDATED"


def test_cp34_preserves_explicit_validated_observations_without_recomputing_them():
    build_risk_allocation = _load_engine()
    result = build_risk_allocation(
        {
            "capital_state": "REAL_CAPITAL",
            "portfolio_risk_capacity": 500.0,
            "trade_risk_capacity": 100.0,
            "allocated_risk": 75.0,
            "correlation_adjustment": 0.8,
            "liquidity_adjustment": 0.9,
            "execution_adjustment": 1.0,
        },
        {"policy_validation": "VALID"},
    )
    assert result.portfolio_risk_capacity == 500.0
    assert result.trade_risk_capacity == 100.0
    assert result.allocated_risk == 75.0
    assert result.correlation_adjustment == 0.8
    assert result.liquidity_adjustment == 0.9
    assert result.execution_adjustment == 1.0


def test_cp34_does_not_create_sizing_or_execution_fields():
    build_risk_allocation = _load_engine()
    result = build_risk_allocation({"capital_state": "UNAVAILABLE_CAPITAL"}, None)
    forbidden = {
        "quantity", "position_size", "entry_price", "stop_price",
        "order_intent", "execution", "take_profit", "trailing_stop",
    }
    assert not (forbidden & set(vars(result)))
