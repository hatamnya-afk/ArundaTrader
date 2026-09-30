"""Focused CP39 verification for the zero-capital downstream order chain.

No runtime, database, exchange, or network execution is used.
"""

from types import SimpleNamespace

import arunda_pipeline
from exchange_execution_boundary import execute_order
from exchange_execution_contract import CanonicalOrderRequest


def _zero_capital_fixture():
    snapshot_id = "RS-CP39-ZERO"
    asset = "BTC"
    opportunity = {
        "asset": asset,
        "status": "ELIGIBLE",
        "price": 100000.0,
        "confidence": 0.90,
        "timestamp": "2026-09-30T00:00:00+00:00",
    }
    gate = {
        "asset": asset,
        "direction": "LONG",
        "trade_gate_status": "TRADE_READY",
    }
    risk = {
        "risk_status": "APPROVED",
        "risk_budget": 0.0,
        "position_size": 0.0,
        "position_quantity": 0.0,
        "quantity_unit": "BASE_ASSET",
        "quantity_source": "POSITION_SIZING.position_size",
        "entry_price": 100000.0,
        "stop_distance": 100.0,
        "quantity_changed": False,
        "quantity_recomputed": False,
        "quantity_rescaled": False,
        "quantity_rounded": False,
        "quantity_clipped": False,
    }
    regime = {asset: {"regime": "TREND"}}
    return snapshot_id, asset, opportunity, gate, risk, regime


def test_zero_capital_trade_ready_to_canonical_request_preserves_zero_quantity():
    snapshot_id, asset, opportunity, gate, risk, regime = _zero_capital_fixture()

    intents = arunda_pipeline.build_current_order_intents(
        gate_results=[gate],
        opportunity_rows=[opportunity],
        snapshot_id=snapshot_id,
        regime_snapshot=regime,
        risk_snapshot={asset: risk},
        observed_real_capital=0.0,
    )

    assert len(intents) == 1
    intent = intents[0]
    assert intent["quantity"] == 0.0
    assert intent["quantity_unit"] == "BASE_ASSET"
    assert intent["quantity_source"] == "RISK.position_quantity"
    assert intent.trade_type == arunda_pipeline.RESEARCH_TRADE
    assert intent.observed_real_capital == 0.0

    assert (
        arunda_pipeline.validate_current_order_intents(
            intents=intents,
            gate_results=[gate],
            opportunity_rows=[opportunity],
            snapshot_id=snapshot_id,
            regime_snapshot=regime,
            risk_rows=[dict(asset=asset, **risk)],
        )
        == 1
    )

    canonical = arunda_pipeline.build_canonical_order_requests(
        order_intents=intents,
        risk_snapshot={asset: risk},
        snapshot_id=snapshot_id,
    )

    request = canonical[asset]["request"]
    assert isinstance(request, CanonicalOrderRequest)
    assert request.quantity == 0.0
    assert request.quantity_unit == "BASE_ASSET"
    assert request.quantity_source == "RISK.position_quantity"


def test_zero_capital_canonical_request_remains_fail_closed_at_execution_boundary():
    snapshot_id, asset, opportunity, gate, risk, regime = _zero_capital_fixture()

    intents = arunda_pipeline.build_current_order_intents(
        gate_results=[gate],
        opportunity_rows=[opportunity],
        snapshot_id=snapshot_id,
        regime_snapshot=regime,
        risk_snapshot={asset: risk},
        observed_real_capital=0.0,
    )
    canonical = arunda_pipeline.build_canonical_order_requests(
        order_intents=intents,
        risk_snapshot={asset: risk},
        snapshot_id=snapshot_id,
    )
    request = canonical[asset]["request"]

    result = execute_order(request=request, adapter=None)

    assert result.accepted is False
    assert result.error_code == "CP46_E_REQUIRED"
    assert result.executed_quantity is None
