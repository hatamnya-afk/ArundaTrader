import pytest

from execution_ready_package_v0_1 import build_execution_ready_package


def valid_certificate():
    return {
        "readiness_state": "PRE_EXECUTION_READY",
        "readiness_validation": "VALID",
        "asset": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_price": 95.0,
        "stop_distance": 5.0,
        "quantity": 2.0,
        "exposure": 200.0,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": "RISK_POLICY_V0_1",
        "provenance": "REAL",
        "observed_at": "2026-09-17T00:00:00+00:00",
        "provider_binding": "DEFERRED",
    }


def test_valid_certificate_builds_execution_ready_package():
    result = build_execution_ready_package(valid_certificate())

    assert result["package_state"] == "EXECUTION_READY_PACKAGE"
    assert result["package_validation"] == "VALID"


def test_package_is_not_execution_authorized():
    result = build_execution_ready_package(valid_certificate())

    assert result["execution_authorized"] is False
    assert result["execution_submitted"] is False


def test_provider_binding_is_deferred():
    result = build_execution_ready_package(valid_certificate())

    assert result["provider_binding"] == "DEFERRED"


def test_invalid_certificate_is_rejected():
    certificate = valid_certificate()
    certificate["readiness_validation"] = "INVALID"

    with pytest.raises(ValueError):
        build_execution_ready_package(certificate)


def test_invalid_readiness_state_is_rejected():
    certificate = valid_certificate()
    certificate["readiness_state"] = "NOT_READY"

    with pytest.raises(ValueError):
        build_execution_ready_package(certificate)


def test_missing_required_certificate_field_is_rejected():
    certificate = valid_certificate()
    certificate.pop("asset")

    with pytest.raises(ValueError):
        build_execution_ready_package(certificate)


@pytest.mark.parametrize("field", [
    "order_id",
    "order_intent",
    "exchange",
    "exchange_client",
    "api_request",
    "signature",
    "submitted",
    "trade_id",
    "withdrawal",
    "order_write",
    "execution_authorization",
    "execution_enabled",
])
def test_execution_surface_is_rejected(field):
    certificate = valid_certificate()
    certificate[field] = "FORBIDDEN"

    with pytest.raises(ValueError):
        build_execution_ready_package(certificate)


@pytest.mark.parametrize("field", [
    "account",
    "account_id",
    "balance",
    "available_balance",
    "capital",
    "wallet",
])
def test_account_balance_capital_surface_is_rejected(field):
    certificate = valid_certificate()
    certificate[field] = 1000

    with pytest.raises(ValueError):
        build_execution_ready_package(certificate)


def test_package_preserves_dynamic_asset():
    certificate = valid_certificate()
    certificate["asset"] = "SOLUSDT"

    result = build_execution_ready_package(certificate)

    assert result["asset"] == "SOLUSDT"


def test_package_preserves_trade_intent_values():
    certificate = valid_certificate()

    result = build_execution_ready_package(certificate)

    assert result["direction"] == "LONG"
    assert result["entry_price"] == 100.0
    assert result["stop_price"] == 95.0
    assert result["quantity"] == 2.0
    assert result["exposure"] == 200.0


def test_package_has_no_exchange_dependency():
    certificate = valid_certificate()

    result = build_execution_ready_package(certificate)

    assert result["provider_binding"] == "DEFERRED"
    assert "exchange" not in result
    assert "exchange_client" not in result


def test_package_does_not_authorize_execution():
    result = build_execution_ready_package(valid_certificate())

    assert result["execution_authorized"] is False
    assert result["execution_submitted"] is False