from __future__ import annotations

import pytest

from pre_execution_readiness_handoff_v0_1 import handoff_pre_execution_readiness


READY = {
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


def test_valid_readiness_handoff_is_provider_neutral_and_complete():
    result = handoff_pre_execution_readiness(READY)
    assert result == READY


def test_non_ready_state_fails_closed():
    readiness = dict(READY)
    readiness["readiness_state"] = "HOLD"
    with pytest.raises(ValueError, match="READINESS_HANDOFF_INVALID"):
        handoff_pre_execution_readiness(readiness)


def test_invalid_readiness_validation_fails_closed():
    readiness = dict(READY)
    readiness["readiness_validation"] = "INVALID"
    with pytest.raises(ValueError, match="READINESS_HANDOFF_INVALID"):
        handoff_pre_execution_readiness(readiness)


def test_missing_required_validation_fails_closed():
    readiness = dict(READY)
    readiness.pop("liquidity_validation")
    with pytest.raises(ValueError, match="READINESS_HANDOFF_INVALID"):
        handoff_pre_execution_readiness(readiness)


def test_provider_coupling_fails_closed():
    readiness = dict(READY)
    readiness["exchange"] = "TOOBIT"
    with pytest.raises(ValueError, match="READINESS_PROVIDER_COUPLING"):
        handoff_pre_execution_readiness(readiness)


def test_execution_surface_fails_closed():
    readiness = dict(READY)
    readiness["order_id"] = "order-1"
    with pytest.raises(ValueError, match="READINESS_EXECUTION_SURFACE"):
        handoff_pre_execution_readiness(readiness)


def test_non_mapping_fails_closed():
    with pytest.raises(ValueError, match="READINESS_INPUT_INVALID"):
        handoff_pre_execution_readiness(None)


def test_handoff_is_deterministic():
    assert handoff_pre_execution_readiness(READY) == handoff_pre_execution_readiness(READY)
