import pytest

from decision_trade_intent_boundary_v0_1 import build_validated_trade_intent


def valid_sources():
    decision = {
        "decision_state": "READY",
        "decision_validation": "VALID",
        "decision_reason": "SEALED_INPUT_VALID",
        "asset": "BTCUSDT",
        "provenance": "REAL_PRODUCTION",
        "observed_at": "2026-09-16T23:40:00+00:00",
    }
    gate = {
        "trade_gate_state": "APPROVED",
        "asset": "BTCUSDT",
        "direction": "LONG",
        "quantity": 0.01,
        "entry_price": 100000.0,
        "stop_distance": 1000.0,
        "exposure": 1000.0,
        "risk_state": "APPROVED",
        "policy_version": "RISK-0.1",
    }
    sizing = {
        "asset": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 100000.0,
        "stop_distance": 1000.0,
        "position_size": 0.01,
        "exposure": 1000.0,
        "risk_state": "APPROVED",
        "policy_version": "RISK-0.1",
    }
    stop_risk = {
        "observation_state": "AVAILABLE",
        "observation_validation": "VALID",
        "observation_source": "REAL_RISK_SOURCE",
        "provenance": "REAL_PRODUCTION",
        "asset": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 100000.0,
        "stop_price": 99000.0,
        "stop_distance": 1000.0,
        "risk_policy_version": "RISK-0.1",
        "risk_policy_validation": "VALID",
    }
    return decision, gate, sizing, stop_risk


def test_decision_to_trade_intent_passes():
    result = build_validated_trade_intent(*valid_sources())
    assert result["decision_state"] == "READY"
    assert result["decision_validation"] == "VALID"
    assert result["asset"] == "BTCUSDT"
    assert result["direction"] == "LONG"
    assert result["entry_price"] == 100000.0
    assert result["stop_price"] == 99000.0
    assert result["quantity"] == 0.01
    assert result["exposure"] == 1000.0
    assert result["risk_state"] == "APPROVED"
    assert result["trade_gate_state"] == "APPROVED"
    assert result["provenance"] == "REAL_PRODUCTION"


def test_decision_not_ready_fails_closed():
    sources = list(valid_sources())
    sources[0] = dict(sources[0], decision_state="BLOCKED")
    with pytest.raises(ValueError, match="DECISION_NOT_READY"):
        build_validated_trade_intent(*sources)


def test_decision_invalid_fails_closed():
    sources = list(valid_sources())
    sources[0] = dict(sources[0], decision_validation="INVALID")
    with pytest.raises(ValueError, match="DECISION_INVALID"):
        build_validated_trade_intent(*sources)


def test_dynamic_asset_passes_without_fixed_universe():
    sources = list(valid_sources())
    for source in sources:
        source["asset"] = "ARBITRARY-ASSET-42"
    result = build_validated_trade_intent(*sources)
    assert result["asset"] == "ARBITRARY-ASSET-42"


def test_provider_neutrality_rejects_exchange_field():
    sources = list(valid_sources())
    sources[1] = dict(sources[1], exchange="TOOBIT")
    with pytest.raises(ValueError, match="TRADE_INTENT_EXECUTION_SURFACE"):
        build_validated_trade_intent(*sources)


def test_test_provenance_fails_closed():
    sources = list(valid_sources())
    sources[0] = dict(sources[0], provenance="TEST")
    with pytest.raises(ValueError, match="PROVENANCE_INVALID"):
        build_validated_trade_intent(*sources)


def test_provenance_mismatch_fails_closed():
    sources = list(valid_sources())
    sources[3] = dict(sources[3], provenance="REAL_OTHER")
    with pytest.raises(ValueError, match="PROVENANCE_MISMATCH"):
        build_validated_trade_intent(*sources)


def test_quantity_mismatch_fails_closed():
    sources = list(valid_sources())
    sources[2] = dict(sources[2], position_size=0.02)
    with pytest.raises(ValueError, match="QUANTITY_MISMATCH"):
        build_validated_trade_intent(*sources)


def test_stop_price_is_never_invented():
    sources = list(valid_sources())
    del sources[3]["stop_price"]
    with pytest.raises(ValueError, match="STOP_PRICE_INVALID"):
        build_validated_trade_intent(*sources)


def test_policy_mismatch_fails_closed():
    sources = list(valid_sources())
    sources[2] = dict(sources[2], policy_version="RISK-OTHER")
    with pytest.raises(ValueError, match="POLICY_VERSION_MISMATCH"):
        build_validated_trade_intent(*sources)


def test_no_order_or_execution_fields_are_created():
    result = build_validated_trade_intent(*valid_sources())
    forbidden = {
        "order_id",
        "order_intent",
        "exchange",
        "api_request",
        "signature",
        "submitted",
        "execution_authorization",
    }
    assert forbidden.isdisjoint(result)


def test_no_capital_or_fixed_15_is_created():
    result = build_validated_trade_intent(*valid_sources())
    assert "capital" not in result
    assert "portfolio_capital" not in result
    assert "usable_capital" not in result
    assert all("15" not in str(value) for value in result.values())
