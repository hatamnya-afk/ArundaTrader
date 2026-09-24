"""Focused CP69 Trader-side producer tests."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from cp69_runtime_observation import (
    CP69_ADAPTER_ID,
    CP69_ENVIRONMENT_ID,
    CP69_SCHEMA,
    CP69_SCHEMA_VERSION,
    append_observation,
    build_observation,
)


def make() -> dict:
    return build_observation(
        observation_id="obs:test-001",
        emitted_at="2026-09-24T00:00:00+00:00",
        runtime_snapshot_id="RS-test",
        universe_assets=["BTC"],
        market_data_results={"BTC": {"status": "READY"}},
        opportunity_by_asset={"BTC": {"asset": "BTC"}},
        dynamic_signals={"BTC": {"direction": "NONE"}},
        validation_results={"BTC": {"valid": True}},
        fusion_snapshot={"BTC": {"score": 0}},
        score_snapshot={"BTC": {"score": 0}},
        decision_snapshot={"BTC": {"decision": "HOLD"}},
        risk_snapshot={"BTC": {"status": "PASS"}},
        trade_gate_snapshot={"BTC": {"trade_gate_state": "REJECTED"}},
        trade_ready_assets=[],
    )


def test_schema() -> None:
    item = make()
    assert item["schema"] == CP69_SCHEMA
    assert item["schema_version"] == CP69_SCHEMA_VERSION


def test_identity() -> None:
    item = make()
    assert item["environment_id"] == CP69_ENVIRONMENT_ID
    assert item["adapter_id"] == CP69_ADAPTER_ID


def test_execution_off() -> None:
    assert make()["execution_state"] == {
        "EXECUTION": "OFF",
        "REAL_ORDER": False,
        "REAL_TRADE": False,
        "DB_WRITES": 0,
    }


def test_provenance() -> None:
    item = make()
    assert item["provenance"]["runtime_snapshot_id"] == "RS-test"


def test_timestamp_preserved() -> None:
    assert make()["emitted_at"] == "2026-09-24T00:00:00+00:00"


def test_deterministic_json() -> None:
    item = make()
    a = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    b = json.dumps(item, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert a == b


def test_append_one_event() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = append_observation(make(), Path(directory) / "stream.jsonl")
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["observation_id"] == "obs:test-001"


def test_append_is_additive() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "stream.jsonl"
        append_observation(make(), path)
        second = dict(make())
        second["observation_id"] = "obs:test-002"
        append_observation(second, path)
        assert len(path.read_text(encoding="utf-8").splitlines()) == 2



def test_dataclass_runtime_state_is_projected() -> None:
    @dataclass(frozen=True)
    class SampleMarketData:
        symbol: str
        status: str
        points: int

    item = build_observation(
        observation_id="obs:dataclass",
        emitted_at="2026-09-24T00:00:00+00:00",
        runtime_snapshot_id="RS-dataclass",
        universe_assets=["BTC"],
        market_data_results=(SampleMarketData("BTC", "READY", 21),),
        opportunity_by_asset={},
        dynamic_signals={},
        validation_results={},
        fusion_snapshot={},
        score_snapshot={},
        decision_snapshot={},
        risk_snapshot={},
        trade_gate_snapshot={},
        trade_ready_assets=[],
    )
    assert item["state"]["market_data_results"] == [
        {"points": 21, "status": "READY", "symbol": "BTC"}
    ]
    json.dumps(item, allow_nan=False)

def test_non_json_runtime_state_rejected() -> None:
    try:
        build_observation(
            observation_id="obs:test",
            emitted_at="2026-09-24T00:00:00+00:00",
            runtime_snapshot_id="RS-test",
            universe_assets={"BTC": object()},
            market_data_results={},
            opportunity_by_asset={},
            dynamic_signals={},
            validation_results={},
            fusion_snapshot={},
            score_snapshot={},
            decision_snapshot={},
            risk_snapshot={},
            trade_gate_snapshot={},
            trade_ready_assets=[],
        )
    except TypeError:
        return
    raise AssertionError("non-JSON state accepted")


def test_unsafe_execution_state_rejected() -> None:
    item = make()
    item["execution_state"]["EXECUTION"] = "ON"
    try:
        append_observation(item, Path(tempfile.gettempdir()) / "cp69-invalid.jsonl")
    except ValueError:
        return
    raise AssertionError("unsafe execution state accepted")


def test_no_execution_methods() -> None:
    assert not hasattr(build_observation, "execute")
    assert not hasattr(append_observation, "submit_order")


if __name__ == "__main__":
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
    print(f"CP69 TRADER PRODUCER TESTS PASS: {len(tests)}/{len(tests)}")
