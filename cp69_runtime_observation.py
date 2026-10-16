"""CP69 — canonical read-only runtime observation producer.

Trader-side serialization only. This module writes an observation artifact;
it never writes trading state, orders, exchange state, or the production DB.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import fields, is_dataclass
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


def _derive_failure_attribution(trade_gate_snapshot: Any, trade_ready_assets: Any) -> dict[str, Any]:
    """Count only attribution explicitly present in the same runtime snapshot."""
    if isinstance(trade_gate_snapshot, dict):
        rows = [row for row in trade_gate_snapshot.values() if isinstance(row, dict)]
    elif isinstance(trade_gate_snapshot, (list, tuple)):
        rows = [row for row in trade_gate_snapshot if isinstance(row, dict)]
    else:
        rows = []

    reason_counts: dict[str, int] = {}
    predicate_failures: dict[str, int] = {}
    for row in rows:
        reasons = row.get("reasons")
        if isinstance(reasons, str):
            reasons = [reasons]
        if isinstance(reasons, (list, tuple, set)):
            for reason in reasons:
                if isinstance(reason, str) and reason.strip():
                    key = reason.strip()
                    reason_counts[key] = reason_counts.get(key, 0) + 1

        # Predicate attribution is reported only when the source row explicitly
        # supplies named failed predicates; it is never inferred from a reason.
        predicates = row.get("predicate_failures", row.get("failed_predicates"))
        if isinstance(predicates, dict):
            for name, count in predicates.items():
                if isinstance(name, str) and name.strip() and isinstance(count, int) and not isinstance(count, bool) and count > 0:
                    key = name.strip()
                    predicate_failures[key] = predicate_failures.get(key, 0) + count
        elif isinstance(predicates, (list, tuple, set)):
            for name in predicates:
                if isinstance(name, str) and name.strip():
                    key = name.strip()
                    predicate_failures[key] = predicate_failures.get(key, 0) + 1

    if isinstance(trade_ready_assets, (list, tuple, set)):
        trade_ready_count = len(trade_ready_assets)
    else:
        # Unknown shape is explicitly unavailable, not a guessed zero.
        trade_ready_count = None

    return {
        "trade_ready_count": trade_ready_count,
        "predicate_failures": dict(sorted(predicate_failures.items())),
        "reason_counts": dict(sorted(reason_counts.items())),
    }


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
    knowledge_cutoff: str | None = None,
    news_items: Any = (),
    social_items: Any = (),
    launch_timestamp: str | None = None,
    db_writes: int = 0,
    db_write_boundary: str | None = None,
) -> dict[str, Any]:
    if not isinstance(emitted_at, str) or not emitted_at.strip():
        raise ValueError("emitted_at must be a non-empty string")

    if knowledge_cutoff is not None and (
        not isinstance(knowledge_cutoff, str) or not knowledge_cutoff.strip()
    ):
        raise ValueError("knowledge_cutoff must be a non-empty string when supplied")

    if not isinstance(db_writes, int) or isinstance(db_writes, bool) or db_writes < 0:
        raise ValueError("db_writes must be a non-negative integer")
    if db_writes == 0 and db_write_boundary is not None:
        raise ValueError("db_write_boundary must be absent when db_writes is zero")
    if db_writes > 0 and db_write_boundary != "CP49_AUTHORITATIVE_BIRTH_PERSISTENCE":
        raise ValueError("non-zero db_writes require the authoritative CP49 Birth boundary")

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
        "failure_attribution": _derive_failure_attribution(trade_gate_snapshot, trade_ready_assets),
        "news_items": news_items,
        "social_items": social_items,
        "launch_timestamp": launch_timestamp,
    }
    state = _project_observation_state(state)
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
            "db_write_boundary": db_write_boundary,
        },
        "state": state,
        "execution_state": {
            "EXECUTION": "OFF",
            "REAL_ORDER": False,
            "REAL_TRADE": False,
            "DB_WRITES": db_writes,
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
    if not isinstance(execution, dict):
        raise ValueError("invalid execution state")
    if execution.get("EXECUTION") != "OFF":
        raise ValueError("unsafe execution state: EXECUTION")
    if execution.get("REAL_ORDER") is not False:
        raise ValueError("unsafe execution state: REAL_ORDER")
    if execution.get("REAL_TRADE") is not False:
        raise ValueError("unsafe execution state: REAL_TRADE")
    db_writes = execution.get("DB_WRITES")
    if not isinstance(db_writes, int) or isinstance(db_writes, bool) or db_writes < 0:
        raise ValueError("invalid execution state: DB_WRITES")
    provenance = observation["provenance"]
    boundary = provenance.get("db_write_boundary") if isinstance(provenance, dict) else None
    if db_writes > 0 and boundary != "CP49_AUTHORITATIVE_BIRTH_PERSISTENCE":
        raise ValueError("unauthorized production DB write boundary")
    if db_writes == 0 and boundary is not None:
        raise ValueError("DB write boundary present with zero writes")


def _project_observation_state(value: Any) -> Any:
    """Project runtime domain objects into JSON-safe observation values."""
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _project_observation_state(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {
            key: _project_observation_state(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [_project_observation_state(item) for item in value]
    return value


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
