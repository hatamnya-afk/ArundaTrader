"""ARUNDA TRADER — EXPLICIT MANAGEMENT AUTHORIZATION CONTRACT v0.1.

Pure management-decision boundary for one future real provider order attempt.

This module does not execute, submit, sign, prepare, mutate a database, contact
a provider, or enable the production pipeline. It validates a separately
recorded management decision and, only when explicitly AUTHORIZED, produces
the bounded authorization observation consumed by the existing execution
authorization boundary.

Management authorization remains distinct from technical readiness.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

AUTHORIZED = "AUTHORIZED"
DENIED = "DENIED"
REAL_PRODUCTION = "REAL_PRODUCTION"

_REQUIRED_SCOPE = (
    "venue",
    "execution_instrument",
    "asset",
    "direction",
    "order_type",
    "quantity",
    "max_exposure",
)


def _text(value: Any, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    return value.strip()


def _positive(value: Any, reason: str) -> float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value <= 0
    ):
        raise ValueError(reason)
    return float(value)


def _parse_aware(value: Any, reason: str) -> datetime:
    raw = _text(value, reason)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(reason) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(reason)
    return parsed.astimezone(timezone.utc)


def _evidence_list(value: Any, reason: str) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(reason)

    result = []
    for item in value:
        result.append(_text(item, reason))

    if not result:
        raise ValueError(reason)

    return result


def evaluate_management_authorization(
    management_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one explicit management decision for one bounded attempt."""

    if not isinstance(management_observation, Mapping):
        raise ValueError("MANAGEMENT_AUTHORIZATION_INPUT_INVALID")

    decision = _text(
        management_observation.get("decision"),
        "MANAGEMENT_DECISION_INVALID",
    ).upper()

    if decision not in {AUTHORIZED, DENIED}:
        raise ValueError("MANAGEMENT_DECISION_INVALID")

    authorization_id = _text(
        management_observation.get("authorization_id"),
        "MANAGEMENT_AUTHORIZATION_ID_INVALID",
    )
    attempt_id = _text(
        management_observation.get("attempt_id"),
        "MANAGEMENT_ATTEMPT_ID_INVALID",
    )
    actor = _text(
        management_observation.get("authorized_by"),
        "MANAGEMENT_AUTHORIZER_INVALID",
    )
    source = _text(
        management_observation.get("authorization_source"),
        "MANAGEMENT_AUTHORIZATION_SOURCE_INVALID",
    )

    environment = _text(
        management_observation.get("environment"),
        "MANAGEMENT_ENVIRONMENT_INVALID",
    ).upper()
    if environment != REAL_PRODUCTION:
        raise ValueError("MANAGEMENT_ENVIRONMENT_INVALID")

    issued_at = _parse_aware(
        management_observation.get("issued_at"),
        "MANAGEMENT_ISSUED_AT_INVALID",
    )
    expires_at = _parse_aware(
        management_observation.get("expires_at"),
        "MANAGEMENT_EXPIRY_INVALID",
    )

    now = datetime.now(timezone.utc)
    if expires_at <= now:
        raise ValueError("MANAGEMENT_AUTHORIZATION_EXPIRED")
    if expires_at <= issued_at:
        raise ValueError("MANAGEMENT_EXPIRY_BEFORE_ISSUANCE")

    scope = management_observation.get("authorization_scope")
    if not isinstance(scope, Mapping):
        raise ValueError("MANAGEMENT_SCOPE_INVALID")

    normalized_scope: dict[str, Any] = {}
    for key in _REQUIRED_SCOPE:
        if key not in scope:
            raise ValueError(f"MANAGEMENT_SCOPE_{key.upper()}_MISSING")
        normalized_scope[key] = scope[key]

    for key in (
        "venue",
        "execution_instrument",
        "asset",
        "direction",
        "order_type",
    ):
        normalized_scope[key] = _text(
            normalized_scope[key],
            f"MANAGEMENT_SCOPE_{key.upper()}_INVALID",
        )

    normalized_scope["quantity"] = _positive(
        normalized_scope["quantity"],
        "MANAGEMENT_SCOPE_QUANTITY_INVALID",
    )
    normalized_scope["max_exposure"] = _positive(
        normalized_scope["max_exposure"],
        "MANAGEMENT_SCOPE_MAX_EXPOSURE_INVALID",
    )

    evidence_before = _evidence_list(
        management_observation.get("evidence_required_before"),
        "MANAGEMENT_EVIDENCE_BEFORE_INVALID",
    )
    evidence_after = _evidence_list(
        management_observation.get("evidence_required_after"),
        "MANAGEMENT_EVIDENCE_AFTER_INVALID",
    )

    result = {
        "management_state": decision,
        "management_authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "authorized_by": actor,
        "authorization_source": source,
        "environment": environment,
        "issued_at": issued_at.isoformat(),
        "expires_at": expires_at.isoformat(),
        "authorization_scope": normalized_scope,
        "evidence_required_before": evidence_before,
        "evidence_required_after": evidence_after,
        "execution_authorization": False,
    }

    if decision == DENIED:
        result["authorization_observation"] = None
        return result

    result["authorization_observation"] = {
        "execution_authorization": "AUTHORIZED",
        "authorization_validation": "VALID",
        "authorization_source": source,
        "authorization_id": authorization_id,
        "attempt_id": attempt_id,
        "expires_at": expires_at.isoformat(),
        "authorization_scope": normalized_scope,
    }
    return result


__all__ = [
    "AUTHORIZED",
    "DENIED",
    "REAL_PRODUCTION",
    "evaluate_management_authorization",
]
