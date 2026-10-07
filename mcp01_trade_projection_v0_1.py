"""MCP-01.4 compact trade projection.

Pure analytical projection over compact event evidence. A trade_event_id is an
authoritative execution/order-attempt identity; this module never creates one.
Repeated evidence for the same trade_event_id is reconciled into one projection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


SCHEMA = "arunda.trade_projection"
SCHEMA_VERSION = "1.0"

LIFECYCLE_ORDER = (
    "ORDER_ATTEMPTED",
    "PROVIDER_RESULT",
    "MARKET_OUTCOME",
)


@dataclass(frozen=True)
class TradeProjection:
    trade_event_id: str
    case_id: str | None
    decision_id: str | None
    asset: str | None
    direction: str | None
    first_cycle_id: str
    last_cycle_id: str
    lifecycle: str
    evidence_count: int
    providers: tuple[str, ...]
    latest_status: str | None
    latest_reason_code: str | None

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "trade_event_id": self.trade_event_id,
            "case_id": self.case_id,
            "decision_id": self.decision_id,
            "asset": self.asset,
            "direction": self.direction,
            "first_cycle_id": self.first_cycle_id,
            "last_cycle_id": self.last_cycle_id,
            "lifecycle": self.lifecycle,
            "evidence_count": self.evidence_count,
            "providers": list(self.providers),
            "latest_status": self.latest_status,
            "latest_reason_code": self.latest_reason_code,
        }


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field)


def _rank(value: str) -> int:
    try:
        return LIFECYCLE_ORDER.index(value)
    except ValueError:
        return -1


def project_trade(
    *,
    trade_event_id: str,
    first_cycle_id: str,
    last_cycle_id: str,
    lifecycle: str,
    evidence_count: int,
    case_id: str | None = None,
    decision_id: str | None = None,
    asset: str | None = None,
    direction: str | None = None,
    providers: Iterable[str] = (),
    latest_status: str | None = None,
    latest_reason_code: str | None = None,
) -> dict:
    trade_event_id = _require_text(trade_event_id, "trade_event_id")
    first_cycle_id = _require_text(first_cycle_id, "first_cycle_id")
    last_cycle_id = _require_text(last_cycle_id, "last_cycle_id")
    lifecycle = _require_text(lifecycle, "lifecycle")
    if lifecycle not in LIFECYCLE_ORDER:
        raise ValueError(f"unsupported lifecycle: {lifecycle}")
    if not isinstance(evidence_count, int) or isinstance(evidence_count, bool):
        raise ValueError("evidence_count must be an integer")
    if evidence_count < 1:
        raise ValueError("evidence_count must be >= 1")

    case_id = _optional_text(case_id, "case_id")
    decision_id = _optional_text(decision_id, "decision_id")
    asset = _optional_text(asset, "asset")
    direction = _optional_text(direction, "direction")
    if direction is not None and direction not in {"LONG", "SHORT", "NONE"}:
        raise ValueError(f"unsupported direction: {direction}")

    providers = tuple(sorted({_require_text(v, "provider") for v in providers}))
    latest_status = _optional_text(latest_status, "latest_status")
    latest_reason_code = _optional_text(latest_reason_code, "latest_reason_code")

    return TradeProjection(
        trade_event_id,
        case_id,
        decision_id,
        asset,
        direction,
        first_cycle_id,
        last_cycle_id,
        lifecycle,
        evidence_count,
        providers,
        latest_status,
        latest_reason_code,
    ).to_dict()


def aggregate_trades(events: Iterable[Mapping[str, object]]) -> list[dict]:
    trades: dict[str, dict] = {}

    for event in events:
        event_type = _require_text(event.get("event_type"), "event_type")
        if event_type not in LIFECYCLE_ORDER:
            continue

        trade_event_id = _require_text(event.get("trade_event_id"), "trade_event_id")
        cycle_id = _require_text(event.get("cycle_id"), "cycle_id")

        state = trades.setdefault(
            trade_event_id,
            {
                "trade_event_id": trade_event_id,
                "case_id": None,
                "decision_id": None,
                "asset": None,
                "direction": None,
                "first_cycle_id": cycle_id,
                "last_cycle_id": cycle_id,
                "lifecycle": event_type,
                "evidence_count": 0,
                "providers": set(),
                "latest_status": None,
                "latest_reason_code": None,
            },
        )

        state["evidence_count"] += 1
        state["first_cycle_id"] = min(state["first_cycle_id"], cycle_id)
        state["last_cycle_id"] = max(state["last_cycle_id"], cycle_id)

        if _rank(event_type) > _rank(state["lifecycle"]):
            state["lifecycle"] = event_type

        for field in ("case_id", "decision_id", "asset", "direction"):
            value = event.get(field)
            if value is None:
                continue
            value = _require_text(value, field)
            if state[field] is not None and state[field] != value:
                raise ValueError(
                    f"trade_event_id identity conflict: {trade_event_id} field={field}"
                )
            state[field] = value

        provider = event.get("provider")
        if provider is not None:
            state["providers"].add(_require_text(provider, "provider"))

        if event.get("status") is not None:
            state["latest_status"] = _require_text(event["status"], "status")
        if event.get("reason_code") is not None:
            state["latest_reason_code"] = _require_text(
                event["reason_code"], "reason_code"
            )

    result = []
    for trade_event_id in sorted(trades):
        state = trades[trade_event_id]
        result.append(project_trade(**state))
    return result
