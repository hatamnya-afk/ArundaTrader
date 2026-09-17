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
    "readiness_state", "readiness_validation", "asset", "direction",
    "entry_price", "stop_price", "stop_distance", "quantity",
    "exposure", "risk_state", "trade_gate_state", "policy_version",
    "provenance", "observed_at", "provider_binding",
}


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _positive(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(value) and value > 0


def _reject_surface(data):
    if (_FORBIDDEN_EXECUTION_FIELDS | _FORBIDDEN_ACCOUNT_FIELDS).intersection(data.keys()):
        raise ValueError("forbidden execution/account field")


def build_execution_ready_package(readiness):
    if not isinstance(readiness, Mapping):
        raise TypeError("readiness must be a Mapping")

    _reject_surface(readiness)

    missing = _REQUIRED_FIELDS - set(readiness.keys())
    if missing:
        raise ValueError("missing required field")

    if readiness["readiness_state"] != "PRE_EXECUTION_READY":
        raise ValueError("invalid readiness state")
    if readiness["readiness_validation"] != "VALID":
        raise ValueError("invalid readiness validation")
    if readiness["risk_state"] != "APPROVED":
        raise ValueError("risk state must be APPROVED")
    if readiness["trade_gate_state"] != "APPROVED":
        raise ValueError("trade gate state must be APPROVED")
    if readiness["provider_binding"] != "DEFERRED":
        raise ValueError("provider binding must be DEFERRED")

    if not _text(readiness["asset"]):
        raise ValueError("asset is required")
    if readiness["direction"] not in _ALLOWED_DIRECTIONS:
        raise ValueError("invalid direction")
    if not _text(readiness["provenance"]):
        raise ValueError("provenance is required")
    if readiness["provenance"].upper() in _FORBIDDEN_PROVENANCE:
        raise ValueError("forbidden provenance")
    if not _text(readiness["policy_version"]):
        raise ValueError("policy version is required")
    if not _text(readiness["observed_at"]):
        raise ValueError("observed_at is required")

    for field in ("entry_price", "stop_price", "stop_distance", "quantity", "exposure"):
        if not _positive(readiness[field]):
            raise ValueError(f"invalid numeric field: {field}")

    entry = readiness["entry_price"]
    stop = readiness["stop_price"]
    distance = readiness["stop_distance"]

    if abs(entry - stop) != distance:
        raise ValueError("stop distance mismatch")
    if readiness["direction"] == "LONG" and not stop < entry:
        raise ValueError("invalid LONG stop")
    if readiness["direction"] == "SHORT" and not stop > entry:
        raise ValueError("invalid SHORT stop")

    return {
        "package_state": "EXECUTION_READY_PACKAGE",
        "package_validation": "VALID",
        "execution_authorized": False,
        "execution_submitted": False,
        "provider_binding": "DEFERRED",
        "asset": readiness["asset"],
        "direction": readiness["direction"],
        "entry_price": readiness["entry_price"],
        "stop_price": readiness["stop_price"],
        "stop_distance": readiness["stop_distance"],
        "quantity": readiness["quantity"],
        "exposure": readiness["exposure"],
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": readiness["policy_version"],
        "provenance": readiness["provenance"],
        "observed_at": readiness["observed_at"],
    }
