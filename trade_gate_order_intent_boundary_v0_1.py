"""
ARUNDA TRADER — TRADE GATE → ORDER INTENT BOUNDARY v0.1
=========================================================
Provider-neutral, read-only downstream contract boundary.

Purpose:
    Consume an APPROVED Trade Gate result and expose only the
    minimal validated fields required by a downstream OrderIntent
    producer/consumer.

This module does NOT:
    - create an OrderIntent object
    - submit or cancel orders
    - call an exchange/API
    - write to the database
    - execute trades
    - select exchange constraints
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
    "risk_state",
    "policy_version",
)


def _positive_number(value: object, reason: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(reason)
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(reason)
    return value


def merge_approved_trade_gate_to_order_intent_input(
    observation: Mapping[str, object],
) -> dict[str, object]:
    """Validate and expose the minimal approved Trade Gate boundary."""
    if not isinstance(observation, Mapping):
        raise ValueError("TRADE_GATE_OBSERVATION_INVALID")

    if observation.get("trade_gate_state") != "APPROVED":
        raise ValueError("TRADE_GATE_NOT_APPROVED")

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

    if observation["risk_state"] != "APPROVED":
        raise ValueError("RISK_NOT_APPROVED")

    policy_version = observation["policy_version"]
    if not isinstance(policy_version, str) or not policy_version.strip():
        raise ValueError("POLICY_VERSION_INVALID")

    return {
        "asset": asset,
        "direction": direction,
        "quantity": quantity,
        "entry_price": entry_price,
        "stop_distance": stop_distance,
        "exposure": exposure,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": policy_version,
    }
