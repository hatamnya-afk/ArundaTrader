"""CP38-D contract-boundary tests for RealCapitalObservation -> Smart Risk."""
import pytest

from real_capital_observation_contract_v0_1 import RealCapitalObservation
from smart_risk_capital_bridge_v0_1 import merge_real_capital_observation
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


def _market():
    return {"asset": "BTCUSDT", "direction": "LONG", "entry_price": 100.0, "stop_distance": 10.0}


def test_validated_capital_is_explicitly_mapped_to_smart_risk_inputs():
    capital = _capital()
    mapped = merge_real_capital_observation(_market(), capital)
    result = build_smart_risk(mapped, _policy())
    assert result.risk_state == "APPROVED"
    assert result.risk_budget == pytest.approx(100.0)


def test_bridge_requires_valid_real_capital():
    capital = _capital()
    object.__setattr__(capital, "capital_state", "TEST_CAPITAL")
    with pytest.raises(ValueError, match="REAL_CAPITAL"):
        merge_real_capital_observation(_market(), capital)


def test_bridge_does_not_mutate_source_or_market_observation():
    capital = _capital()
    market = _market()
    before_capital = (capital.portfolio_capital, capital.usable_capital, capital.allocated_risk, capital.concurrent_positions)
    before_market = dict(market)
    mapped = merge_real_capital_observation(market, capital)
    assert mapped is not market
    assert (capital.portfolio_capital, capital.usable_capital, capital.allocated_risk, capital.concurrent_positions) == before_capital
    assert market == before_market


def test_bridge_has_no_provider_or_execution_surface():
    mapped = merge_real_capital_observation(_market(), _capital())
    assert not any(key in mapped for key in ("api_key", "signature", "order", "execution", "toobit"))
