"""CP40 provider-neutral sealed Decision input contract."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
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
    "decision_input_state",
    "decision_input_validation",
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
    "order_intent",
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

_FORBIDDEN_PROVENANCE = {"TEST", "LEGACY", "SIMULATED"}


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _parse_aware_timestamp(value: Any) -> datetime:
    if not _nonempty_text(value):
        raise ValueError("DECISION_INPUT_INVALID")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("DECISION_INPUT_INVALID") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("DECISION_INPUT_INVALID")
    return parsed


def validate_sealed_decision_input(
    decision_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and return the canonical sealed input without mutation."""
    if not isinstance(decision_input, Mapping):
        raise ValueError("DECISION_INPUT_INVALID")

    if "exchange" in decision_input:
        raise ValueError("DECISION_PROVIDER_COUPLING")

    if _FORBIDDEN_EXECUTION_FIELDS.intersection(decision_input):
        raise ValueError("DECISION_EXECUTION_SURFACE")

    if set(decision_input) != set(_REQUIRED_FIELDS):
        raise ValueError("DECISION_INPUT_INVALID")

    if decision_input.get("readiness_state") != "READY":
        raise ValueError("DECISION_INPUT_INVALID")
    if decision_input.get("readiness_validation") != "VALID":
        raise ValueError("DECISION_INPUT_INVALID")
    if decision_input.get("decision_input_state") != "READY":
        raise ValueError("DECISION_INPUT_INVALID")
    if decision_input.get("decision_input_validation") != "VALID":
        raise ValueError("DECISION_INPUT_INVALID")

    source = decision_input.get("readiness_source")
    provenance = decision_input.get("provenance")
    if not _nonempty_text(source) or not _nonempty_text(provenance):
        raise ValueError("DECISION_INPUT_INVALID")

    if source.strip().upper() in _FORBIDDEN_PROVENANCE or provenance.strip().upper() in _FORBIDDEN_PROVENANCE:
        raise ValueError("DECISION_INPUT_PROVENANCE_INVALID")

    if not _nonempty_text(decision_input.get("asset")):
        raise ValueError("DECISION_INPUT_INVALID")

    for field in _REQUIRED_VALIDATIONS:
        if decision_input.get(field) != "VALID":
            raise ValueError("DECISION_INPUT_INVALID")

    _parse_aware_timestamp(decision_input.get("observed_at"))

    return {field: decision_input[field] for field in _REQUIRED_FIELDS}


__all__ = ["validate_sealed_decision_input"]
