"""CP69 canonical read-only runtime observation producer.

Serializes the current ArundaTrader cycle into one append-only JSONL event.
This boundary never touches trading DB state, orders, exchanges, or execution flags.
"""
from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import math
from collections.abc import Mapping
from pathlib import Path
from typing import Any

CP69_SCHEMA = "arunda.runtime_observation"
CP69_SCHEMA_VERSION = "1.0"
CP69_SOURCE_SYSTEM = "ArundaTrader"
CP69_ENVIRONMENT_ID = "arundatrader"
CP69_ADAPTER_ID = "arundatrader_adapter"
OBSERVATION_DIR = Path(__file__).resolve().parent / "runtime_observations"
DEFAULT_STREAM_PATH = OBSERVATION_DIR / "arundatrader_runtime_observations.jsonl"
DEFAULT_CURRENT_OBSERVATION_PATH = OBSERVATION_DIR / "arundatrader_current_runtime_observation.jsonl"
EXECUTION_STATE = {
    "EXECUTION": "OFF",
    "REAL_ORDER": False,
    "REAL_TRADE": False,
    "DB_WRITES": 0,
}


def _json_safe(value: Any, name: str) -> Any:
    """Convert known data containers only; reject opaque runtime objects."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{name} contains a non-finite number")
        return value
    if isinstance(value, enum.Enum):
        return _json_safe(value.value, name)
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return _json_safe(dataclasses.asdict(value), name)
    if isinstance(value, Mapping):
        result = {}
        for key, item in value.items():
            if not isinstance(key, (str, int, float, bool)):
                raise TypeError(f"{name} contains a non-JSON mapping key")
            result[str(key)] = _json_safe(item, f"{name}.{key}")
        return result
    if isinstance(value, (list, tuple)):
        return [_json_safe(item, f"{name}[]") for item in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        converted = value.to_dict()
        if converted is value:
            raise TypeError(f"{name}.to_dict returned itself")
        return _json_safe(converted, name)
    raise TypeError(f"{name} contains unsupported runtime type: {type(value).__name__}")


def build_runtime_snapshot_id(state: Mapping[str, Any]) -> str:
    """Return a content-addressed ID for this exact serialized runtime state."""
    safe_state = _json_safe(state, "state")
    canonical = json.dumps(
        safe_state, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    )
    return "RS-" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_observation(
    *,
    emitted_at: str,
    universe_assets: Any,
    market_data_results: Any,
    opportunity_by_asset: Any,
    dynamic_signals: Any,
    validation_results: Any,
    fusion_snapshot: Any,
    score_snapshot: Any,
    decision_snapshot: Any,
    risk_snapshot: Any,
    trade_gate_snapshot: Any,
    trade_ready_assets: Any,
    runtime_snapshot_id: str | None = None,
    observation_id: str | None = None,
    knowledge_cutoff: str | None = None,
) -> dict[str, Any]:
    for name, value in (("emitted_at", emitted_at),):
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} must be a non-empty string")
    if knowledge_cutoff is not None and (
        not isinstance(knowledge_cutoff, str) or not knowledge_cutoff.strip()
    ):
        raise ValueError("knowledge_cutoff must be non-empty text when supplied")

    state = _json_safe({
        "universe_assets": universe_assets,
        "market_data_results": market_data_results,
        "opportunity_by_asset": opportunity_by_asset,
        "dynamic_signals": dynamic_signals,
        "validation_results": validation_results,
        "fusion_snapshot": fusion_snapshot,
        "score_snapshot": score_snapshot,
        "decision_snapshot": decision_snapshot,
        "risk_snapshot": risk_snapshot,
        "trade_gate_snapshot": trade_gate_snapshot,
        "trade_ready_assets": trade_ready_assets,
    }, "state")
    derived_snapshot_id = build_runtime_snapshot_id(state)
    if runtime_snapshot_id is not None and runtime_snapshot_id != derived_snapshot_id:
        raise ValueError("runtime_snapshot_id does not match serialized runtime state")
    runtime_snapshot_id = derived_snapshot_id
    observation_id = observation_id or f"obs:{runtime_snapshot_id}"
    if not isinstance(observation_id, str) or not observation_id.strip():
        raise ValueError("observation_id must be non-empty text")

    observation = {
        "schema": CP69_SCHEMA,
        "schema_version": CP69_SCHEMA_VERSION,
        "source_system": CP69_SOURCE_SYSTEM,
        "environment_id": CP69_ENVIRONMENT_ID,
        "adapter_id": CP69_ADAPTER_ID,
        "observation_id": observation_id,
        "emitted_at": emitted_at,
        "knowledge_cutoff": knowledge_cutoff,
        "provenance": {
            "source": "arunda_pipeline",
            "runtime_snapshot_id": runtime_snapshot_id,
        },
        "state": state,
        "execution_state": dict(EXECUTION_STATE),
    }
    _validate_observation(observation)
    return observation


def append_observation(
    observation: dict[str, Any],
    stream_path: Path = DEFAULT_STREAM_PATH,
) -> Path:
    if not isinstance(observation, dict):
        raise TypeError("observation must be a dict")
    _validate_observation(observation)
    encoded = json.dumps(
        observation, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    )
    path = Path(stream_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded + "\n")
    return path


def write_current_observation(
    observation: dict[str, Any],
    observation_path: Path = DEFAULT_CURRENT_OBSERVATION_PATH,
) -> Path:
    """Atomically publish exactly one current event for the existing Aroonda consumer."""
    if not isinstance(observation, dict):
        raise TypeError("observation must be a dict")
    _validate_observation(observation)
    encoded = json.dumps(
        observation, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ) + "\\n"
    path = Path(observation_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(path.name + ".tmp")
    try:
        temporary_path.write_text(encoded, encoding="utf-8", newline="\\n")
        temporary_path.replace(path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()
    return path


def _validate_observation(observation: dict[str, Any]) -> None:
    required = {
        "schema", "schema_version", "source_system", "environment_id",
        "adapter_id", "observation_id", "emitted_at", "provenance",
        "state", "execution_state",
    }
    missing = sorted(required - set(observation))
    if missing:
        raise ValueError(f"missing observation fields: {missing}")
    if observation["schema"] != CP69_SCHEMA or observation["schema_version"] != CP69_SCHEMA_VERSION:
        raise ValueError("invalid CP69 schema")
    if observation["source_system"] != CP69_SOURCE_SYSTEM:
        raise ValueError("invalid CP69 source system")
    if observation["environment_id"] != CP69_ENVIRONMENT_ID:
        raise ValueError("invalid CP69 environment identity")
    if observation["adapter_id"] != CP69_ADAPTER_ID:
        raise ValueError("invalid CP69 adapter identity")
    if observation["execution_state"] != EXECUTION_STATE:
        raise ValueError("unsafe execution state")
    if not isinstance(observation["state"], dict):
        raise ValueError("state must be an object")
    provenance = observation["provenance"]
    if not isinstance(provenance, dict) or not isinstance(provenance.get("runtime_snapshot_id"), str):
        raise ValueError("runtime snapshot provenance missing")
    if observation["observation_id"] != f"obs:{provenance['runtime_snapshot_id']}":
        raise ValueError("observation/runtime snapshot identity mismatch")
    _json_safe(observation, "observation")


__all__ = [
    "CP69_ADAPTER_ID", "CP69_ENVIRONMENT_ID", "CP69_SCHEMA",
    "CP69_SCHEMA_VERSION", "CP69_SOURCE_SYSTEM", "DEFAULT_STREAM_PATH",
    "DEFAULT_CURRENT_OBSERVATION_PATH", "append_observation",
    "write_current_observation", "build_observation", "build_runtime_snapshot_id",
]
