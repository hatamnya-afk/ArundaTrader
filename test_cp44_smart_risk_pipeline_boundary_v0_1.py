"""CP39 — Smart Risk to Quantity canonical field mapping tests."""

from cp44_smart_risk_pipeline_boundary_v0_1 import build_cp44_smart_risk


def test_approved_risk_exposes_canonical_position_quantity():
    decision = {
        "state": "ACTIONABLE",
        "direction": "LONG",
    }
    observation = {
        "entry_price": 100.0,
        "invalidation_price": 98.0,
        "stop_distance": 2.0,
        "capital_state": "REAL_CAPITAL",
        "portfolio_capital": 10_000.0,
        "usable_capital": 10_000.0,
        "allocated_risk": 0.0,
        "concurrent_positions": 0,
    }
    policy = {
        "policy_validation": "VALID",
        "policy_version": "CP39-TEST",
        "risk_per_trade": 0.005,
        "max_portfolio_risk": 0.01,
        "max_concurrent_positions": 2,
    }

    result = build_cp44_smart_risk(
        "TEST/USDT",
        decision,
        observation,
        policy,
    )

    assert result["risk_state"] == "APPROVED"
    assert result["position_quantity"] == result["position_size"]
    assert result["quantity_unit"] == "BASE_ASSET"
    assert result["quantity_source"] == "POSITION_SIZING.position_size"
    assert result["quantity_changed"] is False
    assert result["quantity_recomputed"] is False
    assert result["quantity_rescaled"] is False
    assert result["quantity_rounded"] is False
    assert result["quantity_clipped"] is False
