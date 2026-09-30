"""CP39 — Dynamic Smart Risk boundary fail-closed direction contract tests."""

from dynamic_smart_risk_contract_boundary_v0_1 import build_dynamic_smart_risk


def decision():
    return {
        "state": "ACTIONABLE",
        "direction": "LONG",
    }


def observation():
    return {
        "entry_price": 100.0,
        "invalidation_price": 98.0,
        "capital_state": "REAL_CAPITAL",
        "portfolio_capital": 0.0,
        "usable_capital": 0.0,
        "allocated_risk": 0.0,
        "concurrent_positions": 0,
    }


def policy():
    return {
        "policy_validation": "VALID",
        "policy_version": "CP38-POLICY-0.1",
        "risk_per_trade": 0.005,
        "max_portfolio_risk": 0.01,
        "max_concurrent_positions": 2,
    }


def test_blocked_smart_risk_does_not_require_direction_identity():
    result = build_dynamic_smart_risk(
        "BTC/USDT",
        decision(),
        observation(),
        policy(),
    )
    assert result.risk_state == "BLOCKED"
    assert result.reason == "RISK_BUDGET_ZERO"
    assert result.direction is None


def test_approved_smart_risk_preserves_decision_direction():
    observed = observation()
    observed["portfolio_capital"] = 10_000.0
    observed["usable_capital"] = 10_000.0
    result = build_dynamic_smart_risk(
        "BTC/USDT",
        decision(),
        observed,
        policy(),
    )
    assert result.risk_state == "APPROVED"
    assert result.direction == "LONG"
