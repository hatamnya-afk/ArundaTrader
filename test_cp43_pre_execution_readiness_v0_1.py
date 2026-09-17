from __future__ import annotations

import pytest

from pre_execution_readiness_v0_1 import certify_pre_execution_ready


def intent(**overrides):
    value = {
        "decision_state": "READY",
        "decision_validation": "VALID",
        "decision_reason": "validated signal",
        "asset": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_price": 95.0,
        "stop_distance": 5.0,
        "quantity": 2.0,
        "exposure": 200.0,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": "risk-v1",
        "provenance": "REAL_PRODUCTION",
        "observed_at": "2026-09-17T00:00:00+00:00",
    }
    value.update(overrides)
    return value


def test_valid_long_is_ready():
    result = certify_pre_execution_ready(intent())
    assert result["readiness_state"] == "PRE_EXECUTION_READY"
    assert result["readiness_validation"] == "VALID"
    assert result["asset"] == "BTCUSDT"
    assert result["quantity"] == 2.0


def test_valid_short_is_ready():
    result = certify_pre_execution_ready(intent(direction="SHORT", stop_price=105.0))
    assert result["direction"] == "SHORT"


@pytest.mark.parametrize("field", ["asset", "quantity", "exposure", "observed_at", "policy_version"])
def test_required_field_missing_fails_closed(field):
    value = intent()
    del value[field]
    with pytest.raises(ValueError, match="PRE_EXECUTION_REQUIRED_FIELD_MISSING"):
        certify_pre_execution_ready(value)


@pytest.mark.parametrize(
    "overrides,reason",
    [
        ({"decision_state": "HOLD"}, "PRE_EXECUTION_DECISION_INVALID"),
        ({"risk_state": "REJECTED"}, "PRE_EXECUTION_RISK_NOT_APPROVED"),
        ({"trade_gate_state": "REJECTED"}, "PRE_EXECUTION_GATE_NOT_APPROVED"),
        ({"provenance": "TEST"}, "PRE_EXECUTION_PROVENANCE_INVALID"),
        ({"direction": "SIDEWAYS"}, "PRE_EXECUTION_DIRECTION_INVALID"),
        ({"stop_distance": 4.0}, "PRE_EXECUTION_STOP_DISTANCE_INVALID"),
        ({"stop_price": 105.0}, "PRE_EXECUTION_STOP_DIRECTION_INVALID"),
        ({"quantity": 0}, "PRE_EXECUTION_QUANTITY_INVALID"),
        ({"exposure": float("nan")}, "PRE_EXECUTION_EXPOSURE_INVALID"),
    ],
)
def test_invalid_state_fails_closed(overrides, reason):
    with pytest.raises(ValueError, match=reason):
        certify_pre_execution_ready(intent(**overrides))


@pytest.mark.parametrize(
    "field",
    [
        "exchange", "api_request", "signature", "order_id", "submitted",
        "execution_authorization", "execution_enabled", "capital", "balance",
    ],
)
def test_execution_or_capital_surface_is_rejected(field):
    value = intent()
    value[field] = "FORBIDDEN"
    with pytest.raises(ValueError, match="PRE_EXECUTION_EXECUTION_SURFACE"):
        certify_pre_execution_ready(value)


def test_dynamic_asset_is_preserved():
    result = certify_pre_execution_ready(intent(asset="SOLUSDT"))
    assert result["asset"] == "SOLUSDT"


def test_result_contains_no_exchange_or_capital_surface():
    result = certify_pre_execution_ready(intent())
    assert not {"exchange", "api_request", "signature", "capital", "balance"}.intersection(result)
