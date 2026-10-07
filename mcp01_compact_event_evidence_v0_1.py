"""MCP-01.1 compact event evidence contract.

The evidence layer references authoritative Trader identities; it never creates
decision, case, or trade identities.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MCP01_SCHEMA = "arunda.compact_event_evidence"
MCP01_SCHEMA_VERSION = "1.0"
EVENT_NEW = "NEW"
EVENT_SELECTED = "SELECTED"
EVENT_TRADE_READY = "TRADE_READY"
EVENT_ORDER_ATTEMPTED = "ORDER_ATTEMPTED"
EVENT_PROVIDER_RESULT = "PROVIDER_RESULT"
EVENT_MARKET_OUTCOME = "MARKET_OUTCOME"
EVENT_CLOSED = "CLOSED"
EVENT_DATA_QUALITY = "DATA_QUALITY_EVENT"
EVENT_TYPES = frozenset({EVENT_NEW, EVENT_SELECTED, EVENT_TRADE_READY, EVENT_ORDER_ATTEMPTED, EVENT_PROVIDER_RESULT, EVENT_MARKET_OUTCOME, EVENT_CLOSED, EVENT_DATA_QUALITY})
STAGES = frozenset({"OPPORTUNITY", "DECISION", "RISK", "TRADE_GATE", "ORDER", "EXECUTION", "MARKET_OUTCOME", "DATA_QUALITY", "MANAGEMENT"})
DIRECTIONS = frozenset({"LONG", "SHORT", "NONE"})
DEFAULT_STREAM_PATH = Path(__file__).resolve().parent / "runtime_observations" / "arundatrader_compact_events.jsonl"

@dataclass(frozen=True)
class CompactEvent:
    event_id: str
    event_type: str
    event_timestamp: str
    cycle_id: str
    decision_id: str | None = None
    case_id: str | None = None
    asset: str | None = None
    direction: str | None = None
    stage: str = "MANAGEMENT"
    status: str | None = None
    reason_code: str | None = None
    provider: str | None = None
    trade_event_id: str | None = None
    correlation_id: str | None = None
    source_system: str = "ArundaTrader"
    environment_id: str = "arundatrader"
    schema: str = MCP01_SCHEMA
    schema_version: str = MCP01_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def validate(self) -> bool:
        _validate_event(self.to_dict())
        return True

def build_event(**kwargs: Any) -> CompactEvent:
    event = CompactEvent(**kwargs)
    event.validate()
    return event

def deterministic_event_id(**kwargs: Any) -> str:
    encoded = json.dumps(kwargs, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "EV-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()

def append_event(event: CompactEvent, stream_path: Path = DEFAULT_STREAM_PATH) -> Path:
    event.validate()
    path = Path(stream_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(event.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    return path

def append_event_idempotent(event: CompactEvent, stream_path: Path = DEFAULT_STREAM_PATH) -> Path:
    """Append evidence once; reject conflicting reuse of an existing event_id.

    This is a single-process append-only persistence boundary. Existing identical
    evidence is treated as already persisted; the same event_id with different
    content fails closed.
    """
    event.validate()
    path = Path(stream_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = event.to_dict()
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    if path.exists():
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                if not line.strip():
                    continue
                try:
                    existing = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"invalid evidence stream JSON at line {line_number}"
                    ) from exc
                if existing.get("event_id") != event.event_id:
                    continue
                if existing != payload:
                    raise ValueError(
                        f"event_id conflict at line {line_number}: {event.event_id}"
                    )
                return path
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(encoded + "\n")
    return path

def persist_events_isolated(
    events: list[CompactEvent],
    append_fn=append_event_idempotent,
) -> tuple[int, list[dict[str, str]]]:
    """Persist evidence without allowing persistence failure to abort Trader flow.

    Each event is attempted independently. Persistence failures are returned as
    bounded management diagnostics; they never alter the supplied event list or
    raise into the Trader pipeline. This boundary does not create replacement
    evidence when persistence itself is unavailable.
    """
    persisted = 0
    failures: list[dict[str, str]] = []
    for event in events:
        try:
            append_fn(event)
            persisted += 1
        except Exception as exc:
            failures.append(
                {
                    "event_id": event.event_id,
                    "error_type": f"{type(exc).__module__}.{type(exc).__name__}",
                }
            )
    return persisted, failures


def recover_failed_events(
    events: list[CompactEvent],
    failed_event_ids: list[str],
    append_fn=append_event_idempotent,
) -> tuple[int, list[dict[str, str]]]:
    """Retry only previously failed evidence using the original event identities.

    Recovery never creates replacement events and never retries events outside the
    supplied failure set. Idempotent persistence makes a successful prior write a
    harmless recovery result.
    """
    by_id = {event.event_id: event for event in events}
    if len(by_id) != len(events):
        raise ValueError("recovery input contains duplicate event_id values")
    if len(set(failed_event_ids)) != len(failed_event_ids):
        raise ValueError("recovery failure set contains duplicate event_id values")

    missing = [event_id for event_id in failed_event_ids if event_id not in by_id]
    if missing:
        raise ValueError(f"recovery event_id not present in supplied events: {missing[0]}")

    recovered = 0
    failures: list[dict[str, str]] = []
    for event_id in failed_event_ids:
        event = by_id[event_id]
        try:
            append_fn(event)
            recovered += 1
        except Exception as exc:
            failures.append(
                {
                    "event_id": event_id,
                    "error_type": f"{type(exc).__module__}.{type(exc).__name__}",
                }
            )
    return recovered, failures


def _require_text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")

def _validate_event(event: dict[str, Any]) -> None:
    for name in ("event_id", "event_type", "event_timestamp", "cycle_id"):
        _require_text(event.get(name), name)
    if event["event_type"] not in EVENT_TYPES:
        raise ValueError(f"unsupported event_type: {event['event_type']}")
    if event["stage"] not in STAGES:
        raise ValueError(f"unsupported stage: {event['stage']}")
    if event["schema"] != MCP01_SCHEMA or event["schema_version"] != MCP01_SCHEMA_VERSION:
        raise ValueError("invalid MCP-01 schema")
    if event["source_system"] != "ArundaTrader" or event["environment_id"] != "arundatrader":
        raise ValueError("invalid evidence source identity")
    for name in ("decision_id", "case_id", "asset", "status", "reason_code", "provider", "trade_event_id", "correlation_id"):
        if event.get(name) is not None:
            _require_text(event[name], name)
    if event.get("direction") is not None and event["direction"] not in DIRECTIONS:
        raise ValueError(f"unsupported direction: {event['direction']}")
    if event["event_type"] in {EVENT_SELECTED, EVENT_TRADE_READY}:
        _require_text(event.get("decision_id"), "decision_id")
    if event["event_type"] == EVENT_ORDER_ATTEMPTED:
        _require_text(event.get("decision_id"), "decision_id")
        _require_text(event.get("trade_event_id"), "trade_event_id")
    if event["event_type"] == EVENT_PROVIDER_RESULT:
        _require_text(event.get("trade_event_id"), "trade_event_id")
        _require_text(event.get("provider"), "provider")
    if event["event_type"] == EVENT_MARKET_OUTCOME:
        _require_text(event.get("trade_event_id"), "trade_event_id")
        _require_text(event.get("case_id"), "case_id")
    if event["event_type"] == EVENT_CLOSED:
        _require_text(event.get("case_id"), "case_id")
    if event["event_type"] == EVENT_DATA_QUALITY:
        if event["stage"] != "DATA_QUALITY":
            raise ValueError("DATA_QUALITY_EVENT requires DATA_QUALITY stage")
        _require_text(event.get("reason_code"), "reason_code")
