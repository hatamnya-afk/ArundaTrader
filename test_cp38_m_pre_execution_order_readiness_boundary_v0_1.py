import pytest

from pre_execution_order_readiness_boundary_v0_1 import evaluate_pre_execution_readiness


def valid_constraint_result():
    return {
        "constraint_state": "VALID",
        "reason": "CONSTRAINTS_VALID",
        "asset": "BTCUSDT",
        "quantity": 0.01,
        "entry_price": 100000.0,
        "notional": 1000.0,
    }


def test_valid_constraint_result_is_execution_ready_without_executing():
    result = evaluate_pre_execution_readiness(valid_constraint_result())
    assert result == {
        "readiness_state": "READY",
        "reason": "PRE_EXECUTION_READY",
        "asset": "BTCUSDT",
        "quantity": 0.01,
        "entry_price": 100000.0,
        "notional": 1000.0,
    }


def test_blocked_constraints_fail_closed():
    observation = valid_constraint_result()
    observation["constraint_state"] = "BLOCKED"
    with pytest.raises(ValueError, match="CONSTRAINTS_BLOCKED"):
        evaluate_pre_execution_readiness(observation)


def test_missing_constraint_state_fails_closed():
    observation = valid_constraint_result()
    del observation["constraint_state"]
    with pytest.raises(ValueError, match="CONSTRAINT_STATE_INVALID"):
        evaluate_pre_execution_readiness(observation)


def test_required_order_values_must_remain_valid():
    for field, value, reason in (
        ("asset", "", "ASSET_INVALID"),
        ("quantity", 0, "QUANTITY_INVALID"),
        ("entry_price", 0, "ENTRY_PRICE_INVALID"),
        ("notional", 0, "NOTIONAL_INVALID"),
    ):
        observation = valid_constraint_result()
        observation[field] = value
        with pytest.raises(ValueError, match=reason):
            evaluate_pre_execution_readiness(observation)


def test_execution_fields_are_not_created_or_accepted_as_output():
    result = evaluate_pre_execution_readiness(valid_constraint_result())
    forbidden = {
        "order_id",
        "exchange_client",
        "api_request",
        "signature",
        "submitted",
        "execution",
        "fill",
        "trade_id",
    }
    assert forbidden.isdisjoint(result)


def test_non_mapping_input_fails_closed():
    with pytest.raises(ValueError, match="READINESS_INPUT_INVALID"):
        evaluate_pre_execution_readiness(None)


def test_result_is_deterministic():
    observation = valid_constraint_result()
    assert evaluate_pre_execution_readiness(observation) == evaluate_pre_execution_readiness(observation)
