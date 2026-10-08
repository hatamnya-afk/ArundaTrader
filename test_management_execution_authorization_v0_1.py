from management_execution_authorization_v0_1 import (
    AUTHORIZED,
    DEFERRED,
    DENIED,
    STANDING_MANDATE,
    evaluate_management_authorization,
)


def _base(decision="AUTHORIZED"):
    return {
        "decision": decision,
        "mandate_id": "REAL-PROD-MANDATE-001",
        "authorized_by": "MANAGEMENT",
        "authorization_source": "MANAGEMENT_PHASE_ENTRY",
        "environment": "REAL_PRODUCTION",
        "issued_at": "2026-10-08T00:00:00+00:00",
        "expires_at": "2099-01-01T00:00:00+00:00",
        "allowed_markets": ["SPOT", "FUTURES"],
        "provider": "TOOBIT",
        "capital_policy": "ZERO_INITIAL_CAPITAL_PROVIDER_FEEDBACK_THEN_PROGRESSIVE_SCALING",
        "evidence_required_before": ["canonical_order_path", "provider_readiness"],
        "evidence_required_after": ["provider_response", "fill_or_not_filled", "outcome"],
    }


def test_management_authorization_is_one_time_phase_entry_mandate():
    result = evaluate_management_authorization(_base())
    assert result["management_state"] == AUTHORIZED
    assert result["execution_authorization"] == "AUTHORIZED_STANDING_MANDATE"
    assert result["autonomous_operation"] is True
    assert result["per_trade_management_authorization_required"] is False
    assert result["authorization_observation"]["authorization_mode"] == STANDING_MANDATE
    assert "attempt_id" not in result["authorization_observation"]


def test_management_boundary_rejects_trade_scoped_fields():
    for field in (
        "attempt_id",
        "asset",
        "direction",
        "order_type",
        "quantity",
        "per_order_exposure",
        "exposure",
    ):
        value = _base()
        value[field] = "TRADE-SCOPED"
        try:
            evaluate_management_authorization(value)
        except ValueError as exc:
            assert str(exc) == "MANAGEMENT_TRADE_SCOPE_FIELDS_FORBIDDEN"
        else:
            raise AssertionError(f"{field} must never enter management authorization")


def test_management_boundary_rejects_trade_field_aliases_and_unknown_scope():
    for field in (
        "attemptId",
        "trade_id",
        "tradeId",
        "symbol",
        "side",
        "orderType",
        "qty",
        "exposure_usd",
    ):
        value = _base()
        value[field] = "TRADE-SCOPED"
        try:
            evaluate_management_authorization(value)
        except ValueError as exc:
            assert str(exc) == "MANAGEMENT_TRADE_SCOPE_FIELDS_FORBIDDEN"
        else:
            raise AssertionError(f"{field} must never enter management authorization")

    value = _base()
    value["future_unclassified_field"] = "UNKNOWN"
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_FIELDS_FORBIDDEN"
    else:
        raise AssertionError("unclassified management fields must fail closed")


def test_denied_management_decision_never_produces_execution_authorization():
    result = evaluate_management_authorization(_base(DENIED))
    assert result["management_state"] == DENIED
    assert result["execution_authorization"] is False
    assert result["authorization_observation"] is None


def test_deferred_management_decision_never_produces_execution_authorization():
    result = evaluate_management_authorization(_base(DEFERRED))
    assert result["management_state"] == DEFERRED
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


def test_management_authorization_requires_future_expiry():
    value = _base()
    value["expires_at"] = "2020-01-01T00:00:00+00:00"
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_MANDATE_EXPIRED"
    else:
        raise AssertionError("expired mandate must be rejected")


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


def test_management_authorization_requires_both_spot_and_futures():
    value = _base()
    value["allowed_markets"] = ["FUTURES"]
    try:
        evaluate_management_authorization(value)
    except ValueError as exc:
        assert str(exc) == "MANAGEMENT_SPOT_FUTURES_SCOPE_INVALID"
    else:
        raise AssertionError("standing mandate must cover Spot and Futures")


def test_management_authorization_requires_provider_and_capital_policy():
    for field in ("provider", "capital_policy"):
        value = _base()
        value[field] = ""
        try:
            evaluate_management_authorization(value)
        except ValueError as exc:
            assert str(exc).startswith("MANAGEMENT_")
        else:
            raise AssertionError(f"{field} must be required")


def test_management_authorization_requires_evidence_contract():
    for field, reason in (
        ("evidence_required_before", "MANAGEMENT_EVIDENCE_BEFORE_INVALID"),
        ("evidence_required_after", "MANAGEMENT_EVIDENCE_AFTER_INVALID"),
    ):
        value = _base()
        value[field] = []
        try:
            evaluate_management_authorization(value)
        except ValueError as exc:
            assert str(exc) == reason
        else:
            raise AssertionError(f"{field} must be explicit")


def test_management_output_contains_only_standing_mandate_scope():
    result = evaluate_management_authorization(_base())
    observation = result["authorization_observation"]
    assert observation["authorization_mode"] == STANDING_MANDATE
    assert "attempt_id" not in observation
    assert "asset" not in observation
    assert "direction" not in observation
    assert "order_type" not in observation
    assert "quantity" not in observation
    assert "exposure" not in observation
