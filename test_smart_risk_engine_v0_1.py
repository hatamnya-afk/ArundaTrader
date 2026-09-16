"""CP38-C — Smart Risk Engine deterministic and fail-closed tests."""
from smart_risk_engine_v0_1 import build_smart_risk


def base_observation():
    return {
        "asset": "BTC/USDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_distance": 2.0,
        "capital_state": "REAL_CAPITAL",
        "portfolio_capital": 10000.0,
        "usable_capital": 10000.0,
        "allocated_risk": 0.0,
        "concurrent_positions": 0,
    }


def base_policy():
    return {
        "policy_validation": "VALID",
        "policy_version": "CP38-POLICY-0.1",
        "risk_per_trade": 0.005,
        "max_portfolio_risk": 0.01,
        "max_concurrent_positions": 2,
    }


def test_cp38c_calculates_risk_budget_position_size_and_exposure():
    result = build_smart_risk(base_observation(), base_policy())
    assert result.risk_state == "APPROVED"
    assert result.risk_budget == 50.0
    assert result.position_size == 25.0
    assert result.exposure == 2500.0
    assert result.remaining_portfolio_risk == 100.0


def test_cp38c_caps_new_risk_by_remaining_portfolio_capacity():
    observation = base_observation()
    observation["allocated_risk"] = 80.0
    result = build_smart_risk(observation, base_policy())
    assert result.risk_state == "APPROVED"
    assert result.risk_budget == 20.0
    assert result.position_size == 10.0


def test_cp38c_requires_real_capital():
    observation = base_observation()
    observation["capital_state"] = "UNAVAILABLE_CAPITAL"
    result = build_smart_risk(observation, base_policy())
    assert result.risk_state == "BLOCKED"
    assert result.reason == "REAL_CAPITAL_NOT_AVAILABLE"


def test_cp38c_requires_validated_policy():
    policy = base_policy()
    policy["policy_validation"] = "UNVALIDATED"
    result = build_smart_risk(base_observation(), policy)
    assert result.risk_state == "BLOCKED"
    assert result.reason == "RISK_POLICY_UNVALIDATED"


def test_cp38c_requires_explicit_stop_distance():
    observation = base_observation()
    observation.pop("stop_distance")
    result = build_smart_risk(observation, base_policy())
    assert result.risk_state == "BLOCKED"
    assert result.reason == "STOP_DISTANCE_NOT_EXPLICIT"


def test_cp38c_never_uses_invalid_adjustment_as_neutral():
    observation = base_observation()
    observation["liquidity_adjustment"] = 1.5
    result = build_smart_risk(observation, base_policy())
    assert result.risk_state == "BLOCKED"
    assert result.reason == "LIQUIDITY_ADJUSTMENT_INVALID"


def test_cp38c_adjustments_only_reduce_risk():
    observation = base_observation()
    observation["correlation_adjustment"] = 0.5
    observation["liquidity_adjustment"] = 0.8
    result = build_smart_risk(observation, base_policy())
    assert result.risk_state == "APPROVED"
    assert result.risk_budget == 20.0


def test_cp38c_blocks_concurrent_position_limit():
    observation = base_observation()
    observation["concurrent_positions"] = 2
    result = build_smart_risk(observation, base_policy())
    assert result.risk_state == "BLOCKED"
    assert result.reason == "MAX_CONCURRENT_POSITIONS_REACHED"


def test_cp38c_never_exceeds_usable_capital():
    observation = base_observation()
    observation["usable_capital"] = 10.0
    result = build_smart_risk(observation, base_policy())
    assert result.risk_state == "BLOCKED"
    assert result.reason == "USABLE_CAPITAL_EXCEEDED"


def test_cp38c_does_not_create_execution_fields():
    result = build_smart_risk(base_observation(), base_policy())
    forbidden = {"order_intent", "execution", "exchange", "order_id"}
    assert not (forbidden & set(vars(result)))
