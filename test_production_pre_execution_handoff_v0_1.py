import pytest
from datetime import datetime, timedelta, timezone

from exchange_execution_contract import CanonicalOrderRequest
from production_pre_execution_handoff_v0_1 import build_production_pre_execution_handoff, load_standing_mandate_observation


def _inputs():
    request = CanonicalOrderRequest(
        asset="BTC", direction="LONG", order_type="MARKET", quantity=0.1,
        quantity_unit="BASE_ASSET", quantity_source="RISK.position_quantity",
        entry_price=100.0, reference_price=100.0, intent_id="intent",
        snapshot_id="snapshot", timestamp="2026-10-11T10:00:00+00:00",
        decision_id="decision",
    )
    return {
        "request": request,
        "decision": {"status": "READY", "state": "ACTIONABLE", "direction": "LONG"},
        "validation": {"valid": True, "validation": "VALID"},
        "risk": {
            "asset": "BTC/USDT", "direction": "LONG", "risk_state": "APPROVED", "position_sizing_state": "CALCULATED",
            "position_sizing_reason": "EXISTING_RISK_BUDGET_AND_POSITION_SIZE_POLICY",
            "entry_price": 100.0, "stop_price": 94.0, "stop_distance": 6.0,
            "position_quantity": 0.1, "exposure": 10.0,
        },
        "trade_gate": {"asset": "BTC/USDT", "direction": "LONG", "trade_gate_state": "TRADE_READY"},
        "opportunity": {"asset": "BTC/USDT", "price": 100.0, "status": "ELIGIBLE", "timestamp": "2026-10-11T10:00:00+00:00"},
    }


def test_builds_readiness_and_fails_closed_until_venue_is_explicit():
    result = build_production_pre_execution_handoff(**_inputs())
    assert result["readiness"]["readiness_state"] == "PRE_EXECUTION_READY"
    assert result["readiness"]["provider_binding"] == "DEFERRED"
    assert result["context"] is None
    assert result["status"] == "PRE_EXECUTION_READY_VENUE_SELECTION_BLOCKED"
    assert result["venue_resolution"]["reason"] == "AUTHORITATIVE_PER_INTENT_MARKET_SELECTION_MISSING"


@pytest.mark.parametrize("field,value", [
    ("risk_state", "HOLD"),
    ("position_sizing_state", "BLOCKED"),
])
def test_invalid_risk_or_sizing_never_produces_readiness(field, value):
    values = _inputs()
    values["risk"][field] = value
    with pytest.raises(ValueError):
        build_production_pre_execution_handoff(**values)


def test_request_quantity_mismatch_fails_closed():
    values = _inputs()
    values["risk"]["position_quantity"] = 0.2
    with pytest.raises(ValueError, match="PRE_EXECUTION_REQUEST_MISMATCH:quantity"):
        build_production_pre_execution_handoff(**values)


def test_missing_real_current_run_timestamp_fails_closed():
    values = _inputs()
    values["opportunity"]["timestamp"] = None
    with pytest.raises(ValueError, match="PRE_EXECUTION_CURRENT_RUN_TIMESTAMP_MISSING"):
        build_production_pre_execution_handoff(**values)


def test_standing_mandate_is_loaded_from_authoritative_artifact():
    mandate = load_standing_mandate_observation()
    assert mandate["mandate_id"] == "ARUNDA-REAL-PROD-20261011-001"
    assert mandate["provider"] == "TOOBIT"
    assert set(mandate["allowed_markets"]) == {"SPOT", "FUTURES"}


def _venue_evidence():
    now = datetime.now(timezone.utc)
    selected_at = (now - timedelta(seconds=5)).isoformat()
    instrument_at = (now - timedelta(seconds=2)).isoformat()
    return {
        "venue_selection_evidence": {
            "source": "AUTHORITATIVE_PER_INTENT_MARKET_POLICY",
            "decision": "SELECTED",
            "provider": "TOOBIT",
            "asset": "BTC/USDT",
            "venue": "FUTURES",
            "intent_id": "intent",
            "observed_at": selected_at,
        },
        "instrument_evidence": {
            "source": "TOOBIT_READ_ONLY_INSTRUMENT_CONSTRAINTS",
            "provider": "TOOBIT",
            "asset": "BTC/USDT",
            "venue": "FUTURES",
            "instrument_id": "BTCUSDT-PERP",
            "instrument_status": "TRADING",
            "observed_at": instrument_at,
        },
    }


def test_authoritative_evidence_selects_venue_but_adapter_is_still_required():
    values = _inputs()
    values.update(_venue_evidence())
    with pytest.raises(ValueError, match="EXECUTION_ADAPTER_INVALID"):
        build_production_pre_execution_handoff(**values, venue="FUTURES")


def test_explicit_venue_without_authoritative_evidence_fails_closed():
    values = _inputs()
    result = build_production_pre_execution_handoff(**values, venue="FUTURES")
    assert result["context"] is None
    assert result["status"] == "PRE_EXECUTION_READY_VENUE_SELECTION_BLOCKED"
    assert result["venue_resolution"]["reason"] == "AUTHORITATIVE_PER_INTENT_MARKET_SELECTION_MISSING"


class _Adapter:
    adapter_name = "TOOBIT"


def test_authoritative_selection_and_provider_evidence_build_final_context():
    values = _inputs()
    values.update(_venue_evidence())
    result = build_production_pre_execution_handoff(
        **values,
        venue="FUTURES",
        adapter=_Adapter(),
    )
    assert result["status"] == "FINAL_ATTEMPT_CONTEXT_READY"
    assert result["venue_resolution"]["status"] == "VENUE_SELECTED"
    assert result["venue_resolution"]["venue"] == "FUTURES"
    assert result["context"]["venue"] == "FUTURES"
    assert result["context"]["adapter"].adapter_name == "TOOBIT"


def test_explicit_venue_cannot_override_authoritative_selection():
    values = _inputs()
    values.update(_venue_evidence())
    result = build_production_pre_execution_handoff(
        **values,
        venue="SPOT",
        adapter=_Adapter(),
    )
    assert result["context"] is None
    assert result["status"] == "PRE_EXECUTION_BLOCKED_VENUE_EVIDENCE_MISMATCH"
