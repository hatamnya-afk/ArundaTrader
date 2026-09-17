"""Focused CP44 tests for the dynamic Smart Risk boundary."""

from dynamic_risk_contract_boundary_v0_1 import build_dynamic_risk


def test_dynamic_risk_fails_closed_without_real_capital_context():
    result = build_dynamic_risk(
        "BTC/USDT",
        {
            "asset": "BTC/USDT",
            "state": "ACTIONABLE",
            "direction": "LONG",
        },
    )

    assert result["risk_state"] == "BLOCKED"
    assert result["reason"] == "REAL_CAPITAL_BOUNDARY_UNAVAILABLE"


def test_dynamic_risk_preserves_dynamic_asset_identity():
    result = build_dynamic_risk(
        "NEWASSET/USDT",
        {
            "asset": "NEWASSET/USDT",
            "state": "ACTIONABLE",
            "direction": "LONG",
        },
    )

    assert result["asset"] == "NEWASSET/USDT"
    assert result["dynamic_universe"] is True
    assert result["fixed_15_used"] is False
