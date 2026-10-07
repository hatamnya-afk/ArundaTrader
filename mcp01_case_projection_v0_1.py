"""MCP-01.3 compact case projection.

Analytical projection over compact event evidence. Case identity is an
analytical-management identity only; this module never creates or changes
Trader decision_id or trade_event_id identities and never changes execution.

Implicit case assignment is deterministic and stream-local:
- an explicit case_id is always preserved;
- an event without case_id continues the currently open case for its asset;
- if no open case exists, a new analytical case_id is derived from the first
  event's stable evidence;
- a CLOSED event closes that case, so a later appearance of the same asset can
  begin a new case.

The input is treated as an append-oriented evidence stream and normalized by
(event_timestamp, event_id) before projection.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Iterable, Mapping


SCHEMA = "arunda.case_projection"
SCHEMA_VERSION = "1.1"

LIFECYCLE_ORDER = (
    "NEW",
    "SELECTED",
    "TRADE_READY",
    "ORDER_ATTEMPTED",
    "PROVIDER_RESULT",
    "MARKET_OUTCOME",
    "CLOSED",
)

_LIFECYCLE_EVENTS = frozenset(LIFECYCLE_ORDER)


@dataclass(frozen=True)
class CaseProjection:
    case_id: str
    asset: str
    first_cycle_id: str
    last_cycle_id: str
    lifecycle: str
    appearance_count: int
    decision_ids: tuple[str, ...]
    trade_event_ids: tuple[str, ...]
    latest_status: str | None

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "case_id": self.case_id,
            "asset": self.asset,
            "first_cycle_id": self.first_cycle_id,
            "last_cycle_id": self.last_cycle_id,
            "lifecycle": self.lifecycle,
            "appearance_count": self.appearance_count,
            "decision_ids": list(self.decision_ids),
            "trade_event_ids": list(self.trade_event_ids),
            "latest_status": self.latest_status,
        }


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _validate_event_shape(event: Mapping[str, object]) -> None:
    for field in ("event_type", "event_timestamp", "cycle_id", "asset"):
        _require_text(event.get(field), field)
    event_type = _require_text(event["event_type"], "event_type")
    if event_type not in _LIFECYCLE_EVENTS:
        raise ValueError(f"unsupported event_type: {event_type}")
    for field in (
        "event_id",
        "decision_id",
        "case_id",
        "status",
        "trade_event_id",
        "reason_code",
        "provider",
    ):
        value = event.get(field)
        if value is not None:
            _require_text(value, field)


def _lifecycle_rank(value: str) -> int:
    try:
        return LIFECYCLE_ORDER.index(value)
    except ValueError:
        return -1


def _derived_case_id(event: Mapping[str, object]) -> str:
    anchor = {
        "asset": _require_text(event["asset"], "asset"),
        "cycle_id": _require_text(event["cycle_id"], "cycle_id"),
        "event_id": _require_text(event.get("event_id"), "event_id"),
        "event_timestamp": _require_text(event["event_timestamp"], "event_timestamp"),
        "decision_id": event.get("decision_id"),
    }
    encoded = json.dumps(anchor, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "CASE-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def assign_case_ids(events: Iterable[Mapping[str, object]]) -> list[dict]:
    """Return normalized events with deterministic analytical case_id values.

    This is projection-time identity assignment, not a Trader identity issuer.
    Explicit case_id values remain authoritative for analytical correlation.
    """
    normalized = []
    for event in events:
        _validate_event_shape(event)
        normalized.append(dict(event))

    normalized.sort(
        key=lambda e: (
            _require_text(e["event_timestamp"], "event_timestamp"),
            _require_text(e.get("event_id"), "event_id"),
        )
    )

    active_by_asset: dict[str, str] = {}
    case_assets: dict[str, str] = {}
    result: list[dict] = []

    for event in normalized:
        asset = _require_text(event["asset"], "asset")
        explicit_case_id = event.get("case_id")
        if explicit_case_id is not None:
            case_id = _require_text(explicit_case_id, "case_id")
        else:
            case_id = active_by_asset.get(asset)
            if case_id is None:
                case_id = _derived_case_id(event)

        prior_asset = case_assets.get(case_id)
        if prior_asset is not None and prior_asset != asset:
            raise ValueError(f"case_id reused across assets: {case_id}")
        case_assets[case_id] = asset

        enriched = dict(event)
        enriched["case_id"] = case_id
        result.append(enriched)

        if event["event_type"] == "CLOSED":
            active_by_asset.pop(asset, None)
        else:
            active_by_asset[asset] = case_id

    return result


def project_case(
    *,
    case_id: str,
    asset: str,
    first_cycle_id: str,
    last_cycle_id: str,
    lifecycle: str,
    appearance_count: int,
    decision_ids: Iterable[str] = (),
    trade_event_ids: Iterable[str] = (),
    latest_status: str | None = None,
) -> dict:
    case_id = _require_text(case_id, "case_id")
    asset = _require_text(asset, "asset")
    first_cycle_id = _require_text(first_cycle_id, "first_cycle_id")
    last_cycle_id = _require_text(last_cycle_id, "last_cycle_id")
    lifecycle = _require_text(lifecycle, "lifecycle")
    if lifecycle not in LIFECYCLE_ORDER:
        raise ValueError(f"unsupported lifecycle: {lifecycle}")
    if not isinstance(appearance_count, int) or isinstance(appearance_count, bool):
        raise ValueError("appearance_count must be an integer")
    if appearance_count < 1:
        raise ValueError("appearance_count must be >= 1")

    decision_ids = tuple(sorted({_require_text(v, "decision_id") for v in decision_ids}))
    trade_event_ids = tuple(sorted({_require_text(v, "trade_event_id") for v in trade_event_ids}))
    if latest_status is not None:
        latest_status = _require_text(latest_status, "latest_status")

    return CaseProjection(
        case_id,
        asset,
        first_cycle_id,
        last_cycle_id,
        lifecycle,
        appearance_count,
        decision_ids,
        trade_event_ids,
        latest_status,
    ).to_dict()


def aggregate_cases(events: Iterable[Mapping[str, object]]) -> list[dict]:
    cases: dict[str, dict] = {}

    for event in assign_case_ids(events):
        case_id = _require_text(event["case_id"], "case_id")
        cycle_id = _require_text(event["cycle_id"], "cycle_id")
        asset = _require_text(event["asset"], "asset")
        state = cases.setdefault(
            case_id,
            {
                "case_id": case_id,
                "asset": asset,
                "first_cycle_id": cycle_id,
                "last_cycle_id": cycle_id,
                "lifecycle": "NEW",
                "appearance_count": 0,
                "decision_ids": set(),
                "trade_event_ids": set(),
                "latest_status": None,
            },
        )
        if state["asset"] != asset:
            raise ValueError(f"case_id reused across assets: {case_id}")

        state["appearance_count"] += 1
        state["last_cycle_id"] = cycle_id

        event_type = _require_text(event["event_type"], "event_type")
        if _lifecycle_rank(event_type) > _lifecycle_rank(state["lifecycle"]):
            state["lifecycle"] = event_type

        decision_id = event.get("decision_id")
        if decision_id:
            state["decision_ids"].add(_require_text(decision_id, "decision_id"))

        trade_event_id = event.get("trade_event_id")
        if trade_event_id:
            state["trade_event_ids"].add(_require_text(trade_event_id, "trade_event_id"))

        if event.get("status") is not None:
            state["latest_status"] = _require_text(event["status"], "status")

    return [
        project_case(
            case_id=state["case_id"],
            asset=state["asset"],
            first_cycle_id=state["first_cycle_id"],
            last_cycle_id=state["last_cycle_id"],
            lifecycle=state["lifecycle"],
            appearance_count=state["appearance_count"],
            decision_ids=state["decision_ids"],
            trade_event_ids=state["trade_event_ids"],
            latest_status=state["latest_status"],
        )
        for _, state in sorted(cases.items())
    ]
