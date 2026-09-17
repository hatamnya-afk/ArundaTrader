"""ARUNDA ENTRY / INVALIDATION BOUNDARY v0.1.

Provider-neutral, execution-free boundary for validated upstream entry and
invalidation observations. This boundary does not invent prices or calculate
an invalidation from a hidden/default policy.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from math import isfinite


DIRECTIONS = ("LONG", "SHORT")
STATES = ("READY", "BLOCKED")


@dataclass(frozen=True)
class EntryInvalidation:
    asset: str
    direction: str
    state: str
    entry_price: float | None
    invalidation_price: float | None
    stop_distance: float | None
    reason: str
    source: str | None

    def validate(self) -> bool:
        if not isinstance(self.asset, str) or not self.asset.strip():
            raise ValueError("asset must be non-empty")
        if self.direction not in DIRECTIONS:
            raise ValueError("invalid direction")
        if self.state not in STATES:
            raise ValueError("invalid state")
        if not isinstance(self.reason, str) or not self.reason.strip():
            raise ValueError("reason must be non-empty")
        if self.source is not None and not isinstance(self.source, str):
            raise TypeError("source must be string or None")
        for name, value in (
            ("entry_price", self.entry_price),
            ("invalidation_price", self.invalidation_price),
            ("stop_distance", self.stop_distance),
        ):
            if value is not None and (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not isfinite(float(value))
                or value <= 0
            ):
                raise ValueError(f"invalid {name}")

        if self.state == "READY":
            if self.entry_price is None or self.invalidation_price is None:
                raise ValueError("READY requires entry and invalidation")
            if self.stop_distance is None:
                raise ValueError("READY requires stop_distance")
            if self.direction == "LONG" and self.invalidation_price >= self.entry_price:
                raise ValueError("LONG invalidation must be below entry")
            if self.direction == "SHORT" and self.invalidation_price <= self.entry_price:
                raise ValueError("SHORT invalidation must be above entry")
            expected_distance = abs(self.entry_price - self.invalidation_price)
            if abs(self.stop_distance - expected_distance) > 1e-12:
                raise ValueError("stop_distance does not match entry/invalidation")
        return True


def normalize_entry_invalidation(
    asset: str,
    decision: Mapping[str, object],
    observation: Mapping[str, object],
) -> EntryInvalidation:
    """Accept only explicit upstream values; never infer missing risk geometry."""
    if not isinstance(decision, Mapping) or not isinstance(observation, Mapping):
        raise ValueError("decision and observation must be mappings")

    direction = decision.get("direction")
    if direction not in DIRECTIONS:
        return EntryInvalidation(asset, str(direction), "BLOCKED", None, None, None, "DIRECTION_INVALID", None)

    entry = observation.get("entry_price")
    invalidation = observation.get("invalidation_price")
    source = observation.get("source")

    if entry is None or invalidation is None:
        result = EntryInvalidation(
            asset, direction, "BLOCKED", None, None, None,
            "ENTRY_OR_INVALIDATION_NOT_EXPLICIT", source if isinstance(source, str) else None,
        )
        result.validate()
        return result

    try:
        entry_value = float(entry)
        invalidation_value = float(invalidation)
    except (TypeError, ValueError):
        result = EntryInvalidation(
            asset, direction, "BLOCKED", None, None, None,
            "ENTRY_OR_INVALIDATION_INVALID", source if isinstance(source, str) else None,
        )
        result.validate()
        return result

    if not isfinite(entry_value) or not isfinite(invalidation_value) or entry_value <= 0 or invalidation_value <= 0:
        result = EntryInvalidation(
            asset, direction, "BLOCKED", None, None, None,
            "ENTRY_OR_INVALIDATION_INVALID", source if isinstance(source, str) else None,
        )
        result.validate()
        return result

    distance = abs(entry_value - invalidation_value)
    if distance <= 1e-12:
        result = EntryInvalidation(
            asset, direction, "BLOCKED", entry_value, invalidation_value, None,
            "ZERO_INVALIDATION_DISTANCE", source if isinstance(source, str) else None,
        )
        result.validate()
        return result

    if direction == "LONG" and invalidation_value >= entry_value:
        reason = "LONG_INVALIDATION_MUST_BE_BELOW_ENTRY"
    elif direction == "SHORT" and invalidation_value <= entry_value:
        reason = "SHORT_INVALIDATION_MUST_BE_ABOVE_ENTRY"
    else:
        reason = "ENTRY_AND_INVALIDATION_VALID"

    if reason != "ENTRY_AND_INVALIDATION_VALID":
        result = EntryInvalidation(
            asset, direction, "BLOCKED", entry_value, invalidation_value, distance,
            reason, source if isinstance(source, str) else None,
        )
        result.validate()
        return result

    result = EntryInvalidation(
        asset, direction, "READY", entry_value, invalidation_value, distance,
        reason, source if isinstance(source, str) else None,
    )
    result.validate()
    return result


__all__ = ["EntryInvalidation", "normalize_entry_invalidation"]
