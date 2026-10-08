from management_review_package_v0_1 import (
    REAL_PRODUCTION,
    build_management_review_package,
)


def _base(**overrides):
    data = {
        "mandate_id": "MANDATE-001",
        "decision": "AUTHORIZED",
        "authorized_by": "MANAGEMENT",
        "authorization_source": "EXPLICIT_MANAGEMENT_DECISION",
        "environment": REAL_PRODUCTION,
        "allowed_markets": ["SPOT", "FUTURES"],
        "provider": "TOOBIT",
        "capital_policy": "ZERO_INITIAL_CAPITAL; SCALE_ONLY_AFTER_VALIDATED_QUALITY",
        "evidence_required_before": ["decision", "trade_gate", "provider_readiness"],
        "evidence_required_after": ["provider_response", "outcome"],
    }
    data.update(overrides)
    return data


def test_authorized_is_standing_mandate():
    result = build_management_review_package(**_base())
    assert result["management_state"] == "AUTHORIZED"
    assert result["autonomous_operation"] is True
    assert result["per_trade_management_authorization_required"] is False
    assert result["execution_authorization"] == "AUTHORIZED_STANDING_MANDATE"


def test_both_spot_and_futures_are_allowed():
    result = build_management_review_package(**_base())
    assert result["allowed_markets"] == ("SPOT", "FUTURES")


def test_provider_is_authoritative_for_rejection():
    result = build_management_review_package(**_base())
    assert result["provider_rejection_is_authoritative"] is True


def test_zero_capital_is_a_policy_not_a_local_trade_blocker():
    result = build_management_review_package(**_base())
    assert "ZERO_INITIAL_CAPITAL" in result["capital_policy"]


def test_denied_does_not_authorize():
    result = build_management_review_package(**_base(decision="DENIED"))
    assert result["autonomous_operation"] is False
    assert result["execution_authorization"] is False


def test_deferred_does_not_authorize():
    result = build_management_review_package(**_base(decision="DEFERRED"))
    assert result["autonomous_operation"] is False
    assert result["execution_authorization"] is False


def test_rejects_unknown_market():
    try:
        build_management_review_package(**_base(allowed_markets=["SPOT", "OPTIONS"]))
    except ValueError as exc:
        assert "allowed_markets" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_requires_before_evidence():
    try:
        build_management_review_package(**_base(evidence_required_before=[]))
    except ValueError as exc:
        assert "evidence" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_requires_after_evidence():
    try:
        build_management_review_package(**_base(evidence_required_after=[]))
    except ValueError as exc:
        assert "evidence" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_requires_real_production():
    try:
        build_management_review_package(**_base(environment="SIMULATION"))
    except ValueError as exc:
        assert "REAL_PRODUCTION" in str(exc)
    else:
        raise AssertionError("expected ValueError")
