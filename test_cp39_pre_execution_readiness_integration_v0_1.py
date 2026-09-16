from __future__ import annotations

import pytest

from pre_execution_readiness_integration_v0_1 import build_pre_execution_readiness


VALID_OBSERVATIONS = {
    "capital": {
        "capital_state": "AVAILABLE",
        "capital_validation": "VALID",
        "capital_source": "REAL_ACCOUNT_BALANCE",
        "provenance": "REAL_ACCOUNT",
        "asset_scope": "USDT",
        "available_capital": 10000.0,
        "usable_capital": 8000.0,
        "observed_at": "2026-09-17T00:00:00+00:00",
    },
    "portfolio": {
        "portfolio_state": "AVAILABLE",
        "portfolio_validation": "VALID",
        "portfolio_source": "REAL_ACCOUNT_PORTFOLIO",
        "provenance": "REAL_ACCOUNT_PORTFOLIO",
        "asset_scope": "USDT",
        "portfolio_capital": 10000.0,
        "usable_capital": 8000.0,
        "allocated_risk": 250.0,
        "concurrent_positions": 2,
        "observed_at": "2026-09-17T00:00:00+00:00",
    },
    "stop_risk_policy": {
        "observation_state": "AVAILABLE",
        "observation_validation": "VALID",
        "observation_source": "REAL_MARKET_RISK_POLICY",
        "provenance": "REAL_PRODUCTION_OBSERVATION",
        "asset": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 60000.0,
        "stop_price": 59000.0,
        "stop_distance": 1000.0,
        "risk_policy_version": "RISK_POLICY_V0_1",
        "risk_policy_validation": "VALID",
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 3,
        "observed_at": "2026-09-17T00:00:00+00:00",
    },
    "liquidity": {
        "observation_state": "AVAILABLE",
        "observation_validation": "VALID",
        "observation_source": "REAL_PRODUCTION_LIQUIDITY",
        "provenance": "REAL_PRODUCTION_OBSERVATION",
        "asset": "BTCUSDT",
        "liquidity_validation": "VALID",
        "observed_at": "2026-09-17T00:00:00+00:00",
    },
    "execution": {
        "observation_state": "AVAILABLE",
        "observation_validation": "VALID",
        "observation_source": "REAL_PRODUCTION_EXECUTION_CONSTRAINTS",
        "provenance": "REAL_PRODUCTION_OBSERVATION",
        "asset": "BTCUSDT",
        "execution_validation": "VALID",
        "observed_at": "2026-09-17T00:00:00+00:00",
    },
}


def test_valid_production_observations_build_ready_state():
    result = build_pre_execution_readiness(VALID_OBSERVATIONS)

    assert result == {
        "readiness_state": "READY",
        "readiness_validation": "VALID",
        "readiness_source": "REAL_PRODUCTION_READINESS",
        "provenance": "REAL_PRODUCTION_OBSERVATION",
        "asset": "BTCUSDT",
        "capital_validation": "VALID",
        "portfolio_validation": "VALID",
        "stop_risk_policy_validation": "VALID",
        "liquidity_validation": "VALID",
        "execution_validation": "VALID",
        "observed_at": "2026-09-17T00:00:00+00:00",
    }


@pytest.mark.parametrize("component", ["capital", "portfolio", "stop_risk_policy", "liquidity", "execution"])
def test_missing_component_fails_closed(component):
    observations = dict(VALID_OBSERVATIONS)
    observations.pop(component)

    with pytest.raises(ValueError, match="READINESS_OBSERVATION_MISSING"):
        build_pre_execution_readiness(observations)


def test_invalid_component_validation_fails_closed():
    observations = {key: dict(value) for key, value in VALID_OBSERVATIONS.items()}
    observations["liquidity"]["liquidity_validation"] = "INVALID"

    with pytest.raises(ValueError, match="READINESS_OBSERVATION_INVALID"):
        build_pre_execution_readiness(observations)


def test_test_legacy_or_simulated_observation_is_rejected():
    for component, field in (
        ("capital", "capital_source"),
        ("portfolio", "portfolio_source"),
        ("stop_risk_policy", "observation_source"),
        ("liquidity", "observation_source"),
        ("execution", "observation_source"),
    ):
        observations = {key: dict(value) for key, value in VALID_OBSERVATIONS.items()}
        observations[component][field] = "TEST"
        with pytest.raises(ValueError, match="READINESS_PROVENANCE_INVALID"):
            build_pre_execution_readiness(observations)


def test_asset_must_be_consistent_across_asset_bound_observations():
    observations = {key: dict(value) for key, value in VALID_OBSERVATIONS.items()}
    observations["execution"]["asset"] = "ETHUSDT"

    with pytest.raises(ValueError, match="READINESS_ASSET_MISMATCH"):
        build_pre_execution_readiness(observations)


def test_result_is_provider_neutral_and_has_no_execution_surface():
    result = build_pre_execution_readiness(VALID_OBSERVATIONS)

    assert "exchange" not in result
    assert not {
        "order_id",
        "exchange_client",
        "api_request",
        "signature",
        "submitted",
        "trade_id",
        "withdrawal",
        "order_write",
        "execution_authorization",
        "execution_enabled",
    }.intersection(result)


def test_non_mapping_input_fails_closed():
    with pytest.raises(ValueError, match="READINESS_INPUT_INVALID"):
        build_pre_execution_readiness(None)


def test_output_is_deterministic():
    first = build_pre_execution_readiness(VALID_OBSERVATIONS)
    second = build_pre_execution_readiness(VALID_OBSERVATIONS)

    assert first == second
