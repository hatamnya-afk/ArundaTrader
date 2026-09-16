"""
ARUNDA TRADER — EXCHANGE CONSTRAINT EVALUATOR v0.1
===================================================

Provider-neutral, read-only, deterministic evaluation boundary.

Flow:
    APPROVED ORDER INTENT INPUT
        +
    VALIDATED EXCHANGE CONSTRAINTS
        -> CONSTRAINT EVALUATION
        -> VALID / BLOCKED

This module does not create, mutate, submit, or execute orders.
It does not resolve exchange metadata, call APIs, access the DB,
or perform quantity/price rounding.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

VALID = "VALID"
BLOCKED = "BLOCKED"

_FORBIDDEN_SOURCES = {"TEST", "SIMULATED", "LEGACY"}


def _positive_finite(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0.0
    )


def _multiple_of(value: float, step: float) -> bool:
    quotient = value / step
    return math.isclose(quotient, round(quotient), rel_tol=0.0, abs_tol=1e-9)


def _blocked(reason: str) -> dict[str, str]:
    return {"constraint_state": BLOCKED, "reason": reason}


def evaluate_exchange_constraints(
    order_intent: Mapping[str, Any],
    constraints: Mapping[str, Any],
) -> dict[str, Any]:
    """Evaluate an approved order-intent observation against validated constraints.

    The evaluator is deliberately strict and fail-closed. It validates only
    generic, provider-neutral constraint semantics and never rounds inputs.
    """
    if not isinstance(order_intent, Mapping) or not isinstance(constraints, Mapping):
        return _blocked("CONSTRAINT_INPUT_INVALID")

    if order_intent.get("trade_gate_state") != "APPROVED":
        return _blocked("TRADE_GATE_NOT_APPROVED")
    if order_intent.get("risk_state") != "APPROVED":
        return _blocked("RISK_NOT_APPROVED")

    if constraints.get("constraint_validation") != VALID:
        return _blocked("CONSTRAINTS_UNVALIDATED")

    source = constraints.get("constraint_source")
    if not isinstance(source, str) or not source.strip():
        return _blocked("CONSTRAINT_SOURCE_INVALID")
    if source.strip().upper() in _FORBIDDEN_SOURCES:
        return _blocked("CONSTRAINT_SOURCE_INVALID")

    asset = order_intent.get("asset")
    constraint_asset = constraints.get("asset")
    if (
        not isinstance(asset, str)
        or not asset.strip()
        or not isinstance(constraint_asset, str)
        or not constraint_asset.strip()
        or asset.strip() != constraint_asset.strip()
    ):
        return _blocked("ASSET_MISMATCH")

    quantity = order_intent.get("quantity")
    entry_price = order_intent.get("entry_price")
    if not _positive_finite(quantity):
        return _blocked("QUANTITY_INVALID")
    if not _positive_finite(entry_price):
        return _blocked("ENTRY_PRICE_INVALID")

    numeric_names = (
        "tick_size",
        "step_size",
        "min_qty",
        "max_qty",
        "min_notional",
    )
    values: dict[str, float] = {}
    for name in numeric_names:
        value = constraints.get(name)
        if not _positive_finite(value):
            return _blocked(f"{name.upper()}_INVALID")
        values[name] = float(value)

    if values["min_qty"] > values["max_qty"]:
        return _blocked("QUANTITY_RANGE_INVALID")

    if quantity < values["min_qty"] or quantity > values["max_qty"]:
        return _blocked("QUANTITY_RANGE_INVALID")

    if not _multiple_of(float(quantity), values["step_size"]):
        return _blocked("QUANTITY_STEP_INVALID")

    if not _multiple_of(float(entry_price), values["tick_size"]):
        return _blocked("PRICE_TICK_INVALID")

    notional = float(quantity) * float(entry_price)
    if notional < values["min_notional"]:
        return _blocked("MIN_NOTIONAL_INVALID")

    return {
        "constraint_state": VALID,
        "reason": "CONSTRAINTS_VALID",
        "asset": asset.strip(),
        "quantity": float(quantity),
        "entry_price": float(entry_price),
        "notional": notional,
    }
