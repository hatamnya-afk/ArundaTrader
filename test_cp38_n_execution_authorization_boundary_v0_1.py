import pytest

from execution_authorization_boundary_v0_1 import evaluate_execution_authorization


def ready():
    return {
        "readiness_state": "READY",
        "asset": "BTC",
        "quantity": 0.01,
        "entry_price": 100000.0,
        "notional": 1000.0,
        "venue": "SPOT",
    }


def mandate():
    return {
        "execution_authorization": "AUTHORIZED",
        "authorization_validation": "VALID",
        "authorization_source": "MANAGEMENT_PHASE_ENTRY",
        "authorization_mode": "STANDING_MANDATE",
        "authorization_id": "REAL-PROD-MANDATE-001",
        "mandate_id": "REAL-PROD-MANDATE-001",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "environment": "REAL_PRODUCTION",
        "allowed_markets": ("SPOT", "FUTURES"),
    }


def test_standing_mandate_authorizes_ready_request():
    result = evaluate_execution_authorization(ready(), mandate())
    assert result["authorization_state"] == "AUTHORIZED"
    assert result["authorization_mode"] == "STANDING_MANDATE"


def test_blocked_readiness_fails_closed():
    value = ready()
    value["readiness_state"] = "BLOCKED"
    with pytest.raises(ValueError, match="READINESS_NOT_READY"):
        evaluate_execution_authorization(value, mandate())


def test_missing_readiness_fails_closed():
    value = ready()
    del value["readiness_state"]
    with pytest.raises(ValueError, match="READINESS_STATE_INVALID"):
        evaluate_execution_authorization(value, mandate())


def test_invalid_authorization_fields_fail_closed():
    for field, value, reason in (
        ("execution_authorization", "", "AUTHORIZATION_INVALID"),
        ("authorization_validation", "INVALID", "AUTHORIZATION_VALIDATION_INVALID"),
        ("authorization_source", "", "AUTHORIZATION_SOURCE_INVALID"),
        ("authorization_mode", "", "AUTHORIZATION_MODE_INVALID"),
    ):
        value = mandate()
        value[field] = value
        with pytest.raises(ValueError, match=reason):
            evaluate_execution_authorization(ready(), value)


def test_disallowed_source_fails_closed():
    value = mandate()
    value["authorization_source"] = "TEST"
    with pytest.raises(ValueError, match="AUTHORIZATION_SOURCE_INVALID"):
        evaluate_execution_authorization(ready(), value)


def test_real_production_environment_is_required():
    value = mandate()
    value["environment"] = "TEST"
    with pytest.raises(ValueError, match="AUTHORIZATION_ENVIRONMENT_INVALID"):
        evaluate_execution_authorization(ready(), value)


def test_spot_and_futures_must_be_in_mandate():
    value = mandate()
    value["allowed_markets"] = ("FUTURES",)
    with pytest.raises(ValueError, match="AUTHORIZATION_MARKETS_INCOMPLETE"):
        evaluate_execution_authorization(ready(), value)


def test_current_market_must_be_allowed():
    value = mandate()
    value["allowed_markets"] = ("FUTURES",)
    with pytest.raises(ValueError, match="AUTHORIZATION_MARKET_NOT_ALLOWED"):
        evaluate_execution_authorization(ready(), value)


def test_non_mapping_inputs_fail_closed():
    with pytest.raises(ValueError, match="READINESS_INPUT_INVALID"):
        evaluate_execution_authorization(None, mandate())
    with pytest.raises(ValueError, match="AUTHORIZATION_INPUT_INVALID"):
        evaluate_execution_authorization(ready(), None)
