"""MCP-01.3 compact case projection.

Pure analytical projection over compact event evidence. It never creates Trader
decision identities or trade identities and never changes execution behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


SCHEMA = "arunda.case_projection"
SCHEMA_VERSION = "1.0"

LIFECYCLE_ORDER = (
    "NEW",
    "SELECTED",
    "TRADE_READY",
    "ORDER_ATTEMPTED",
    "PROVIDER_RESULT",
    "MARKET_OUTCOME",
    "CLOSED",
)


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


def _require_event(event: Mapping[str, object]) -> None:
    for field in ("event_type", "cycle_id", "case_id", "asset"):
        _require_text(event.get(field), field)


def _lifecycle_rank(value: str) -> int:
    try:
        return LIFECYCLE_ORDER.index(value)
    except ValueError:
        return -1


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
    trade_event_ids = tuple(
        sorted({_require_text(v, "trade_event_id") for v in trade_event_ids})
    )
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
    for event in events:
        _require_event(event)
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
        state["first_cycle_id"] = min(state["first_cycle_id"], cycle_id)
        state["last_cycle_id"] = max(state["last_cycle_id"], cycle_id)

        event_type = _require_text(event["event_type"], "event_type")
        if _lifecycle_rank(event_type) > _lifecycle_rank(state["lifecycle"]):
            state["lifecycle"] = event_type

        decision_id = event.get("decision_id")
        if decision_id:
            state["decision_ids"].add(_require_text(decision_id, "decision_id"))
        trade_event_id = event.get("trade_event_id")
        if trade_event_id:
            state["trade_event_ids"].add(
                _require_text(trade_event_id, "trade_event_id")
            )
        if event.get("status") is not None:
            state["latest_status"] = _require_text(event["status"], "status")

    result = []
    for case_id in sorted(cases):
        state = cases[case_id]
        result.append(
            project_case(
                case_id=case_id,
                asset=state["asset"],
                first_cycle_id=state["first_cycle_id"],
                last_cycle_id=state["last_cycle_id"],
                lifecycle=state["lifecycle"],
                appearance_count=state["appearance_count"],
                decision_ids=state["decision_ids"],
                trade_event_ids=state["trade_event_ids"],
                latest_status=state["latest_status"],
            )
        )
    return result
