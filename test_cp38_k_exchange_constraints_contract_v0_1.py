import pytest

from exchange_constraints_contract_v0_1 import build_exchange_constraints


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


def test_valid_constraints_are_exposed_as_provider_neutral_contract():
    result = build_exchange_constraints(valid_constraints())
    assert result == {
        "asset": "BTCUSDT",
        "tick_size": 0.01,
        "step_size": 0.001,
        "min_qty": 0.001,
        "max_qty": 100.0,
        "min_notional": 10.0,
    }


def test_unvalidated_constraints_fail_closed():
    observation = valid_constraints()
    observation["constraint_validation"] = "INVALID"
    with pytest.raises(ValueError, match="CONSTRAINTS_UNVALIDATED"):
        build_exchange_constraints(observation)


def test_test_or_simulated_source_fails_closed():
    for source in ("TEST", "SIMULATED", "LEGACY"):
        observation = valid_constraints()
        observation["constraint_source"] = source
        with pytest.raises(ValueError, match="CONSTRAINT_SOURCE_INVALID"):
            build_exchange_constraints(observation)


def test_invalid_numeric_constraints_fail_closed():
    observation = valid_constraints()
    observation["step_size"] = 0
    with pytest.raises(ValueError, match="STEP_SIZE_INVALID"):
        build_exchange_constraints(observation)


def test_constraint_relationships_are_validated():
    observation = valid_constraints()
    observation["max_qty"] = 0.0005
    with pytest.raises(ValueError, match="QUANTITY_RANGE_INVALID"):
        build_exchange_constraints(observation)


def test_contract_does_not_create_execution_or_order_fields():
    result = build_exchange_constraints(valid_constraints())
    forbidden = {"order_id", "api_request", "signature", "execution", "submitted", "exchange_client"}
    assert forbidden.isdisjoint(result)
