from exchange_execution_contract import CanonicalOrderRequest
from execution_attempt_readiness_contract_v0_1 import evaluate_execution_attempt_readiness


def _request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=0.001,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100000.0,
        reference_price=100000.0,
        intent_id="INTENT-1",
        snapshot_id="SNAP-1",
        timestamp="2026-10-08T00:00:00Z",
        decision_id="DECISION-1",
    )


def _package():
    return {
        "package_state": "EXECUTION_READY_PACKAGE",
        "package_validation": "VALID",
        "execution_authorized": False,
        "execution_submitted": False,
        "provider_binding": "DEFERRED",
        "asset": "BTC",
        "direction": "LONG",
        "entry_price": 100000.0,
        "stop_price": 99000.0,
        "stop_distance": 1000.0,
        "quantity": 0.001,
        "exposure": 100.0,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": "POLICY-1",
        "provenance": "REAL_MARKET",
        "observed_at": "2026-10-08T00:00:00Z",
    }


def test_execution_attempt_readiness_is_ready_but_not_authorized():
    observation = evaluate_execution_attempt_readiness(
        execution_ready_package=_package(),
        request=_request(),
    )
    assert observation["readiness_state"] == "READY"
    assert observation["readiness_validation"] == "VALID"
    assert observation["execution_authorized"] is False
    assert observation["provider_binding"] == "DEFERRED"


def test_execution_attempt_readiness_rejects_mismatch():
    package = _package()
    package["quantity"] = 0.002

    try:
        evaluate_execution_attempt_readiness(
            execution_ready_package=package,
            request=_request(),
        )
    except ValueError as exc:
        assert str(exc) == "READINESS_REQUEST_QUANTITY_MISMATCH"
    else:
        raise AssertionError("mismatched quantity must fail closed")


def test_execution_attempt_readiness_rejects_pre_authorized_package():
    package = _package()
    package["execution_authorized"] = True

    try:
        evaluate_execution_attempt_readiness(
            execution_ready_package=package,
            request=_request(),
        )
    except ValueError as exc:
        assert str(exc) == "EXECUTION_AUTHORIZATION_MUST_REMAIN_EXPLICIT"
    else:
        raise AssertionError("pre-authorized package must fail closed")


def test_readiness_rejects_non_finite_exposure():
    import math
    import pytest

    for exposure in (math.nan, math.inf, -math.inf):
        package = _package()
        package["exposure"] = exposure
        with pytest.raises(ValueError, match="READINESS_EXPOSURE_INVALID"):
            evaluate_execution_attempt_readiness(
                execution_ready_package=package,
                request=_request(),
            )
