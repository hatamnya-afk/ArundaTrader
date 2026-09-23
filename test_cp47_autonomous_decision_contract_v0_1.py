"""CP47 focused contract tests."""

from cp47_autonomous_decision_contract_v0_1 import (
    AnalysisOnlyOpportunity,
    AroondaObservation,
    AutonomousDecision,
    CommandCenterEvent,
    DecisionSnapshot,
    DecisionStage,
    FirstAttemptAuthorization,
    ResultState,
    validate_analysis_only_opportunity,
    validate_aroonda_observation,
    validate_autonomous_decision,
    validate_command_center_event,
    validate_first_attempt_authorization,
)


def snapshot() -> DecisionSnapshot:
    return DecisionSnapshot("S1", 1000, 1000, frozenset({"M1"}))


def decision(direction: str = "LONG", **kwargs) -> AutonomousDecision:
    values = dict(
        decision_id="D1",
        snapshot=snapshot(),
        opportunity_id="O1",
        signal_id="SG1",
        asset="ABC/USDT",
        direction=direction,
        entry_price=100.0,
        invalidation_price=99.0,
        allocation_fraction=0.25,
        position_size=2.0,
        venue="Toobit",
        intent_id="I1",
    )
    values.update(kwargs)
    return AutonomousDecision(**values)


def test_snapshot_rejects_future_knowledge_cutoff():
    assert DecisionSnapshot("S1", 1000, 1001, frozenset({"M1"})).validate() == ResultState.BLOCK


def test_decision_passes_without_manual_thesis():
    assert validate_autonomous_decision(decision()) == ResultState.PASS


def test_decision_blocks_manual_thesis():
    assert validate_autonomous_decision(decision(manually_injected_thesis=True)) == ResultState.BLOCK


def test_long_invalidation_must_be_below_entry():
    assert validate_autonomous_decision(decision(invalidation_price=100.0)) == ResultState.BLOCK


def test_short_invalidation_must_be_above_entry():
    assert validate_autonomous_decision(decision("SHORT", invalidation_price=100.0)) == ResultState.BLOCK


def test_allocation_is_bounded():
    assert validate_autonomous_decision(decision(allocation_fraction=1.1)) == ResultState.BLOCK


def test_analysis_only_requires_unavailable_execution_venue():
    item = AnalysisOnlyOpportunity("D1", "S1", "ABC/USDT", 2000, False)
    assert validate_analysis_only_opportunity(item) == ResultState.PASS


def test_analysis_only_cannot_claim_realized_execution():
    item = AnalysisOnlyOpportunity("D1", "S1", "ABC/USDT", 2000, False, True)
    assert validate_analysis_only_opportunity(item) == ResultState.BLOCK


def test_command_event_preserves_time_order():
    event = CommandCenterEvent("E1", "D1", DecisionStage.DECISION, 2000, 2000)
    assert validate_command_center_event(event) == ResultState.PASS


def test_command_event_blocks_future_knowledge():
    event = CommandCenterEvent("E1", "D1", DecisionStage.DECISION, 2000, 2001)
    assert validate_command_center_event(event) == ResultState.BLOCK


def test_first_attempt_requires_all_execution_flags():
    auth = FirstAttemptAuthorization(True, True, False, True, True, True, False, False)
    assert validate_first_attempt_authorization(auth) == ResultState.PASS


def test_first_attempt_blocks_without_management_authorization():
    auth = FirstAttemptAuthorization(False, True, False, True, True, True, False, False)
    assert validate_first_attempt_authorization(auth) == ResultState.BLOCK


def test_first_attempt_blocks_retry():
    auth = FirstAttemptAuthorization(True, True, False, True, True, True, False, True)
    assert validate_first_attempt_authorization(auth) == ResultState.BLOCK


def test_first_attempt_blocks_prior_attempt():
    auth = FirstAttemptAuthorization(True, True, True, True, True, True, False, False)
    assert validate_first_attempt_authorization(auth) == ResultState.BLOCK


def test_aroonda_observation_separates_outcome_time():
    observation = AroondaObservation("D1", 1000, 2000, ResultState.BLOCK, "observe", "insufficient evidence")
    assert validate_aroonda_observation(observation) == ResultState.PASS


def test_aroonda_observation_cannot_rewrite_history():
    observation = AroondaObservation("D1", 1000, 2000, ResultState.PASS, "rewrite", "none", True)
    assert validate_aroonda_observation(observation) == ResultState.BLOCK
