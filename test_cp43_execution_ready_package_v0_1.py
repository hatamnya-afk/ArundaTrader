from __future__ import annotations

import pytest

from execution_ready_package_v0_1 import build_execution_ready_package
from pre_execution_readiness_v0_1 import certify_pre_execution_ready


def certificate():
    return certify_pre_execution_ready({
        "decision_state": "READY", "decision_validation": "VALID",
        "decision_reason": "validated", "asset": "ETHUSDT", "direction": "SHORT",
        "entry_price": 200.0, "stop_price": 210.0, "stop_distance": 10.0,
        "quantity": 1.5, "exposure": 300.0, "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED", "policy_version": "risk-v1",
        "provenance": "REAL_PRODUCTION", "observed_at": "2026-09-17T00:00:00+00:00",
    })


def test_valid_certificate_packages():
    result = build_execution_ready_package(certificate())
    assert result["package_state"] == "EXECUTION_READY_PACKAGE"
    assert result["package_validation"] == "VALID"
    assert result["execution_authorized"] is False
    assert result["execution_submitted"] is False
    assert result["provider_binding"] == "DEFERRED"
    assert result["payload"]["asset"] == "ETHUSDT"


def test_package_is_provider_neutral_and_portable():
    result = build_execution_ready_package(certificate())
    assert "exchange" not in result
    assert "api_request" not in result
    assert "signature" not in result
    assert "capital" not in result
    assert "balance" not in result


@pytest.mark.parametrize("field", ["exchange", "api_request", "signature", "capital", "balance", "order_id"])
def test_forbidden_surface_fails_closed(field):
    value = certificate()
    value[field] = "FORBIDDEN"
    with pytest.raises(ValueError, match="EXECUTION_PACKAGE_FORBIDDEN_SURFACE"):
        build_execution_ready_package(value)


def test_invalid_certificate_cannot_be_packaged():
    value = certificate()
    value["readiness_state"] = "NOT_READY"
    with pytest.raises(ValueError, match="EXECUTION_PACKAGE_NOT_READY"):
        build_execution_ready_package(value)
