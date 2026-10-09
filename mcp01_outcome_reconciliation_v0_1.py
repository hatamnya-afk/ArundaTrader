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
    "FILL_OUTCOME",
    "MARKET_OUTCOME",
    "CASE_OUTCOME",
)

_EVENT_STAGE = {
    "TRADE_READY": "DECISION",
    "ORDER_ATTEMPTED": "ORDER",
    "PROVIDER_RESULT": "PROVIDER_RESULT",
    "FILL_OUTCOME": "FILL_OUTCOME",
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
    fill_outcome: str | None
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
            "fill_outcome": self.fill_outcome,
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


def _merge_identity(state: dict, event: Mapping[str, object]) -> None:
    for field in ("decision_id", "trade_event_id", "asset", "direction", "case_id"):
        value = event.get(field)
        if value is None:
            continue
        value = _require_text(value, field)
        if state[field] is not None and state[field] != value:
            raise ValueError(f"reconciliation identity conflict: {field}={value}")
        state[field] = value


def _new_state(case_id: str | None, decision_id: str | None, trade_event_id: str | None) -> dict:
    return {
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
        "fill_outcome": None,
        "market_outcome": None,
        "case_outcome": None,
        "events": [],
    }


def reconcile_outcomes(events: Iterable[Mapping[str, object]]) -> list[dict]:
    # First retain the decision anchor independently. Trade evidence is keyed by
    # its authoritative trade_event_id. This allows one decision to have multiple
    # order attempts while still attaching the decision state to every trade chain.
    decision_anchors: dict[tuple[str | None, str], dict] = {}
    trades: dict[tuple[str | None, str], dict] = {}
    case_closures: dict[str, list[Mapping[str, object]]] = {}

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
        if state_name == "DECISION" and decision_id is None:
            raise ValueError("TRADE_READY requires decision_id")

        if state_name == "CASE_OUTCOME":
            if case_id is None:
                raise ValueError("CLOSED requires case_id")
            case_closures.setdefault(case_id, []).append(event)
            continue

        if state_name == "DECISION":
            key = (case_id, decision_id)
            state = decision_anchors.setdefault(key, _new_state(case_id, decision_id, None))
        else:
            key = (case_id, trade_event_id)
            state = trades.setdefault(key, _new_state(case_id, decision_id, trade_event_id))

        _merge_identity(state, event)
        state["evidence_count"] += 1
        state["states"].add(state_name)
        state["events"].append(event)

        provider = event.get("provider")
        if provider is not None:
            provider = _require_text(provider, "provider")
            if state["provider"] is not None and state["provider"] != provider:
                raise ValueError("reconciliation provider conflict")
            state["provider"] = provider

        if state_name == "PROVIDER_RESULT":
            state["provider_status"] = _optional_text(event.get("status"), "status")
            state["provider_reason_code"] = _optional_text(event.get("reason_code"), "reason_code")
        elif state_name == "FILL_OUTCOME":
            fill_outcome = _require_text(event.get("status"), "status")
            if fill_outcome not in {"FILLED", "NOT_FILLED"}:
                raise ValueError("FILL_OUTCOME status must be explicit FILLED or NOT_FILLED")
            if state["fill_outcome"] is not None and state["fill_outcome"] != fill_outcome:
                raise ValueError("conflicting fill outcomes for trade_event_id")
            state["fill_outcome"] = fill_outcome
        elif state_name == "MARKET_OUTCOME":
            state["market_outcome"] = _optional_text(event.get("status"), "status")

    # Attach each decision anchor to every trade event carrying that decision.
    # A decision with no order attempt remains a decision-only reconciliation.
    results = []
    attached_decisions: set[tuple[str | None, str]] = set()
    for key, state in trades.items():
        anchor_key = (state["case_id"], state["decision_id"]) if state["decision_id"] else None
        if anchor_key is not None and anchor_key in decision_anchors:
            anchor = decision_anchors[anchor_key]
            for field in ("case_id", "decision_id", "asset", "direction"):
                if anchor[field] is not None and state[field] is not None and anchor[field] != state[field]:
                    raise ValueError(f"reconciliation identity conflict: {field}={state[field]}")
                if state[field] is None:
                    state[field] = anchor[field]
            state["states"].add("DECISION")
            state["evidence_count"] += anchor["evidence_count"]
            attached_decisions.add(anchor_key)

    # A case closure belongs to the case, not to a newly-created trade identity.
    # When a case has multiple trades, its closure is reflected on each trade chain.
    for state in trades.values():
        case_id = state["case_id"]
        if case_id in case_closures:
            closure = case_closures[case_id][-1]
            state["states"].add("CASE_OUTCOME")
            state["evidence_count"] += 1
            state["case_outcome"] = _optional_text(closure.get("status"), "status")

    for key, state in decision_anchors.items():
        if key in attached_decisions:
            continue
        states_seen = tuple(name for name in RECONCILIATION_STATES if name in state["states"])
        results.append(OutcomeReconciliation(
            case_id=state["case_id"], decision_id=state["decision_id"], trade_event_id=None,
            asset=state["asset"], direction=state["direction"],
            state=states_seen[-1] if states_seen else "DECISION", states_seen=states_seen,
            evidence_count=state["evidence_count"], provider=None, provider_status=None,
            provider_reason_code=None, market_outcome=None, case_outcome=None,
            fill_outcome=None, complete=False,
        ).to_dict())

    for key in sorted(trades, key=lambda item: (item[0] or "", item[1] or "")):
        state = trades[key]
        states_seen = tuple(name for name in RECONCILIATION_STATES if name in state["states"])
        state_name = states_seen[-1] if states_seen else "DECISION"
        complete = all(name in state["states"] for name in ("DECISION", "ORDER", "PROVIDER_RESULT", "FILL_OUTCOME"))
        results.append(OutcomeReconciliation(
            case_id=state["case_id"], decision_id=state["decision_id"], trade_event_id=state["trade_event_id"],
            asset=state["asset"], direction=state["direction"], state=state_name,
            states_seen=states_seen, evidence_count=state["evidence_count"], provider=state["provider"],
            provider_status=state["provider_status"], provider_reason_code=state["provider_reason_code"],
            fill_outcome=state["fill_outcome"],
            market_outcome=state["market_outcome"], case_outcome=state["case_outcome"], complete=complete,
        ).to_dict())

    return results
