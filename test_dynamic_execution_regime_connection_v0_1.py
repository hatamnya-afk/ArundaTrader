from __future__ import annotations

import ast
from pathlib import Path
from types import SimpleNamespace

import market_regime_engine


PIPELINE = Path(__file__).resolve().parent / "arunda_pipeline.py"


def _structure(asset):
    return {
        "status": "AVAILABLE",
        "asset": asset,
        "points": 21,
        "context_status": "LIMITED",
        "context_target": market_regime_engine.FULL_CONTEXT_TARGET,
        "context_minimum": market_regime_engine.MIN_CONTEXT,
        "structure_direction": "NEUTRAL",
        "structure_strength": "WEAK",
        "structure_confidence": "LOW",
        "bos_recent": False,
        "choch_recent": False,
        "acceleration": 0.0,
    }


def _market_result():
    candles = tuple(
        {
            "timestamp": index + 1,
            "open": 100.0 + index,
            "high": 102.0 + index,
            "low": 99.0 + index,
            "close": 101.0 + index,
            "volume": 10.0 + index,
        }
        for index in range(21)
    )
    return SimpleNamespace(
        status="READY",
        real_data=True,
        candles=candles,
        source="REAL_PROVIDER_TEST_FIXTURE",
    )


def test_market_regime_uses_exact_dynamic_assets_and_in_memory_market_data(monkeypatch):
    requested = ["IMX/USDT", "APR/USDT"]
    market = {symbol: _market_result() for symbol in requested}

    monkeypatch.setattr(
        market_regime_engine,
        "calculate_structure",
        lambda asset, bars: _structure(asset),
    )

    snapshot = market_regime_engine.load_market_regime(
        assets=requested,
        market_data_by_symbol=market,
    )

    assert set(snapshot) == {"IMX", "APR"}
    assert len(snapshot) == len(requested)
    assert snapshot["IMX"]["status"] == "AVAILABLE"
    assert snapshot["APR"]["status"] == "AVAILABLE"
    assert all(row["regime"] == "RANGING" for row in snapshot.values())
    assert market_regime_engine.validate_market_regime(snapshot)


def test_market_regime_rejects_missing_or_non_real_current_market_data():
    market = {"IMX/USDT": _market_result()}
    try:
        market_regime_engine.load_market_regime(
            assets=["IMX/USDT", "APR/USDT"],
            market_data_by_symbol=market,
        )
    except RuntimeError as exc:
        assert "REAL_MARKET_DATA_MISSING:APR" in str(exc)
    else:
        raise AssertionError("missing current market data must fail closed")

    bad = _market_result()
    bad.real_data = False
    try:
        market_regime_engine.load_market_regime(
            assets=["IMX/USDT"],
            market_data_by_symbol={"IMX/USDT": bad},
        )
    except RuntimeError as exc:
        assert "REAL_MARKET_DATA_NOT_REAL:IMX" in str(exc)
    else:
        raise AssertionError("non-real market data must fail closed")


def test_pipeline_wires_dynamic_regime_to_execution_handoff():
    source = PIPELINE.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(PIPELINE))

    loaders = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "load_current_market_regime"
    ]
    assert loaders
    loader = loaders[-1]
    assert [arg.arg for arg in loader.args.args][-2:] == [
        "assets", "market_data_by_symbol"
    ]
    assert any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "load_market_regime"
        and {kw.arg for kw in node.keywords} >= {
            "assets", "market_data_by_symbol"
        }
        for node in ast.walk(loader)
    )

    handoff_calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "build_order_intents_and_boundary_results"
    ]
    assert handoff_calls
    assert any(
        keyword.arg == "regime_snapshot"
        and isinstance(keyword.value, ast.IfExp)
        and isinstance(keyword.value.body, ast.Call)
        and isinstance(keyword.value.body.func, ast.Name)
        and keyword.value.body.func.id == "load_current_market_regime"
        for call in handoff_calls for keyword in call.keywords
    )
