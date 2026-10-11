"""Build and persist MCP-01 evidence for a single execution attempt.

Pure event construction plus an explicit append-only JSONL persistence helper.
No exchange/network calls and no database access.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest
from mcp01_compact_event_evidence_v0_1 import (
    EVENT_ORDER_ATTEMPTED,
    EVENT_PROVIDER_RESULT,
    append_event_idempotent,
    build_event,
    deterministic_event_id,
)
from mcp01_trade_event_identity_v0_1 import validate_trade_event_id


def build_execution_attempt_events(
    *, request: CanonicalOrderRequest, result: CanonicalExecutionResult,
    cycle_id: str | None = None,
) -> list:
    """Create an ORDER_ATTEMPTED + PROVIDER_RESULT evidence pair.

    The boundary-issued trade_event_id is mandatory. The provider status is
    preserved verbatim; this function never infers FILL from acceptance or
    rejection from a transport exception.
    """
    trade_event_id = result.trade_event_id
    if not validate_trade_event_id(trade_event_id):
        raise ValueError("AUTHORITATIVE_TRADE_EVENT_ID_REQUIRED")
    if not request.decision_id:
        raise ValueError("AUTHORITATIVE_DECISION_ID_REQUIRED")
    timestamp = result.timestamp or request.timestamp
    provider = result.adapter or "PROVIDER_UNKNOWN"
    cycle = cycle_id or request.snapshot_id
    common = {
        "event_timestamp": timestamp,
        "cycle_id": cycle,
        "decision_id": request.decision_id,
        "asset": request.asset,
        "direction": request.direction,
        "trade_event_id": trade_event_id,
        "correlation_id": request.snapshot_id,
    }
    attempted = build_event(
        event_id=deterministic_event_id(
            event_type=EVENT_ORDER_ATTEMPTED, trade_event_id=trade_event_id
        ),
        event_type=EVENT_ORDER_ATTEMPTED,
        stage="ORDER",
        status="ATTEMPTED",
        reason_code=None,
        provider=provider,
        **common,
    )
    provider_result = build_event(
        event_id=deterministic_event_id(
            event_type=EVENT_PROVIDER_RESULT, trade_event_id=trade_event_id,
            status=result.status, error_code=result.error_code,
        ),
        event_type=EVENT_PROVIDER_RESULT,
        stage="EXECUTION",
        status=result.status,
        reason_code=result.error_code,
        provider=provider,
        **common,
    )
    return [attempted, provider_result]


def persist_execution_attempt_events(
    events: list,
    *,
    stream_path: Path,
) -> dict[str, Any]:
    """Persist evidence idempotently; report failures without fabricating success.

    The caller must explicitly invoke this function and choose the stream path.
    A failed write is returned as a failure and must remain visible to the
    observation/reconciliation owner.
    """
    persisted = 0
    failures = []
    for event in events:
        try:
            append_event_idempotent(event, Path(stream_path))
            persisted += 1
        except Exception as exc:
            failures.append({
                "event_id": getattr(event, "event_id", None),
                "error_type": f"{type(exc).__module__}.{type(exc).__name__}",
            })
    return {
        "persisted_count": persisted,
        "failure_count": len(failures),
        "failures": failures,
        "persistence_state": "PERSISTED" if not failures else "INCOMPLETE",
    }


__all__ = ["build_execution_attempt_events", "persist_execution_attempt_events"]
