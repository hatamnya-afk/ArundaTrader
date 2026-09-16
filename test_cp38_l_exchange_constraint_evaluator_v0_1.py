import pytest

from exchange_constraints_evaluator_v0_1 import evaluate_exchange_constraints


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


def valid_constraints():
    return {
        "constraint_validation": "VALID",
        "constraint_source": "REAL_EXCHANGE_CONSTRAINTS",
        "asset": "BTCUSDT",
        "tick_size": 0.01,
        "step_size": 0.001,
        "min_qty": 0.001,
        "max_qty": 100.0,
        "min_notional": 10.0,
    }


def test_valid_order_intent_passes_constraints():
    result = evaluate_exchange_constraints(valid_order_intent(), valid_constraints())
    assert result == {
        "constraint_state": "VALID",
        "reason": "CONSTRAINTS_VALID",
        "asset": "BTCUSDT",
        "quantity": 0.01,
        "entry_price": 100000.0,
        "notional": 1000.0,
    }


def test_unvalidated_constraints_fail_closed():
    constraints = valid_constraints()
    constraints["constraint_validation"] = "INVALID"
    result = evaluate_exchange_constraints(valid_order_intent(), constraints)
    assert result == {"constraint_state": "BLOCKED", "reason": "CONSTRAINTS_UNVALIDATED"}


def test_quantity_outside_range_is_blocked():
    intent = valid_order_intent()
    intent["quantity"] = 0.0005
    result = evaluate_exchange_constraints(intent, valid_constraints())
    assert result["reason"] == "QUANTITY_RANGE_INVALID"


def test_quantity_step_mismatch_is_blocked_without_rounding():
    intent = valid_order_intent()
    intent["quantity"] = 0.0105
    result = evaluate_exchange_constraints(intent, valid_constraints())
    assert result["reason"] == "QUANTITY_STEP_INVALID"
    assert result["quantity"] if "quantity" in result else True


def test_price_tick_mismatch_is_blocked_without_rounding():
    intent = valid_order_intent()
    intent["entry_price"] = 100000.005
    result = evaluate_exchange_constraints(intent, valid_constraints())
    assert result["reason"] == "PRICE_TICK_INVALID"


def test_min_notional_is_enforced():
    intent = valid_order_intent()
    intent["quantity"] = 0.001
    intent["entry_price"] = 1000.0
    result = evaluate_exchange_constraints(intent, valid_constraints())
    assert result["reason"] == "MIN_NOTIONAL_INVALID"


def test_asset_mismatch_is_blocked():
    constraints = valid_constraints()
    constraints["asset"] = "ETHUSDT"
    result = evaluate_exchange_constraints(valid_order_intent(), constraints)
    assert result["reason"] == "ASSET_MISMATCH"


def test_downstream_result_contains_no_execution_surface():
    result = evaluate_exchange_constraints(valid_order_intent(), valid_constraints())
    forbidden = {
        "order_id",
        "api_request",
        "signature",
        "execution",
        "submitted",
        "exchange_client",
    }
    assert forbidden.isdisjoint(result)
