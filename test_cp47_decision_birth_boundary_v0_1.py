from __future__ import annotations

import uuid

from dynamic_decision_contract_boundary_v0_1 import (
    build_dynamic_decision,
    static_contract_check,
)


def _signal():
    return {
        "asset": "BTC",
        "signal_state": "ACTIVE",
        "direction": "LONG",
        "valid": True,
        "validation": "VALID",
    }


def _score():
    return {
        "asset": "BTC",
        "signal_state": "ACTIVE",
        "direction": "LONG",
        "score": 0.75,
    }


def test_dynamic_decision_birth_issues_uuid4_and_binds_provenance():
    result = build_dynamic_decision(
        "BTC/USDT",
        _signal(),
        _score(),
    )

    decision_id = result["decision_id"]
    parsed = uuid.UUID(decision_id)

    assert parsed.version == 4
    assert result["state"] == "ACTIONABLE"
    assert result["direction"] == "LONG"
    assert result["decision_birth_source"] == "DYNAMIC_DECISION_BIRTH"
    assert result["decision_birth_issuer_contract"] == (
        "CP49-AUTHORITATIVE-DECISION-BIRTH-UUID4-v0.1"
    )
    assert result["snapshot_id"].startswith("DYN-")
    assert isinstance(result["decision_timestamp_ms"], int)
    assert result["decision_timestamp_ms"] > 0
    assert result["db_writes"] == 0
    assert result["execution"] is False


def test_existing_decision_id_is_propagated_unchanged():
    decision_id = str(uuid.uuid4())

    result = build_dynamic_decision(
        "BTC/USDT",
        _signal(),
        _score(),
        decision_id=decision_id,
    )

    assert result["decision_id"] == decision_id


def test_dynamic_decision_contract_static_check():
    static_contract_check()
