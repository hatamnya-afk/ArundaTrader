"""Tests for the read-only Smart Risk evidence producer boundary."""
from smart_risk_readonly_producer_boundary_v0_1 import evaluate_readonly_smart_risk_cycle


def _evidence():
    timestamp = "2026-10-14T09:00:00+00:00"
    capital = {
        "capital_state": "AVAILABLE",
        "capital_validation": "VALID",
        "capital_source": "TOOBIT_ACCOUNT_POLICY_VALUATION",
        "provenance": "approved valuation ledger v1",
        "asset_scope": "TOOBIT_SPOT_USDT",
        "available_capital": 1000.0,
        "usable_capital": 800.0,
        "observed_at": timestamp,
    }
    portfolio = {
        "portfolio_state": "AVAILABLE",
        "portfolio_validation": "VALID",
        "portfolio_source": "AUTHORITATIVE_PORTFOLIO_LEDGER",
        "provenance": "portfolio ledger v1",
        "asset_scope": "TOOBIT_SPOT_USDT",
        "portfolio_capital": 1000.0,
        "usable_capital": 800.0,
        "allocated_risk": 10.0,
        "concurrent_positions": 1,
        "observed_at": timestamp,
    }
    stop = {
        "observation_validation": "VALID",
        "observation_state": "AVAILABLE",
        "observation_source": "APPROVED_ENTRY_STOP_POLICY",
        "provenance": "entry-stop policy v3",
        "asset": "BTC",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_price": 95.0,
        "stop_distance": 5.0,
        "risk_policy_version": "risk-v1",
        "risk_policy_validation": "VALID",
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 5,
        "observed_at": timestamp,
    }
    policy = {
        "policy_version": "risk-v1",
        "policy_validation": "VALID",
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 5,
    }
    return capital, portfolio, stop, policy


def test_missing_any_authoritative_observation_blocks_without_quantity():
    capital, portfolio, stop, policy = _evidence()
    result = evaluate_readonly_smart_risk_cycle(
        asset="BTC", direction="LONG", entry_price=100.0,
        capital_source_observation=capital,
        portfolio_source_observation=portfolio,
        stop_policy_observation=stop,
        risk_policy_observation=None,
    )
    assert result["risk_state"] == "BLOCKED"
    assert result["block_reason"] == "SMART_RISK_EVIDENCE_MISSING"
    assert result["missing_observations"] == ["risk_policy"]
    assert result["position_quantity"] is None


def test_same_cycle_validated_inputs_reach_smart_risk_sizing():
    capital, portfolio, stop, policy = _evidence()
    result = evaluate_readonly_smart_risk_cycle(
        asset="BTC", direction="LONG", entry_price=100.0,
        capital_source_observation=capital,
        portfolio_source_observation=portfolio,
        stop_policy_observation=stop,
        risk_policy_observation=policy,
    )
    assert result["risk_state"] == "APPROVED", result.get("block_reason")
    assert result["quantity_source"] == "SMART_RISK_ENGINE_V0_1"
    assert result["position_quantity"] == 2.0
    assert result["quantity_unit"] == "BASE_ASSET"


def test_mismatched_observation_cycle_blocks():
    capital, portfolio, stop, policy = _evidence()
    portfolio["observed_at"] = "2026-10-14T09:00:01+00:00"
    result = evaluate_readonly_smart_risk_cycle(
        asset="BTC", direction="LONG", entry_price=100.0,
        capital_source_observation=capital,
        portfolio_source_observation=portfolio,
        stop_policy_observation=stop,
        risk_policy_observation=policy,
    )
    assert result["risk_state"] == "BLOCKED"
    assert result["block_reason"] == "SMART_RISK_OBSERVATION_CYCLE_MISMATCH"
    assert result["position_quantity"] is None


def test_unapproved_or_mismatched_stop_policy_blocks():
    capital, portfolio, stop, policy = _evidence()
    stop["asset"] = "ETH"
    result = evaluate_readonly_smart_risk_cycle(
        asset="BTC", direction="LONG", entry_price=100.0,
        capital_source_observation=capital,
        portfolio_source_observation=portfolio,
        stop_policy_observation=stop,
        risk_policy_observation=policy,
    )
    assert result["risk_state"] == "BLOCKED"
    assert result["block_reason"] == "STOP_POLICY_ASSET_MISMATCH"
    assert result["position_quantity"] is None
