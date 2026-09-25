"""CP49 first-attempt lifecycle orchestration contract.

This module orchestrates contracts only. It performs no exchange/network/DB I/O.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional

from cp49_first_execution_contract_v0_1 import (
    AttemptState, ExecutionSafetyGate, FirstExecutionAttempt, OrderIntentBoundary,
)
from cp49_observation_envelope_v0_1 import ObservationEnvelope
from cp49_provider_preflight_v0_1 import ProviderPreflightResult


@dataclass(frozen=True)
class LifecycleResult:
    status: AttemptState
    reason: str
    attempt: Optional[FirstExecutionAttempt] = None
    observation: Optional[ObservationEnvelope] = None


def prepare_first_attempt(
    safety: ExecutionSafetyGate,
    intent: OrderIntentBoundary,
    preflight: ProviderPreflightResult,
    *,
    attempt_id: str,
    started_at_ms: int,
) -> LifecycleResult:
    if safety.validate() is not AttemptState.READY:
        return LifecycleResult(AttemptState.BLOCKED, "EXECUTION_AUTHORIZATION_NOT_READY")
    if intent.validate() is not AttemptState.READY:
        return LifecycleResult(AttemptState.BLOCKED, "ORDER_INTENT_NOT_READY")
    if preflight.status != "PASS" or preflight.intent_id != intent.intent_id:
        return LifecycleResult(AttemptState.BLOCKED, "PROVIDER_PREFLIGHT_NOT_PASS")

    attempt = FirstExecutionAttempt(
        attempt_id=attempt_id,
        decision_id=intent.decision_id,
        intent_id=intent.intent_id,
        started_at_ms=started_at_ms,
        outcome=AttemptState.READY,
    )
    if attempt.validate() is not AttemptState.READY:
        return LifecycleResult(AttemptState.BLOCKED, "FIRST_ATTEMPT_INVALID")
    return LifecycleResult(AttemptState.READY, "FIRST_ATTEMPT_READY", attempt=attempt)


def finalize_attempt(
    attempt: FirstExecutionAttempt,
    *,
    decision_timestamp_ms: int,
    knowledge_cutoff_ms: int,
    execution_attempt_timestamp_ms: int,
    snapshot_id: str,
    market: str,
    venue: str,
    response_status: str,
    outcome: AttemptState,
    latency_ms: int,
    request_id: str,
    rejection_code: str | None = None,
    post_attempt_state: str | None = None,
    aroonda_observation_id: str | None = None,
    lesson_id: str | None = None,
) -> LifecycleResult:
    if not isinstance(attempt, FirstExecutionAttempt):
        return LifecycleResult(AttemptState.BLOCKED, "ATTEMPT_INVALID")
    if attempt.outcome is not AttemptState.READY:
        return LifecycleResult(AttemptState.BLOCKED, "ATTEMPT_ALREADY_FINALIZED")
    final_attempt = FirstExecutionAttempt(
        attempt_id=attempt.attempt_id,
        decision_id=attempt.decision_id,
        intent_id=attempt.intent_id,
        started_at_ms=attempt.started_at_ms,
        outcome=outcome,
        response_code=response_status,
        latency_ms=latency_ms,
    )
    if final_attempt.validate() is not outcome:
        return LifecycleResult(AttemptState.BLOCKED, "FINAL_ATTEMPT_INVALID")

    observation = ObservationEnvelope(
        decision_id=attempt.decision_id,
        snapshot_id=snapshot_id,
        attempt_id=attempt.attempt_id,
        decision_timestamp_ms=decision_timestamp_ms,
        knowledge_cutoff_ms=knowledge_cutoff_ms,
        execution_attempt_timestamp_ms=execution_attempt_timestamp_ms,
        market=market,
        venue=venue,
        order_intent_id=attempt.intent_id,
        request_id=request_id,
        response_status=response_status,
        outcome=outcome,
        latency_ms=latency_ms,
        rejection_code=rejection_code,
        post_attempt_state=post_attempt_state,
        aroonda_observation_id=aroonda_observation_id,
        lesson_id=lesson_id,
        non_secret_metadata=(
            ("response_status", response_status),
            ("outcome", outcome.value),
        ),
    )
    if observation.validate() is not outcome:
        return LifecycleResult(AttemptState.BLOCKED, "OBSERVATION_INVALID")
    return LifecycleResult(outcome, "FIRST_ATTEMPT_FINALIZED", final_attempt, observation)
