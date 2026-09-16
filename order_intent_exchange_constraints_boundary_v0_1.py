"""ARUNDA TRADER — ORDER INTENT → EXCHANGE CONSTRAINTS BOUNDARY v0.1.
Provider-neutral, read-only downstream contract boundary.

Purpose:
    Consume an approved OrderIntent-shaped observation and expose only
    the minimal validated fields required by a future exchange-constraint
    evaluation layer.

This module does NOT:
    - select an exchange
    - resolve symbol metadata or trading constraints
    - call an exchange/API
    - create or submit an order
    - execute trades
    - write to the database
"""

from __future__ import annotations

import math
from collections.abc import Mapping


_ALLOWED_DIRECTIONS = {"LONG", "SHORT"}
_REQUIRED = (
    "asset",
    "direction",
    "quantity",
    "entry_price",
    "stop_distance",
    "exposure",
)


def _positive_number(value: object, reason: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(reason)
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(reason)
    return value


def merge_validated_order_intent_to_exchange_constraints_input(
    observation: Mapping[str, object],
) -> dict[str, object]:
    """Validate and expose the minimal OrderIntent boundary."""
    if not isinstance(observation, Mapping):
        raise ValueError("ORDER_INTENT_OBSERVATION_INVALID")

    if observation.get("trade_gate_state") != "APPROVED":
        raise ValueError("TRADE_GATE_NOT_APPROVED")

    if observation.get("risk_state") != "APPROVED":
        raise ValueError("RISK_NOT_APPROVED")

    for field in _REQUIRED:
        if field not in observation:
            raise ValueError(f"{field.upper()}_INVALID")

    asset = observation["asset"]
    if not isinstance(asset, str) or not asset.strip():
        raise ValueError("ASSET_INVALID")

    direction = observation["direction"]
    if direction not in _ALLOWED_DIRECTIONS:
        raise ValueError("DIRECTION_INVALID")

    quantity = _positive_number(observation["quantity"], "QUANTITY_INVALID")
    entry_price = _positive_number(observation["entry_price"], "ENTRY_PRICE_INVALID")
    stop_distance = _positive_number(observation["stop_distance"], "STOP_DISTANCE_INVALID")
    exposure = _positive_number(observation["exposure"], "EXPOSURE_INVALID")

    return {
        "asset": asset,
        "direction": direction,
        "quantity": quantity,
        "entry_price": entry_price,
        "stop_distance": stop_distance,
        "exposure": exposure,
    }
