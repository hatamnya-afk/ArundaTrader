from __future__ import annotations

import pytest

from readiness_to_decision_handoff_v0_1 import handoff_readiness_to_decision


SEALED_READINESS = {
    "readiness_state": "READY",
    "readiness_validation": "VALID",
    "readiness_source": "REAL_PRODUCTION_READINESS",
    "provenance": "REAL_PRODUCTION_OBSERVATION",
    "asset": "BTCUSDT",
    "capital_validation": "VALID",
    "portfolio_validation": "VALID",
    "stop_risk_policy_validation": "VALID",
    "liquidity_validation": "VALID",
    "execution_validation": "VALID",
    "observed_at": "2026-09-17T00:00:00+00:00",
}


def test_sealed_readiness_can_be_handed_to_decision():
    handed_off = handoff_readiness_to_decision(SEALED_READINESS)
    assert handed_off == {
        **SEALED_READINESS,
        "decision_input_state": "READY",
        "decision_input_validation": "VALID",
    }


def test_decision_handoff_rejects_non_ready_readiness():
    readiness = dict(SEALED_READINESS)
    readiness["readiness_state"] = "HOLD"
    with pytest.raises(ValueError, match="READINESS_TO_DECISION_HANDOFF_INVALID"):
        handoff_readiness_to_decision(readiness)


def test_decision_handoff_rejects_invalid_readiness_validation():
    readiness = dict(SEALED_READINESS)
    readiness["readiness_validation"] = "INVALID"
    with pytest.raises(ValueError, match="READINESS_TO_DECISION_HANDOFF_INVALID"):
        handoff_readiness_to_decision(readiness)


def test_decision_handoff_rejects_provider_coupling():
    readiness = dict(SEALED_READINESS)
    readiness["exchange"] = "TOOBIT"
    with pytest.raises(ValueError, match="READINESS_PROVIDER_COUPLING"):
        handoff_readiness_to_decision(readiness)


def test_decision_handoff_rejects_execution_surface():
    readiness = dict(SEALED_READINESS)
    readiness["order_id"] = "order-1"
    with pytest.raises(ValueError, match="READINESS_EXECUTION_SURFACE"):
        handoff_readiness_to_decision(readiness)


def test_decision_handoff_rejects_missing_readiness_field():
    readiness = dict(SEALED_READINESS)
    readiness.pop("liquidity_validation")
    with pytest.raises(ValueError, match="READINESS_TO_DECISION_HANDOFF_INVALID"):
        handoff_readiness_to_decision(readiness)


def test_decision_handoff_rejects_invalid_component_validation():
    readiness = dict(SEALED_READINESS)
    readiness["execution_validation"] = "INVALID"
    with pytest.raises(ValueError, match="READINESS_TO_DECISION_HANDOFF_INVALID"):
        handoff_readiness_to_decision(readiness)


def test_decision_handoff_is_deterministic():
    assert handoff_readiness_to_decision(SEALED_READINESS) == handoff_readiness_to_decision(
        SEALED_READINESS
    )


def test_decision_handoff_preserves_readiness_fields():
    handed_off = handoff_readiness_to_decision(SEALED_READINESS)
    assert list(handed_off) == list(SEALED_READINESS) + [
        "decision_input_state",
        "decision_input_validation",
    ]


def test_decision_handoff_adds_no_execution_authorization():
    handed_off = handoff_readiness_to_decision(SEALED_READINESS)
    assert "execution_authorization" not in handed_off
    assert "execution_enabled" not in handed_off
    assert "order_id" not in handed_off
