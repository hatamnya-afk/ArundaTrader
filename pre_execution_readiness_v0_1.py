from math import isfinite
from collections.abc import Mapping

_ALLOWED_DIRECTIONS = {"LONG", "SHORT"}
_FORBIDDEN_PROVENANCE = {"TEST", "LEGACY", "SIMULATED"}
_FORBIDDEN_EXECUTION_FIELDS = {
    "order_id", "order_intent", "exchange", "exchange_client",
    "api_request", "signature", "submitted", "trade_id",
    "withdrawal", "order_write", "execution_authorization",
    "execution_enabled",
}
_FORBIDDEN_ACCOUNT_FIELDS = {
    "account", "account_id", "balance", "available_balance",
    "capital", "wallet",
}
_REQUIRED_FIELDS = {
    "decision_state", "decision_validation", "asset", "direction",
    "entry_price", "stop_price", "stop_distance", "quantity",
    "exposure", "risk_state", "trade_gate_state", "policy_version",
    "provenance", "observed_at",
}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value > 0


def _reject_surface(data):
    forbidden = _FORBIDDEN_EXECUTION_FIELDS | _FORBIDDEN_ACCOUNT_FIELDS
    found = forbidden.intersection(data.keys())
    if found:
        raise ValueError("forbidden execution/account field")


def build_pre_execution_readiness(trade_intent):
    if not isinstance(trade_intent, Mapping):
        raise TypeError("trade_intent must be a Mapping")

    _reject_surface(trade_intent)

    missing = _REQUIRED_FIELDS - set(trade_intent.keys())
    if missing:
        raise ValueError("missing required field")

    if trade_intent["decision_state"] != "READY":
        raise ValueError("decision state must be READY")
    if trade_intent["decision_validation"] != "VALID":
        raise ValueError("decision validation must be VALID")
    if trade_intent["risk_state"] != "APPROVED":
        raise ValueError("risk state must be APPROVED")
    if trade_intent["trade_gate_state"] != "APPROVED":
        raise ValueError("trade gate state must be APPROVED")

    asset = trade_intent["asset"]
    direction = trade_intent["direction"]
    provenance = trade_intent["provenance"]

    if not _text(asset):
        raise ValueError("asset is required")
    if direction not in _ALLOWED_DIRECTIONS:
        raise ValueError("invalid direction")
    if not _text(provenance):
        raise ValueError("provenance is required")
    if provenance.upper() in _FORBIDDEN_PROVENANCE:
        raise ValueError("forbidden provenance")
    if not _text(trade_intent["policy_version"]):
        raise ValueError("policy version is required")
    if not _text(trade_intent["observed_at"]):
        raise ValueError("observed_at is required")

    numeric = (
        "entry_price", "stop_price", "stop_distance",
        "quantity", "exposure",
    )
    for field in numeric:
        if not _positive(trade_intent[field]):
            raise ValueError(f"invalid numeric field: {field}")

    entry = trade_intent["entry_price"]
    stop = trade_intent["stop_price"]
    distance = trade_intent["stop_distance"]

    if abs(entry - stop) != distance:
        raise ValueError("stop distance mismatch")

    if direction == "LONG" and not stop < entry:
        raise ValueError("invalid LONG stop")
    if direction == "SHORT" and not stop > entry:
        raise ValueError("invalid SHORT stop")

    return {
        "readiness_state": "PRE_EXECUTION_READY",
        "readiness_validation": "VALID",
        "asset": asset,
        "direction": direction,
        "entry_price": trade_intent["entry_price"],
        "stop_price": trade_intent["stop_price"],
        "stop_distance": trade_intent["stop_distance"],
        "quantity": trade_intent["quantity"],
        "exposure": trade_intent["exposure"],
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": trade_intent["policy_version"],
        "provenance": provenance,
        "observed_at": trade_intent["observed_at"],
        "provider_binding": "DEFERRED",
    }
