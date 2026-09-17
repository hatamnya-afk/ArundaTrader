"""CP43 exchange-neutral execution-ready package boundary.

Packages a validated pre-execution certificate for a later exchange adapter.
This artifact does not authorize, submit, sign, or execute anything.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_REQUIRED = {
    "readiness_state", "readiness_validation", "asset", "direction",
    "entry_price", "stop_price", "stop_distance", "quantity", "exposure",
    "risk_state", "trade_gate_state", "decision_state", "decision_validation",
    "decision_reason", "policy_version", "provenance", "observed_at",
}
_FORBIDDEN = {
    "exchange", "exchange_client", "api_request", "signature", "order_id",
    "order_intent", "trade_id", "submitted", "execution_authorization",
    "execution_enabled", "order_write", "withdrawal", "capital", "balance",
    "available_balance", "account_balance",
}


def build_execution_ready_package(pre_execution_certificate: Mapping[str, Any]) -> dict[str, Any]:
    """Create a portable, exchange-neutral handoff package from a valid certificate."""
    if not isinstance(pre_execution_certificate, Mapping):
        raise ValueError("EXECUTION_PACKAGE_INPUT_INVALID")
    if _FORBIDDEN.intersection(pre_execution_certificate):
        raise ValueError("EXECUTION_PACKAGE_FORBIDDEN_SURFACE")
    if not _REQUIRED.issubset(pre_execution_certificate):
        raise ValueError("EXECUTION_PACKAGE_REQUIRED_FIELD_MISSING")
    if pre_execution_certificate["readiness_state"] != "PRE_EXECUTION_READY":
        raise ValueError("EXECUTION_PACKAGE_NOT_READY")
    if pre_execution_certificate["readiness_validation"] != "VALID":
        raise ValueError("EXECUTION_PACKAGE_INVALID")

    # Copy only the certified, provider-neutral fields. No new trading value is generated.
    payload = {key: pre_execution_certificate[key] for key in sorted(_REQUIRED)}
    return {
        "package_state": "EXECUTION_READY_PACKAGE",
        "package_validation": "VALID",
        "execution_authorized": False,
        "execution_submitted": False,
        "provider_binding": "DEFERRED",
        "payload": payload,
    }


__all__ = ["build_execution_ready_package"]
