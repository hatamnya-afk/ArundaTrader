import pytest

from pre_execution_readiness_contract_v0_1 import validate_pre_execution_readiness


def valid_readiness():
    return {
        "readiness_state": "READY",
        "readiness_validation": "VALID",
        "readiness_source": "REAL_PRODUCTION_READINESS",
        "provenance": "REAL_PRODUCTION_OBSERVATION",
        "asset": "BTCUSDT",
        "capital_validation": "VALID",
        "portfolio_validation": "VALID",
        "stop_risk_policy_validation": "VALID",
        "liquidity_validation": "VALID",
        "execution_validation": "VALID",
        "observed_at": "2026-09-17T00:00:00+00:00",
    }


def test_valid_pre_execution_readiness_is_accepted():
    assert validate_pre_execution_readiness(valid_readiness()) == valid_readiness()


def test_readiness_must_be_ready_and_valid():
    for field, value, error in (
        ("readiness_state", "BLOCKED", "READINESS_STATE_INVALID"),
        ("readiness_validation", "INVALID", "READINESS_VALIDATION_INVALID"),
    ):
        readiness = valid_readiness()
        readiness[field] = value
        with pytest.raises(ValueError, match=error):
            validate_pre_execution_readiness(readiness)


def test_readiness_source_must_be_production_bound():
    for source in ("TEST", "LEGACY", "SIMULATED", ""):
        readiness = valid_readiness()
        readiness["readiness_source"] = source
        with pytest.raises(ValueError, match="READINESS_SOURCE_INVALID"):
            validate_pre_execution_readiness(readiness)


def test_provenance_asset_and_observed_at_are_required():
    for field in ("provenance", "asset", "observed_at"):
        readiness = valid_readiness()
        readiness[field] = ""
        with pytest.raises(ValueError, match="READINESS_METADATA_INVALID"):
            validate_pre_execution_readiness(readiness)


def test_all_required_production_validations_are_required():
    for field in (
        "capital_validation",
        "portfolio_validation",
        "stop_risk_policy_validation",
        "liquidity_validation",
        "execution_validation",
    ):
        readiness = valid_readiness()
        readiness[field] = "INVALID"
        with pytest.raises(ValueError, match="REQUIRED_OBSERVATION_INVALID"):
            validate_pre_execution_readiness(readiness)


def test_non_mapping_input_fails_closed():
    with pytest.raises(ValueError, match="READINESS_INPUT_INVALID"):
        validate_pre_execution_readiness(None)


def test_no_execution_surface_is_allowed():
    result = validate_pre_execution_readiness(valid_readiness())
    forbidden = {
        "order_id", "exchange_client", "api_request", "signature",
        "submitted", "trade_id", "withdrawal", "order_write",
        "execution_authorization", "execution_enabled",
    }
    assert forbidden.isdisjoint(result)


def test_readiness_contract_is_provider_neutral():
    readiness = valid_readiness()
    readiness["exchange"] = "TOOBIT"
    with pytest.raises(ValueError, match="READINESS_PROVIDER_COUPLING"):
        validate_pre_execution_readiness(readiness)


def test_result_is_deterministic():
    readiness = valid_readiness()
    assert validate_pre_execution_readiness(readiness) == validate_pre_execution_readiness(readiness)
