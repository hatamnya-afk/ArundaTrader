from __future__ import annotations

import pytest

from real_capital_observation_contract_v0_1 import RealCapitalObservation
from dynamic_smart_risk_sizing_boundary_v0_1 import (
    build_dynamic_smart_risk_decision,
    to_dynamic_risk_sizing_fields,
)


def inputs():
    capital = RealCapitalObservation(
        capital_state="REAL_CAPITAL",
        portfolio_capital=10000.0,
        usable_capital=8000.0,
        allocated_risk=250.0,
        concurrent_positions=2,
        source="REAL_ACCOUNT_PORTFOLIO",
        observed_at="2026-10-13T10:00:00+00:00",
        provenance={"source": "ACCOUNT_OBSERVATION", "id": "CAP-OBS-1"},
        validation="VALID",
    )
    portfolio = {
        "portfolio_state": "AVAILABLE",
        "portfolio_validation": "VALID",
        "portfolio_source": "REAL_ACCOUNT_PORTFOLIO",
        "provenance": "PORTFOLIO_OBS-1",
        "asset_scope": "USDT",
        "portfolio_capital": 10000.0,
        "usable_capital": 8000.0,
        "allocated_risk": 250.0,
        "concurrent_positions": 2,
        "observed_at": "2026-10-13T10:00:00+00:00",
    }
    stop = {
        "observation_state": "AVAILABLE",
        "observation_validation": "VALID",
        "observation_source": "VALIDATED_STOP_POLICY",
        "provenance": "STOP-OBS-1",
        "asset": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 60000.0,
        "stop_price": 59000.0,
        "stop_distance": 1000.0,
        "risk_policy_version": "RISK_POLICY_V1",
        "risk_policy_validation": "VALID",
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 3,
        "observed_at": "2026-10-13T10:00:00+00:00",
    }
    policy = {
        "policy_version": "RISK_POLICY_V1",
        "policy_validation": "VALID",
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 3,
    }
    return {
        "asset": "BTC/USDT",
        "direction": "LONG",
        "entry_price": 60000.0,
        "capital": capital,
        "portfolio_observation": portfolio,
        "stop_policy_observation": stop,
        "risk_policy": policy,
    }


def test_validated_dynamic_inputs_produce_smart_risk_sizing():
    decision = build_dynamic_smart_risk_decision(**inputs())
    assert decision.risk_state == "APPROVED"
    assert decision.position_size == pytest.approx(0.1)
    assert decision.exposure == pytest.approx(6000.0)
    assert decision.risk_budget == pytest.approx(100.0)
    fields = to_dynamic_risk_sizing_fields(decision)
    assert fields["position_quantity"] == pytest.approx(0.1)
    assert fields["quantity_unit"] == "BASE_ASSET"
    assert fields["quantity_source"] == "SMART_RISK_ENGINE_V0_1"
    assert fields["quantity_rounded"] is False
    assert fields["quantity_clipped"] is False


def test_capital_portfolio_disagreement_fails_closed():
    args = inputs()
    args["portfolio_observation"] = {
        **args["portfolio_observation"],
        "usable_capital": 7000.0,
    }
    with pytest.raises(ValueError, match="SMART_RISK_CAPITAL_PORTFOLIO_MISMATCH:usable_capital"):
        build_dynamic_smart_risk_decision(**args)


def test_stop_asset_direction_and_entry_must_match_current_candidate():
    args = inputs()
    args["stop_policy_observation"] = {
        **args["stop_policy_observation"],
        "asset": "ETHUSDT",
    }
    with pytest.raises(ValueError, match="SMART_RISK_STOP_ASSET_MISMATCH"):
        build_dynamic_smart_risk_decision(**args)

    args = inputs()
    args["stop_policy_observation"] = {
        **args["stop_policy_observation"],
        "entry_price": 61000.0,
        "stop_distance": 2000.0,
    }
    with pytest.raises(ValueError, match="SMART_RISK_STOP_ENTRY_MISMATCH"):
        build_dynamic_smart_risk_decision(**args)


def test_policy_must_match_validated_stop_policy_observation():
    args = inputs()
    args["risk_policy"] = {
        **args["risk_policy"],
        "risk_per_trade": 0.02,
    }
    with pytest.raises(ValueError, match="SMART_RISK_POLICY_SOURCE_MISMATCH"):
        build_dynamic_smart_risk_decision(**args)


def test_missing_or_invalid_sources_fail_closed():
    args = inputs()
    args["stop_policy_observation"] = {
        **args["stop_policy_observation"],
        "observation_source": "SIMULATED",
    }
    with pytest.raises(ValueError, match="OBSERVATION_SOURCE_INVALID"):
        build_dynamic_smart_risk_decision(**args)

    args = inputs()
    args["portfolio_observation"] = {
        **args["portfolio_observation"],
        "portfolio_validation": "INVALID",
    }
    with pytest.raises(ValueError, match="PORTFOLIO_OBSERVATION_UNVALIDATED"):
        build_dynamic_smart_risk_decision(**args)


def test_invalid_risk_decision_cannot_be_mapped_to_dynamic_quantity():
    from smart_risk_contract_v0_1 import SmartRiskDecision

    blocked = SmartRiskDecision(
        asset="BTC", direction=None, entry_price=None, stop_distance=None,
        risk_budget=None, position_size=None, exposure=None,
        remaining_portfolio_risk=None, concurrent_positions=None,
        max_concurrent_positions=None, risk_state="BLOCKED",
        reason="SOURCE_MISSING", policy_version=None,
    )
    with pytest.raises(ValueError, match="SMART_RISK_NOT_APPROVED"):
        to_dynamic_risk_sizing_fields(blocked)
