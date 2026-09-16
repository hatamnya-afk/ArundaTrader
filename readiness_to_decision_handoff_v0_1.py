"""CP39 provider-neutral readiness-to-decision handoff boundary."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_REQUIRED_FIELDS = (
    "readiness_state",
    "readiness_validation",
    "readiness_source",
    "provenance",
    "asset",
    "capital_validation",
    "portfolio_validation",
    "stop_risk_policy_validation",
    "liquidity_validation",
    "execution_validation",
    "observed_at",
)

_REQUIRED_VALIDATIONS = (
    "capital_validation",
    "portfolio_validation",
    "stop_risk_policy_validation",
    "liquidity_validation",
    "execution_validation",
)

_FORBIDDEN_EXECUTION_FIELDS = {
    "order_id",
    "exchange_client",
    "api_request",
    "signature",
    "submitted",
    "trade_id",
    "withdrawal",
    "order_write",
    "execution_authorization",
    "execution_enabled",
}


def _text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def handoff_readiness_to_decision(
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    """Hand a sealed readiness state to the decision boundary.

    This is a logical provider-neutral handoff only. It performs no provider
    call, database mutation, order creation, execution, or authorization.
    """
    if not isinstance(readiness, Mapping):
        raise ValueError("READINESS_TO_DECISION_HANDOFF_INVALID")

    if "exchange" in readiness:
        raise ValueError("READINESS_PROVIDER_COUPLING")

    if _FORBIDDEN_EXECUTION_FIELDS.intersection(readiness):
        raise ValueError("READINESS_EXECUTION_SURFACE")

    if set(readiness) != set(_REQUIRED_FIELDS):
        raise ValueError("READINESS_TO_DECISION_HANDOFF_INVALID")

    if readiness.get("readiness_state") != "READY":
        raise ValueError("READINESS_TO_DECISION_HANDOFF_INVALID")

    if readiness.get("readiness_validation") != "VALID":
        raise ValueError("READINESS_TO_DECISION_HANDOFF_INVALID")

    for field in _REQUIRED_VALIDATIONS:
        if readiness.get(field) != "VALID":
            raise ValueError("READINESS_TO_DECISION_HANDOFF_INVALID")

    for field in ("readiness_source", "provenance", "asset", "observed_at"):
        if _text(readiness.get(field)) is None:
            raise ValueError("READINESS_TO_DECISION_HANDOFF_INVALID")

    handed_off = {field: readiness[field] for field in _REQUIRED_FIELDS}
    handed_off["decision_input_state"] = "READY"
    handed_off["decision_input_validation"] = "VALID"
    return handed_off


__all__ = ["handoff_readiness_to_decision"]
