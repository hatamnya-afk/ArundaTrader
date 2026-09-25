"""ARUNDA TRADER — CP49 execution observation envelope v0.1.

Immutable observation-time metadata; no secret material and no I/O.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Tuple
from cp49_first_execution_contract_v0_1 import AttemptState


@dataclass(frozen=True)
class ObservationEnvelope:
    decision_id: str
    snapshot_id: str
    attempt_id: str
    decision_timestamp_ms: int
    knowledge_cutoff_ms: int
    execution_attempt_timestamp_ms: int
    market: str
    venue: str
    order_intent_id: str
    request_id: str
    response_status: str
    outcome: AttemptState
    latency_ms: int
    rejection_code: Optional[str] = None
    post_attempt_state: Optional[str] = None
    aroonda_observation_id: Optional[str] = None
    lesson_id: Optional[str] = None
    non_secret_metadata: Tuple[Tuple[str, str], ...] = ()

    def validate(self) -> AttemptState:
        required = (
            self.decision_id, self.snapshot_id, self.attempt_id,
            self.market, self.venue, self.order_intent_id,
            self.request_id, self.response_status,
        )
        if any(not value.strip() for value in required):
            return AttemptState.BLOCKED
        positive = (
            self.decision_timestamp_ms,
            self.knowledge_cutoff_ms,
            self.execution_attempt_timestamp_ms,
        )
        if any(value <= 0 for value in positive):
            return AttemptState.BLOCKED
        if self.knowledge_cutoff_ms > self.decision_timestamp_ms:
            return AttemptState.BLOCKED
        if self.execution_attempt_timestamp_ms < self.decision_timestamp_ms:
            return AttemptState.BLOCKED
        if self.latency_ms < 0:
            return AttemptState.BLOCKED
        if any(not k.strip() or not v.strip() for k, v in self.non_secret_metadata):
            return AttemptState.BLOCKED
        return self.outcome


__all__ = ["ObservationEnvelope"]
