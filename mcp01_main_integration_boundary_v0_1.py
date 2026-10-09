"""Minimal MCP-01 selective integration boundary for MAIN.

Owns only the handoff between already-produced Trader decision/gate state and
the frozen CP49/MCP-01 contracts. It does not implement strategy, risk, gate,
execution, provider logic, or outcome inference.
"""
from __future__ import annotations

import sqlite3
from dataclasses import asdict
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from cp49_authoritative_decision_birth_issuer_v0_1 import (
    build_birth_identity_record,
    issue_canonical_decision_id,
)
from cp49_authoritative_decision_birth_store_v0_1 import ensure_birth_schema
from cp49_production_decision_birth_producer_v0_1 import require_production_decision_birth
from exchange_execution_contract import CanonicalExecutionResult
from mcp01_compact_event_evidence_v0_1 import (
    persist_events_isolated,
)
from mcp01_trader_evidence_bridge_v0_1 import (
    build_runtime_evidence_events,
    deduplicate_events,
)


def _market_birth_context(asset: str, market_data: Any) -> dict[str, Any]:
    candles = tuple(getattr(market_data, "candles", ()) or ())
    if not candles:
        raise RuntimeError(f"MCP01_BIRTH_MARKET_SNAPSHOT_MISSING:{asset}")
    last = candles[-1]
    timestamp = last.get("timestamp") if isinstance(last, Mapping) else getattr(last, "timestamp", None)
    if not isinstance(timestamp, (int, float)):
        raise RuntimeError(f"MCP01_BIRTH_SNAPSHOT_TIMESTAMP_MISSING:{asset}")
    source = getattr(market_data, "source", None)
    if not isinstance(source, str) or not source.strip():
        raise RuntimeError(f"MCP01_BIRTH_SOURCE_MISSING:{asset}")
    symbol = f"{asset}/USDT"
    snapshot_id = f"{source.strip()}|{symbol}|1h|{int(timestamp)}"
    return {
        "asset": asset,
        "decision_timestamp_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
        "snapshot_id": snapshot_id,
        "source": source.strip(),
    }


def bind_authoritative_decision_birth(
    *,
    db_path: str,
    decision_snapshot: Mapping[str, Mapping[str, Any]],
    market_data_by_symbol: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], int]:
    """Create/persist canonical Decision Birth immediately after semantic Decision."""
    if not isinstance(decision_snapshot, Mapping) or not decision_snapshot:
        raise RuntimeError("MCP01_DECISION_SNAPSHOT_INVALID")

    birth_events: dict[str, dict[str, Any]] = {}
    issued: dict[str, str] = {}

    for raw_asset, decision in decision_snapshot.items():
        asset = str(raw_asset).strip().upper()
        if not asset or not isinstance(decision, Mapping):
            raise RuntimeError(f"MCP01_DECISION_BIRTH_INPUT_INVALID:{asset}")

        ctx = _market_birth_context(
            asset,
            market_data_by_symbol.get(f"{asset}/USDT"),
        )
        ctx["decision"] = dict(decision)
        decision_id = issue_canonical_decision_id(ctx)
        birth_events[asset] = build_birth_identity_record(
            ctx,
            decision_id=decision_id,
        )
        issued[asset] = decision_id

    with sqlite3.connect(db_path) as conn:
        ensure_birth_schema(conn)
        committed = require_production_decision_birth(
            birth_events,
            expected_assets=set(issued),
            conn=conn,
        )

    if committed != issued:
        raise RuntimeError("MCP01_COMMITTED_DECISION_ID_MISMATCH")

    bound_decisions: dict[str, dict[str, Any]] = {}
    for raw_asset, decision in decision_snapshot.items():
        asset = str(raw_asset).strip().upper()
        record = dict(decision)
        record["decision_id"] = issued[asset]
        bound_decisions[asset] = record

    return bound_decisions, len(committed)


def emit_mcp01_evidence(
    *,
    cycle_id: str,
    decision_snapshot: Mapping[str, Mapping[str, Any]],
    trade_gate_snapshot: Mapping[str, Mapping[str, Any]],
    trade_ready_assets: Sequence[str],
    execution_results: Mapping[str, Any] | None = None,
) -> tuple[int, list[dict[str, str]]]:
    """Emit frozen MCP-01 evidence after authoritative Trader outputs exist.

    The production execution boundary returns CanonicalExecutionResult objects,
    while the evidence bridge consumes mappings. Adapt those objects without
    inventing attempt identities or fill outcomes. Existing mapping callers are
    forwarded unchanged for backwards compatibility.
    """
    bridge_execution_results = execution_results
    if execution_results is not None and any(
        not isinstance(result, Mapping)
        for result in execution_results.values()
    ):
        bridge_execution_results = {}
        for raw_asset, result in execution_results.items():
            if isinstance(result, Mapping):
                bridge_execution_results[raw_asset] = result
            elif isinstance(result, CanonicalExecutionResult):
                bridge_execution_results[raw_asset] = asdict(result)
            else:
                raise TypeError(
                    "execution_results values must be mappings or "
                    "CanonicalExecutionResult instances"
                )
    normalized_gate: dict[str, dict[str, Any]] = {}
    for raw_asset, gate in trade_gate_snapshot.items():
        asset = str(raw_asset).strip().upper()
        row = dict(gate)
        if "trade_gate_status" not in row and "trade_gate_state" in row:
            row["trade_gate_status"] = row["trade_gate_state"]
        if "decision_id" not in row:
            row["decision_id"] = decision_snapshot.get(asset, {}).get("decision_id")
        normalized_gate[asset] = row

    events = build_runtime_evidence_events(
        cycle_id=cycle_id,
        emitted_at=datetime.now(timezone.utc).isoformat(),
        decision_snapshot=decision_snapshot,
        trade_gate_snapshot=normalized_gate,
        trade_ready_assets=trade_ready_assets,
        execution_results=bridge_execution_results,
    )
    events = deduplicate_events(events)
    return persist_events_isolated(events)
