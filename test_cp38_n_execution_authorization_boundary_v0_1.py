import pytest

from execution_authorization_boundary_v0_1 import evaluate_execution_authorization


def valid_ready_observation():
    return {
        "readiness_state": "READY",
        "reason": "PRE_EXECUTION_READY",
        "asset": "BTCUSDT",
        "quantity": 0.01,
        "entry_price": 100000.0,
        "notional": 1000.0,
    }


def valid_authorization():
    return {
        "execution_authorization": "AUTHORIZED",
        "authorization_validation": "VALID",
        "authorization_source": "MANAGEMENT_AUTHORIZATION",
    }


def test_ready_with_explicit_valid_authorization_is_authorized_without_execution():
    result = evaluate_execution_authorization(valid_ready_observation(), valid_authorization())
    assert result == {
        "authorization_state": "AUTHORIZED",
        "reason": "EXECUTION_AUTHORIZED",
        "asset": "BTCUSDT",
        "quantity": 0.01,
        "entry_price": 100000.0,
        "notional": 1000.0,
    }


def test_not_ready_fails_closed():
    observation = valid_ready_observation()
    observation["readiness_state"] = "BLOCKED"
    with pytest.raises(ValueError, match="READINESS_NOT_READY"):
        evaluate_execution_authorization(observation, valid_authorization())


def test_missing_readiness_state_fails_closed():
    observation = valid_ready_observation()
    del observation["readiness_state"]
    with pytest.raises(ValueError, match="READINESS_STATE_INVALID"):
        evaluate_execution_authorization(observation, valid_authorization())


def test_authorization_must_be_explicit_and_valid():
    for field, value, reason in (
        ("execution_authorization", "", "AUTHORIZATION_INVALID"),
        ("authorization_validation", "INVALID", "AUTHORIZATION_VALIDATION_INVALID"),
        ("authorization_source", "", "AUTHORIZATION_SOURCE_INVALID"),
    ):
        authorization = valid_authorization()
        authorization[field] = value
        with pytest.raises(ValueError, match=reason):
            evaluate_execution_authorization(valid_ready_observation(), authorization)


def test_test_simulated_or_legacy_authorization_sources_fail_closed():
    for source in ("TEST", "SIMULATED", "LEGACY"):
        authorization = valid_authorization()
        authorization["authorization_source"] = source
        with pytest.raises(ValueError, match="AUTHORIZATION_SOURCE_INVALID"):
            evaluate_execution_authorization(valid_ready_observation(), authorization)


def test_required_ready_values_remain_valid():
    for field, value, reason in (
        ("asset", "", "ASSET_INVALID"),
        ("quantity", 0, "QUANTITY_INVALID"),
        ("entry_price", 0, "ENTRY_PRICE_INVALID"),
        ("notional", 0, "NOTIONAL_INVALID"),
    ):
        observation = valid_ready_observation()
        observation[field] = value
        with pytest.raises(ValueError, match=reason):
            evaluate_execution_authorization(observation, valid_authorization())


def test_execution_artifacts_are_never_created_or_accepted_as_output():
    result = evaluate_execution_authorization(valid_ready_observation(), valid_authorization())
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


def test_non_mapping_inputs_fail_closed():
    with pytest.raises(ValueError, match="READINESS_INPUT_INVALID"):
        evaluate_execution_authorization(None, valid_authorization())
    with pytest.raises(ValueError, match="AUTHORIZATION_INPUT_INVALID"):
        evaluate_execution_authorization(valid_ready_observation(), None)


def test_result_is_deterministic():
    observation = valid_ready_observation()
    authorization = valid_authorization()
    assert evaluate_execution_authorization(observation, authorization) == evaluate_execution_authorization(
        observation, authorization
    )
