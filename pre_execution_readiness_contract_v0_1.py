"""CP39 pre-execution readiness source contract.

Provider-neutral, read-only logical readiness boundary for determining
whether all required production-bound observations are complete and valid.

No API, DB, order, execution, pipeline, or provider coupling.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


_FORBIDDEN_SOURCES = {"TEST", "LEGACY", "SIMULATED"}

_FORBIDDEN_OUTPUT_FIELDS = {
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

_REQUIRED_VALIDATIONS = (
    "capital_validation",
    "portfolio_validation",
    "stop_risk_policy_validation",
    "liquidity_validation",
    "execution_validation",
)


def _text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value


def validate_pre_execution_readiness(
    readiness: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate an explicit provider-neutral pre-execution readiness state."""

    if not isinstance(readiness, Mapping):
        raise ValueError("READINESS_INPUT_INVALID")

    if readiness.get("readiness_state") != "READY":
        raise ValueError("READINESS_STATE_INVALID")

    if readiness.get("readiness_validation") != "VALID":
        raise ValueError("READINESS_VALIDATION_INVALID")

    readiness_source = _text(readiness.get("readiness_source"))
    if readiness_source is None or readiness_source in _FORBIDDEN_SOURCES:
        raise ValueError("READINESS_SOURCE_INVALID")

    provenance = _text(readiness.get("provenance"))
    asset = _text(readiness.get("asset"))
    observed_at = _text(readiness.get("observed_at"))

    if any(value is None for value in (provenance, asset, observed_at)):
        raise ValueError("READINESS_METADATA_INVALID")

    for field in _REQUIRED_VALIDATIONS:
        if readiness.get(field) != "VALID":
            raise ValueError("REQUIRED_OBSERVATION_INVALID")

    if "exchange" in readiness:
        raise ValueError("READINESS_PROVIDER_COUPLING")

    result = {
        "readiness_state": "READY",
        "readiness_validation": "VALID",
        "readiness_source": readiness_source,
        "provenance": provenance,
        "asset": asset,
        "capital_validation": "VALID",
        "portfolio_validation": "VALID",
        "stop_risk_policy_validation": "VALID",
        "liquidity_validation": "VALID",
        "execution_validation": "VALID",
        "observed_at": observed_at,
    }

    if not _FORBIDDEN_OUTPUT_FIELDS.isdisjoint(result):
        raise ValueError("READINESS_EXECUTION_SURFACE")

    return result


__all__ = ["validate_pre_execution_readiness"]