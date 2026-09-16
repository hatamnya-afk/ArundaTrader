"""
ARUNDA TRADER — EXECUTION AUTHORIZATION BOUNDARY v0.1
======================================================

Final provider-neutral authorization boundary before any future execution
layer.

Flow:
    PRE-EXECUTION READY + EXPLICIT VALID AUTHORIZATION
    -> AUTHORIZED

This module never creates, submits, signs, mutates, or executes an order.
It has no exchange/API/DB/runtime dependencies and performs no rounding.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

READY = "READY"
AUTHORIZED = "AUTHORIZED"
VALID = "VALID"


def _positive_finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0.0
    )


def _require_mapping(value: Any, reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(reason)
    return value


def evaluate_execution_authorization(
    readiness_observation: Mapping[str, Any],
    authorization_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate an explicit execution authorization without executing anything."""
    readiness = _require_mapping(readiness_observation, "READINESS_INPUT_INVALID")
    authorization = _require_mapping(authorization_observation, "AUTHORIZATION_INPUT_INVALID")

    readiness_state = readiness.get("readiness_state")
    if readiness_state is None:
        raise ValueError("READINESS_STATE_INVALID")
    if readiness_state != READY:
        raise ValueError("READINESS_NOT_READY")

    if authorization.get("execution_authorization") != AUTHORIZED:
        raise ValueError("AUTHORIZATION_INVALID")
    if authorization.get("authorization_validation") != VALID:
        raise ValueError("AUTHORIZATION_VALIDATION_INVALID")

    source = authorization.get("authorization_source")
    if (
        not isinstance(source, str)
        or not source.strip()
        or source.strip().upper() in {"TEST", "SIMULATED", "LEGACY"}
    ):
        raise ValueError("AUTHORIZATION_SOURCE_INVALID")

    asset = readiness.get("asset")
    if not isinstance(asset, str) or not asset.strip():
        raise ValueError("ASSET_INVALID")

    quantity = readiness.get("quantity")
    if not _positive_finite(quantity):
        raise ValueError("QUANTITY_INVALID")

    entry_price = readiness.get("entry_price")
    if not _positive_finite(entry_price):
        raise ValueError("ENTRY_PRICE_INVALID")

    notional = readiness.get("notional")
    if not _positive_finite(notional):
        raise ValueError("NOTIONAL_INVALID")

    return {
        "authorization_state": AUTHORIZED,
        "reason": "EXECUTION_AUTHORIZED",
        "asset": asset.strip(),
        "quantity": float(quantity),
        "entry_price": float(entry_price),
        "notional": float(notional),
    }
