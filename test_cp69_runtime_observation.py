"""Focused CP69 Trader-side producer tests."""

from __future__ import annotations

import json
import tempfile
from dataclasses import dataclass
from pathlib import Path



@dataclass(frozen=True)
class SampleMarketDataResult:
    symbol: str
    status: str
    candles: tuple[dict, ...]
    source: str
    error: str | None
    real_data: bool

from cp69_runtime_observation import (
    CP69_ADAPTER_ID,
    CP69_ENVIRONMENT_ID,
    CP69_SCHEMA,
    CP69_SCHEMA_VERSION,
    append_observation,
    build_failure_attribution,
    build_observation,
)


def make() -> dict:
    return build_observation(
        observation_id="obs:test-001",
        emitted_at="2026-09-24T00:00:00+00:00",
        runtime_snapshot_id="RS-test",
        cycle_id="RC-test",
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



def test_failure_attribution_aggregates_predicates() -> None:
    snapshot = [
        {
            "asset": "BTC",
            "trade_gate_status": "WATCH",
            "status_reason": "confidence too low",
            "gate_observability": [
                {"name": "OPPORTUNITY_CONFIDENCE", "pass": False},
                {"name": "MARKET_DATA_POINTS", "pass": True},
            ],
        },
        {
            "asset": "ETH",
            "trade_gate_status": "WATCH",
            "status_reason": "confidence too low",
            "gate_observability": [
                {"name": "OPPORTUNITY_CONFIDENCE", "pass": False},
                {"name": "DECISION_STATE", "pass": False},
            ],
        },
        {
            "asset": "SOL",
            "trade_gate_status": "TRADE_READY",
            "status_reason": "all gates passed",
            "gate_observability": [
                {"name": "OPPORTUNITY_CONFIDENCE", "pass": True},
            ],
        },
    ]
    attribution = build_failure_attribution(snapshot)
    assert attribution["candidate_count"] == 3
    assert attribution["trade_ready_count"] == 1
    assert attribution["predicate_failures"] == {
        "DECISION_STATE": 1,
        "OPPORTUNITY_CONFIDENCE": 2,
    }
    assert attribution["reason_counts"] == {"confidence too low": 2}
    assert attribution["asset_failures"] == {
        "BTC": ["OPPORTUNITY_CONFIDENCE"],
        "ETH": ["DECISION_STATE", "OPPORTUNITY_CONFIDENCE"],
    }


def test_failure_attribution_is_embedded_in_observation() -> None:
    item = make()
    attribution = item["state"]["failure_attribution"]
    assert attribution["candidate_count"] == 1
    assert attribution["trade_ready_count"] == 0
    assert attribution["predicate_failures"] == {}


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


def test_authorized_cp49_birth_write_provenance() -> None:
    item = build_observation(
        observation_id="obs:cp49-write",
        emitted_at="2026-09-24T00:00:00+00:00",
        runtime_snapshot_id="RS-cp49-write",
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


def test_provenance() -> None:
    item = make()
    assert item["provenance"]["runtime_snapshot_id"] == "RS-test"
    assert item["provenance"]["cycle_id"] == "RC-test"


def test_cycle_id_validation() -> None:
    try:
        build_observation(
            observation_id="obs:cycle-invalid",
            emitted_at="2026-09-24T00:00:00+00:00",
            cycle_id="   ",
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
        )
    except ValueError as exc:
        assert str(exc) == "cycle_id must be a non-empty string when supplied"
        return
    raise AssertionError("invalid cycle_id accepted")


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
    except TypeError as exc:
        assert "state.universe_assets.BTC" in str(exc)
        assert "object" in str(exc)
        return
    raise AssertionError("non-JSON state accepted")


def test_execution_state_contract() -> None:
    valid_states = [
        {
            "EXECUTION": "OFF",
            "REAL_ORDER": False,
            "REAL_TRADE": False,
            "DB_WRITES": 0,
        },
        {
            "EXECUTION": "ON",
            "REAL_ORDER": True,
            "REAL_TRADE": False,
            "DB_WRITES": 0,
        },
        {
            "EXECUTION": "ON",
            "REAL_ORDER": True,
            "REAL_TRADE": True,
            "DB_WRITES": 0,
        },
    ]

    for state in valid_states:
        item = make()
        item["execution_state"] = state
        with tempfile.TemporaryDirectory() as directory:
            append_observation(
                item,
                Path(directory) / "valid.jsonl",
            )

    invalid_states = [
        {
            "EXECUTION": "OFF",
            "REAL_ORDER": True,
            "REAL_TRADE": False,
            "DB_WRITES": 0,
        },
        {
            "EXECUTION": "OFF",
            "REAL_ORDER": False,
            "REAL_TRADE": True,
            "DB_WRITES": 0,
        },
        {
            "EXECUTION": "ON",
            "REAL_ORDER": False,
            "REAL_TRADE": True,
            "DB_WRITES": 0,
        },
        {
            "EXECUTION": "INVALID",
            "REAL_ORDER": False,
            "REAL_TRADE": False,
            "DB_WRITES": 0,
        },
    ]

    for state in invalid_states:
        item = make()
        item["execution_state"] = state
        try:
            with tempfile.TemporaryDirectory() as directory:
                append_observation(
                    item,
                    Path(directory) / "invalid.jsonl",
                )
        except ValueError:
            continue
        raise AssertionError(f"invalid execution state accepted: {state}")

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
