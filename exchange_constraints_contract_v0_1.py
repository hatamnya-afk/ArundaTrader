"""ARUNDA TRADER — EXCHANGE CONSTRAINTS CONTRACT v0.1
========================================================
Provider-neutral, read-only contract for validated exchange trading rules.

Purpose:
    Establish the immutable boundary between an approved OrderIntent and a
    future exchange-constraint evaluation layer. The contract carries only
    normalized constraint observations; it does not select an exchange,
    contact an API, mutate state, create orders, or execute trades.

Required real observations:
    - tick_size
    - step_size
    - min_qty
    - max_qty
    - min_notional

Safety properties:
    - explicit VALID validation state is mandatory
    - TEST / SIMULATED / LEGACY sources are rejected
    - all numeric constraints must be finite and strictly positive
    - quantity bounds must be internally consistent
    - provider-specific metadata is deliberately excluded from the output
    - fail-closed on malformed or incomplete observations
"""

from __future__ import annotations

import math
from collections.abc import Mapping


_VALIDATION_STATE = "VALID"
_FORBIDDEN_SOURCES = {"TEST", "SIMULATED", "LEGACY"}
_REQUIRED_FIELDS = (
    "asset",
    "tick_size",
    "step_size",
    "min_qty",
    "max_qty",
    "min_notional",
)


def _positive_finite(value: object, reason: str) -> float:
    """Return a normalized positive finite number or fail closed."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(reason)

    normalized = float(value)
    if not math.isfinite(normalized) or normalized <= 0:
        raise ValueError(reason)

    return normalized


def build_exchange_constraints(
    observation: Mapping[str, object],
) -> dict[str, object]:
    """Validate and expose the provider-neutral exchange constraints contract.

    The function intentionally accepts an observation rather than an exchange
    client. This keeps the contract independent of any provider and prevents
    exchange/API behavior from entering the Core risk boundary.
    """
    if not isinstance(observation, Mapping):
        raise ValueError("CONSTRAINT_OBSERVATION_INVALID")

    if observation.get("constraint_validation") != _VALIDATION_STATE:
        raise ValueError("CONSTRAINTS_UNVALIDATED")

    source = observation.get("constraint_source")
    if not isinstance(source, str) or not source.strip():
        raise ValueError("CONSTRAINT_SOURCE_INVALID")
    if source.strip().upper() in _FORBIDDEN_SOURCES:
        raise ValueError("CONSTRAINT_SOURCE_INVALID")

    for field in _REQUIRED_FIELDS:
        if field not in observation:
            raise ValueError(f"{field.upper()}_INVALID")

    asset = observation["asset"]
    if not isinstance(asset, str) or not asset.strip():
        raise ValueError("ASSET_INVALID")

    tick_size = _positive_finite(observation["tick_size"], "TICK_SIZE_INVALID")
    step_size = _positive_finite(observation["step_size"], "STEP_SIZE_INVALID")
    min_qty = _positive_finite(observation["min_qty"], "MIN_QTY_INVALID")
    max_qty = _positive_finite(observation["max_qty"], "MAX_QTY_INVALID")
    min_notional = _positive_finite(
        observation["min_notional"],
        "MIN_NOTIONAL_INVALID",
    )

    if min_qty > max_qty:
        raise ValueError("QUANTITY_RANGE_INVALID")

    return {
        "asset": asset,
        "tick_size": tick_size,
        "step_size": step_size,
        "min_qty": min_qty,
        "max_qty": max_qty,
        "min_notional": min_notional,
    }
