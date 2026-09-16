import pytest

from smart_risk_policy_bridge_v0_1 import merge_validated_risk_policy


def test_valid_policy_is_explicit_and_preserved():
    policy = {
        "policy_version": "RISK-POLICY-v0.1",
        "policy_validation": "VALID",
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 3,
    }
    result = merge_validated_risk_policy(policy)
    assert result == policy


def test_missing_policy_version_fails_closed():
    with pytest.raises(ValueError, match="POLICY_VERSION_MISSING"):
        merge_validated_risk_policy({
            "policy_validation": "VALID",
            "risk_per_trade": 0.01,
            "max_portfolio_risk": 0.05,
            "max_concurrent_positions": 3,
        })


def test_unvalidated_policy_fails_closed():
    with pytest.raises(ValueError, match="POLICY_NOT_VALIDATED"):
        merge_validated_risk_policy({
            "policy_version": "RISK-POLICY-v0.1",
            "policy_validation": "PENDING",
            "risk_per_trade": 0.01,
            "max_portfolio_risk": 0.05,
            "max_concurrent_positions": 3,
        })


def test_invalid_policy_values_fail_closed():
    with pytest.raises(ValueError, match="RISK_PER_TRADE_INVALID"):
        merge_validated_risk_policy({
            "policy_version": "RISK-POLICY-v0.1",
            "policy_validation": "VALID",
            "risk_per_trade": 0,
            "max_portfolio_risk": 0.05,
            "max_concurrent_positions": 3,
        })


def test_policy_bridge_does_not_infer_or_mutate_values():
    policy = {
        "policy_version": "RISK-POLICY-v0.1",
        "policy_validation": "VALID",
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 3,
    }
    result = merge_validated_risk_policy(policy)
    assert result["risk_per_trade"] == 0.01
    assert result["max_portfolio_risk"] == 0.05
    assert result["max_concurrent_positions"] == 3
