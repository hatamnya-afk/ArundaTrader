from __future__ import annotations

import ast
from pathlib import Path

import decision_contract
import decision_engine
import trade_gate_engine
from dynamic_decision_contract_boundary_v0_1 import build_dynamic_decision


ROOT = Path(__file__).resolve().parent


def test_decision_engine_accepts_dynamic_assets_without_fixed_universe():
    signals = {
        "IMX": {
            "asset": "IMX",
            "signal_state": "ACTIVE",
            "direction": "LONG",
            "valid": True,
            "validation": "VALID",
        },
        "APR": {
            "asset": "APR",
            "signal_state": "ACTIVE",
            "direction": "SHORT",
            "valid": True,
            "validation": "VALID",
        },
    }
    scores = {
        "IMX": {
            "asset": "IMX",
            "signal_state": "ACTIVE",
            "direction": "LONG",
            "score": 0.75,
        },
        "APR": {
            "asset": "APR",
            "signal_state": "ACTIVE",
            "direction": "SHORT",
            "score": -0.65,
        },
    }
    decisions = decision_engine.build_decision_snapshot(
        signals,
        scores,
        decision_ids={
            "IMX": "D-IMX-001",
            "APR": "D-APR-001",
        },
    )
    assert set(decisions) == {"IMX", "APR"}
    assert decision_contract.validate_decision_snapshot(decisions)["observed_asset_count"] == 2


def test_dynamic_decision_boundary_does_not_mutate_decision_contract():
    before = (
        getattr(decision_contract, "EXPECTED_ASSETS", None),
        getattr(decision_contract, "EXPECTED_ASSET_COUNT", None),
    )
    result = build_dynamic_decision(
        "IMX/USDT",
        {
            "asset": "IMX",
            "signal_state": "ACTIVE",
            "direction": "LONG",
            "valid": True,
            "validation": "VALID",
        },
        {
            "asset": "IMX",
            "signal_state": "ACTIVE",
            "direction": "LONG",
            "score": 0.75,
        },
        decision_id="D-IMX-002",
    )
    assert result["asset"] == "IMX/USDT"
    assert not hasattr(decision_contract, "EXPECTED_ASSETS")
    assert not hasattr(decision_contract, "EXPECTED_ASSET_COUNT")
    assert before == (None, None)


def test_trade_gate_runtime_accepts_dynamic_assets():
    opportunities = {
        "IMX": {
            "asset": "IMX",
            "status": "ELIGIBLE",
            "direction": "LONG",
            "score": 0.8,
            "confidence": 0.9,
            "market_data_points": 50,
            "snapshot_age": 0.0,
        },
        "APR": {
            "asset": "APR",
            "status": "ELIGIBLE",
            "direction": "SHORT",
            "score": 0.8,
            "confidence": 0.9,
            "market_data_points": 50,
            "snapshot_age": 0.0,
        },
    }
    decisions = {
        "IMX": {"asset": "IMX", "state": "TRADE", "direction": "LONG"},
        "APR": {"asset": "APR", "state": "TRADE", "direction": "SHORT"},
    }
    risks = {
        "IMX": {"asset": "IMX", "risk_state": "APPROVED", "risk_decision": "APPROVED"},
        "APR": {"asset": "APR", "risk_state": "APPROVED", "risk_decision": "APPROVED"},
    }
    results = trade_gate_engine.run_runtime(
        opportunities,
        decisions,
        risks,
    )
    assert {row["asset"] for row in results} == {"IMX", "APR"}


def test_production_contracts_have_no_fixed_asset_constants():
    for name in (
        "arunda_pipeline.py",
        "decision_engine.py",
        "decision_contract.py",
        "trade_gate_engine.py",
        "toobit_trading_adapter.py",
    ):
        source = (ROOT / name).read_text(encoding="utf-8-sig")
        assert "EXPECTED_ASSETS" not in source
        assert "EXPECTED_ASSET_COUNT" not in source
        assert "EXPECTED_ASSET_SET" not in source

    pipeline = ast.parse(
        (ROOT / "arunda_pipeline.py").read_text(encoding="utf-8-sig")
    )
    defs = [
        node.name
        for node in pipeline.body
        if isinstance(node, ast.FunctionDef)
    ]
    assert len(defs) == len(set(defs))
