"""Normalize a Toobit read-only order lookup into append-only outcome evidence.

This module never performs HTTP calls and never submits or cancels an order.
Only provider-returned fields are used; order limit price is never treated as
an execution price. Unknown statuses and incomplete fills remain explicit.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from exchange_execution_contract import CanonicalOrderRequest
from execution_outcome_evidence_contract_v0_1 import (
    append_execution_outcome_record,
    build_execution_outcome_record,
)


def capture_toobit_read_only_order_observation(
    *,
    request: CanonicalOrderRequest,
    provider_order: Mapping[str, Any],
    trade_event_id: str,
    observed_at: str,
    stream_path: Path,
) -> dict[str, Any]:
    """Persist one observed Toobit order row after identity checks.

    `observed_at` must be the caller's timezone-aware observation timestamp,
    not a fabricated provider timestamp. The row must identify the exact
    canonical intent through Toobit's clientOrderId. The trade-event identity
    must originate from the existing attempt boundary.
    """
    if not isinstance(request, CanonicalOrderRequest):
        raise ValueError("CANONICAL_ORDER_REQUEST_INVALID")
    if not isinstance(provider_order, Mapping):
        raise ValueError("TOOBIT_ORDER_OBSERVATION_INVALID")
    if not request.decision_id or not request.decision_id.strip():
        raise ValueError("AUTHORITATIVE_DECISION_ID_REQUIRED")
    if not isinstance(trade_event_id, str) or not trade_event_id.strip():
        raise ValueError("AUTHORITATIVE_TRADE_EVENT_ID_REQUIRED")

    client_order_id = provider_order.get("clientOrderId")
    if not isinstance(client_order_id, str) or not client_order_id.strip():
        raise ValueError("TOOBIT_CLIENT_ORDER_ID_MISSING")
    if client_order_id.strip() != request.intent_id:
        raise ValueError("TOOBIT_CLIENT_ORDER_ID_MISMATCH")

    symbol = provider_order.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError("TOOBIT_PROVIDER_SYMBOL_MISSING")

    order_id = provider_order.get("orderId")
    status = provider_order.get("status")
    if not isinstance(status, str) or not status.strip():
        raise ValueError("TOOBIT_PROVIDER_STATUS_MISSING")

    # Toobit exposes executedQty; avgPrice is accepted only when explicitly
    # present. The order's limit/quoted price is intentionally not substituted.
    executed_quantity = provider_order.get("executedQty")
    executed_price = provider_order.get("avgPrice")
    if executed_price is None:
        executed_price = provider_order.get("averagePrice")

    raw_identity = json.dumps(
        dict(provider_order), sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, default=str,
    )
    observation_id = "TOOBIT-LOOKUP-" + hashlib.sha256(
        (observed_at + "|" + raw_identity).encode("utf-8")
    ).hexdigest()

    record = build_execution_outcome_record(
        provider="TOOBIT",
        decision_id=request.decision_id,
        intent_id=request.intent_id,
        trade_event_id=trade_event_id.strip(),
        client_order_id=client_order_id.strip(),
        source_observation_id=observation_id,
        source_kind="READ_ONLY_LOOKUP",
        provider_status=status,
        observed_at=observed_at,
        exchange_order_id=None if order_id is None else str(order_id),
        executed_quantity=executed_quantity,
        executed_price=executed_price,
    )
    record["provider_symbol"] = symbol.strip().upper()
    persisted = append_execution_outcome_record(record, stream_path=Path(stream_path))
    return {"record": record, **persisted}


__all__ = ["capture_toobit_read_only_order_observation"]
