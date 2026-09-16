"""CP38-D contract-boundary tests for RealCapitalObservation -> Smart Risk."""
import pytest

from real_capital_observation_contract_v0_1 import RealCapitalObservation
from smart_risk_engine_v0_1 import build_smart_risk


def _capital():
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


def _policy():
    return {
        "policy_version": "CP38-D-TEST",
        "policy_validation": "VALID",
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 5,
    }


def _observation():
    observation = _capital()
    return {
        "asset": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_distance": 10.0,
        "capital_state": observation.capital_state,
        "portfolio_capital": observation.portfolio_capital,
        "usable_capital": observation.usable_capital,
        "allocated_risk": observation.allocated_risk,
        "concurrent_positions": observation.concurrent_positions,
    }


def test_validated_real_capital_observation_can_feed_smart_risk():
    capital = _capital()
    assert capital.validate() is True
    result = build_smart_risk(_observation(), _policy())
    assert result.risk_state == "APPROVED"
    assert result.risk_budget == pytest.approx(100.0)


def test_capital_contract_does_not_require_provider_specific_fields():
    fields = set(_capital().__dataclass_fields__)
    assert not {"toobit", "api_key", "signature", "order"} & fields


def test_smart_risk_rejects_non_real_capital_at_boundary():
    observation = _observation()
    observation["capital_state"] = "TEST_CAPITAL"
    result = build_smart_risk(observation, _policy())
    assert result.risk_state == "BLOCKED"
    assert result.reason == "REAL_CAPITAL_NOT_AVAILABLE"


def test_smart_risk_consumes_capital_values_without_mutating_contract():
    capital = _capital()
    before = (capital.portfolio_capital, capital.usable_capital, capital.allocated_risk, capital.concurrent_positions)
    build_smart_risk(_observation(), _policy())
    after = (capital.portfolio_capital, capital.usable_capital, capital.allocated_risk, capital.concurrent_positions)
    assert after == before
