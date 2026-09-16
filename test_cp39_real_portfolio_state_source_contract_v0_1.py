import pytest

from real_portfolio_state_source_contract_v0_1 import validate_real_portfolio_state


def valid_observation():
    return {
        "portfolio_state": "AVAILABLE",
        "portfolio_validation": "VALID",
        "portfolio_source": "REAL_ACCOUNT_PORTFOLIO",
        "provenance": "REAL_ACCOUNT_PORTFOLIO",
        "asset_scope": "USDT",
        "portfolio_capital": 10000.0,
        "usable_capital": 8000.0,
        "allocated_risk": 250.0,
        "concurrent_positions": 2,
        "observed_at": "2026-09-17T00:00:00+00:00",
    }


def test_valid_real_portfolio_observation_is_accepted():
    result = validate_real_portfolio_state(valid_observation())
    assert result == {
        "portfolio_state": "AVAILABLE",
        "portfolio_source": "REAL_ACCOUNT_PORTFOLIO",
        "provenance": "REAL_ACCOUNT_PORTFOLIO",
        "asset_scope": "USDT",
        "portfolio_capital": 10000.0,
        "usable_capital": 8000.0,
        "allocated_risk": 250.0,
        "concurrent_positions": 2,
        "observed_at": "2026-09-17T00:00:00+00:00",
    }


def test_unvalidated_portfolio_fails_closed():
    observation = valid_observation()
    observation["portfolio_validation"] = "INVALID"
    with pytest.raises(ValueError, match="PORTFOLIO_VALIDATION_INVALID"):
        validate_real_portfolio_state(observation)


def test_portfolio_must_be_available():
    observation = valid_observation()
    observation["portfolio_state"] = "BLOCKED"
    with pytest.raises(ValueError, match="PORTFOLIO_STATE_INVALID"):
        validate_real_portfolio_state(observation)


def test_test_legacy_simulated_sources_are_rejected():
    for source in ("TEST", "LEGACY", "SIMULATED"):
        observation = valid_observation()
        observation["portfolio_source"] = source
        with pytest.raises(ValueError, match="PORTFOLIO_SOURCE_INVALID"):
            validate_real_portfolio_state(observation)


def test_required_provenance_is_explicit():
    observation = valid_observation()
    observation["provenance"] = ""
    with pytest.raises(ValueError, match="PORTFOLIO_PROVENANCE_INVALID"):
        validate_real_portfolio_state(observation)


def test_portfolio_capital_must_be_positive_finite():
    for value in (0, -1, float("nan"), float("inf"), True):
        observation = valid_observation()
        observation["portfolio_capital"] = value
        with pytest.raises(ValueError, match="PORTFOLIO_CAPITAL_INVALID"):
            validate_real_portfolio_state(observation)


def test_usable_capital_must_be_positive_and_not_exceed_portfolio():
    for value in (0, -1, float("nan"), float("inf"), True, 10001.0):
        observation = valid_observation()
        observation["usable_capital"] = value
        with pytest.raises(ValueError, match="USABLE_CAPITAL_INVALID"):
            validate_real_portfolio_state(observation)


def test_allocated_risk_must_be_nonnegative_finite():
    for value in (-1, float("nan"), float("inf"), True):
        observation = valid_observation()
        observation["allocated_risk"] = value
        with pytest.raises(ValueError, match="ALLOCATED_RISK_INVALID"):
            validate_real_portfolio_state(observation)


def test_concurrent_positions_must_be_nonnegative_integer():
    for value in (-1, 1.5, True, "2"):
        observation = valid_observation()
        observation["concurrent_positions"] = value
        with pytest.raises(ValueError, match="CONCURRENT_POSITIONS_INVALID"):
            validate_real_portfolio_state(observation)


def test_required_source_metadata_is_explicit():
    for field in ("portfolio_source", "provenance", "asset_scope", "observed_at"):
        observation = valid_observation()
        observation[field] = ""
        with pytest.raises(ValueError):
            validate_real_portfolio_state(observation)


def test_non_mapping_input_fails_closed():
    with pytest.raises(ValueError, match="PORTFOLIO_INPUT_INVALID"):
        validate_real_portfolio_state(None)


def test_output_is_provider_neutral_and_has_no_execution_surface():
    result = validate_real_portfolio_state(valid_observation())
    forbidden = {
        "order_id", "exchange_client", "api_request", "signature",
        "execution", "submitted", "trade_id", "withdrawal",
        "execution_enabled", "execution_authorization", "order_write",
    }
    assert forbidden.isdisjoint(result)


def test_result_is_deterministic():
    observation = valid_observation()
    assert validate_real_portfolio_state(observation) == validate_real_portfolio_state(observation)
