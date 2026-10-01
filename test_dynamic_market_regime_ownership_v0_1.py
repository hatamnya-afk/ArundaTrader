from __future__ import annotations

import ast
import pathlib

import market_regime_engine


BASE_DIR = pathlib.Path(__file__).resolve().parent
PIPELINE_FILE = BASE_DIR / "arunda_pipeline.py"


def _available_structure(asset: str) -> dict:
    return {
        "status": "AVAILABLE",
        "asset": asset,
        "points": 21,
        "context_status": "LIMITED",
        "context_target": 150,
        "context_minimum": 21,
        "structure_direction": "NEUTRAL",
        "structure_strength": "UNKNOWN",
        "structure_confidence": "UNKNOWN",
        "structure_point_type": None,
        "bos_recent": False,
        "choch_recent": False,
        "swing_count": 0,
        "structure_point_count": 0,
        "event_count": 0,
        "acceleration": 0.0,
    }


def test_build_market_regime_owns_exact_dynamic_assets(monkeypatch):
    requested = {"IMX", "APR", "BTC"}

    def fake_build_structural_state(assets=None):
        assert set(assets) == requested
        return {
            asset: _available_structure(asset)
            for asset in sorted(requested)
        }

    monkeypatch.setattr(
        market_regime_engine,
        "build_structural_state",
        fake_build_structural_state,
    )

    snapshot = market_regime_engine.build_market_regime(
        ["IMX/USDT", "APR", "BTC"]
    )

    assert set(snapshot) == requested
    assert len(snapshot) == len(requested)

    for asset in requested:
        assert snapshot[asset]["asset"] == asset
        assert "regime" in snapshot[asset]


def test_build_market_regime_does_not_inherit_fixed_asset_ceiling(monkeypatch):
    requested = {"IMX", "APR"}

    monkeypatch.setattr(
        market_regime_engine,
        "build_structural_state",
        lambda assets=None: {
            asset: _available_structure(asset)
            for asset in sorted(requested)
        },
    )

    snapshot = market_regime_engine.build_market_regime(
        requested
    )

    assert set(snapshot) == requested
    assert "IMX" in snapshot
    assert "APR" in snapshot
    assert "BTC" not in snapshot


def test_pipeline_passes_trade_ready_assets_to_market_regime():
    source = PIPELINE_FILE.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(PIPELINE_FILE))

    matching_calls = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            continue
        if node.func.id != "load_current_market_regime":
            continue
        if len(node.args) != 1:
            continue

        argument = node.args[0]
        if isinstance(argument, ast.Name) and argument.id == "trade_ready_assets":
            matching_calls.append(node)

    assert matching_calls, (
        "Production orchestration must pass trade_ready_assets "
        "into load_current_market_regime()."
    )


def test_pipeline_market_regime_loader_forwards_assets():
    source = PIPELINE_FILE.read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=str(PIPELINE_FILE))

    loaders = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "load_current_market_regime"
    ]

    assert loaders
    loader = loaders[-1]

    calls = [
        node
        for node in ast.walk(loader)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "load_market_regime"
    ]

    assert calls
    def forwards_assets(call):
        if len(call.args) == 1:
            argument = call.args[0]
            if (
                isinstance(argument, ast.Name)
                and argument.id == "assets"
            ):
                return True

        return any(
            keyword.arg == "assets"
            and isinstance(keyword.value, ast.Name)
            and keyword.value.id == "assets"
            for keyword in call.keywords
        )

    assert any(forwards_assets(call) for call in calls)


def test_validate_market_regime_accepts_dynamic_assets():
    snapshot = {
        asset: {
            "asset": asset,
            "status": "AVAILABLE",
            "points": 21,
            "context_status": "LIMITED",
            "context_target": market_regime_engine.FULL_CONTEXT_TARGET,
            "context_minimum": market_regime_engine.MIN_CONTEXT,
            "regime": "UNDEFINED",
            "structure": {
                "trend": None,
                "volatility": None,
                "momentum": None,
                "position": None,
                "acceleration": 0.0,
            },
        }
        for asset in ("IMX", "APR", "BTC")
    }

    assert market_regime_engine.validate_market_regime(snapshot) is True


def test_validate_market_regime_rejects_missing_dynamic_row():
    snapshot = {
        "IMX": {
            "asset": "IMX",
            "status": "AVAILABLE",
            "points": 21,
            "context_status": "LIMITED",
            "context_target": market_regime_engine.FULL_CONTEXT_TARGET,
            "context_minimum": market_regime_engine.MIN_CONTEXT,
            "regime": "UNDEFINED",
            "structure": {
                "trend": None,
                "volatility": None,
                "momentum": None,
                "position": None,
                "acceleration": 0.0,
            },
        },
        "APR": {
            "asset": "APR",
            "status": "AVAILABLE",
            "points": 20,
            "context_status": "INSUFFICIENT",
            "context_target": market_regime_engine.FULL_CONTEXT_TARGET,
            "context_minimum": market_regime_engine.MIN_CONTEXT,
            "regime": "UNDEFINED",
            "structure": {
                "trend": None,
                "volatility": None,
                "momentum": None,
                "position": None,
                "acceleration": None,
            },
        },
    }

    assert market_regime_engine.validate_market_regime(snapshot) is True


def test_load_market_data_discovers_dynamic_assets_without_fixed_ceiling(monkeypatch):
    rows = [
        {
            "symbol": "IMX/USDT",
            "timestamp": 1,
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 1.0,
        },
        {
            "symbol": "APR",
            "timestamp": 2,
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 1.0,
        },
        {
            "symbol": "BTC/USDT",
            "timestamp": 3,
            "open": 1.0,
            "high": 1.0,
            "low": 1.0,
            "close": 1.0,
            "volume": 1.0,
        },
    ]

    monkeypatch.setattr(
        market_regime_engine,
        "_get_columns",
        lambda conn, table_name: [
            "symbol", "timestamp", "open", "high", "low", "close", "volume"
        ],
    )

    class FakeConn:
        def execute(self, query):
            class Result:
                def fetchall(self):
                    return rows
            return Result()

        def close(self):
            pass

    monkeypatch.setattr(
        market_regime_engine.sqlite3,
        "connect",
        lambda path: FakeConn(),
    )

    result = market_regime_engine.load_market_data_by_symbol()

    assert set(result) == {"IMX", "APR", "BTC"}
