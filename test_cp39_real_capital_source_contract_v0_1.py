import pytest

from real_capital_source_contract_v0_1 import validate_real_capital_source


def valid_observation():
    return {
        "capital_state": "AVAILABLE",
        "capital_validation": "VALID",
        "capital_source": "REAL_ACCOUNT_BALANCE",
        "provenance": "REAL_ACCOUNT",
        "asset_scope": "USDT",
        "available_capital": 10000.0,
        "usable_capital": 8000.0,
        "observed_at": "2026-09-17T00:00:00+00:00",
    }


def test_valid_real_capital_observation_is_accepted():
    result = validate_real_capital_source(valid_observation())
    assert result == {
        "capital_state": "AVAILABLE",
        "capital_source": "REAL_ACCOUNT_BALANCE",
        "provenance": "REAL_ACCOUNT",
        "asset_scope": "USDT",
        "available_capital": 10000.0,
        "usable_capital": 8000.0,
        "observed_at": "2026-09-17T00:00:00+00:00",
    }


def test_unvalidated_capital_fails_closed():
    observation = valid_observation()
    observation["capital_validation"] = "INVALID"
    with pytest.raises(ValueError, match="CAPITAL_VALIDATION_INVALID"):
        validate_real_capital_source(observation)


def test_capital_must_be_available():
    observation = valid_observation()
    observation["capital_state"] = "BLOCKED"
    with pytest.raises(ValueError, match="CAPITAL_STATE_INVALID"):
        validate_real_capital_source(observation)


def test_test_legacy_simulated_sources_are_rejected():
    for source in ("TEST", "LEGACY", "SIMULATED"):
        observation = valid_observation()
        observation["capital_source"] = source
        with pytest.raises(ValueError, match="CAPITAL_SOURCE_INVALID"):
            validate_real_capital_source(observation)


def test_provenance_is_required():
    observation = valid_observation()
    observation["provenance"] = ""
    with pytest.raises(ValueError, match="CAPITAL_PROVENANCE_INVALID"):
        validate_real_capital_source(observation)


def test_available_capital_must_be_positive_finite():
    for value in (0, -1, float("nan"), float("inf"), True):
        observation = valid_observation()
        observation["available_capital"] = value
        with pytest.raises(ValueError, match="AVAILABLE_CAPITAL_INVALID"):
            validate_real_capital_source(observation)


def test_usable_capital_must_be_positive_and_not_exceed_available():
    observation = valid_observation()
    observation["usable_capital"] = 0
    with pytest.raises(ValueError, match="USABLE_CAPITAL_INVALID"):
        validate_real_capital_source(observation)

    observation = valid_observation()
    observation["usable_capital"] = 10001.0
    with pytest.raises(ValueError, match="USABLE_CAPITAL_INVALID"):
        validate_real_capital_source(observation)


def test_required_source_metadata_is_explicit():
    for field in ("capital_source", "provenance", "asset_scope", "observed_at"):
        observation = valid_observation()
        observation[field] = ""
        with pytest.raises(ValueError):
            validate_real_capital_source(observation)


def test_non_mapping_input_fails_closed():
    with pytest.raises(ValueError, match="CAPITAL_INPUT_INVALID"):
        validate_real_capital_source(None)


def test_output_is_provider_neutral_and_has_no_execution_surface():
    result = validate_real_capital_source(valid_observation())
    forbidden = {
        "order_id",
        "exchange_client",
        "api_request",
        "signature",
        "execution",
        "submitted",
        "trade_id",
        "withdrawal",
    }
    assert forbidden.isdisjoint(result)


def test_output_does_not_promote_capital_to_execution_permission():
    result = validate_real_capital_source(valid_observation())
    assert "execution_enabled" not in result
    assert "execution_authorization" not in result
    assert "order_write" not in result


def test_result_is_deterministic():
    observation = valid_observation()
    assert validate_real_capital_source(observation) == validate_real_capital_source(observation)
