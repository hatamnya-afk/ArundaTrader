"""CP38-G RED tests: portfolio observation -> Smart Risk bridge."""
from smart_risk_portfolio_bridge_v0_1 import merge_validated_portfolio_observation


def valid_observation():
    return {
        "portfolio_capital": 10000.0,
        "usable_capital": 8000.0,
        "allocated_risk": 250.0,
        "concurrent_positions": 2,
        "portfolio_validation": "VALID",
        "portfolio_source": "REAL_PORTFOLIO_OBSERVATION",
        "observed_at": "2026-09-17T00:00:00+00:00",
        "provenance": "REAL_ACCOUNT_PORTFOLIO",
    }


def test_valid_portfolio_observation_is_mapped_explicitly():
    result = merge_validated_portfolio_observation(valid_observation())
    assert result == {
        "portfolio_capital": 10000.0,
        "usable_capital": 8000.0,
        "allocated_risk": 250.0,
        "concurrent_positions": 2,
    }


def test_missing_validation_fails_closed():
    obs = valid_observation()
    obs.pop("portfolio_validation")
    try:
        merge_validated_portfolio_observation(obs)
    except ValueError as exc:
        assert str(exc) == "PORTFOLIO_OBSERVATION_UNVALIDATED"
    else:
        raise AssertionError("expected fail-closed validation")


def test_invalid_capital_bounds_fail_closed():
    obs = valid_observation()
    obs["usable_capital"] = 10001.0
    try:
        merge_validated_portfolio_observation(obs)
    except ValueError as exc:
        assert str(exc) == "USABLE_CAPITAL_INVALID"
    else:
        raise AssertionError("expected fail-closed capital bounds")


def test_invalid_allocated_risk_and_concurrency_fail_closed():
    obs = valid_observation()
    obs["allocated_risk"] = -1.0
    try:
        merge_validated_portfolio_observation(obs)
    except ValueError as exc:
        assert str(exc) == "ALLOCATED_RISK_INVALID"
    else:
        raise AssertionError("expected fail-closed allocated risk")

    obs = valid_observation()
    obs["concurrent_positions"] = True
    try:
        merge_validated_portfolio_observation(obs)
    except ValueError as exc:
        assert str(exc) == "CONCURRENT_POSITIONS_INVALID"
    else:
        raise AssertionError("expected fail-closed concurrency")


def test_source_and_provenance_are_required():
    obs = valid_observation()
    obs["portfolio_source"] = "TEST"
    try:
        merge_validated_portfolio_observation(obs)
    except ValueError as exc:
        assert str(exc) == "PORTFOLIO_SOURCE_INVALID"
    else:
        raise AssertionError("expected fail-closed source")
