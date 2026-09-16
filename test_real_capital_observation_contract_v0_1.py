"""CP38-C focused tests for the real capital observation contract."""
import pytest

from real_capital_observation_contract_v0_1 import RealCapitalObservation


def _valid():
    return RealCapitalObservation(
        capital_state="REAL_CAPITAL",
        portfolio_capital=10000.0,
        usable_capital=8000.0,
        allocated_risk=100.0,
        concurrent_positions=1,
        source="ACCOUNT_BALANCE_PRODUCER",
        observed_at="2026-09-17T00:00:00+00:00",
        provenance={"provider": "PROVIDER_BOUNDARY", "mode": "READ_ONLY"},
        validation="VALID",
    )


def test_valid_real_capital_observation():
    observation = _valid()
    assert observation.validate() is True


def test_non_real_capital_blocks():
    observation = _valid()
    object.__setattr__(observation, "capital_state", "TEST_CAPITAL")
    with pytest.raises(ValueError, match="REAL_CAPITAL"):
        observation.validate()


def test_invalid_validation_state_blocks():
    observation = _valid()
    object.__setattr__(observation, "validation", "INVALID")
    with pytest.raises(ValueError, match="VALID"):
        observation.validate()


def test_usable_capital_cannot_exceed_portfolio_capital():
    observation = _valid()
    object.__setattr__(observation, "usable_capital", 10001.0)
    with pytest.raises(ValueError, match="usable_capital"):
        observation.validate()


def test_missing_provenance_blocks():
    observation = _valid()
    object.__setattr__(observation, "provenance", {})
    with pytest.raises(ValueError, match="provenance"):
        observation.validate()


def test_negative_allocated_risk_blocks():
    observation = _valid()
    object.__setattr__(observation, "allocated_risk", -1.0)
    with pytest.raises(ValueError, match="allocated_risk"):
        observation.validate()


def test_negative_concurrent_positions_blocks():
    observation = _valid()
    object.__setattr__(observation, "concurrent_positions", -1)
    with pytest.raises(ValueError, match="concurrent_positions"):
        observation.validate()


def test_missing_source_blocks():
    observation = _valid()
    object.__setattr__(observation, "source", "")
    with pytest.raises(ValueError, match="source"):
        observation.validate()


def test_contract_has_no_order_or_execution_fields():
    observation = _valid()
    assert not hasattr(observation, "order")
    assert not hasattr(observation, "order_intent")
    assert not hasattr(observation, "execution")
