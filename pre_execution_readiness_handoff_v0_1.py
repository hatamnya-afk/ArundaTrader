"""CP39 provider-neutral pre-execution readiness handoff contract."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_REQUIRED_VALIDATIONS = (
    "capital_validation",
    "portfolio_validation",
    "stop_risk_policy_validation",
    "liquidity_validation",
    "execution_validation",
)

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


def handoff_pre_execution_readiness(
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and hand off a complete provider-neutral readiness state.

    This boundary performs validation only. It does not call an exchange,
    mutate a database, create or submit an order, or authorize execution.
    """
    if not isinstance(readiness, Mapping):
        raise ValueError("READINESS_INPUT_INVALID")

    if readiness.get("readiness_state") != "READY":
        raise ValueError("READINESS_HANDOFF_INVALID")

    if readiness.get("readiness_validation") != "VALID":
        raise ValueError("READINESS_HANDOFF_INVALID")

    for field in _REQUIRED_FIELDS[2:]:
        if field not in readiness:
            raise ValueError("READINESS_HANDOFF_INVALID")

    for field in _REQUIRED_VALIDATIONS:
        if readiness.get(field) != "VALID":
            raise ValueError("READINESS_HANDOFF_INVALID")

    for field in ("readiness_source", "provenance", "asset", "observed_at"):
        if _text(readiness.get(field)) is None:
            raise ValueError("READINESS_HANDOFF_INVALID")

    if "exchange" in readiness:
        raise ValueError("READINESS_PROVIDER_COUPLING")

    if _FORBIDDEN_EXECUTION_FIELDS.intersection(readiness):
        raise ValueError("READINESS_EXECUTION_SURFACE")

    return {field: readiness[field] for field in _REQUIRED_FIELDS}


__all__ = ["handoff_pre_execution_readiness"]
