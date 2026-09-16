"""CP38-E validated Entry + Stop -> Smart Risk boundary.

Provider-neutral, read-only contract mapping. No inference, API, DB,
execution, or pipeline coupling.
"""
from __future__ import annotations
from collections.abc import Mapping
from math import isfinite
from typing import Any


def _positive(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not isfinite(number) or number <= 0:
        return None
    return number


def merge_validated_entry_stop(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Return explicit validated Entry/Stop inputs for Smart Risk."""
    if not isinstance(observation, Mapping):
        raise ValueError("INVALID_INPUT")

    asset = observation.get("asset")
    direction = observation.get("direction")
    if not isinstance(asset, str) or not asset.strip():
        raise ValueError("ASSET_NOT_EXPLICIT")
    if direction not in ("LONG", "SHORT"):
        raise ValueError("DIRECTION_INVALID")

    entry = _positive(observation.get("entry_price"))
    if entry is None or observation.get("entry_validation") != "VALID":
        raise ValueError("ENTRY_PRICE_NOT_EXPLICIT")

    stop = _positive(observation.get("stop_distance"))
    if stop is None or observation.get("stop_validation") != "VALID":
        raise ValueError("STOP_DISTANCE_NOT_VALIDATED")

    source = observation.get("stop_source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("STOP_SOURCE_MISSING")

    return {
        "asset": asset,
        "direction": direction,
        "entry_price": entry,
        "stop_distance": stop,
        "entry_validation": "VALID",
        "stop_validation": "VALID",
        "stop_source": source,
    }


__all__ = ["merge_validated_entry_stop"]
