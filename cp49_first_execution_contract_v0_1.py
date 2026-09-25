"""ARUNDA TRADER — CP49 first execution attempt contracts v0.1.

Provider-neutral, fail-closed lifecycle. No network, exchange, order, or DB I/O.
"""
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AttemptState(str, Enum):
    BLOCKED = "BLOCKED"
    READY = "READY"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True)
class ExecutionSafetyGate:
    management_authorized: bool
    implementation_verified: bool
    prior_attempt_exists: bool
    execution_enabled: bool
    order_submission_enabled: bool
    exchange_write_enabled: bool
    automatic_retry_enabled: bool

    def validate(self) -> AttemptState:
        if not self.management_authorized or not self.implementation_verified:
            return AttemptState.BLOCKED
        if self.prior_attempt_exists or self.automatic_retry_enabled:
            return AttemptState.BLOCKED
        if not self.execution_enabled or not self.order_submission_enabled:
            return AttemptState.BLOCKED
        if not self.exchange_write_enabled:
            return AttemptState.BLOCKED
        return AttemptState.READY


@dataclass(frozen=True)
class OrderIntentBoundary:
    decision_id: str
    intent_id: str
    asset: str
    direction: str
    quantity: float
    quantity_source: str
    venue: str

    def validate(self) -> AttemptState:
        required = (self.decision_id, self.intent_id, self.asset, self.venue, self.quantity_source)
        if any(not value.strip() for value in required):
            return AttemptState.BLOCKED
        if self.direction not in {"LONG", "SHORT"}:
            return AttemptState.BLOCKED
        if self.quantity <= 0:
            return AttemptState.BLOCKED
        return AttemptState.READY


@dataclass(frozen=True)
class FirstExecutionAttempt:
    attempt_id: str
    decision_id: str
    intent_id: str
    started_at_ms: int
    outcome: AttemptState
    response_code: Optional[str] = None
    latency_ms: Optional[int] = None

    def validate(self) -> AttemptState:
        if not self.attempt_id.strip() or not self.decision_id.strip() or not self.intent_id.strip():
            return AttemptState.BLOCKED
        if self.started_at_ms <= 0:
            return AttemptState.BLOCKED
        if self.outcome not in {
            AttemptState.ACCEPTED,
            AttemptState.REJECTED,
            AttemptState.BLOCKED,
            AttemptState.INCONCLUSIVE,
        }:
            return AttemptState.BLOCKED
        if self.latency_ms is not None and self.latency_ms < 0:
            return AttemptState.BLOCKED
        return self.outcome


def validate_execution_safety_gate(gate: ExecutionSafetyGate) -> AttemptState:
    return gate.validate()


def validate_order_intent(intent: OrderIntentBoundary) -> AttemptState:
    return intent.validate()


def validate_first_execution_attempt(attempt: FirstExecutionAttempt) -> AttemptState:
    return attempt.validate()


__all__ = [
    "AttemptState",
    "ExecutionSafetyGate",
    "FirstExecutionAttempt",
    "OrderIntentBoundary",
    "validate_execution_safety_gate",
    "validate_first_execution_attempt",
    "validate_order_intent",
]
