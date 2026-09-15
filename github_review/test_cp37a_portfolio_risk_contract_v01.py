from dataclasses import FrozenInstanceError
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from portfolio_risk_contract_v0_1 import PortfolioRisk
from trade_management_contract_common import CapitalState


def _base_kwargs():
    return {
        "portfolio_id": "portfolio-main",
        "capital_state": CapitalState.UNAVAILABLE_CAPITAL,
        "portfolio_capital": None,
        "usable_capital": None,
        "total_risk": None,
        "allocated_risk": None,
        "remaining_risk_capacity": None,
        "total_exposure": None,
        "remaining_exposure_capacity": None,
        "concurrent_positions": None,
        "concentration": None,
        "correlation_exposure": None,
        "liquidity_state": None,
        "constraints": None,
        "portfolio_risk_state": None,
        "policy_version": None,
    }


def test_all_cp37_fields_can_be_represented():
    obj = PortfolioRisk(
        **_base_kwargs(),
        capital_state=CapitalState.REAL_CAPITAL,
        portfolio_capital=1000.0,
        usable_capital=800.0,
        total_risk=10.0,
        allocated_risk=4.0,
        remaining_risk_capacity=6.0,
        total_exposure=500.0,
        remaining_exposure_capacity=300.0,
        concurrent_positions=2,
        concentration={"AAA/USDT": 0.4},
        correlation_exposure={"group_a": 0.5},
        liquidity_state="OBSERVED",
        constraints={"source": "observed"},
        portfolio_risk_state="OBSERVED",
        policy_version="UNVALIDATED",
    )
    assert obj.validate() is True


def test_optional_unavailable_fields_remain_none():
    obj = PortfolioRisk(**_base_kwargs())
    assert obj.remaining_risk_capacity is None
    assert obj.remaining_exposure_capacity is None
    assert obj.liquidity_state is None
    assert obj.constraints is None
    assert obj.policy_version is None
    assert obj.validate() is True


def test_invalid_portfolio_identity_fails():
    data = _base_kwargs()
    data["portfolio_id"] = ""
    with pytest.raises((ValueError, TypeError)):
        PortfolioRisk(**data).validate()


def test_invalid_portfolio_state_fails_closed():
    data = _base_kwargs()
    data["portfolio_risk_state"] = 123
    with pytest.raises((ValueError, TypeError)):
        PortfolioRisk(**data).validate()


def test_dynamic_arbitrary_portfolio_and_assets_pass():
    data = _base_kwargs()
    data["portfolio_id"] = "arbitrary-portfolio"
    data["concentration"] = {"AAA/USDT": 0.2, "ZZZ/USDT": 0.3}
    data["correlation_exposure"] = {"AAA/USDT|ZZZ/USDT": "OBSERVED"}
    obj = PortfolioRisk(**data)
    assert obj.validate() is True
    assert set(obj.concentration) == {"AAA/USDT", "ZZZ/USDT"}


def test_fixed_15_and_expected_assets_are_absent_from_contract_semantics():
    field_names = set(PortfolioRisk.__dataclass_fields__)
    assert "EXPECTED_ASSETS" not in field_names
    assert not any(name.lower() == "expected_assets" for name in field_names)
    assert not any("fixed_15" in name.lower() for name in field_names)


def test_provider_neutrality():
    source = Path(__file__).with_name("portfolio_risk_contract_v0_1.py").read_text(encoding="utf-8").lower()
    for provider in ("kucoin", "bitget", "toobit"):
        assert provider not in source


def test_test_capital_is_not_a_production_default():
    obj = PortfolioRisk(**_base_kwargs())
    assert obj.capital_state is CapitalState.UNAVAILABLE_CAPITAL
    assert obj.portfolio_capital is None
    assert obj.usable_capital is None


def test_deterministic_representation():
    kwargs = _base_kwargs()
    a = PortfolioRisk(**kwargs)
    b = PortfolioRisk(**kwargs)
    assert a == b
    assert a.to_dict() == b.to_dict()


def test_immutable_behavior():
    obj = PortfolioRisk(**_base_kwargs())
    with pytest.raises(FrozenInstanceError):
        obj.portfolio_id = "changed"


def test_contract_does_not_calculate_capacity_or_risk():
    data = _base_kwargs()
    data["portfolio_capital"] = 1_000_000.0
    data["usable_capital"] = 1_000_000.0
    obj = PortfolioRisk(**data)
    assert obj.remaining_risk_capacity is None
    assert obj.remaining_exposure_capacity is None
    assert obj.allocated_risk is None
    assert obj.total_exposure is None


def test_contract_is_db_network_and_execution_semantics_free():
    source = Path(__file__).with_name("portfolio_risk_contract_v0_1.py").read_text(encoding="utf-8").lower()
    forbidden = (
        "sqlite", "sql", "requests", "urllib", "http", "order_intent",
        "execution", "position_size", "position_sizing", "buy", "sell",
        "exit", "close", "reduce", "calculate", "capital_config",
    )
    for token in forbidden:
        assert token not in source


def test_policy_fields_are_observation_only():
    data = _base_kwargs()
    data["policy_version"] = "UNVALIDATED"
    obj = PortfolioRisk(**data)
    assert obj.policy_version == "UNVALIDATED"
    assert obj.remaining_risk_capacity is None
    assert obj.remaining_exposure_capacity is None
