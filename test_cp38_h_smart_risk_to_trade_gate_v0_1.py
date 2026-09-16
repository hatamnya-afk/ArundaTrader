import pytest

from smart_risk_contract_v0_1 import SmartRiskDecision
from smart_risk_trade_gate_bridge_v0_1 import build_trade_gate_input


def approved_decision():
    return SmartRiskDecision(
        asset="BTCUSDT",
        direction="LONG",
        entry_price=100.0,
        stop_distance=5.0,
        risk_budget=100.0,
        position_size=20.0,
        exposure=2000.0,
        remaining_portfolio_risk=400.0,
        concurrent_positions=1,
        max_concurrent_positions=3,
        risk_state="APPROVED",
        reason="RISK_APPROVED",
        policy_version="RISK_POLICY_V0.1",
    )


def test_approved_smart_risk_maps_only_trade_gate_risk_inputs():
    result = build_trade_gate_input(approved_decision())

    assert result == {
        "asset": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_distance": 5.0,
        "position_size": 20.0,
        "exposure": 2000.0,
        "risk_budget": 100.0,
        "remaining_portfolio_risk": 400.0,
        "concurrent_positions": 1,
        "max_concurrent_positions": 3,
        "risk_state": "APPROVED",
        "risk_reason": "RISK_APPROVED",
        "policy_version": "RISK_POLICY_V0.1",
    }


def test_blocked_smart_risk_is_not_forwarded_to_trade_gate():
    decision = approved_decision()
    blocked = SmartRiskDecision(**{**decision.__dict__, "risk_state": "BLOCKED", "reason": "PORTFOLIO_LIMIT"})

    with pytest.raises(ValueError, match="SMART_RISK_NOT_APPROVED"):
        build_trade_gate_input(blocked)


def test_invalid_smart_risk_decision_is_fail_closed():
    with pytest.raises(ValueError, match="SMART_RISK_DECISION_INVALID"):
        build_trade_gate_input({"risk_state": "APPROVED"})


def test_trade_gate_boundary_contains_no_order_or_execution_surface():
    result = build_trade_gate_input(approved_decision())
    forbidden = {"order", "order_intent", "quantity", "execution", "exchange", "api_key", "signature"}
    assert forbidden.isdisjoint(result)
