from execution_authorization_boundary_v0_1 import (
    AUTHORIZED,
    STANDING_MANDATE,
    VALID,
    evaluate_execution_authorization,
)


def _mandate(**overrides):
    value = {
        "execution_authorization": AUTHORIZED,
        "authorization_validation": VALID,
        "authorization_source": "MANAGEMENT_PHASE_ENTRY",
        "authorization_mode": STANDING_MANDATE,
        "authorization_id": "REAL-PROD-MANDATE-001",
        "mandate_id": "REAL-PROD-MANDATE-001",
        "issued_at": None,
        "expires_at": None,
        "mandate_expiry_policy": "NON_EXPIRING_STANDING_MANDATE",
        "environment": "REAL_PRODUCTION",
        "allowed_markets": ("SPOT", "FUTURES"),
    }
    value.update(overrides)
    return value


def test_non_expiring_standing_mandate_authorizes_only_ready_allowed_venue():
    result = evaluate_execution_authorization(
        {"readiness_state": "READY", "venue": "SPOT"},
        _mandate(),
    )
    assert result["authorization_state"] == AUTHORIZED
    assert result["mandate_id"] == "REAL-PROD-MANDATE-001"
    assert result["expires_at"] is None
    assert result["mandate_expiry_policy"] == "NON_EXPIRING_STANDING_MANDATE"


def test_explicit_expiry_is_still_validated_when_present():
    try:
        evaluate_execution_authorization(
            {"readiness_state": "READY", "venue": "SPOT"},
            _mandate(expires_at="2020-01-01T00:00:00+00:00"),
        )
    except ValueError as exc:
        assert str(exc) == "AUTHORIZATION_EXPIRED"
    else:
        raise AssertionError("expired explicitly timed mandate must be rejected")


def test_non_expiring_mandate_does_not_bypass_readiness_or_market_scope():
    try:
        evaluate_execution_authorization(
            {"readiness_state": "NOT_READY", "venue": "SPOT"},
            _mandate(),
        )
    except ValueError as exc:
        assert str(exc) == "READINESS_NOT_READY"
    else:
        raise AssertionError("standing mandate must not bypass readiness")

    try:
        evaluate_execution_authorization(
            {"readiness_state": "READY", "venue": "MARGIN"},
            _mandate(),
        )
    except ValueError as exc:
        assert str(exc) == "AUTHORIZATION_MARKET_NOT_ALLOWED"
    else:
        raise AssertionError("standing mandate must not widen market scope")
