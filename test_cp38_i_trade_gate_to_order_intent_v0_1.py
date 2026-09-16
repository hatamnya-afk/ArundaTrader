import pytest

from trade_gate_order_intent_boundary_v0_1 import merge_approved_trade_gate_to_order_intent_input


def valid_gate_output():
    return {
        "trade_gate_state": "APPROVED",
        "asset": "BTCUSDT",
        "direction": "LONG",
        "quantity": 0.01,
        "entry_price": 100000.0,
        "stop_distance": 1000.0,
        "exposure": 1000.0,
        "risk_state": "APPROVED",
        "policy_version": "RISK-0.1",
    }


def test_approved_gate_maps_to_minimal_order_intent_input():
    result = merge_approved_trade_gate_to_order_intent_input(valid_gate_output())
    assert result == {
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


def test_unapproved_gate_fails_closed():
    observation = valid_gate_output()
    observation["trade_gate_state"] = "BLOCKED"
    with pytest.raises(ValueError, match="TRADE_GATE_NOT_APPROVED"):
        merge_approved_trade_gate_to_order_intent_input(observation)


def test_missing_quantity_fails_closed():
    observation = valid_gate_output()
    del observation["quantity"]
    with pytest.raises(ValueError, match="QUANTITY_INVALID"):
        merge_approved_trade_gate_to_order_intent_input(observation)


def test_boundary_does_not_create_order_or_execution_fields():
    result = merge_approved_trade_gate_to_order_intent_input(valid_gate_output())
    forbidden = {"order_id", "exchange", "symbol_info", "execution", "submitted", "api_request"}
    assert forbidden.isdisjoint(result)
