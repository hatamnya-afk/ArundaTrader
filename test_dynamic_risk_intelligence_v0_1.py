import pytest

from dynamic_risk_intelligence_v0_1 import (
    MAX_PORTFOLIO_RISK_CEILING,
    POLICY_VERSION,
    build_dynamic_risk_policy,
)


def market_data():
    return {
        "AAA/USDT": [
            {"close": 100.0, "volume": 100.0},
            {"close": 101.0, "volume": 120.0},
            {"close": 102.0, "volume": 110.0},
            {"close": 103.0, "volume": 130.0},
            {"close": 104.0, "volume": 125.0},
            {"close": 105.0, "volume": 140.0},
        ],
        "BBB/USDT": [
            {"close": 100.0, "volume": 100.0},
            {"close": 99.0, "volume": 100.0},
            {"close": 101.0, "volume": 100.0},
            {"close": 100.0, "volume": 100.0},
            {"close": 102.0, "volume": 100.0},
            {"close": 101.0, "volume": 100.0},
        ],
    }


def test_dynamic_policy_is_valid_and_bounded():
    result = build_dynamic_risk_policy(
        asset="AAA",
        decision={"state": "ACTIONABLE", "direction": "LONG"},
        opportunity={"confidence": 0.8},
        entry_price=105.0,
        stop_distance=5.0,
        market_data_by_symbol=market_data(),
    )
    assert result["policy_version"] == POLICY_VERSION
    assert result["policy_validation"] == "VALID"
    assert 0.0 < result["risk_per_trade"] <= MAX_PORTFOLIO_RISK_CEILING
    assert result["max_portfolio_risk"] == MAX_PORTFOLIO_RISK_CEILING
    assert result["max_concurrent_positions"] >= 1
    assert set(result["risk_factors"]) == {
        "confidence", "volatility", "liquidity", "correlation", "execution"
    }


def test_dynamic_policy_changes_with_confidence():
    low = build_dynamic_risk_policy(
        asset="AAA",
        decision={"state": "ACTIONABLE", "direction": "LONG"},
        opportunity={"confidence": 0.4},
        entry_price=105.0,
        stop_distance=5.0,
        market_data_by_symbol=market_data(),
    )
    high = build_dynamic_risk_policy(
        asset="AAA",
        decision={"state": "ACTIONABLE", "direction": "LONG"},
        opportunity={"confidence": 0.9},
        entry_price=105.0,
        stop_distance=5.0,
        market_data_by_symbol=market_data(),
    )
    assert high["risk_per_trade"] > low["risk_per_trade"]


def test_dynamic_policy_fails_closed_without_real_context():
    with pytest.raises(ValueError, match="DYNAMIC_RISK_CONTEXT_INCOMPLETE"):
        build_dynamic_risk_policy(
            asset="AAA",
            decision={"state": "ACTIONABLE", "direction": "LONG"},
            opportunity={"confidence": 0.8},
            entry_price=105.0,
            stop_distance=5.0,
            market_data_by_symbol={},
        )


def test_non_actionable_decision_is_rejected():
    with pytest.raises(ValueError, match="DECISION_NOT_ACTIONABLE"):
        build_dynamic_risk_policy(
            asset="AAA",
            decision={"state": "HOLD", "direction": "NONE"},
            opportunity={"confidence": 0.8},
            entry_price=105.0,
            stop_distance=5.0,
            market_data_by_symbol=market_data(),
        )
