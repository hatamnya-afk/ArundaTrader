"""CP39 — intelligence capital is independent from real account balance."""

from smart_risk_engine_v0_1 import build_smart_risk


def _policy():
    return {
        "policy_version": "CP39-CAPITAL-INDEPENDENCE-0.1",
        "policy_validation": "VALID",
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 2,
        "recommended_capital": 500.0,
        "strategy_capital_envelope": 1000.0,
        "capital_allocation_factor": 0.5,
        "capital_source": "TEST_STRATEGY_ENVELOPE",
    }


def _observation(balance):
    return {
        "asset": "BTC/USDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_distance": 10.0,
        "capital_state": "REAL_CAPITAL",
        "portfolio_capital": balance,
        "usable_capital": balance,
        "allocated_risk": 0.0,
        "concurrent_positions": 0,
    }


def test_zero_balance_does_not_zero_intelligence_output():
    result = build_smart_risk(_observation(0.0), _policy())

    assert result.risk_state == "APPROVED"
    assert result.risk_budget == 5.0
    assert result.position_size == 0.5
    assert result.exposure == 50.0


def test_positive_balance_does_not_replace_intelligence_output():
    zero = build_smart_risk(_observation(0.0), _policy())
    funded = build_smart_risk(_observation(250.0), _policy())

    assert funded.risk_state == "APPROVED"
    assert funded.risk_budget == zero.risk_budget
    assert funded.position_size == zero.position_size
    assert funded.exposure == zero.exposure


def test_actual_allocated_risk_remains_a_portfolio_constraint():
    observation = _observation(0.0)
    observation["allocated_risk"] = 26.0

    result = build_smart_risk(observation, _policy())

    assert result.risk_state == "BLOCKED"
    assert result.reason == "PORTFOLIO_RISK_CAPACITY_INVALID"
