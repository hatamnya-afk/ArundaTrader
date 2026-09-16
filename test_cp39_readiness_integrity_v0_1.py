from __future__ import annotations

import pytest

from pre_execution_readiness_integrity_v0_1 import validate_readiness_integrity


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


def test_valid_readiness_integrity_is_accepted():
    assert validate_readiness_integrity(READY) == READY


def test_missing_field_fails_closed():
    readiness = dict(READY)
    readiness.pop("asset")
    with pytest.raises(ValueError, match="READINESS_INTEGRITY_INVALID"):
        validate_readiness_integrity(readiness)


def test_invalid_validation_fails_closed():
    readiness = dict(READY)
    readiness["execution_validation"] = "INVALID"
    with pytest.raises(ValueError, match="READINESS_INTEGRITY_INVALID"):
        validate_readiness_integrity(readiness)


def test_provider_field_fails_closed():
    readiness = dict(READY)
    readiness["exchange"] = "TOOBIT"
    with pytest.raises(ValueError, match="READINESS_PROVIDER_COUPLING"):
        validate_readiness_integrity(readiness)


def test_execution_surface_fails_closed():
    readiness = dict(READY)
    readiness["order_id"] = "order-1"
    with pytest.raises(ValueError, match="READINESS_EXECUTION_SURFACE"):
        validate_readiness_integrity(readiness)


def test_extra_non_execution_field_fails_closed():
    readiness = dict(READY)
    readiness["unexpected"] = "value"
    with pytest.raises(ValueError, match="READINESS_INTEGRITY_INVALID"):
        validate_readiness_integrity(readiness)


def test_non_mapping_fails_closed():
    with pytest.raises(ValueError, match="READINESS_INPUT_INVALID"):
        validate_readiness_integrity(None)


def test_integrity_is_deterministic():
    assert validate_readiness_integrity(READY) == validate_readiness_integrity(READY)
