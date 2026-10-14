import pytest

from smart_risk_authoritative_ledger_source_bridge_v0_1 import build_smart_risk_sources_from_authoritative_ledger
from real_capital_source_contract_v0_1 import validate_real_capital_source
from real_portfolio_state_source_contract_v0_1 import validate_real_portfolio_state


def ledger():
    return {
        "portfolio_state": "AVAILABLE", "portfolio_validation": "VALID",
        "coverage_scope": "ACCOUNT_WIDE", "market_coverage": ["SPOT", "FUTURES"],
        "account_scope": "TOOBIT:fixture", "observed_at": "2026-10-14T18:00:00Z",
        "cycle_id": "cycle-1", "provenance": "synthetic fixture only",
        "valuation_policy_state": "APPROVED", "valuation_policy_id": "policy-1",
        "valuation_policy_version": "v1", "ledger_id": "ledger-1", "ledger_version": "v1",
        "portfolio_capital": 1500.0, "usable_capital": 1200.0,
        "allocated_risk": 20.0, "concurrent_positions": 2,
        "valued_assets": ["BTC", "USDC", "USDT"],
        "asset_valuation_evidence": {
            "BTC": {"rate_to_usdt": 65000.0}, "USDC": {"rate_to_usdt": 0.999},
            "USDT": {"rate_to_usdt": 1.0},
        },
    }


def test_validated_ledger_maps_to_real_capital_and_portfolio_contracts():
    result = build_smart_risk_sources_from_authoritative_ledger(ledger())
    assert result["bridge_state"] == "AVAILABLE"
    capital = validate_real_capital_source(result["capital_source_observation"])
    portfolio = validate_real_portfolio_state(result["portfolio_source_observation"])
    assert capital["available_capital"] == 1500.0
    assert capital["usable_capital"] == 1200.0
    assert portfolio["allocated_risk"] == 20.0
    assert portfolio["concurrent_positions"] == 2


@pytest.mark.parametrize("change,reason", [
    ({"portfolio_state": "BLOCKED"}, "SMART_RISK_AUTHORITATIVE_LEDGER_NOT_VALID"),
    ({"coverage_scope": "SYMBOL_SCOPED"}, "SMART_RISK_ACCOUNT_WIDE_SPOT_FUTURES_COVERAGE_REQUIRED"),
    ({"asset_valuation_evidence": {"USDT": {"rate_to_usdt": 1.0}}}, "SMART_RISK_ASSET_VALUATION_COVERAGE_MISMATCH"),
    ({"usable_capital": 0}, "SMART_RISK_LEDGER_USABLE_CAPITAL_INVALID"),
])
def test_invalid_or_incomplete_ledger_never_produces_capital(change, reason):
    row = ledger()
    row.update(change)
    result = build_smart_risk_sources_from_authoritative_ledger(row)
    assert result["bridge_state"] == "BLOCKED"
    assert result["bridge_block_reason"] == reason
    assert result["capital_source_observation"] is None
    assert result["portfolio_source_observation"] is None


def test_missing_ledger_blocks():
    result = build_smart_risk_sources_from_authoritative_ledger(None)
    assert result["bridge_state"] == "BLOCKED"
    assert result["capital_source_observation"] is None



def test_validated_ledger_reaches_readonly_smart_risk_sizing():
    from smart_risk_authoritative_ledger_source_bridge_v0_1 import evaluate_smart_risk_from_authoritative_ledger

    row = ledger()
    row.update({
        "portfolio_capital": 1000.0, "usable_capital": 800.0,
        "allocated_risk": 10.0, "concurrent_positions": 1,
    })
    stop = {
        "observation_validation": "VALID", "observation_state": "AVAILABLE",
        "observation_source": "APPROVED_ENTRY_STOP_POLICY",
        "provenance": "fixture stop policy", "asset": "BTC", "direction": "LONG",
        "entry_price": 100.0, "stop_price": 95.0, "stop_distance": 5.0,
        "risk_policy_version": "risk-v1", "risk_policy_validation": "VALID",
        "risk_per_trade": 0.01, "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 5, "observed_at": "2026-10-14T18:00:00Z",
    }
    policy = {
        "policy_version": "risk-v1", "policy_validation": "VALID",
        "risk_per_trade": 0.01, "max_portfolio_risk": 0.05,
        "max_concurrent_positions": 5,
    }
    result = evaluate_smart_risk_from_authoritative_ledger(
        ledger_observation=row, asset="BTC", direction="LONG", entry_price=100.0,
        stop_policy_observation=stop, risk_policy_observation=policy,
    )
    assert result["ledger_bridge_state"] == "AVAILABLE"
    assert result["risk_state"] == "APPROVED", result.get("block_reason")
    assert result["quantity_source"] == "SMART_RISK_ENGINE_V0_1"
    assert result["position_quantity"] == pytest.approx(2.0)
    assert result["quantity_unit"] == "BASE_ASSET"
