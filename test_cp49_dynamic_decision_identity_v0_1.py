import pytest

from dynamic_decision_contract_boundary_v0_1 import build_dynamic_decision


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


def test_dynamic_decision_requires_canonical_decision_id():
    with pytest.raises(ValueError, match="canonical decision_id is required"):
        build_dynamic_decision("BTC/USDT", _signal(), _score())


def test_dynamic_decision_preserves_real_decision_id():
    result = build_dynamic_decision(
        "BTC/USDT",
        _signal(),
        _score(),
        decision_id="D-REAL-001",
    )
    assert result["status"] == "READY"
    assert result["decision_id"] == "D-REAL-001"


def test_dynamic_decision_does_not_derive_identity():
    result = build_dynamic_decision(
        "BTC/USDT",
        _signal(),
        _score(),
        decision_id="D-REAL-001",
    )
    assert result["decision_id"] != "BTC/USDT"
    assert result["decision_id"] != "D-REAL-001:BTC"
