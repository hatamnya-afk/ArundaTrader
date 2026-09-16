import pytest

from validated_stop_risk_policy_source_contract_v0_1 import validate_stop_risk_policy_source


def valid_observation():
    return {
        "observation_state": "AVAILABLE",
        "observation_validation": "VALID",
        "observation_source": "REAL_MARKET_RISK_POLICY",
        "provenance": "REAL_PRODUCTION_OBSERVATION",
        "asset": "BTCUSDT",
        "entry_price": 60000.0,
        "stop_price": 59000.0,
        "stop_distance": 1000.0,
        "risk_policy_version": "RISK_POLICY_V0_1",
        "risk_policy_validation": "VALID",
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 3,
        "observed_at": "2026-09-17T00:00:00+00:00",
    }


def test_valid_real_stop_and_policy_is_accepted():
    result = validate_stop_risk_policy_source(valid_observation())
    assert result == valid_observation()


def test_observation_validation_must_be_valid():
    observation = valid_observation()
    observation["observation_validation"] = "INVALID"
    with pytest.raises(ValueError, match="OBSERVATION_VALIDATION_INVALID"):
        validate_stop_risk_policy_source(observation)


def test_observation_state_must_be_available():
    observation = valid_observation()
    observation["observation_state"] = "BLOCKED"
    with pytest.raises(ValueError, match="OBSERVATION_STATE_INVALID"):
        validate_stop_risk_policy_source(observation)


def test_test_legacy_simulated_sources_are_rejected():
    for source in ("TEST", "LEGACY", "SIMULATED"):
        observation = valid_observation()
        observation["observation_source"] = source
        with pytest.raises(ValueError, match="OBSERVATION_SOURCE_INVALID"):
            validate_stop_risk_policy_source(observation)


def test_required_provenance_and_metadata_are_explicit():
    for field in ("provenance", "asset", "observed_at", "risk_policy_version"):
        observation = valid_observation()
        observation[field] = ""
        with pytest.raises(ValueError):
            validate_stop_risk_policy_source(observation)


def test_entry_and_stop_must_be_positive_finite_and_stop_distance_valid():
    for field, values in {
        "entry_price": (0, -1, float("nan"), float("inf"), True),
        "stop_price": (0, -1, float("nan"), float("inf"), True),
        "stop_distance": (0, -1, float("nan"), float("inf"), True),
    }.items():
        for value in values:
            observation = valid_observation()
            observation[field] = value
            with pytest.raises(ValueError, match="STOP_INPUT_INVALID"):
                validate_stop_risk_policy_source(observation)


def test_stop_distance_must_match_entry_and_stop():
    observation = valid_observation()
    observation["stop_distance"] = 999.0
    with pytest.raises(ValueError, match="STOP_DISTANCE_INVALID"):
        validate_stop_risk_policy_source(observation)


def test_stop_must_be_below_entry_for_long_direction():
    observation = valid_observation()
    observation["direction"] = "LONG"
    observation["stop_price"] = 61000.0
    with pytest.raises(ValueError, match="STOP_DIRECTION_INVALID"):
        validate_stop_risk_policy_source(observation)


def test_short_direction_requires_explicit_direction_and_stop_above_entry():
    observation = valid_observation()
    observation["direction"] = "SHORT"
    observation["stop_price"] = 61000.0
    observation["stop_distance"] = 1000.0
    result = validate_stop_risk_policy_source(observation)
    assert result["direction"] == "SHORT"


def test_risk_policy_must_be_valid_and_positive():
    observation = valid_observation()
    observation["risk_policy_validation"] = "INVALID"
    with pytest.raises(ValueError, match="RISK_POLICY_VALIDATION_INVALID"):
        validate_stop_risk_policy_source(observation)

    for field, values in {
        "risk_per_trade": (0, -0.1, float("nan"), float("inf"), True),
        "max_portfolio_risk": (0, -0.1, float("nan"), float("inf"), True),
    }.items():
        for value in values:
            observation = valid_observation()
            observation[field] = value
            with pytest.raises(ValueError, match="RISK_POLICY_VALUE_INVALID"):
                validate_stop_risk_policy_source(observation)


def test_portfolio_risk_must_not_be_below_trade_risk():
    observation = valid_observation()
    observation["max_portfolio_risk"] = 0.005
    with pytest.raises(ValueError, match="RISK_POLICY_RELATION_INVALID"):
        validate_stop_risk_policy_source(observation)


def test_max_concurrent_positions_must_be_positive_integer():
    for value in (0, -1, 1.5, True, "3"):
        observation = valid_observation()
        observation["max_concurrent_positions"] = value
        with pytest.raises(ValueError, match="MAX_CONCURRENT_POSITIONS_INVALID"):
            validate_stop_risk_policy_source(observation)


def test_output_has_no_execution_surface():
    result = validate_stop_risk_policy_source(valid_observation())
    forbidden = {
        "order_id", "exchange_client", "api_request", "signature",
        "execution", "submitted", "trade_id", "withdrawal",
        "execution_enabled", "execution_authorization", "order_write",
    }
    assert forbidden.isdisjoint(result)


def test_result_is_deterministic():
    observation = valid_observation()
    assert validate_stop_risk_policy_source(observation) == validate_stop_risk_policy_source(observation)
