import pytest

from real_production_phase_readiness_v0_1 import evaluate_phase_entry_readiness


def _evaluate(**overrides):
    values = {
        "environment": "REAL_PRODUCTION",
        "management_decision": "PENDING",
        "allowed_markets": ("SPOT", "FUTURES"),
        "canonical_order_path_verified": True,
        "execution_attempt_contract_verified": True,
        "provider_read_only_evidence_verified": True,
        "decision_risk_trade_gate_verified": True,
        "zero_balance_allowed": True,
        "no_per_trade_management_approval": True,
        "evidence_requirements": ("canonical_order_path", "provider_readiness"),
    }
    values.update(overrides)
    return evaluate_phase_entry_readiness(**values)


@pytest.mark.parametrize("decision", ("PENDING", "AUTHORIZED", "DENIED", "DEFERRED"))
def test_readiness_never_issues_or_mirrors_execution_authorization(decision):
    result = _evaluate(management_decision=decision)

    assert result["ready"] is True
    assert result["management_decision"] == decision
    assert "execution_authorization" not in result
    assert "authorization_observation" not in result


def test_wrong_environment_fails_closed():
    result = _evaluate(environment="TEST")

    assert result == {
        "ready": False,
        "blocker": "ENVIRONMENT_NOT_REAL_PRODUCTION",
    }


def test_incomplete_market_scope_fails_closed():
    result = _evaluate(allowed_markets=("SPOT",))

    assert result == {
        "ready": False,
        "blocker": "SPOT_FUTURES_SCOPE_INCOMPLETE",
    }


def test_missing_provider_evidence_fails_closed():
    result = _evaluate(provider_read_only_evidence_verified=False)

    assert result == {
        "ready": False,
        "blocker": "PROVIDER_READ_ONLY_EVIDENCE_NOT_VERIFIED",
    }


def test_empty_evidence_requirements_fail_closed():
    result = _evaluate(evidence_requirements=())

    assert result == {
        "ready": False,
        "blocker": "EVIDENCE_REQUIREMENTS_EMPTY",
    }
