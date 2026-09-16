"""CP39 provider-neutral pre-execution readiness boundary seal."""

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


def seal_pre_execution_readiness(
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    """Seal a certified provider-neutral pre-execution readiness boundary.

    The seal is a logical contract boundary only. It performs no provider
    call, database mutation, order creation, or execution authorization.
    """
    if not isinstance(readiness, Mapping):
        raise ValueError("READINESS_INPUT_INVALID")

    if "exchange" in readiness:
        raise ValueError("READINESS_PROVIDER_COUPLING")

    if _FORBIDDEN_EXECUTION_FIELDS.intersection(readiness):
        raise ValueError("READINESS_EXECUTION_SURFACE")

    if set(readiness) != set(_REQUIRED_FIELDS):
        raise ValueError("READINESS_BOUNDARY_SEAL_INVALID")

    if readiness.get("readiness_state") != "READY":
        raise ValueError("READINESS_BOUNDARY_SEAL_INVALID")

    if readiness.get("readiness_validation") != "VALID":
        raise ValueError("READINESS_BOUNDARY_SEAL_INVALID")

    for field in _REQUIRED_VALIDATIONS:
        if readiness.get(field) != "VALID":
            raise ValueError("READINESS_BOUNDARY_SEAL_INVALID")

    for field in ("readiness_source", "provenance", "asset", "observed_at"):
        if _text(readiness.get(field)) is None:
            raise ValueError("READINESS_BOUNDARY_SEAL_INVALID")

    return {field: readiness[field] for field in _REQUIRED_FIELDS}


__all__ = ["seal_pre_execution_readiness"]
