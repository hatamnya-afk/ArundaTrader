"""Fail-closed verification of a current standing-mandate revocation observation.

This contract validates the shape, identity, status, and freshness of a
revocation observation supplied by an authoritative management source.
It does not create that source, persist mandate state, or authenticate a source.
Production remains blocked until runtime wiring supplies a trusted observation
and its freshness policy from the management authority.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

ACTIVE = "ACTIVE"
REVOKED = "REVOKED"
_VALID_STATUSES = {ACTIVE, REVOKED}
_FORBIDDEN_SOURCES = {"TEST", "SIMULATED", "LEGACY"}


def _text(value: Any, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    return value.strip()


def evaluate_mandate_revocation_observation(
    *,
    mandate: Mapping[str, Any],
    observation: Mapping[str, Any] | None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Require a fresh, identity-matched ACTIVE observation; otherwise block."""
    if not isinstance(mandate, Mapping):
        raise ValueError("MANDATE_REVOCATION_MANDATE_INVALID")
    if not isinstance(observation, Mapping):
        raise ValueError("MANDATE_REVOCATION_OBSERVATION_MISSING")

    mandate_id = _text(
        mandate.get("mandate_id") or mandate.get("authorization_id"),
        "MANDATE_REVOCATION_MANDATE_ID_INVALID",
    )
    observed_mandate_id = _text(
        observation.get("mandate_id"), "MANDATE_REVOCATION_IDENTITY_INVALID"
    )
    if observed_mandate_id != mandate_id:
        raise ValueError("MANDATE_REVOCATION_IDENTITY_MISMATCH")

    status = _text(observation.get("status"), "MANDATE_REVOCATION_STATUS_INVALID").upper()
    if status not in _VALID_STATUSES:
        raise ValueError("MANDATE_REVOCATION_STATUS_INVALID")
    if status == REVOKED:
        raise ValueError("MANDATE_REVOKED")

    source = _text(observation.get("source"), "MANDATE_REVOCATION_SOURCE_INVALID")
    if source.upper() in _FORBIDDEN_SOURCES:
        raise ValueError("MANDATE_REVOCATION_SOURCE_INVALID")
    _text(observation.get("record_id"), "MANDATE_REVOCATION_RECORD_ID_INVALID")
    _text(
        observation.get("freshness_policy_id"),
        "MANDATE_REVOCATION_FRESHNESS_POLICY_INVALID",
    )

    raw_time = _text(
        observation.get("observed_at"), "MANDATE_REVOCATION_TIMESTAMP_INVALID"
    )
    try:
        observed_at = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("MANDATE_REVOCATION_TIMESTAMP_INVALID") from exc
    if observed_at.tzinfo is None or observed_at.utcoffset() is None:
        raise ValueError("MANDATE_REVOCATION_TIMESTAMP_INVALID")
    observed_at = observed_at.astimezone(timezone.utc)

    max_age = observation.get("max_age_seconds")
    if (
        not isinstance(max_age, (int, float))
        or isinstance(max_age, bool)
        or not math.isfinite(float(max_age))
        or float(max_age) <= 0
    ):
        raise ValueError("MANDATE_REVOCATION_MAX_AGE_INVALID")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None or current.utcoffset() is None:
        raise ValueError("MANDATE_REVOCATION_CLOCK_INVALID")
    age = (current.astimezone(timezone.utc) - observed_at).total_seconds()
    if age < 0:
        raise ValueError("MANDATE_REVOCATION_TIMESTAMP_IN_FUTURE")
    if age > float(max_age):
        raise ValueError("MANDATE_REVOCATION_OBSERVATION_STALE")

    return {
        "revocation_state": ACTIVE,
        "mandate_id": mandate_id,
        "source": source,
        "record_id": observation["record_id"].strip(),
        "observed_at": observed_at.isoformat(),
        "freshness_policy_id": observation["freshness_policy_id"].strip(),
    }


__all__ = ["ACTIVE", "REVOKED", "evaluate_mandate_revocation_observation"]
