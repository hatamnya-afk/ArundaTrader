"""CP41 provider-neutral Decision -> Trade Intent boundary.

Boundary/contract/validation only. This module does not calculate, infer,
repair, authorize, submit, or execute an order.
"""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

_ALLOWED_DIRECTIONS = {"LONG", "SHORT"}
_FORBIDDEN_PROVENANCE = {"TEST", "LEGACY", "SIMULATED"}
_FORBIDDEN_EXECUTION_FIELDS = {
    "order_id",
    "order_intent",
    "exchange",
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


def _positive(value: Any, reason: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(reason)
    number = float(value)
    if not isfinite(number) or number <= 0:
        raise ValueError(reason)
    return number


def _text(value: Any, reason: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(reason)
    return value.strip()


def _reject_execution_surface(observation: Mapping[str, Any]) -> None:
    if _FORBIDDEN_EXECUTION_FIELDS.intersection(observation):
        raise ValueError("TRADE_INTENT_EXECUTION_SURFACE")


def build_validated_trade_intent(
    decision_output: Mapping[str, Any],
    trade_gate_output: Mapping[str, Any],
    position_sizing_output: Mapping[str, Any],
    stop_risk_output: Mapping[str, Any],
) -> dict[str, Any]:
    """Build a Trade Intent only from independently validated upstream outputs.

    No value is invented. Decision validity is mandatory, while direction,
    entry, stop, quantity, exposure, risk and policy values are sourced from
    the existing upstream boundaries and cross-checked for semantic identity.
    """
    sources = (
        decision_output,
        trade_gate_output,
        position_sizing_output,
        stop_risk_output,
    )
    if not all(isinstance(source, Mapping) for source in sources):
        raise ValueError("TRADE_INTENT_INPUT_INVALID")
    for source in sources:
        _reject_execution_surface(source)

    if decision_output.get("decision_state") != "READY":
        raise ValueError("DECISION_NOT_READY")
    if decision_output.get("decision_validation") != "VALID":
        raise ValueError("DECISION_INVALID")

    asset = _text(decision_output.get("asset"), "ASSET_INVALID")
    provenance = _text(decision_output.get("provenance"), "PROVENANCE_INVALID")
    if provenance.upper() in _FORBIDDEN_PROVENANCE:
        raise ValueError("PROVENANCE_INVALID")

    gate_asset = _text(trade_gate_output.get("asset"), "ASSET_INVALID")
    sizing_asset = _text(position_sizing_output.get("asset"), "ASSET_INVALID")
    stop_asset = _text(stop_risk_output.get("asset"), "ASSET_INVALID")
    if {asset, gate_asset, sizing_asset, stop_asset} != {asset}:
        raise ValueError("ASSET_MISMATCH")

    if trade_gate_output.get("trade_gate_state") != "APPROVED":
        raise ValueError("TRADE_GATE_NOT_APPROVED")
    if position_sizing_output.get("risk_state") != "APPROVED":
        raise ValueError("RISK_NOT_APPROVED")
    if stop_risk_output.get("observation_state") != "AVAILABLE":
        raise ValueError("STOP_RISK_NOT_AVAILABLE")
    if stop_risk_output.get("observation_validation") != "VALID":
        raise ValueError("STOP_RISK_INVALID")
    if stop_risk_output.get("risk_policy_validation") != "VALID":
        raise ValueError("RISK_POLICY_INVALID")

    stop_provenance = _text(
        stop_risk_output.get("provenance"), "PROVENANCE_INVALID"
    )
    if stop_provenance.upper() in _FORBIDDEN_PROVENANCE:
        raise ValueError("PROVENANCE_INVALID")
    if stop_provenance != provenance:
        raise ValueError("PROVENANCE_MISMATCH")

    direction = trade_gate_output.get("direction")
    if direction not in _ALLOWED_DIRECTIONS:
        raise ValueError("DIRECTION_INVALID")
    if position_sizing_output.get("direction") != direction:
        raise ValueError("DIRECTION_MISMATCH")
    if stop_risk_output.get("direction") != direction:
        raise ValueError("DIRECTION_MISMATCH")

    entry = _positive(trade_gate_output.get("entry_price"), "ENTRY_PRICE_INVALID")
    stop_price = _positive(stop_risk_output.get("stop_price"), "STOP_PRICE_INVALID")
    stop_distance = _positive(
        stop_risk_output.get("stop_distance"), "STOP_DISTANCE_INVALID"
    )
    gate_stop_distance = _positive(
        trade_gate_output.get("stop_distance"), "STOP_DISTANCE_INVALID"
    )
    sizing_entry = _positive(
        position_sizing_output.get("entry_price"), "ENTRY_PRICE_INVALID"
    )
    sizing_stop_distance = _positive(
        position_sizing_output.get("stop_distance"), "STOP_DISTANCE_INVALID"
    )
    if entry != sizing_entry or entry != _positive(stop_risk_output.get("entry_price"), "ENTRY_PRICE_INVALID"):
        raise ValueError("ENTRY_PRICE_MISMATCH")
    if stop_distance != gate_stop_distance or stop_distance != sizing_stop_distance:
        raise ValueError("STOP_DISTANCE_MISMATCH")

    expected_stop_distance = abs(entry - stop_price)
    if stop_distance != expected_stop_distance:
        raise ValueError("STOP_DISTANCE_INVALID")
    if direction == "LONG" and stop_price >= entry:
        raise ValueError("STOP_DIRECTION_INVALID")
    if direction == "SHORT" and stop_price <= entry:
        raise ValueError("STOP_DIRECTION_INVALID")

    quantity = _positive(
        position_sizing_output.get("position_size"), "QUANTITY_INVALID"
    )
    gate_quantity = _positive(trade_gate_output.get("quantity"), "QUANTITY_INVALID")
    if quantity != gate_quantity:
        raise ValueError("QUANTITY_MISMATCH")

    exposure = _positive(
        position_sizing_output.get("exposure"), "EXPOSURE_INVALID"
    )
    gate_exposure = _positive(trade_gate_output.get("exposure"), "EXPOSURE_INVALID")
    if exposure != gate_exposure:
        raise ValueError("EXPOSURE_MISMATCH")

    policy_version = _text(
        trade_gate_output.get("policy_version"), "POLICY_VERSION_INVALID"
    )
    sizing_policy = _text(
        position_sizing_output.get("policy_version"), "POLICY_VERSION_INVALID"
    )
    stop_policy = _text(
        stop_risk_output.get("risk_policy_version"), "POLICY_VERSION_INVALID"
    )
    if len({policy_version, sizing_policy, stop_policy}) != 1:
        raise ValueError("POLICY_VERSION_MISMATCH")

    return {
        "decision_state": "READY",
        "decision_validation": "VALID",
        "decision_reason": _text(
            decision_output.get("decision_reason"), "DECISION_REASON_INVALID"
        ),
        "asset": asset,
        "direction": direction,
        "entry_price": entry,
        "stop_price": stop_price,
        "stop_distance": stop_distance,
        "quantity": quantity,
        "exposure": exposure,
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": policy_version,
        "provenance": provenance,
        "observed_at": _text(
            decision_output.get("observed_at"), "OBSERVED_AT_INVALID"
        ),
    }


__all__ = ["build_validated_trade_intent"]
