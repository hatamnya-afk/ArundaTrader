"""
ARUNDA TRADER — EXECUTION AUTHORIZATION BOUNDARY v0.2
=====================================================

Technical authorization boundary before a future provider attempt.

Management is NOT consulted here per trade. Management provides one
REAL-PRODUCTION STANDING_MANDATE at phase entry. This boundary verifies that
the current ready order is inside that standing mandate and the mandate is
still valid.

No exchange/API/DB/runtime dependency. No order submission. No execution.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

READY = "READY"
AUTHORIZED = "AUTHORIZED"
VALID = "VALID"
STANDING_MANDATE = "STANDING_MANDATE"

_FORBIDDEN_AUTHORIZATION_SOURCES = {"TEST", "SIMULATED", "LEGACY"}


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


def _parse_future_expiry(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("AUTHORIZATION_EXPIRY_INVALID")

    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("AUTHORIZATION_EXPIRY_INVALID") from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("AUTHORIZATION_EXPIRY_INVALID")

    if parsed.astimezone(timezone.utc) <= datetime.now(timezone.utc):
        raise ValueError("AUTHORIZATION_EXPIRED")

    return value.strip()


def _evaluate_standing_mandate(
    *,
    readiness: Mapping[str, Any],
    mandate: Mapping[str, Any],
) -> dict[str, Any]:
    if mandate.get("execution_authorization") != AUTHORIZED:
        raise ValueError("AUTHORIZATION_INVALID")
    if mandate.get("authorization_validation") != VALID:
        raise ValueError("AUTHORIZATION_VALIDATION_INVALID")
    if mandate.get("authorization_mode") != STANDING_MANDATE:
        raise ValueError("AUTHORIZATION_MODE_INVALID")

    source = _require_nonempty_string(
        mandate.get("authorization_source"),
        "AUTHORIZATION_SOURCE_INVALID",
    )
    if source.upper() in _FORBIDDEN_AUTHORIZATION_SOURCES:
        raise ValueError("AUTHORIZATION_SOURCE_INVALID")

    mandate_id = _require_nonempty_string(
        mandate.get("mandate_id") or mandate.get("authorization_id"),
        "AUTHORIZATION_MANDATE_ID_INVALID",
    )
    expires_at = _parse_future_expiry(mandate.get("expires_at"))

    environment = _require_nonempty_string(
        mandate.get("environment"),
        "AUTHORIZATION_ENVIRONMENT_INVALID",
    ).upper()
    if environment != "REAL_PRODUCTION":
        raise ValueError("AUTHORIZATION_ENVIRONMENT_INVALID")

    allowed_markets = mandate.get("allowed_markets")
    if not isinstance(allowed_markets, (list, tuple, set, frozenset)):
        raise ValueError("AUTHORIZATION_MARKETS_INVALID")
    normalized_markets = {str(x).strip().upper() for x in allowed_markets}
    if not {"SPOT", "FUTURES"}.issubset(normalized_markets):
        raise ValueError("AUTHORIZATION_MARKETS_INCOMPLETE")

    venue = _require_nonempty_string(
        readiness.get("venue"),
        "AUTHORIZATION_VENUE_INVALID",
    ).upper()
    if venue not in normalized_markets:
        raise ValueError("AUTHORIZATION_MARKET_NOT_ALLOWED")

    return {
        "authorization_state": AUTHORIZED,
        "reason": "EXECUTION_AUTHORIZED_BY_STANDING_MANDATE",
        "authorization_id": mandate_id,
        "authorization_source": source,
        "authorization_mode": STANDING_MANDATE,
        "expires_at": expires_at,
        "venue": venue,
        "mandate_id": mandate_id,
    }


def evaluate_execution_authorization(
    readiness_observation: Mapping[str, Any],
    authorization_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify a standing phase-entry mandate against the current ready request."""

    readiness = _require_mapping(readiness_observation, "READINESS_INPUT_INVALID")
    mandate = _require_mapping(authorization_observation, "AUTHORIZATION_INPUT_INVALID")

    if readiness.get("readiness_state") != READY:
        if readiness.get("readiness_state") is None:
            raise ValueError("READINESS_STATE_INVALID")
        raise ValueError("READINESS_NOT_READY")

    return _evaluate_standing_mandate(
        readiness=readiness,
        mandate=mandate,
    )


__all__ = ["READY", "AUTHORIZED", "VALID", "STANDING_MANDATE", "evaluate_execution_authorization"]
