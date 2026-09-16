import pytest

from other_required_production_observations_contract_v0_1 import validate_production_observations


def valid_observation():
    return {
        "observation_state": "AVAILABLE",
        "observation_validation": "VALID",
        "observation_source": "REAL_PRODUCTION_OBSERVATIONS",
        "provenance": "REAL_PRODUCTION_OBSERVATION",
        "asset": "BTCUSDT",
        "liquidity_validation": "VALID",
        "liquidity_source": "REAL_MARKET_LIQUIDITY",
        "liquidity_score": 0.8,
        "execution_validation": "VALID",
        "execution_source": "REAL_EXECUTION_CONSTRAINTS",
        "execution_adjustment": 0.9,
        "observed_at": "2026-09-17T00:00:00+00:00",
    }


def test_valid_real_observations_are_accepted():
    assert validate_production_observations(valid_observation()) == valid_observation()


def test_observation_must_be_available_and_valid():
    for field, value, error in (
        ("observation_state", "BLOCKED", "OBSERVATION_STATE_INVALID"),
        ("observation_validation", "INVALID", "OBSERVATION_VALIDATION_INVALID"),
    ):
        observation = valid_observation()
        observation[field] = value
        with pytest.raises(ValueError, match=error):
            validate_production_observations(observation)


def test_test_legacy_simulated_sources_are_rejected():
    for source in ("TEST", "LEGACY", "SIMULATED"):
        observation = valid_observation()
        observation["observation_source"] = source
        with pytest.raises(ValueError, match="OBSERVATION_SOURCE_INVALID"):
            validate_production_observations(observation)


def test_provenance_and_asset_metadata_are_required():
    for field in ("provenance", "asset", "observed_at"):
        observation = valid_observation()
        observation[field] = ""
        with pytest.raises(ValueError, match="OBSERVATION_METADATA_INVALID"):
            validate_production_observations(observation)


def test_liquidity_validation_and_source_are_required():
    observation = valid_observation()
    observation["liquidity_validation"] = "INVALID"
    with pytest.raises(ValueError, match="LIQUIDITY_VALIDATION_INVALID"):
        validate_production_observations(observation)

    observation = valid_observation()
    observation["liquidity_source"] = ""
    with pytest.raises(ValueError, match="LIQUIDITY_SOURCE_INVALID"):
        validate_production_observations(observation)


def test_liquidity_score_must_be_finite_between_zero_and_one():
    for value in (-0.1, 0, 1.1, float("nan"), float("inf"), True):
        observation = valid_observation()
        observation["liquidity_score"] = value
        with pytest.raises(ValueError, match="LIQUIDITY_SCORE_INVALID"):
            validate_production_observations(observation)


def test_execution_validation_and_source_are_required():
    observation = valid_observation()
    observation["execution_validation"] = "INVALID"
    with pytest.raises(ValueError, match="EXECUTION_VALIDATION_INVALID"):
        validate_production_observations(observation)

    observation = valid_observation()
    observation["execution_source"] = ""
    with pytest.raises(ValueError, match="EXECUTION_SOURCE_INVALID"):
        validate_production_observations(observation)


def test_execution_adjustment_must_be_finite_and_positive():
    for value in (0, -0.1, float("nan"), float("inf"), True):
        observation = valid_observation()
        observation["execution_adjustment"] = value
        with pytest.raises(ValueError, match="EXECUTION_ADJUSTMENT_INVALID"):
            validate_production_observations(observation)


def test_non_mapping_input_fails_closed():
    with pytest.raises(ValueError, match="OBSERVATION_INPUT_INVALID"):
        validate_production_observations(None)


def test_output_has_no_execution_surface():
    result = validate_production_observations(valid_observation())
    forbidden = {
        "order_id", "exchange_client", "api_request", "signature",
        "submitted", "trade_id", "withdrawal", "order_write",
        "execution_authorization", "execution_enabled",
    }
    assert forbidden.isdisjoint(result)


def test_result_is_deterministic():
    observation = valid_observation()
    assert validate_production_observations(observation) == validate_production_observations(observation)
