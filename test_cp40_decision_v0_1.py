from __future__ import annotations

from datetime import datetime, timezone

import pytest

from decision_contract_v0_1 import validate_sealed_decision_input
from decision_engine_v0_1 import build_decision


SEALED_DECISION_INPUT = {
    "readiness_state": "READY",
    "readiness_validation": "VALID",
    "readiness_source": "REAL_PRODUCTION_READINESS",
    "provenance": "REAL_PRODUCTION_OBSERVATION",
    "asset": "ETHUSDT",
    "capital_validation": "VALID",
    "portfolio_validation": "VALID",
    "stop_risk_policy_validation": "VALID",
    "liquidity_validation": "VALID",
    "execution_validation": "VALID",
    "observed_at": "2026-09-17T00:00:00+00:00",
    "decision_input_state": "READY",
    "decision_input_validation": "VALID",
}


def test_valid_sealed_input_produces_deterministic_decision():
    result = build_decision(SEALED_DECISION_INPUT, evaluation_time="2026-09-17T00:01:00+00:00")
    assert result == {
        "decision_state": "READY",
        "decision_validation": "VALID",
        "decision_reason": "SEALED_INPUT_VALID",
        "asset": "ETHUSDT",
        "provenance": "REAL_PRODUCTION_OBSERVATION",
        "observed_at": "2026-09-17T00:00:00+00:00",
    }
    assert result == build_decision(
        SEALED_DECISION_INPUT, evaluation_time="2026-09-17T00:01:00+00:00"
    )


def test_contract_accepts_dynamic_asset_without_fixed_universe():
    validate_sealed_decision_input({**SEALED_DECISION_INPUT, "asset": "XRPUSDT"})


def test_contract_rejects_test_legacy_or_simulated_provenance():
    for value in ("TEST", "LEGACY", "SIMULATED"):
        invalid = {**SEALED_DECISION_INPUT, "provenance": value}
        with pytest.raises(ValueError, match="DECISION_INPUT_PROVENANCE_INVALID"):
            validate_sealed_decision_input(invalid)


def test_contract_rejects_missing_or_invalid_sealed_input():
    for field in ("asset", "provenance", "observed_at", "decision_input_state"):
        invalid = dict(SEALED_DECISION_INPUT)
        invalid.pop(field)
        with pytest.raises(ValueError, match="DECISION_INPUT_INVALID"):
            validate_sealed_decision_input(invalid)


def test_contract_rejects_stale_input_against_explicit_evaluation_time():
    with pytest.raises(ValueError, match="DECISION_INPUT_STALE"):
        build_decision(
            SEALED_DECISION_INPUT,
            evaluation_time="2026-09-17T01:00:01+00:00",
            max_age_seconds=3600,
        )


def test_contract_rejects_provider_coupling():
    invalid = {**SEALED_DECISION_INPUT, "exchange": "TOOBIT"}
    with pytest.raises(ValueError, match="DECISION_PROVIDER_COUPLING"):
        validate_sealed_decision_input(invalid)


def test_contract_rejects_execution_surface():
    for field in ("order_id", "execution_authorization", "execution_enabled", "api_request"):
        invalid = {**SEALED_DECISION_INPUT, field: "forbidden"}
        with pytest.raises(ValueError, match="DECISION_EXECUTION_SURFACE"):
            validate_sealed_decision_input(invalid)


def test_engine_produces_no_order_or_execution_fields():
    result = build_decision(SEALED_DECISION_INPUT, evaluation_time="2026-09-17T00:01:00+00:00")
    assert not {"order_id", "order_intent", "execution_authorization", "execution_enabled"}.intersection(result)


def test_engine_does_not_invent_capital_price_or_stop():
    result = build_decision(SEALED_DECISION_INPUT, evaluation_time="2026-09-17T00:01:00+00:00")
    assert not {"capital", "price", "entry", "stop", "quantity"}.intersection(result)


def test_evaluation_time_is_explicit_and_deterministic():
    with pytest.raises(ValueError, match="DECISION_EVALUATION_TIME_REQUIRED"):
        build_decision(SEALED_DECISION_INPUT)


def test_evaluation_time_must_be_timezone_aware():
    with pytest.raises(ValueError, match="DECISION_EVALUATION_TIME_INVALID"):
        build_decision(SEALED_DECISION_INPUT, evaluation_time="2026-09-17T00:01:00")
