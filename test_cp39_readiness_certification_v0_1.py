from __future__ import annotations

import pytest

from pre_execution_readiness_certification_v0_1 import certify_pre_execution_readiness


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


def test_valid_integrity_state_can_be_certified():
    assert certify_pre_execution_readiness(READY) == READY


def test_certification_rejects_non_ready_state():
    readiness = dict(READY)
    readiness["readiness_state"] = "HOLD"
    with pytest.raises(ValueError, match="READINESS_CERTIFICATION_INVALID"):
        certify_pre_execution_readiness(readiness)


def test_certification_rejects_invalid_readiness_validation():
    readiness = dict(READY)
    readiness["readiness_validation"] = "INVALID"
    with pytest.raises(ValueError, match="READINESS_CERTIFICATION_INVALID"):
        certify_pre_execution_readiness(readiness)


def test_certification_requires_all_validations():
    readiness = dict(READY)
    readiness["liquidity_validation"] = "INVALID"
    with pytest.raises(ValueError, match="READINESS_CERTIFICATION_INVALID"):
        certify_pre_execution_readiness(readiness)


def test_certification_rejects_provider_coupling():
    readiness = dict(READY)
    readiness["exchange"] = "TOOBIT"
    with pytest.raises(ValueError, match="READINESS_PROVIDER_COUPLING"):
        certify_pre_execution_readiness(readiness)


def test_certification_rejects_execution_surface():
    readiness = dict(READY)
    readiness["order_id"] = "order-1"
    with pytest.raises(ValueError, match="READINESS_EXECUTION_SURFACE"):
        certify_pre_execution_readiness(readiness)


def test_certification_rejects_missing_integrity_field():
    readiness = dict(READY)
    readiness.pop("provenance")
    with pytest.raises(ValueError, match="READINESS_CERTIFICATION_INVALID"):
        certify_pre_execution_readiness(readiness)


def test_certification_is_deterministic():
    assert certify_pre_execution_readiness(READY) == certify_pre_execution_readiness(READY)
