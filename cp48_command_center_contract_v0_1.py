"""ARUNDA TRADER — CP48 Command Center contracts v0.1.

Read-only observability contracts for the desktop Command Center.
The Command Center is a projection of canonical decision/event state; it is
not a source of truth and performs no network, exchange, order, or DB write.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import FrozenSet, Tuple


class ProjectionState(str, Enum):
    PASS = "PASS"
    BLOCK = "BLOCK"
    INCONCLUSIVE = "INCONCLUSIVE"


class CommandCenterView(str, Enum):
    LIVE_ACTIVITY = "LIVE_ACTIVITY"
    AROONDA_SUPERVISOR = "AROONDA_SUPERVISOR"
    SYSTEM_HEALTH = "SYSTEM_HEALTH"
    DAILY_REPORT = "DAILY_REPORT"
    AUDIT = "AUDIT"


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    decision_id: str
    stage: str
    occurred_at_ms: int
    knowledge_cutoff_ms: int
    parent_event_ids: Tuple[str, ...] = ()
    state: ProjectionState = ProjectionState.INCONCLUSIVE

    def validate(self) -> ProjectionState:
        required = (self.event_id, self.decision_id, self.stage)
        if any(not value.strip() for value in required):
            return ProjectionState.BLOCK
        if self.occurred_at_ms <= 0 or self.knowledge_cutoff_ms <= 0:
            return ProjectionState.BLOCK
        if self.knowledge_cutoff_ms > self.occurred_at_ms:
            return ProjectionState.BLOCK
        if any(not value.strip() for value in self.parent_event_ids):
            return ProjectionState.BLOCK
        return ProjectionState.PASS


@dataclass(frozen=True)
class DecisionTrace:
    decision_id: str
    event_ids: Tuple[str, ...]
    source_ids: FrozenSet[str]
    snapshot_id: str

    def validate(self) -> ProjectionState:
        if not self.decision_id.strip() or not self.snapshot_id.strip():
            return ProjectionState.BLOCK
        if not self.event_ids or any(not value.strip() for value in self.event_ids):
            return ProjectionState.BLOCK
        if not self.source_ids or any(not value.strip() for value in self.source_ids):
            return ProjectionState.BLOCK
        return ProjectionState.PASS


@dataclass(frozen=True)
class CommandCenterProjection:
    decision_trace: DecisionTrace
    view: CommandCenterView
    generated_at_ms: int
    events: Tuple[EventRecord, ...]
    execution_controls_visible: bool = True
    execution_controls_writable: bool = False

    def validate(self) -> ProjectionState:
        if self.decision_trace.validate() is not ProjectionState.PASS:
            return ProjectionState.BLOCK
        if self.generated_at_ms <= 0 or not self.events:
            return ProjectionState.BLOCK
        if any(event.validate() is not ProjectionState.PASS for event in self.events):
            return ProjectionState.BLOCK
        if any(event.decision_id != self.decision_trace.decision_id for event in self.events):
            return ProjectionState.BLOCK
        if self.execution_controls_writable:
            return ProjectionState.BLOCK
        return ProjectionState.PASS


@dataclass(frozen=True)
class DesktopEntryContract:
    application_id: str
    display_name: str
    entrypoint: str
    command_center_view: CommandCenterView = CommandCenterView.LIVE_ACTIVITY
    requires_terminal: bool = False
    requires_manual_command: bool = False

    def validate(self) -> ProjectionState:
        if not self.application_id.strip() or not self.display_name.strip():
            return ProjectionState.BLOCK
        if not self.entrypoint.strip():
            return ProjectionState.BLOCK
        if self.requires_terminal or self.requires_manual_command:
            return ProjectionState.BLOCK
        return ProjectionState.PASS


@dataclass(frozen=True)
class SupervisorObservationLink:
    decision_id: str
    observation_id: str
    lesson_id: str
    source_event_ids: Tuple[str, ...]
    history_mutation_allowed: bool = False

    def validate(self) -> ProjectionState:
        required = (self.decision_id, self.observation_id, self.lesson_id)
        if any(not value.strip() for value in required):
            return ProjectionState.BLOCK
        if not self.source_event_ids or any(not value.strip() for value in self.source_event_ids):
            return ProjectionState.BLOCK
        if self.history_mutation_allowed:
            return ProjectionState.BLOCK
        return ProjectionState.PASS


def validate_event_record(event: EventRecord) -> ProjectionState:
    return event.validate()


def validate_decision_trace(trace: DecisionTrace) -> ProjectionState:
    return trace.validate()


def validate_command_center_projection(
    projection: CommandCenterProjection,
) -> ProjectionState:
    return projection.validate()


def validate_desktop_entry(contract: DesktopEntryContract) -> ProjectionState:
    return contract.validate()


def validate_supervisor_observation_link(
    link: SupervisorObservationLink,
) -> ProjectionState:
    return link.validate()


__all__ = [
    "CommandCenterProjection",
    "CommandCenterView",
    "DecisionTrace",
    "DesktopEntryContract",
    "EventRecord",
    "ProjectionState",
    "SupervisorObservationLink",
    "validate_command_center_projection",
    "validate_decision_trace",
    "validate_desktop_entry",
    "validate_event_record",
    "validate_supervisor_observation_link",
]
