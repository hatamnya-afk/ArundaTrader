from management_execution_authorization_v0_1 import (
    AUTHORIZED,
    DENIED,
    evaluate_management_authorization,
)


def _base(decision="AUTHORIZED"):
    return {
        "decision": decision,
        "authorization_id": "MGT-AUTH-001",
        "attempt_id": "ATTEMPT-001",
        "authorized_by": "MANAGEMENT",
        "authorization_source": "MANAGEMENT_AUTHORIZATION",
        "environment": "REAL_PRODUCTION",
        "issued_at": "2026-10-08T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "authorization_scope": {
            "venue": "FUTURES",
            "execution_instrument": "BTC-SWAP-USDT",
            "asset": "BTC",
            "direction": "LONG",
            "order_type": "MARKET",
            "quantity": 1.0,
            "max_exposure": 100.0,
        },
        "evidence_required_before": ["provider_readiness"],
        "evidence_required_after": ["order_state", "account_state"],
    }


def test_explicit_management_authorization_is_bounded():
    result = evaluate_management_authorization(_base())
    assert result["management_state"] == AUTHORIZED
    assert result["execution_authorization"] is False
    assert result["authorization_observation"]["execution_authorization"] == "AUTHORIZED"
    assert result["authorization_observation"]["attempt_id"] == "ATTEMPT-001"


def test_denied_management_decision_never_produces_execution_authorization():
    result = evaluate_management_authorization(_base(DENIED))
    assert result["management_state"] == DENIED
    assert result["execution_authorization"] is False
    assert result["authorization_observation"] is None


def test_management_authorization_requires_real_production_environment():
    value = _base()
    value["environment"] = "TEST"
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_ENVIRONMENT_INVALID"
    else:
        raise AssertionError("TEST environment must be rejected")


def test_management_authorization_requires_unique_attempt():
    value = _base()
    value["attempt_id"] = ""
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_ATTEMPT_ID_INVALID"
    else:
        raise AssertionError("missing attempt identity must be rejected")


def test_management_authorization_requires_future_expiry():
    value = _base()
    value["expires_at"] = "2020-01-01T00:00:00+00:00"
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_AUTHORIZATION_EXPIRED"
    else:
        raise AssertionError("expired authorization must be rejected")


def test_management_authorization_requires_expiry_after_issuance():
    value = _base()
    value["issued_at"] = "2099-01-01T00:00:00+00:00"
    value["expires_at"] = "2099-01-01T00:00:00+00:00"
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_EXPIRY_BEFORE_ISSUANCE"
    else:
        raise AssertionError("non-forward expiry must be rejected")


def test_management_authorization_requires_complete_scope():
    value = _base()
    del value["authorization_scope"]["execution_instrument"]
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_SCOPE_EXECUTION_INSTRUMENT_MISSING"
    else:
        raise AssertionError("incomplete scope must be rejected")


def test_management_authorization_requires_positive_quantity():
    value = _base()
    value["authorization_scope"]["quantity"] = 0
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_SCOPE_QUANTITY_INVALID"
    else:
        raise AssertionError("invalid quantity must be rejected")


def test_management_authorization_requires_exposure_bound():
    value = _base()
    value["authorization_scope"]["max_exposure"] = 0
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_SCOPE_MAX_EXPOSURE_INVALID"
    else:
        raise AssertionError("invalid exposure bound must be rejected")


def test_management_authorization_requires_evidence_contract():
    value = _base()
    value["evidence_required_before"] = []
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_EVIDENCE_BEFORE_INVALID"
    else:
        raise AssertionError("before-attempt evidence must be explicit")
