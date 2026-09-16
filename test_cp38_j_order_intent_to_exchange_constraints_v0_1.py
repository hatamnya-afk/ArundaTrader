import pytest

from order_intent_exchange_constraints_boundary_v0_1 import merge_validated_order_intent_to_exchange_constraints_input


def valid_order_intent():
    return {
        "asset": "BTCUSDT",
        "direction": "LONG",
        "quantity": 0.01,
        "entry_price": 100000.0,
        "stop_distance": 1000.0,
        "exposure": 1000.0,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": "RISK-0.1",
    }


def test_approved_order_intent_maps_to_minimal_exchange_constraints_input():
    result = merge_validated_order_intent_to_exchange_constraints_input(valid_order_intent())
    assert result == {
        "asset": "BTCUSDT",
        "direction": "LONG",
        "quantity": 0.01,
        "entry_price": 100000.0,
        "stop_distance": 1000.0,
        "exposure": 1000.0,
    }


def test_unapproved_trade_gate_fails_closed():
    observation = valid_order_intent()
    observation["trade_gate_state"] = "BLOCKED"
    with pytest.raises(ValueError, match="TRADE_GATE_NOT_APPROVED"):
        merge_validated_order_intent_to_exchange_constraints_input(observation)


def test_unapproved_risk_fails_closed():
    observation = valid_order_intent()
    observation["risk_state"] = "BLOCKED"
    with pytest.raises(ValueError, match="RISK_NOT_APPROVED"):
        merge_validated_order_intent_to_exchange_constraints_input(observation)


def test_boundary_does_not_select_exchange_or_create_api_fields():
    result = merge_validated_order_intent_to_exchange_constraints_input(valid_order_intent())
    forbidden = {
        "exchange", "symbol_info", "tick_size", "step_size", "min_qty", "max_qty",
        "order_id", "api_request", "signature", "execution", "submitted",
    }
    assert forbidden.isdisjoint(result)
