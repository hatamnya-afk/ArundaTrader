"""Provider-neutral execution outcome evidence contract v0.1.

Accepts already-observed adapter/provider facts only. This module makes no
network calls, submits no orders, does not infer fills from acceptance, and
requires the caller to choose an explicit evidence path. Persistence is
append-only and idempotent within a single process; it is not a cross-process
claim/locking mechanism.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

from exchange_execution_contract import CanonicalExecutionResult, CanonicalOrderRequest

SCHEMA = "arunda.execution_outcome_evidence"
SCHEMA_VERSION = "1.0"
SOURCE_KINDS = frozenset({"PROVIDER_RESPONSE", "READ_ONLY_LOOKUP", "ATTEMPT_EVENT"})

_OPEN_STATUSES = frozenset({"NEW", "OPEN", "ACCEPTED", "PENDING"})
_PARTIAL_STATUSES = frozenset({"PARTIALLY_FILLED", "PARTIAL_FILL"})
_FILLED_STATUSES = frozenset({"FILLED"})
_REJECTED_STATUSES = frozenset({"REJECTED"})
_TERMINAL_STATUSES = frozenset({"CANCELED", "CANCELLED", "EXPIRED"})


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field.upper()}_REQUIRED")
    return value.strip()


def _timestamp_utc(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("OBSERVED_AT_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("OBSERVED_AT_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("OBSERVED_AT_TIMEZONE_REQUIRED")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _optional_decimal(value: Any, field: str, *, allow_zero: bool = False) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field.upper()}_INVALID")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{field.upper()}_INVALID") from exc
    if not number.is_finite() or (number < 0 if allow_zero else number <= 0):
        raise ValueError(f"{field.upper()}_INVALID")
    return format(number, "f")


def _classify(status: str, quantity: str | None, price: str | None) -> tuple[str, str]:
    if status == "SUBMISSION_UNKNOWN":
        return "SUBMISSION_UNKNOWN", "POST_OUTCOME_AMBIGUOUS_RECONCILIATION_REQUIRED_NO_RETRY"
    if status in _OPEN_STATUSES:
        return "OPEN", "PROVIDER_STATUS_ONLY_NO_FILL_INFERRED"
    if status in _FILLED_STATUSES:
        if quantity is None or price is None:
            return "OUTCOME_INCOMPLETE", "FILLED_STATUS_MISSING_EXECUTION_DETAILS"
        return "FILLED", "EXPLICIT_FILLED_STATUS_WITH_EXECUTION_DETAILS"
    if status in _PARTIAL_STATUSES:
        if quantity is None or price is None:
            return "PARTIAL_FILL_INCOMPLETE", "PARTIAL_FILL_MISSING_EXECUTION_DETAILS"
        return "PARTIALLY_FILLED", "EXPLICIT_PARTIAL_STATUS_WITH_EXECUTION_DETAILS"
    if status in _REJECTED_STATUSES:
        return "REJECTED", "EXPLICIT_PROVIDER_REJECTION"
    if status in _TERMINAL_STATUSES:
        if quantity is None:
            return "TERMINAL_UNRECONCILED", "TERMINAL_STATUS_DOES_NOT_PROVE_ZERO_FILL"
        return "TERMINAL_WITH_EXECUTION_EVIDENCE", "TERMINAL_STATUS_REQUIRES_RECONCILIATION"
    return "UNKNOWN", "UNRECOGNIZED_PROVIDER_STATUS"


def build_execution_outcome_record(
    *,
    provider: str,
    decision_id: str,
    intent_id: str,
    trade_event_id: str,
    client_order_id: str,
    source_observation_id: str,
    source_kind: str,
    provider_status: str,
    observed_at: str,
    exchange_order_id: str | None = None,
    executed_quantity: Any = None,
    executed_price: Any = None,
    attempt_error_code: str | None = None,
) -> dict[str, Any]:
    """Normalize provider facts or a separately typed local attempt event."""
    provider = _required_text(provider, "provider").upper()
    decision_id = _required_text(decision_id, "decision_id")
    intent_id = _required_text(intent_id, "intent_id")
    trade_event_id = _required_text(trade_event_id, "trade_event_id")
    client_order_id = _required_text(client_order_id, "client_order_id")
    source_observation_id = _required_text(source_observation_id, "source_observation_id")
    source_kind = _required_text(source_kind, "source_kind").upper()
    if source_kind not in SOURCE_KINDS:
        raise ValueError("SOURCE_KIND_INVALID")
    status = _required_text(provider_status, "provider_status").upper()
    if status == "SUBMISSION_UNKNOWN" and source_kind != "ATTEMPT_EVENT":
        raise ValueError("AMBIGUOUS_SUBMISSION_MUST_BE_ATTEMPT_EVENT")
    if source_kind == "ATTEMPT_EVENT" and status != "SUBMISSION_UNKNOWN":
        raise ValueError("ATTEMPT_EVENT_STATUS_INVALID")
    if source_kind == "ATTEMPT_EVENT" and any(
        value is not None for value in (exchange_order_id, executed_quantity, executed_price)
    ):
        raise ValueError("ATTEMPT_EVENT_CANNOT_CLAIM_PROVIDER_EXECUTION_FACTS")
    timestamp = _timestamp_utc(observed_at)
    quantity = _optional_decimal(executed_quantity, "executed_quantity", allow_zero=True)
    price = _optional_decimal(executed_price, "executed_price")
    order_id = None if exchange_order_id is None else _required_text(exchange_order_id, "exchange_order_id")
    outcome_state, reason = _classify(status, quantity, price)

    identity = f"{provider}|{trade_event_id}|{source_kind}|{source_observation_id}"
    event_id = "OUT-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()
    event_type = (
        "EXECUTION_ATTEMPT_OUTCOME_OBSERVED"
        if source_kind == "ATTEMPT_EVENT"
        else "PROVIDER_OUTCOME_OBSERVED"
    )
    record = {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "event_type": event_type,
        "event_id": event_id,
        "provider": provider,
        "decision_id": decision_id,
        "intent_id": intent_id,
        "trade_event_id": trade_event_id,
        "client_order_id": client_order_id,
        "exchange_order_id": order_id,
        "source_observation_id": source_observation_id,
        "source_kind": source_kind,
        "observed_at": timestamp,
        "observed_at_source": "LOCAL_CAPTURE_CLOCK" if source_kind == "ATTEMPT_EVENT" else "PROVIDER_OR_LOOKUP_OBSERVATION",
        "provider_status": status,
        "outcome_state": outcome_state,
        "outcome_reason": reason,
        "executed_quantity": quantity,
        "executed_price": price,
        "fill_inferred": False,
    }
    if source_kind == "ATTEMPT_EVENT":
        record["provider_timestamp"] = None
        record["attempt_error_code"] = (
            None if attempt_error_code is None else _required_text(attempt_error_code, "attempt_error_code")
        )
    return record


def build_outcome_record_from_canonical_result(
    *,
    request: CanonicalOrderRequest,
    result: CanonicalExecutionResult,
    client_order_id: str,
    source_observation_id: str,
    observed_at: str | None = None,
) -> dict[str, Any]:
    """Bind a canonical adapter result to its authoritative request identities."""
    if not isinstance(request, CanonicalOrderRequest):
        raise ValueError("CANONICAL_ORDER_REQUEST_INVALID")
    if not isinstance(result, CanonicalExecutionResult):
        raise ValueError("CANONICAL_EXECUTION_RESULT_INVALID")
    if not request.decision_id or not request.decision_id.strip():
        raise ValueError("AUTHORITATIVE_DECISION_ID_REQUIRED")
    if not result.trade_event_id or not result.trade_event_id.strip():
        raise ValueError("AUTHORITATIVE_TRADE_EVENT_ID_REQUIRED")
    if result.asset is not None and result.asset.strip().upper() != request.asset.strip().upper():
        raise ValueError("PROVIDER_RESULT_ASSET_MISMATCH")
    if result.direction is not None and result.direction.strip().upper() != request.direction.strip().upper():
        raise ValueError("PROVIDER_RESULT_DIRECTION_MISMATCH")
    timestamp = observed_at or result.timestamp
    if not timestamp:
        raise ValueError("PROVIDER_OBSERVATION_TIMESTAMP_REQUIRED")
    return build_execution_outcome_record(
        provider=result.adapter or "PROVIDER_UNKNOWN",
        decision_id=request.decision_id,
        intent_id=request.intent_id,
        trade_event_id=result.trade_event_id,
        client_order_id=client_order_id,
        source_observation_id=source_observation_id,
        source_kind="PROVIDER_RESPONSE",
        provider_status=result.status,
        observed_at=timestamp,
        exchange_order_id=result.exchange_order_id,
        executed_quantity=result.executed_quantity,
        executed_price=result.executed_price,
    )


def append_execution_outcome_record(
    record: Mapping[str, Any],
    *,
    stream_path: Path,
) -> dict[str, Any]:
    """Append one record idempotently; caller explicitly supplies the target path."""
    if not isinstance(record, Mapping):
        raise ValueError("OUTCOME_RECORD_INVALID")
    row = dict(record)
    if row.get("schema") != SCHEMA or row.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("OUTCOME_SCHEMA_INVALID")
    if not isinstance(row.get("event_id"), str) or not row["event_id"].strip():
        raise ValueError("OUTCOME_EVENT_ID_REQUIRED")
    path = Path(stream_path)
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"OUTCOME_STREAM_INVALID_JSON_LINE:{line_number}") from exc
                if existing.get("event_id") != row["event_id"]:
                    continue
                if existing != row:
                    raise ValueError("OUTCOME_EVENT_ID_CONFLICT")
                return {"state": "ALREADY_PERSISTED", "event_id": row["event_id"], "path": str(path)}
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded + "\n")
    return {"state": "PERSISTED", "event_id": row["event_id"], "path": str(path)}


__all__ = [
    "SCHEMA", "SCHEMA_VERSION", "build_execution_outcome_record",
    "append_execution_outcome_record", "build_outcome_record_from_canonical_result",
]
