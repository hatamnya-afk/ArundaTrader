import pytest

from decision_trade_intent_boundary_v0_1 import build_validated_trade_intent
from pre_execution_readiness_v0_1 import build_pre_execution_readiness


def make_trade_intent(
    *,
    asset="BTCUSDT",
    direction="LONG",
    entry_price=100.0,
    stop_price=95.0,
    stop_distance=5.0,
    quantity=2.0,
    exposure=200.0,
    provenance="REAL",
):
    decision = {
        "decision_state": "READY",
        "decision_validation": "VALID",
        "decision_reason": "VALIDATED",
        "asset": asset,
        "provenance": provenance,
        "observed_at": "2026-09-17T00:00:00+00:00",
    }

    gate = {
        "trade_gate_state": "APPROVED",
        "asset": asset,
        "direction": direction,
        "entry_price": entry_price,
        "stop_distance": stop_distance,
        "quantity": quantity,
        "exposure": exposure,
        "policy_version": "RISK_POLICY_V0_1",
    }

    sizing = {
        "risk_state": "APPROVED",
        "asset": asset,
        "direction": direction,
        "entry_price": entry_price,
        "stop_distance": stop_distance,
        "position_size": quantity,
        "exposure": exposure,
        "policy_version": "RISK_POLICY_V0_1",
    }

    stop_risk = {
        "observation_state": "AVAILABLE",
        "observation_validation": "VALID",
        "risk_policy_validation": "VALID",
        "asset": asset,
        "direction": direction,
        "entry_price": entry_price,
        "stop_price": stop_price,
        "stop_distance": stop_distance,
        "risk_policy_version": "RISK_POLICY_V0_1",
        "provenance": provenance,
    }

    return build_validated_trade_intent(
        decision,
        gate,
        sizing,
        stop_risk,
    )


def test_valid_long_trade_intent_builds_readiness_certificate():
    trade_intent = make_trade_intent()

    result = build_pre_execution_readiness(trade_intent)

    assert result["readiness_state"] == "PRE_EXECUTION_READY"
    assert result["readiness_validation"] == "VALID"
    assert result["asset"] == "BTCUSDT"
    assert result["direction"] == "LONG"
    assert result["quantity"] == 2.0
    assert result["exposure"] == 200.0
    assert result["provenance"] == "REAL"


def test_valid_short_trade_intent_builds_readiness_certificate():
    trade_intent = make_trade_intent(
        asset="ETHUSDT",
        direction="SHORT",
        entry_price=100.0,
        stop_price=105.0,
        stop_distance=5.0,
    )

    result = build_pre_execution_readiness(trade_intent)

    assert result["readiness_state"] == "PRE_EXECUTION_READY"
    assert result["readiness_validation"] == "VALID"
    assert result["asset"] == "ETHUSDT"
    assert result["direction"] == "SHORT"


def test_asset_is_dynamic():
    trade_intent = make_trade_intent(asset="SOLUSDT")

    result = build_pre_execution_readiness(trade_intent)

    assert result["asset"] == "SOLUSDT"


@pytest.mark.parametrize("field", [
    "asset",
    "direction",
    "entry_price",
    "stop_price",
    "stop_distance",
    "quantity",
    "exposure",
    "provenance",
    "policy_version",
])
def test_missing_required_field_is_rejected(field):
    trade_intent = make_trade_intent()
    trade_intent.pop(field)

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)


def test_invalid_decision_state_is_rejected():
    trade_intent = make_trade_intent()
    trade_intent["decision_state"] = "HOLD"

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)


def test_invalid_decision_validation_is_rejected():
    trade_intent = make_trade_intent()
    trade_intent["decision_validation"] = "INVALID"

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)


def test_invalid_risk_state_is_rejected():
    trade_intent = make_trade_intent()
    trade_intent["risk_state"] = "REJECTED"

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)


def test_invalid_trade_gate_state_is_rejected():
    trade_intent = make_trade_intent()
    trade_intent["trade_gate_state"] = "REJECTED"

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)


@pytest.mark.parametrize("provenance", ["TEST", "LEGACY", "SIMULATED"])
def test_forbidden_provenance_is_rejected(provenance):
    trade_intent = make_trade_intent()
    trade_intent["provenance"] = provenance

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)


def test_long_with_wrong_stop_direction_is_rejected():
    trade_intent = make_trade_intent()
    trade_intent["stop_price"] = 105.0
    trade_intent["stop_distance"] = 5.0

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)


def test_short_with_wrong_stop_direction_is_rejected():
    trade_intent = make_trade_intent(
        direction="SHORT",
        entry_price=100.0,
        stop_price=105.0,
        stop_distance=5.0,
    )
    trade_intent["stop_price"] = 95.0
    trade_intent["stop_distance"] = 5.0

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)

def test_short_with_wrong_stop_direction_is_rejected():
    trade_intent = make_trade_intent(
        direction="SHORT",
        entry_price=100.0,
        stop_price=105.0,
        stop_distance=5.0,
    )
    trade_intent["stop_price"] = 95.0
    trade_intent["stop_distance"] = 5.0

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)

@pytest.mark.parametrize("field,value", [
    ("quantity", 0),
    ("quantity", -1),
    ("exposure", 0),
    ("exposure", -1),
    ("entry_price", 0),
    ("stop_price", 0),
    ("stop_distance", 0),
])
def test_invalid_numeric_values_are_rejected(field, value):
    trade_intent = make_trade_intent()
    trade_intent[field] = value

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)


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
    trade_intent = make_trade_intent()
    trade_intent[field] = "FORBIDDEN"

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)


@pytest.mark.parametrize("field", [
    "account",
    "account_id",
    "balance",
    "available_balance",
    "capital",
    "wallet",
])
def test_account_balance_capital_surface_is_rejected(field):
    trade_intent = make_trade_intent()
    trade_intent[field] = 1000

    with pytest.raises(ValueError):
        build_pre_execution_readiness(trade_intent)


def test_quantity_is_consumed_not_calculated():
    trade_intent = make_trade_intent(quantity=7.25)

    result = build_pre_execution_readiness(trade_intent)

    assert result["quantity"] == 7.25


def test_exposure_is_consumed_not_calculated():
    trade_intent = make_trade_intent(exposure=913.75)

    result = build_pre_execution_readiness(trade_intent)

    assert result["exposure"] == 913.75


def test_readiness_does_not_require_exchange_binding():
    trade_intent = make_trade_intent()

    result = build_pre_execution_readiness(trade_intent)

    assert result["provider_binding"] == "DEFERRED"