from __future__ import annotations

import uuid

import pytest

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


def test_dynamic_decision_requires_authoritative_birth_identity():
    with pytest.raises(ValueError, match="canonical decision_id is required"):
        build_dynamic_decision("BTC/USDT", _signal(), _score())


def test_existing_decision_id_is_propagated_unchanged():
    decision_id = str(uuid.uuid4())
    result = build_dynamic_decision(
        "BTC/USDT",
        _signal(),
        _score(),
        decision_id=decision_id,
    )
    assert result["decision_id"] == decision_id
    assert result["state"] == "ACTIONABLE"
    assert result["direction"] == "LONG"
    assert result["dynamic_universe"] is True
    assert result["fixed_15_used"] is False
    assert result["db_writes"] == 0
    assert result["execution"] is False


def test_dynamic_decision_contract_static_check():
    static_contract_check()
