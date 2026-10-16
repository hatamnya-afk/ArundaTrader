"""Focused CP69 regression tests for the operational producer contract."""
from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path

from cp69_runtime_observation import (
    CP69_ADAPTER_ID, CP69_ENVIRONMENT_ID, CP69_SCHEMA,
    CP69_SCHEMA_VERSION, append_observation, build_observation,
    build_runtime_snapshot_id,
)


def make(**overrides):
    values = {
        "emitted_at": "2026-10-16T00:00:00+00:00",
        "universe_assets": ["BTC"],
        "market_data_results": {"BTC/USDT": {"status": "READY", "real_data": True}},
        "opportunity_by_asset": {"BTC": {"asset": "BTC"}},
        "dynamic_signals": {"BTC": {"direction": "NONE"}},
        "validation_results": {"BTC": {"valid": True}},
        "fusion_snapshot": {"BTC": {"score": 0}},
        "score_snapshot": {"BTC": {"score": 0}},
        "decision_snapshot": {"BTC": {"decision": "HOLD"}},
        "risk_snapshot": {"BTC": {"status": "PASS"}},
        "trade_gate_snapshot": {"BTC": {"trade_gate_state": "REJECTED"}},
        "trade_ready_assets": [],
    }
    values.update(overrides)
    return build_observation(**values)


def test_canonical_schema_and_identity():
    row = make()
    assert row["schema"] == CP69_SCHEMA
    assert row["schema_version"] == CP69_SCHEMA_VERSION
    assert row["environment_id"] == CP69_ENVIRONMENT_ID
    assert row["adapter_id"] == CP69_ADAPTER_ID
    assert row["observation_id"] == "obs:" + row["provenance"]["runtime_snapshot_id"]


def test_execution_state_is_fail_closed():
    assert make()["execution_state"] == {
        "EXECUTION": "OFF", "REAL_ORDER": False,
        "REAL_TRADE": False, "DB_WRITES": 0,
    }


def test_snapshot_identity_is_deterministic_for_same_state():
    row_a, row_b = make(), make()
    assert row_a["provenance"]["runtime_snapshot_id"] == row_b["provenance"]["runtime_snapshot_id"]


def test_snapshot_identity_changes_when_runtime_state_changes():
    row_a = make()
    row_b = make(decision_snapshot={"BTC": {"decision": "LONG"}})
    assert row_a["provenance"]["runtime_snapshot_id"] != row_b["provenance"]["runtime_snapshot_id"]


def test_dataclass_market_results_are_serialized_explicitly():
    @dataclass
    class MarketResult:
        status: str
        real_data: bool
    row = make(market_data_results={"BTC/USDT": MarketResult("READY", True)})
    assert row["state"]["market_data_results"]["BTC/USDT"] == {"status": "READY", "real_data": True}


def test_opaque_runtime_objects_fail_closed():
    try:
        make(market_data_results={"BTC/USDT": object()})
    except TypeError as exc:
        assert "unsupported runtime type" in str(exc)
    else:
        raise AssertionError("opaque runtime object was silently accepted")


def test_non_finite_values_fail_closed():
    try:
        make(score_snapshot={"BTC": {"score": float("nan")}})
    except ValueError:
        return
    raise AssertionError("NaN was accepted")


def test_append_writes_one_canonical_jsonl_event():
    with tempfile.TemporaryDirectory() as tmp:
        path = append_observation(make(), Path(tmp) / "stream.jsonl")
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["schema"] == CP69_SCHEMA


def test_append_is_additive():
    first = make()
    second = make(decision_snapshot={"BTC": {"decision": "LONG"}})
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "stream.jsonl"
        append_observation(first, path)
        append_observation(second, path)
        assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_unsafe_execution_state_rejected():
    row = make()
    row["execution_state"]["EXECUTION"] = "ON"
    try:
        append_observation(row, Path(tempfile.gettempdir()) / "cp69-invalid-should-not-be-written.jsonl")
    except ValueError:
        return
    raise AssertionError("unsafe execution state was accepted")


def test_snapshot_id_rejects_mismatch():
    try:
        make(runtime_snapshot_id="RS-not-the-current-state")
    except ValueError:
        return
    raise AssertionError("mismatched runtime identity was accepted")


if __name__ == "__main__":
    tests = [value for name, value in sorted(globals().items()) if name.startswith("test_") and callable(value)]
    for test in tests:
        test()
    print(f"CP69 REGRESSION TESTS PASS: {len(tests)}/{len(tests)}")
