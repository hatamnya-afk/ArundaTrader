"""CP48 Command Center contract tests."""

from cp48_command_center_contract_v0_1 import (
    CommandCenterProjection,
    CommandCenterView,
    DecisionTrace,
    DesktopEntryContract,
    EventRecord,
    ProjectionState,
    SupervisorObservationLink,
    validate_command_center_projection,
    validate_decision_trace,
    validate_desktop_entry,
    validate_event_record,
    validate_supervisor_observation_link,
)


def event(event_id="E1", decision_id="D1", **kwargs):
    values = dict(
        event_id=event_id,
        decision_id=decision_id,
        stage="DECISION",
        occurred_at_ms=2000,
        knowledge_cutoff_ms=2000,
        parent_event_ids=(),
        state=ProjectionState.PASS,
    )
    values.update(kwargs)
    return EventRecord(**values)


def trace():
    return DecisionTrace("D1", ("E1",), frozenset({"S1"}), "S1")


def projection(**kwargs):
    values = dict(
        decision_trace=trace(),
        view=CommandCenterView.LIVE_ACTIVITY,
        generated_at_ms=3000,
        events=(event(),),
    )
    values.update(kwargs)
    return CommandCenterProjection(**values)


def test_event_requires_decision_and_time_provenance():
    assert validate_event_record(event(occurred_at_ms=0)) == ProjectionState.BLOCK


def test_event_rejects_future_knowledge():
    assert validate_event_record(event(knowledge_cutoff_ms=2001)) == ProjectionState.BLOCK


def test_decision_trace_requires_events_and_sources():
    assert validate_decision_trace(trace()) == ProjectionState.PASS
    assert validate_decision_trace(DecisionTrace("D1", (), frozenset({"S1"}), "S1")) == ProjectionState.BLOCK


def test_projection_is_read_only():
    assert validate_command_center_projection(projection()) == ProjectionState.PASS
    assert validate_command_center_projection(
        projection(execution_controls_writable=True)
    ) == ProjectionState.BLOCK


def test_projection_rejects_cross_decision_events():
    assert validate_command_center_projection(
        projection(events=(event(decision_id="D2"),))
    ) == ProjectionState.BLOCK


def test_desktop_entry_is_terminal_free():
    contract = DesktopEntryContract("aroonda.command.center", "Aroonda", "command_center")
    assert validate_desktop_entry(contract) == ProjectionState.PASS


def test_desktop_entry_blocks_terminal_dependency():
    contract = DesktopEntryContract(
        "aroonda.command.center",
        "Aroonda",
        "command_center",
        requires_terminal=True,
    )
    assert validate_desktop_entry(contract) == ProjectionState.BLOCK


def test_supervisor_link_preserves_history():
    link = SupervisorObservationLink("D1", "O1", "L1", ("E1",))
    assert validate_supervisor_observation_link(link) == ProjectionState.PASS


def test_supervisor_link_blocks_history_mutation():
    link = SupervisorObservationLink("D1", "O1", "L1", ("E1",), True)
    assert validate_supervisor_observation_link(link) == ProjectionState.BLOCK
