"""
ARUNDA TRADER — EXECUTION AUTHORIZATION BOUNDARY v0.1
======================================================

Final provider-neutral authorization boundary before any future execution
layer.

Flow:
    PRE-EXECUTION READY
    + EXPLICIT VALID BOUNDED AUTHORIZATION
    -> AUTHORIZED

This module never creates, submits, signs, mutates, or executes an order.
It has no exchange/API/DB/runtime dependencies and performs no rounding.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

READY = "READY"
AUTHORIZED = "AUTHORIZED"
VALID = "VALID"

_FORBIDDEN_AUTHORIZATION_SOURCES = {
    "TEST",
    "SIMULATED",
    "LEGACY",
}


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


def _require_nonempty_string(value: Any, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    return value.strip()


def _require_scope_value(
    scope: Mapping[str, Any],
    key: str,
    reason: str,
) -> Any:
    if key not in scope:
        raise ValueError(reason)
    return scope[key]


def _parse_future_expiry(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("AUTHORIZATION_EXPIRY_INVALID")

    raw = value.strip()

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("AUTHORIZATION_EXPIRY_INVALID") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("AUTHORIZATION_EXPIRY_INVALID")

    now = datetime.now(timezone.utc)

    if parsed.astimezone(timezone.utc) <= now:
        raise ValueError("AUTHORIZATION_EXPIRED")

    return raw


def _require_exact_alignment(
    *,
    readiness: Mapping[str, Any],
    scope: Mapping[str, Any],
    key: str,
    reason_missing: str,
    reason_mismatch: str,
) -> Any:
    readiness_value = readiness.get(key)

    if readiness_value is None:
        raise ValueError(reason_missing)

    scope_value = _require_scope_value(scope, key, reason_missing)

    if isinstance(readiness_value, str):
        if not isinstance(scope_value, str):
            raise ValueError(reason_mismatch)

        if readiness_value.strip() != scope_value.strip():
            raise ValueError(reason_mismatch)
    else:
        if readiness_value != scope_value:
            raise ValueError(reason_mismatch)

    return readiness_value


def evaluate_execution_authorization(
    readiness_observation: Mapping[str, Any],
    authorization_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Evaluate one explicit, bounded execution authorization.

    This function does not execute anything and has no provider/API/DB
    dependency.

    Authorization must be:
      - explicitly AUTHORIZED
      - explicitly VALID
      - issued by a non-test/non-simulated/non-legacy source
      - uniquely identified
      - bounded by a future expiry
      - bounded by venue/instrument/asset/direction/order type/quantity
      - bounded by maximum exposure
      - bound to exactly one execution attempt
    """

    readiness = _require_mapping(
        readiness_observation,
        "READINESS_INPUT_INVALID",
    )
    authorization = _require_mapping(
        authorization_observation,
        "AUTHORIZATION_INPUT_INVALID",
    )

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
        or source.strip().upper() in _FORBIDDEN_AUTHORIZATION_SOURCES
    ):
        raise ValueError("AUTHORIZATION_SOURCE_INVALID")

    authorization_id = _require_nonempty_string(
        authorization.get("authorization_id"),
        "AUTHORIZATION_ID_INVALID",
    )

    attempt_id = _require_nonempty_string(
        authorization.get("attempt_id"),
        "ATTEMPT_ID_INVALID",
    )

    expires_at = _parse_future_expiry(
        authorization.get("expires_at"),
    )

    scope = _require_mapping(
        authorization.get("authorization_scope"),
        "AUTHORIZATION_SCOPE_INVALID",
    )

    asset = _require_nonempty_string(
        readiness.get("asset"),
        "ASSET_INVALID",
    )

    scoped_asset = _require_nonempty_string(
        _require_scope_value(
            scope,
            "asset",
            "AUTHORIZATION_ASSET_SCOPE_INVALID",
        ),
        "AUTHORIZATION_ASSET_SCOPE_INVALID",
    )

    if asset != scoped_asset:
        raise ValueError("AUTHORIZATION_ASSET_MISMATCH")

    venue = _require_nonempty_string(
        _require_scope_value(
            scope,
            "venue",
            "AUTHORIZATION_VENUE_SCOPE_INVALID",
        ),
        "AUTHORIZATION_VENUE_SCOPE_INVALID",
    )

    execution_instrument = _require_exact_alignment(
        readiness=readiness,
        scope=scope,
        key="execution_instrument",
        reason_missing="EXECUTION_INSTRUMENT_SCOPE_INVALID",
        reason_mismatch="EXECUTION_INSTRUMENT_SCOPE_MISMATCH",
    )

    direction = _require_exact_alignment(
        readiness=readiness,
        scope=scope,
        key="direction",
        reason_missing="DIRECTION_SCOPE_INVALID",
        reason_mismatch="DIRECTION_SCOPE_MISMATCH",
    )

    order_type = _require_exact_alignment(
        readiness=readiness,
        scope=scope,
        key="order_type",
        reason_missing="ORDER_TYPE_SCOPE_INVALID",
        reason_mismatch="ORDER_TYPE_SCOPE_MISMATCH",
    )

    quantity = readiness.get("quantity")

    if not _positive_finite(quantity):
        raise ValueError("QUANTITY_INVALID")

    scoped_quantity = _require_scope_value(
        scope,
        "quantity",
        "AUTHORIZATION_QUANTITY_SCOPE_INVALID",
    )

    if not _positive_finite(scoped_quantity):
        raise ValueError("AUTHORIZATION_QUANTITY_SCOPE_INVALID")

    if float(quantity) != float(scoped_quantity):
        raise ValueError("AUTHORIZATION_QUANTITY_SCOPE_MISMATCH")

    entry_price = readiness.get("entry_price")

    if not _positive_finite(entry_price):
        raise ValueError("ENTRY_PRICE_INVALID")

    notional = readiness.get("notional")

    if not _positive_finite(notional):
        raise ValueError("NOTIONAL_INVALID")

    max_exposure = _require_scope_value(
        scope,
        "max_exposure",
        "AUTHORIZATION_MAX_EXPOSURE_INVALID",
    )

    if not _positive_finite(max_exposure):
        raise ValueError("AUTHORIZATION_MAX_EXPOSURE_INVALID")

    if float(notional) > float(max_exposure):
        raise ValueError("AUTHORIZATION_MAX_EXPOSURE_EXCEEDED")

    return {
        "authorization_state": AUTHORIZED,
        "reason": "EXECUTION_AUTHORIZED",
        "authorization_id": authorization_id,
        "authorization_source": source.strip(),
        "authorization_validation": VALID,
        "attempt_id": attempt_id,
        "expires_at": expires_at,
        "venue": venue,
        "execution_instrument": (
            execution_instrument.strip()
            if isinstance(execution_instrument, str)
            else execution_instrument
        ),
        "asset": asset,
        "direction": (
            direction.strip()
            if isinstance(direction, str)
            else direction
        ),
        "order_type": (
            order_type.strip()
            if isinstance(order_type, str)
            else order_type
        ),
        "quantity": float(quantity),
        "entry_price": float(entry_price),
        "notional": float(notional),
        "max_exposure": float(max_exposure),
    }
