"""
ARUNDA TRADER — PRE-EXECUTION ORDER READINESS BOUNDARY v0.1
==============================================================

Final provider-neutral boundary before any future execution layer.

Flow:
    VALIDATED CONSTRAINT RESULT -> PRE-EXECUTION READINESS
    -> READY / (exception on invalid or blocked input)

This module never creates, submits, signs, mutates, or executes an order.
It has no exchange/API/DB/runtime dependencies and performs no rounding.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

READY = "READY"
VALID = "VALID"


def _positive_finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0.0
    )


def _require_mapping(observation: Any) -> Mapping[str, Any]:
    if not isinstance(observation, Mapping):
        raise ValueError("READINESS_INPUT_INVALID")
    return observation


def evaluate_pre_execution_readiness(observation: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the final provider-neutral readiness boundary.

    Only an already VALID constraint evaluation can become READY. The
    function is deterministic, side-effect free, and fail-closed.
    """
    data = _require_mapping(observation)

    state = data.get("constraint_state")
    if state is None:
        raise ValueError("CONSTRAINT_STATE_INVALID")
    if state != VALID:
        raise ValueError("CONSTRAINTS_BLOCKED")

    asset = data.get("asset")
    if not isinstance(asset, str) or not asset.strip():
        raise ValueError("ASSET_INVALID")

    quantity = data.get("quantity")
    if not _positive_finite(quantity):
        raise ValueError("QUANTITY_INVALID")

    entry_price = data.get("entry_price")
    if not _positive_finite(entry_price):
        raise ValueError("ENTRY_PRICE_INVALID")

    notional = data.get("notional")
    if not _positive_finite(notional):
        raise ValueError("NOTIONAL_INVALID")

    return {
        "readiness_state": READY,
        "reason": "PRE_EXECUTION_READY",
        "asset": asset.strip(),
        "quantity": float(quantity),
        "entry_price": float(entry_price),
        "notional": float(notional),
    }
