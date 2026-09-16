"""CP38-E contract-boundary tests for validated Entry + Stop -> Smart Risk."""
import pytest

from smart_risk_entry_stop_bridge_v0_1 import merge_validated_entry_stop


def _valid():
    return {
        "asset": "BTCUSDT",
        "direction": "LONG",
        "entry_price": 100.0,
        "stop_distance": 10.0,
        "entry_validation": "VALID",
        "stop_validation": "VALID",
        "stop_source": "VALIDATED_STOP_PRODUCER",
    }


def test_validated_entry_and_stop_are_consumed_explicitly():
    result = merge_validated_entry_stop(_valid())
    assert result["entry_price"] == pytest.approx(100.0)
    assert result["stop_distance"] == pytest.approx(10.0)
    assert result["asset"] == "BTCUSDT"
    assert result["direction"] == "LONG"


def test_missing_entry_is_fail_closed():
    observation = _valid(); observation.pop("entry_price")
    with pytest.raises(ValueError, match="ENTRY_PRICE_NOT_EXPLICIT"):
        merge_validated_entry_stop(observation)


def test_missing_or_invalid_stop_is_fail_closed():
    observation = _valid(); observation["stop_validation"] = "INVALID"
    with pytest.raises(ValueError, match="STOP_DISTANCE_NOT_VALIDATED"):
        merge_validated_entry_stop(observation)


def test_bridge_does_not_infer_entry_or_stop():
    observation = _valid()
    observation.pop("entry_price")
    observation.pop("stop_distance")
    with pytest.raises(ValueError):
        merge_validated_entry_stop(observation)
