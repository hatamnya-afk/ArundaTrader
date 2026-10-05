"""MCP-01.5 outcome reconciliation.

Pure analytical reconciliation over compact evidence. It links the authoritative
decision, case, trade event, provider response, and market outcome without
creating identities or changing Trader/execution behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping


SCHEMA = "arunda.outcome_reconciliation"
SCHEMA_VERSION = "1.0"

RECONCILIATION_STATES = (
    "DECISION",
    "ORDER",
    "PROVIDER_RESULT",
    "MARKET_OUTCOME",
    "CASE_OUTCOME",
)

_EVENT_STAGE = {
    "TRADE_READY": "DECISION",
    "ORDER_ATTEMPTED": "ORDER",
    "PROVIDER_RESULT": "PROVIDER_RESULT",
    "MARKET_OUTCOME": "MARKET_OUTCOME",
    "CLOSED": "CASE_OUTCOME",
}


@dataclass(frozen=True)
class OutcomeReconciliation:
    case_id: str | None
    decision_id: str | None
    trade_event_id: str | None
    asset: str | None
    direction: str | None
    state: str
    states_seen: tuple[str, ...]
    evidence_count: int
    provider: str | None
    provider_status: str | None
    provider_reason_code: str | None
    market_outcome: str | None
    case_outcome: str | None
    complete: bool

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "case_id": self.case_id,
            "decision_id": self.decision_id,
            "trade_event_id": self.trade_event_id,
            "asset": self.asset,
            "direction": self.direction,
            "state": self.state,
            "states_seen": list(self.states_seen),
            "evidence_count": self.evidence_count,
            "provider": self.provider,
            "provider_status": self.provider_status,
            "provider_reason_code": self.provider_reason_code,
            "market_outcome": self.market_outcome,
            "case_outcome": self.case_outcome,
            "complete": self.complete,
        }


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _optional_text(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field)


def _event_state(event_type: str) -> str | None:
    return _EVENT_STAGE.get(event_type)


def reconcile_outcomes(events: Iterable[Mapping[str, object]]) -> list[dict]:
    groups: dict[tuple[str | None, str | None], dict] = {}

    for event in events:
        event_type = _require_text(event.get("event_type"), "event_type")
        state_name = _event_state(event_type)
        if state_name is None:
            continue

        case_id = _optional_text(event.get("case_id"), "case_id")
        decision_id = _optional_text(event.get("decision_id"), "decision_id")
        trade_event_id = _optional_text(event.get("trade_event_id"), "trade_event_id")

        if state_name in {"ORDER", "PROVIDER_RESULT", "MARKET_OUTCOME"} and trade_event_id is None:
            raise ValueError(f"{event_type} requires trade_event_id")

        key = (case_id, trade_event_id or decision_id)
        state = groups.setdefault(
            key,
            {
                "case_id": case_id,
                "decision_id": decision_id,
                "trade_event_id": trade_event_id,
                "asset": None,
                "direction": None,
                "states": set(),
                "evidence_count": 0,
                "provider": None,
                "provider_status": None,
                "provider_reason_code": None,
                "market_outcome": None,
                "case_outcome": None,
            },
        )

        state["evidence_count"] += 1
        state["states"].add(state_name)

        for field in ("decision_id", "trade_event_id", "asset", "direction", "case_id"):
            value = event.get(field)
            if value is None:
                continue
            value = _require_text(value, field)
            if state[field] is not None and state[field] != value:
                raise ValueError(
                    f"reconciliation identity conflict: {field}={value}"
                )
            state[field] = value

        provider = event.get("provider")
        if provider is not None:
            provider = _require_text(provider, "provider")
            if state["provider"] is not None and state["provider"] != provider:
                raise ValueError("reconciliation provider conflict")
            state["provider"] = provider

        if state_name == "PROVIDER_RESULT":
            state["provider_status"] = _optional_text(
                event.get("status"), "status"
            )
            state["provider_reason_code"] = _optional_text(
                event.get("reason_code"), "reason_code"
            )
        elif state_name == "MARKET_OUTCOME":
            state["market_outcome"] = _optional_text(
                event.get("status"), "status"
            )
        elif state_name == "CASE_OUTCOME":
            state["case_outcome"] = _optional_text(
                event.get("status"), "status"
            )

    result = []
    for key in sorted(groups, key=lambda item: (item[0] or "", item[1] or "")):
        state = groups[key]
        states_seen = tuple(
            name for name in RECONCILIATION_STATES if name in state["states"]
        )
        state_name = states_seen[-1] if states_seen else "DECISION"
        complete = all(
            name in state["states"]
            for name in ("DECISION", "ORDER", "PROVIDER_RESULT")
        )
        result.append(
            OutcomeReconciliation(
                case_id=state["case_id"],
                decision_id=state["decision_id"],
                trade_event_id=state["trade_event_id"],
                asset=state["asset"],
                direction=state["direction"],
                state=state_name,
                states_seen=states_seen,
                evidence_count=state["evidence_count"],
                provider=state["provider"],
                provider_status=state["provider_status"],
                provider_reason_code=state["provider_reason_code"],
                market_outcome=state["market_outcome"],
                case_outcome=state["case_outcome"],
                complete=complete,
            ).to_dict()
        )
    return result
