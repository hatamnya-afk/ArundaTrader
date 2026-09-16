from __future__ import annotations

import pytest

from pre_execution_readiness_seal_v0_1 import seal_pre_execution_readiness


CERTIFIED = {
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


def test_certified_readiness_can_be_sealed():
    sealed = seal_pre_execution_readiness(CERTIFIED)
    assert sealed == CERTIFIED


def test_seal_rejects_non_certified_state():
    readiness = dict(CERTIFIED)
    readiness["readiness_state"] = "HOLD"
    with pytest.raises(ValueError, match="READINESS_BOUNDARY_SEAL_INVALID"):
        seal_pre_execution_readiness(readiness)


def test_seal_rejects_provider_coupling():
    readiness = dict(CERTIFIED)
    readiness["exchange"] = "TOOBIT"
    with pytest.raises(ValueError, match="READINESS_PROVIDER_COUPLING"):
        seal_pre_execution_readiness(readiness)


def test_seal_rejects_execution_surface():
    readiness = dict(CERTIFIED)
    readiness["order_id"] = "order-1"
    with pytest.raises(ValueError, match="READINESS_EXECUTION_SURFACE"):
        seal_pre_execution_readiness(readiness)


def test_seal_rejects_missing_certification_field():
    readiness = dict(CERTIFIED)
    readiness.pop("execution_validation")
    with pytest.raises(ValueError, match="READINESS_BOUNDARY_SEAL_INVALID"):
        seal_pre_execution_readiness(readiness)


def test_seal_rejects_invalid_validation():
    readiness = dict(CERTIFIED)
    readiness["capital_validation"] = "INVALID"
    with pytest.raises(ValueError, match="READINESS_BOUNDARY_SEAL_INVALID"):
        seal_pre_execution_readiness(readiness)


def test_seal_is_deterministic():
    assert seal_pre_execution_readiness(CERTIFIED) == seal_pre_execution_readiness(CERTIFIED)


def test_seal_preserves_canonical_field_order():
    sealed = seal_pre_execution_readiness(dict(reversed(list(CERTIFIED.items()))))
    assert list(sealed) == list(CERTIFIED)


def test_seal_does_not_add_execution_authorization():
    sealed = seal_pre_execution_readiness(CERTIFIED)
    assert "execution_authorization" not in sealed
    assert "execution_enabled" not in sealed
