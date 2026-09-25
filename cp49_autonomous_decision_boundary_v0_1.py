"""CP49 autonomous decision boundary.

Provider-neutral adapter from a canonical market decision to CP49 OrderIntent.
No network, exchange, database, or execution I/O.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping

from cp49_first_execution_contract_v0_1 import OrderIntentBoundary


@dataclass(frozen=True)
class AutonomousDecisionInput:
    decision_id: str
    snapshot_id: str
    decision_timestamp_ms: int
    knowledge_cutoff_ms: int
    asset: str
    direction: str
    entry_price: float
    invalidation_price: float
    position_size: float
    quantity_source: str
    venue: str
    intent_id: str
    provenance: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class AutonomousDecisionBoundaryResult:
    status: str
    reason: str
    decision: AutonomousDecisionInput | None = None
    order_intent: OrderIntentBoundary | None = None


def _block(reason: str) -> AutonomousDecisionBoundaryResult:
    return AutonomousDecisionBoundaryResult("BLOCK", reason)


def build_autonomous_decision_boundary(
    decision: AutonomousDecisionInput,
) -> AutonomousDecisionBoundaryResult:
    if not isinstance(decision, AutonomousDecisionInput):
        return _block("DECISION_INPUT_INVALID")

    required = (
        decision.decision_id, decision.snapshot_id, decision.asset,
        decision.venue, decision.intent_id, decision.quantity_source,
    )
    if any(not str(v).strip() for v in required):
        return _block("DECISION_IDENTITY_OR_PROVENANCE_MISSING")

    if decision.decision_timestamp_ms <= 0 or decision.knowledge_cutoff_ms <= 0:
        return _block("DECISION_TIMESTAMP_INVALID")
    if decision.knowledge_cutoff_ms > decision.decision_timestamp_ms:
        return _block("KNOWLEDGE_CUTOFF_AFTER_DECISION")
    if decision.direction not in {"LONG", "SHORT"}:
        return _block("DIRECTION_INVALID")
    if decision.entry_price <= 0 or decision.invalidation_price <= 0:
        return _block("PRICE_INVALID")
    if decision.position_size <= 0:
        return _block("POSITION_SIZE_INVALID")
    if not decision.provenance:
        return _block("PROVENANCE_MISSING")

    provenance_keys = {str(k).strip().lower() for k, _ in decision.provenance}
    required_keys = {"decision", "risk", "allocation", "position_size", "quantity"}
    if not required_keys.issubset(provenance_keys):
        return _block("UPSTREAM_PROVENANCE_INCOMPLETE")

    intent = OrderIntentBoundary(
        decision_id=decision.decision_id,
        intent_id=decision.intent_id,
        asset=decision.asset,
        direction=decision.direction,
        quantity=decision.position_size,
        quantity_source=decision.quantity_source,
        venue=decision.venue,
    )
    if intent.validate().value != "READY":
        return _block("ORDER_INTENT_INVALID")

    return AutonomousDecisionBoundaryResult(
        "PASS", "AUTONOMOUS_DECISION_BOUNDARY_VALID", decision, intent
    )


def build_from_mapping(data: Mapping[str, Any]) -> AutonomousDecisionBoundaryResult:
    """Explicit mapping adapter; caller must supply the canonical upstream data."""
    try:
        decision = AutonomousDecisionInput(
            decision_id=str(data["decision_id"]),
            snapshot_id=str(data["snapshot_id"]),
            decision_timestamp_ms=int(data["decision_timestamp_ms"]),
            knowledge_cutoff_ms=int(data["knowledge_cutoff_ms"]),
            asset=str(data["asset"]),
            direction=str(data["direction"]),
            entry_price=float(data["entry_price"]),
            invalidation_price=float(data["invalidation_price"]),
            position_size=float(data["position_size"]),
            quantity_source=str(data["quantity_source"]),
            venue=str(data["venue"]),
            intent_id=str(data["intent_id"]),
            provenance=tuple((str(k), str(v)) for k, v in data["provenance"]),
        )
    except (KeyError, TypeError, ValueError):
        return _block("CANONICAL_DECISION_MAPPING_INVALID")
    return build_autonomous_decision_boundary(decision)
