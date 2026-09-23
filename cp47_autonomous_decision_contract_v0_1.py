"""ARUNDA TRADER — CP47 autonomous decision and observation contracts v0.1.

Provider-neutral, fail-closed contracts for the first autonomous real-market
decision boundary. No network, exchange, database, execution, or order I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Tuple


class ResultState(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    INCONCLUSIVE = "INCONCLUSIVE"


class DecisionStage(str, Enum):
    MARKET_SNAPSHOT = "MARKET_SNAPSHOT"
    OPPORTUNITY = "OPPORTUNITY"
    SIGNAL = "SIGNAL"
    DECISION = "DECISION"
    RISK = "RISK"
    ALLOCATION = "ALLOCATION"
    POSITION_SIZE = "POSITION_SIZE"
    TRADE_GATE = "TRADE_GATE"
    TRADE_READY = "TRADE_READY"
    ORDER_INTENT = "ORDER_INTENT"
    PROVIDER_PREFLIGHT = "PROVIDER_PREFLIGHT"
    EXECUTION_ATTEMPT = "EXECUTION_ATTEMPT"
    EXCHANGE_RESPONSE = "EXCHANGE_RESPONSE"
    AROONDA_OBSERVATION = "AROONDA_OBSERVATION"
    LESSON = "LESSON"


@dataclass(frozen=True)
class DecisionSnapshot:
    snapshot_id: str
    captured_at_ms: int
    knowledge_cutoff_ms: int
    source_ids: FrozenSet[str]

    def validate(self) -> ResultState:
        if not self.snapshot_id.strip():
            return ResultState.BLOCK
        if self.captured_at_ms <= 0 or self.knowledge_cutoff_ms <= 0:
            return ResultState.BLOCK
        if self.knowledge_cutoff_ms > self.captured_at_ms:
            return ResultState.BLOCK
        if not self.source_ids or any(not item.strip() for item in self.source_ids):
            return ResultState.BLOCK
        return ResultState.PASS


@dataclass(frozen=True)
class AutonomousDecision:
    decision_id: str
    snapshot: DecisionSnapshot
    opportunity_id: str
    signal_id: str
    asset: str
    direction: str
    entry_price: float
    invalidation_price: float
    allocation_fraction: float
    position_size: float
    venue: str
    intent_id: str
    manually_injected_thesis: bool = False

    def validate(self) -> ResultState:
        if self.snapshot.validate() is not ResultState.PASS:
            return ResultState.BLOCK
        required = (
            self.decision_id,
            self.opportunity_id,
            self.signal_id,
            self.asset,
            self.venue,
            self.intent_id,
        )
        if any(not value.strip() for value in required):
            return ResultState.BLOCK
        if self.direction not in {"LONG", "SHORT"}:
            return ResultState.BLOCK
        if self.entry_price <= 0 or self.invalidation_price <= 0:
            return ResultState.BLOCK
        if self.direction == "LONG" and self.invalidation_price >= self.entry_price:
            return ResultState.BLOCK
        if self.direction == "SHORT" and self.invalidation_price <= self.entry_price:
            return ResultState.BLOCK
        if not 0.0 <= self.allocation_fraction <= 1.0:
            return ResultState.BLOCK
        if self.position_size <= 0:
            return ResultState.BLOCK
        if self.manually_injected_thesis:
            return ResultState.BLOCK
        return ResultState.PASS


@dataclass(frozen=True)
class AnalysisOnlyOpportunity:
    decision_id: str
    snapshot_id: str
    asset: str
    evaluated_at_ms: int
    execution_venue_available: bool
    realized_execution: bool = False

    def validate(self) -> ResultState:
        if not self.decision_id.strip() or not self.snapshot_id.strip():
            return ResultState.BLOCK
        if not self.asset.strip() or self.evaluated_at_ms <= 0:
            return ResultState.BLOCK
        if self.execution_venue_available or self.realized_execution:
            return ResultState.BLOCK
        return ResultState.PASS


@dataclass(frozen=True)
class CommandCenterEvent:
    event_id: str
    decision_id: str
    stage: DecisionStage
    occurred_at_ms: int
    knowledge_cutoff_ms: int
    parent_event_ids: Tuple[str, ...] = ()

    def validate(self) -> ResultState:
        if not self.event_id.strip() or not self.decision_id.strip():
            return ResultState.BLOCK
        if self.occurred_at_ms <= 0 or self.knowledge_cutoff_ms <= 0:
            return ResultState.BLOCK
        if self.knowledge_cutoff_ms > self.occurred_at_ms:
            return ResultState.BLOCK
        if any(not item.strip() for item in self.parent_event_ids):
            return ResultState.BLOCK
        return ResultState.PASS


@dataclass(frozen=True)
class FirstAttemptAuthorization:
    management_authorized: bool
    implementation_verified: bool
    prior_attempt_exists: bool
    execution_enabled: bool
    order_submission_enabled: bool
    exchange_write_enabled: bool
    database_write_enabled: bool
    automatic_retry_enabled: bool

    def validate(self) -> ResultState:
        if not self.management_authorized or not self.implementation_verified:
            return ResultState.BLOCK
        if self.prior_attempt_exists or self.automatic_retry_enabled:
            return ResultState.BLOCK
        if not self.execution_enabled:
            return ResultState.BLOCK
        if not self.order_submission_enabled or not self.exchange_write_enabled:
            return ResultState.BLOCK
        if self.database_write_enabled:
            return ResultState.BLOCK
        return ResultState.PASS


@dataclass(frozen=True)
class AroondaObservation:
    decision_id: str
    decision_snapshot_at_ms: int
    observed_at_ms: int
    outcome: ResultState
    recommendation: str
    uncertainty: str
    history_mutation_requested: bool = False

    def validate(self) -> ResultState:
        if not self.decision_id.strip():
            return ResultState.BLOCK
        if self.decision_snapshot_at_ms <= 0 or self.observed_at_ms <= 0:
            return ResultState.BLOCK
        if self.observed_at_ms < self.decision_snapshot_at_ms:
            return ResultState.BLOCK
        if not self.recommendation.strip() or not self.uncertainty.strip():
            return ResultState.BLOCK
        if self.history_mutation_requested:
            return ResultState.BLOCK
        return ResultState.PASS


def validate_autonomous_decision(decision: AutonomousDecision) -> ResultState:
    return decision.validate()


def validate_analysis_only_opportunity(
    opportunity: AnalysisOnlyOpportunity,
) -> ResultState:
    return opportunity.validate()


def validate_command_center_event(event: CommandCenterEvent) -> ResultState:
    return event.validate()


def validate_first_attempt_authorization(
    authorization: FirstAttemptAuthorization,
) -> ResultState:
    return authorization.validate()


def validate_aroonda_observation(
    observation: AroondaObservation,
) -> ResultState:
    return observation.validate()


__all__ = [
    "AnalysisOnlyOpportunity",
    "AroondaObservation",
    "AutonomousDecision",
    "CommandCenterEvent",
    "DecisionSnapshot",
    "DecisionStage",
    "FirstAttemptAuthorization",
    "ResultState",
    "validate_analysis_only_opportunity",
    "validate_aroonda_observation",
    "validate_autonomous_decision",
    "validate_command_center_event",
    "validate_first_attempt_authorization",
]
