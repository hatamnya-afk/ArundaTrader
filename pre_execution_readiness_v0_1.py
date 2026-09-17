"""CP43 provider-neutral Trade Intent -> Pre-Execution Ready boundary.

Validation/sealing only. This module does not calculate, infer, repair,
authorize, submit, or execute trades and has no exchange/API/DB dependency.
"""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

_FORBIDDEN = {
    "order_id", "order_intent", "exchange", "exchange_client", "api_request",
    "signature", "submitted", "trade_id", "withdrawal", "order_write",
    "execution_authorization", "execution_enabled", "capital", "balance",
    "available_balance", "account_balance",
}
_FORBIDDEN_PROVENANCE = {"TEST", "LEGACY", "SIMULATED"}


def _text(value: Any, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    return value.strip()


def _positive(value: Any, reason: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(reason)
    number = float(value)
    if not isfinite(number) or number <= 0:
        raise ValueError(reason)
    return number


def certify_pre_execution_ready(trade_intent: Mapping[str, Any]) -> dict[str, Any]:
    """Certify a complete validated Trade Intent for pre-execution handoff.

    The returned certificate is an execution-neutral readiness artifact. It
    intentionally carries no account/balance/capital, exchange, API, order,
    authorization, signature, or execution fields.
    """
    if not isinstance(trade_intent, Mapping):
        raise ValueError("PRE_EXECUTION_INPUT_INVALID")
    if _FORBIDDEN.intersection(trade_intent):
        raise ValueError("PRE_EXECUTION_EXECUTION_SURFACE")

    required = (
        "decision_state", "decision_validation", "decision_reason", "asset",
        "direction", "entry_price", "stop_price", "stop_distance", "quantity",
        "exposure", "risk_state", "trade_gate_state", "policy_version",
        "provenance", "observed_at",
    )
    if any(field not in trade_intent for field in required):
        raise ValueError("PRE_EXECUTION_REQUIRED_FIELD_MISSING")

    if trade_intent["decision_state"] != "READY" or trade_intent["decision_validation"] != "VALID":
        raise ValueError("PRE_EXECUTION_DECISION_INVALID")
    if trade_intent["risk_state"] != "APPROVED":
        raise ValueError("PRE_EXECUTION_RISK_NOT_APPROVED")
    if trade_intent["trade_gate_state"] != "APPROVED":
        raise ValueError("PRE_EXECUTION_GATE_NOT_APPROVED")

    asset = _text(trade_intent["asset"], "PRE_EXECUTION_ASSET_INVALID")
    direction = trade_intent["direction"]
    if direction not in {"LONG", "SHORT"}:
        raise ValueError("PRE_EXECUTION_DIRECTION_INVALID")
    provenance = _text(trade_intent["provenance"], "PRE_EXECUTION_PROVENANCE_INVALID")
    if provenance.upper() in _FORBIDDEN_PROVENANCE:
        raise ValueError("PRE_EXECUTION_PROVENANCE_INVALID")
    observed_at = _text(trade_intent["observed_at"], "PRE_EXECUTION_TIMESTAMP_INVALID")
    policy_version = _text(trade_intent["policy_version"], "PRE_EXECUTION_POLICY_INVALID")
    decision_reason = _text(trade_intent["decision_reason"], "PRE_EXECUTION_REASON_INVALID")

    entry = _positive(trade_intent["entry_price"], "PRE_EXECUTION_ENTRY_INVALID")
    stop = _positive(trade_intent["stop_price"], "PRE_EXECUTION_STOP_INVALID")
    distance = _positive(trade_intent["stop_distance"], "PRE_EXECUTION_DISTANCE_INVALID")
    quantity = _positive(trade_intent["quantity"], "PRE_EXECUTION_QUANTITY_INVALID")
    exposure = _positive(trade_intent["exposure"], "PRE_EXECUTION_EXPOSURE_INVALID")

    if distance != abs(entry - stop):
        raise ValueError("PRE_EXECUTION_STOP_DISTANCE_INVALID")
    if direction == "LONG" and stop >= entry:
        raise ValueError("PRE_EXECUTION_STOP_DIRECTION_INVALID")
    if direction == "SHORT" and stop <= entry:
        raise ValueError("PRE_EXECUTION_STOP_DIRECTION_INVALID")

    return {
        "readiness_state": "PRE_EXECUTION_READY",
        "readiness_validation": "VALID",
        "asset": asset,
        "direction": direction,
        "entry_price": entry,
        "stop_price": stop,
        "stop_distance": distance,
        "quantity": quantity,
        "exposure": exposure,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "decision_state": "READY",
        "decision_validation": "VALID",
        "decision_reason": decision_reason,
        "policy_version": policy_version,
        "provenance": provenance,
        "observed_at": observed_at,
    }


__all__ = ["certify_pre_execution_ready"]
