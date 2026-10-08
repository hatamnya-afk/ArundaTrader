"""ARUNDA TRADER — REAL-PRODUCTION PHASE-ENTRY MANAGEMENT MANDATE v0.2.

This module is the single management boundary for entering the first
real-production trading phase.

Management authorization is a ONE-TIME PHASE-ENTRY MANDATE.
It is NOT a per-trade approval and this module never receives or requires an
individual order-attempt identity.

After phase entry is explicitly AUTHORIZED, the trader operates autonomously
inside the existing Spot/Futures decision, risk, trade-gate, readiness, and
execution contracts. Provider acceptance/rejection remains authoritative.

This module does not execute, submit, sign, prepare, mutate a database,
contact a provider, or enable the production pipeline.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

AUTHORIZED = "AUTHORIZED"
DENIED = "DENIED"
DEFERRED = "DEFERRED"
REAL_PRODUCTION = "REAL_PRODUCTION"
STANDING_MANDATE = "STANDING_MANDATE"

_REQUIRED_MARKETS = frozenset({"SPOT", "FUTURES"})

# Management is intentionally a closed-schema boundary. New fields must be
# explicitly classified as management scope before they can enter this API.
_ALLOWED_MANAGEMENT_FIELDS = frozenset(
    {
        "decision",
        "mandate_id",
        "authorized_by",
        "authorization_source",
        "environment",
        "issued_at",
        "expires_at",
        "allowed_markets",
        "provider",
        "capital_policy",
        "evidence_required_before",
        "evidence_required_after",
    }
)

_KNOWN_TRADE_SCOPE_FIELDS = frozenset(
    {
        "attempt_id",
        "attemptId",
        "trade_id",
        "tradeId",
        "asset",
        "symbol",
        "direction",
        "side",
        "order_type",
        "orderType",
        "quantity",
        "qty",
        "per_order_exposure",
        "exposure",
        "exposure_usd",
    }
)


def _text(value: Any, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    return value.strip()


def _parse_aware(value: Any, reason: str) -> datetime:
    raw = _text(value, reason)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(reason) from exc

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(reason)
    return parsed.astimezone(timezone.utc)


def _evidence_list(value: Any, reason: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(reason)

    result = tuple(_text(item, reason) for item in value)
    if not result:
        raise ValueError(reason)
    return result


def _markets(value: Any) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("MANAGEMENT_ALLOWED_MARKETS_INVALID")

    result = tuple(dict.fromkeys(_text(item, "MANAGEMENT_ALLOWED_MARKET_INVALID").upper() for item in value))
    if set(result) != _REQUIRED_MARKETS:
        raise ValueError("MANAGEMENT_SPOT_FUTURES_SCOPE_INVALID")
    return result


def evaluate_management_phase_entry(
    management_observation: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate the single management decision for real-production phase entry."""

    if not isinstance(management_observation, Mapping):
        raise ValueError("MANAGEMENT_PHASE_ENTRY_INPUT_INVALID")

    supplied_fields = frozenset(management_observation.keys())
    unknown_fields = supplied_fields - _ALLOWED_MANAGEMENT_FIELDS
    if unknown_fields:
        if unknown_fields.intersection(_KNOWN_TRADE_SCOPE_FIELDS):
            raise ValueError("MANAGEMENT_TRADE_SCOPE_FIELDS_FORBIDDEN")
        raise ValueError("MANAGEMENT_FIELDS_FORBIDDEN")

    decision = _text(
        management_observation.get("decision"),
        "MANAGEMENT_DECISION_INVALID",
    ).upper()

    if decision not in {AUTHORIZED, DENIED, DEFERRED}:
        raise ValueError("MANAGEMENT_DECISION_INVALID")

    mandate_id = _text(
        management_observation.get("mandate_id"),
        "MANAGEMENT_MANDATE_ID_INVALID",
    )
    actor = _text(
        management_observation.get("authorized_by"),
        "MANAGEMENT_AUTHORIZER_INVALID",
    )
    source = _text(
        management_observation.get("authorization_source"),
        "MANAGEMENT_AUTHORIZATION_SOURCE_INVALID",
    )
    provider = _text(
        management_observation.get("provider"),
        "MANAGEMENT_PROVIDER_INVALID",
    )
    capital_policy = _text(
        management_observation.get("capital_policy"),
        "MANAGEMENT_CAPITAL_POLICY_INVALID",
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
        raise ValueError("MANAGEMENT_MANDATE_EXPIRED")
    if expires_at <= issued_at:
        raise ValueError("MANAGEMENT_EXPIRY_BEFORE_ISSUANCE")

    allowed_markets = _markets(
        management_observation.get("allowed_markets"),
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
        "mandate_id": mandate_id,
        "authorized_by": actor,
        "authorization_source": source,
        "environment": environment,
        "allowed_markets": allowed_markets,
        "provider": provider,
        "capital_policy": capital_policy,
        "evidence_required_before": evidence_before,
        "evidence_required_after": evidence_after,
        "autonomous_operation": decision == AUTHORIZED,
        "per_trade_management_authorization_required": False,
        "provider_acceptance_rejection_is_authoritative": True,
        "execution_authorization": (
            "AUTHORIZED_STANDING_MANDATE" if decision == AUTHORIZED else False
        ),
    }

    if decision == AUTHORIZED:
        result["authorization_observation"] = {
            "execution_authorization": "AUTHORIZED",
            "authorization_validation": "VALID",
            "authorization_source": source,
            "authorization_mode": STANDING_MANDATE,
            "authorization_id": mandate_id,
            "mandate_id": mandate_id,
            "expires_at": expires_at.isoformat(),
            "environment": environment,
            "allowed_markets": allowed_markets,
            "provider": provider,
        }
    else:
        result["authorization_observation"] = None

    return result


# Compatibility alias retained only as a name-level migration aid. It now
# evaluates the phase-entry mandate and cannot represent a per-trade decision.
evaluate_management_authorization = evaluate_management_phase_entry


__all__ = [
    "AUTHORIZED",
    "DENIED",
    "DEFERRED",
    "REAL_PRODUCTION",
    "STANDING_MANDATE",
    "evaluate_management_phase_entry",
    "evaluate_management_authorization",
]
