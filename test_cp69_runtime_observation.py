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
    write_current_observation,
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

def test_repeated_identical_state_gets_distinct_observation_ids() -> None:
    first = build_observation(
        emitted_at="2026-10-16T00:00:00+00:00",
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
    second = build_observation(
        emitted_at="2026-10-16T00:00:01+00:00",
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
    assert first["provenance"]["runtime_snapshot_id"] == second["provenance"]["runtime_snapshot_id"]
    assert first["observation_id"] != second["observation_id"]

def test_authoritative_birth_write_provenance_is_preserved() -> None:
    item = build_observation(
        emitted_at="2026-10-16T00:00:00+00:00",
        universe_assets=["BTC"],
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
        db_writes=1,
        db_write_boundary="CP49_AUTHORITATIVE_BIRTH_PERSISTENCE",
    )
    assert item["execution_state"]["DB_WRITES"] == 1
    assert item["provenance"]["db_write_boundary"] == "CP49_AUTHORITATIVE_BIRTH_PERSISTENCE"


def test_nonzero_write_count_requires_authoritative_boundary() -> None:
    try:
        build_observation(
            emitted_at="2026-10-16T00:00:00+00:00",
            universe_assets=[],
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
            db_writes=1,
        )
    except ValueError as exc:
        assert "authoritative CP49 Birth boundary" in str(exc)
        return
    raise AssertionError("unattributed DB write count accepted")


def test_zero_write_count_rejects_boundary() -> None:
    try:
        build_observation(
            emitted_at="2026-10-16T00:00:00+00:00",
            universe_assets=[],
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
            db_writes=0,
            db_write_boundary="CP49_AUTHORITATIVE_BIRTH_PERSISTENCE",
        )
    except ValueError as exc:
        assert "must be absent" in str(exc)
        return
    raise AssertionError("boundary accepted with zero writes")


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


def test_failure_attribution_is_source_derived() -> None:
    item = build_observation(
        emitted_at="2026-10-16T00:00:00+00:00",
        universe_assets=["BTC", "ETH"],
        market_data_results={},
        opportunity_by_asset={},
        dynamic_signals={},
        validation_results={},
        fusion_snapshot={},
        score_snapshot={},
        decision_snapshot={},
        risk_snapshot={},
        trade_gate_snapshot={
            "BTC": {
                "trade_gate_state": "REJECTED",
                "reasons": ["opportunity unavailable", "confidence too low"],
                "failed_predicates": ["OPPORTUNITY_CONFIDENCE"],
            },
            "ETH": {
                "trade_gate_state": "TRADE_READY",
                "reasons": ["risk cap"],
                "predicate_failures": {"RISK_LIMIT": 2},
            },
        },
        trade_ready_assets=["ETH"],
    )
    attribution = item["state"]["failure_attribution"]
    assert attribution["trade_ready_count"] == 1
    assert attribution["reason_counts"] == {
        "confidence too low": 1,
        "opportunity unavailable": 1,
        "risk cap": 1,
    }
    assert attribution["predicate_failures"] == {
        "OPPORTUNITY_CONFIDENCE": 1,
        "RISK_LIMIT": 2,
    }


def test_failure_attribution_does_not_infer_predicates() -> None:
    item = build_observation(
        emitted_at="2026-10-16T00:00:00+00:00",
        universe_assets=["BTC"],
        market_data_results={},
        opportunity_by_asset={},
        dynamic_signals={},
        validation_results={},
        fusion_snapshot={},
        score_snapshot={},
        decision_snapshot={},
        risk_snapshot={},
        trade_gate_snapshot={"BTC": {"trade_gate_state": "REJECTED", "reasons": ["risk blocked"]}},
        trade_ready_assets=[],
    )
    attribution = item["state"]["failure_attribution"]
    assert attribution["trade_ready_count"] == 0
    assert attribution["reason_counts"] == {"risk blocked": 1}
    assert attribution["predicate_failures"] == {}



def test_pipeline_emits_cp69_after_trade_gate_before_downstream_evidence() -> None:
    pipeline_path = Path(__file__).with_name("arunda_pipeline.py")
    source = pipeline_path.read_text(encoding="utf-8-sig")
    cp69_marker = "# CP69 CANONICAL RUNTIME OBSERVATION — READ-ONLY ARTIFACT"
    downstream_marker = "# MCP-01 DOWNSTREAM EVIDENCE EMISSION"
    assert source.count(cp69_marker) == 1
    assert source.count(downstream_marker) == 1
    cp69_index = source.index(cp69_marker)
    downstream_index = source.index(downstream_marker)
    assert cp69_index < downstream_index
    assert source.rfind("trade_gate_snapshot =", 0, cp69_index) != -1
    assert source.rfind("trade_ready_assets =", 0, cp69_index) != -1
    assert source.index("cp69_observation = build_observation(", cp69_index) < downstream_index
    assert source.index("cp69_stream_path = append_observation(cp69_observation)", cp69_index) < downstream_index
    assert "EXECUTION_ENABLED = False" in source


if __name__ == "__main__":
    tests = [
        value
        for name, value in sorted(globals().items())
        if name.startswith("test_") and callable(value)
    ]
    for test in tests:
        test()
    print(f"CP69 TRADER PRODUCER TESTS PASS: {len(tests)}/{len(tests)}")



def test_current_handoff_contains_exactly_one_latest_observation() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "current.jsonl"
        first = make()
        write_current_observation(first, path)
        assert len(path.read_text(encoding="utf-8").splitlines()) == 1
        second = dict(make())
        second["observation_id"] = "obs:latest"
        write_current_observation(second, path)
        lines = path.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["observation_id"] == "obs:latest"


def test_current_handoff_rejects_unsafe_observation() -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "current.jsonl"
        unsafe = make()
        unsafe["execution_state"]["REAL_ORDER"] = True
        try:
            write_current_observation(unsafe, path)
        except ValueError:
            assert not path.exists()
            return
        raise AssertionError("unsafe current observation accepted")
