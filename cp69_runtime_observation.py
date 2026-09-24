"""CP69 — canonical read-only runtime observation producer.

Trader-side serialization only. This module writes an observation artifact;
it never writes trading state, orders, exchange state, or the production DB.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

CP69_SCHEMA = "arunda.runtime_observation"
CP69_SCHEMA_VERSION = "1.0"
CP69_SOURCE_SYSTEM = "ArundaTrader"
CP69_ENVIRONMENT_ID = "arundatrader"
CP69_ADAPTER_ID = "arundatrader_adapter"

DEFAULT_STREAM_PATH = (
    Path(__file__).resolve().parent
    / "runtime_observations"
    / "arundatrader_runtime_observations.jsonl"
)


def build_observation(
    *,
    emitted_at: str,
    observation_id: str | None = None,
    runtime_snapshot_id: str | None = None,
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
    knowledge_cutoff: str | None = None,
    news_items: Any = (),
    social_items: Any = (),
    launch_timestamp: str | None = None,
) -> dict[str, Any]:
    if not isinstance(emitted_at, str) or not emitted_at.strip():
        raise ValueError("emitted_at must be a non-empty string")

    if knowledge_cutoff is not None and (
        not isinstance(knowledge_cutoff, str) or not knowledge_cutoff.strip()
    ):
        raise ValueError("knowledge_cutoff must be a non-empty string when supplied")

    state = {
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
        "news_items": news_items,
        "social_items": social_items,
        "launch_timestamp": launch_timestamp,
    }
    _assert_json_safe(state, "state")

    canonical_state = json.dumps(
        state,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    if runtime_snapshot_id is None:
        runtime_snapshot_id = (
            "RS-"
            + hashlib.sha256(
                canonical_state.encode("utf-8")
            ).hexdigest()
        )

    observation_id = (
        observation_id
        if isinstance(observation_id, str) and observation_id.strip()
        else f"obs:{runtime_snapshot_id}"
    )

    return {
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
            "launch_boundary": launch_timestamp,
        },
        "state": state,
        "execution_state": {
            "EXECUTION": "OFF",
            "REAL_ORDER": False,
            "REAL_TRADE": False,
            "DB_WRITES": 0,
        },
    }


def append_observation(
    observation: dict[str, Any],
    stream_path: Path = DEFAULT_STREAM_PATH,
) -> Path:
    if not isinstance(observation, dict):
        raise TypeError("observation must be a dict")
    _validate_observation(observation)

    path = Path(stream_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        observation,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded)
        handle.write("\n")
    return path


def _validate_observation(observation: dict[str, Any]) -> None:
    required = {
        "schema",
        "schema_version",
        "source_system",
        "environment_id",
        "adapter_id",
        "observation_id",
        "emitted_at",
        "provenance",
        "state",
        "execution_state",
    }
    missing = sorted(required - set(observation))
    if missing:
        raise ValueError(f"missing observation fields: {missing}")
    if observation["schema"] != CP69_SCHEMA:
        raise ValueError("invalid CP69 schema")
    if observation["schema_version"] != CP69_SCHEMA_VERSION:
        raise ValueError("invalid CP69 schema version")
    if observation["source_system"] != CP69_SOURCE_SYSTEM:
        raise ValueError("invalid CP69 source system")
    if observation["environment_id"] != CP69_ENVIRONMENT_ID:
        raise ValueError("invalid CP69 environment identity")
    if observation["adapter_id"] != CP69_ADAPTER_ID:
        raise ValueError("invalid CP69 adapter identity")
    execution = observation["execution_state"]
    if execution != {
        "EXECUTION": "OFF",
        "REAL_ORDER": False,
        "REAL_TRADE": False,
        "DB_WRITES": 0,
    }:
        raise ValueError("unsafe execution state")


def _assert_json_safe(value: Any, name: str) -> None:
    try:
        json.dumps(value, sort_keys=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise TypeError(
            f"{name} contains non-JSON or non-finite runtime state"
        ) from exc


__all__ = [
    "CP69_ADAPTER_ID",
    "CP69_ENVIRONMENT_ID",
    "CP69_SCHEMA",
    "CP69_SCHEMA_VERSION",
    "CP69_SOURCE_SYSTEM",
    "DEFAULT_STREAM_PATH",
    "append_observation",
    "build_observation",
]
