from cp49_first_execution_contract_v0_1 import (
    AttemptState, ExecutionSafetyGate, FirstExecutionAttempt, OrderIntentBoundary,
)
from cp49_observation_envelope_v0_1 import ObservationEnvelope


def test_gate_closed_until_explicit_authorization():
    gate = ExecutionSafetyGate(True, True, False, False, False, False, False)
    assert gate.validate() is AttemptState.BLOCKED


def test_gate_requires_all_write_flags():
    gate = ExecutionSafetyGate(True, True, False, True, True, False, False)
    assert gate.validate() is AttemptState.BLOCKED


def test_gate_ready_only_for_one_authorized_attempt():
    gate = ExecutionSafetyGate(True, True, False, True, True, True, False)
    assert gate.validate() is AttemptState.READY


def test_prior_attempt_and_retry_are_blocked():
    assert ExecutionSafetyGate(True, True, True, True, True, True, False).validate() is AttemptState.BLOCKED
    assert ExecutionSafetyGate(True, True, False, True, True, True, True).validate() is AttemptState.BLOCKED


def test_order_intent_requires_explicit_quantity_provenance():
    intent = OrderIntentBoundary("D1", "I1", "BTC/USDT", "LONG", 1.0, "dynamic_risk", "TOOBIT")
    assert intent.validate() is AttemptState.READY
    assert OrderIntentBoundary("D1", "I1", "BTC/USDT", "LONG", 1.0, "", "TOOBIT").validate() is AttemptState.BLOCKED


def test_invalid_intent_fails_closed():
    assert OrderIntentBoundary("D1", "I1", "BTC/USDT", "BUY", 1.0, "x", "TOOBIT").validate() is AttemptState.BLOCKED
    assert OrderIntentBoundary("D1", "I1", "BTC/USDT", "LONG", 0.0, "x", "TOOBIT").validate() is AttemptState.BLOCKED


def test_attempt_preserves_open_outcomes():
    for state in (AttemptState.ACCEPTED, AttemptState.REJECTED, AttemptState.BLOCKED, AttemptState.INCONCLUSIVE):
        attempt = FirstExecutionAttempt("A1", "D1", "I1", 100, state, latency_ms=12)
        assert attempt.validate() is state


def test_attempt_temporal_and_identity_validation():
    assert FirstExecutionAttempt("", "D1", "I1", 100, AttemptState.REJECTED).validate() is AttemptState.BLOCKED
    assert FirstExecutionAttempt("A1", "D1", "I1", 100, AttemptState.REJECTED, latency_ms=-1).validate() is AttemptState.BLOCKED


def test_observation_separates_decision_and_attempt_time():
    env = ObservationEnvelope(
        "D1", "S1", "A1", 1000, 900, 1100, "BTC/USDT", "TOOBIT",
        "I1", "REQ1", "REJECTED", AttemptState.REJECTED, 35,
        rejection_code="INSUFFICIENT_BALANCE",
    )
    assert env.validate() is AttemptState.REJECTED


def test_observation_rejects_future_knowledge_cutoff():
    env = ObservationEnvelope(
        "D1", "S1", "A1", 1000, 1001, 1100, "BTC/USDT", "TOOBIT",
        "I1", "REQ1", "REJECTED", AttemptState.REJECTED, 35,
    )
    assert env.validate() is AttemptState.BLOCKED


def test_observation_rejects_secret_like_metadata():
    env = ObservationEnvelope(
        "D1", "S1", "A1", 1000, 900, 1100, "BTC/USDT", "TOOBIT",
        "I1", "REQ1", "REJECTED", AttemptState.REJECTED, 35,
        non_secret_metadata=(("api_key", "SECRET"),),
    )
    assert env.validate() is AttemptState.BLOCKED


def test_observation_requires_decision_time_not_future_time():
    env = ObservationEnvelope(
        "D1", "S1", "A1", 1000, 900, 999, "BTC/USDT", "TOOBIT",
        "I1", "REQ1", "BLOCKED", AttemptState.BLOCKED, 0,
    )
    assert env.validate() is AttemptState.BLOCKED
