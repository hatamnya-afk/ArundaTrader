import pytest

from exchange_execution_contract import CanonicalOrderRequest
from production_final_execution_context_v0_1 import build_production_final_attempt_context


def _request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=0.1,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100.0,
        reference_price=100.0,
        intent_id="OI-snapshot-BTC",
        snapshot_id="snapshot",
        timestamp="2026-10-11T10:00:00+00:00",
        decision_id="decision",
    )


def _readiness():
    return {
        "readiness_state": "PRE_EXECUTION_READY",
        "readiness_validation": "VALID",
        "provider_binding": "DEFERRED",
        "asset": "BTC",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_price": 95.0,
        "stop_distance": 5.0,
        "quantity": 0.1,
        "exposure": 10.0,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": "risk-policy-v1",
        "provenance": "REAL_MARKET_CURRENT_RUN",
        "observed_at": "2026-10-11T10:00:00+00:00",
    }


class _Adapter:
    adapter_name = "TOOBIT"


def test_builds_context_from_explicit_authoritative_inputs_without_provider_calls():
    result = build_production_final_attempt_context(
        request=_request(),
        pre_execution_readiness=_readiness(),
        management_observation={"decision": "AUTHORIZED"},
        adapter=_Adapter(),
        venue="FUTURES",
    )
    assert result["execution_ready_package"]["package_state"] == "EXECUTION_READY_PACKAGE"
    assert result["execution_ready_package"]["execution_authorized"] is False
    assert result["execution_instrument"].venue == "FUTURES"
    assert result["execution_instrument"].settlement_asset == "USDT"
    assert result["execution_instrument"].instrument_type == "PERPETUAL"
    assert result["venue"] == "FUTURES"


def test_missing_stop_or_other_readiness_evidence_fails_closed_without_inference():
    readiness = _readiness()
    del readiness["stop_price"]
    with pytest.raises(ValueError, match="missing required field"):
        build_production_final_attempt_context(
            request=_request(),
            pre_execution_readiness=readiness,
            management_observation={"decision": "AUTHORIZED"},
            adapter=_Adapter(),
            venue="SPOT",
        )


def test_request_readiness_mismatch_fails_closed():
    readiness = _readiness()
    readiness["quantity"] = 0.2
    with pytest.raises(ValueError, match="PRE_EXECUTION_REQUEST_MISMATCH:quantity"):
        build_production_final_attempt_context(
            request=_request(),
            pre_execution_readiness=readiness,
            management_observation={"decision": "AUTHORIZED"},
            adapter=_Adapter(),
            venue="SPOT",
        )


def test_invalid_venue_fails_closed():
    with pytest.raises(ValueError, match="EXECUTION_VENUE_INVALID"):
        build_production_final_attempt_context(
            request=_request(),
            pre_execution_readiness=_readiness(),
            management_observation={"decision": "AUTHORIZED"},
            adapter=_Adapter(),
            venue="UNKNOWN",
        )
