"""Build canonical requests only from real Decision/Risk/Gate plus produced OrderIntent records.

No sizing, price inference, timestamp creation, or execution authorization is
performed here. Missing or misaligned upstream records fail closed.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from exchange_execution_contract import build_order_request, validate_order_request
from execution_ready_package_v0_1 import build_execution_ready_package
from execution_instrument_policy_v0_1 import build_execution_instrument_specification
from execution_runtime_policy_source_v0_1 import load_authoritative_execution_runtime_policy


def _required(record: Mapping[str, Any], key: str, code: str) -> Any:
    value = record.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(code)
    return value


def produce_canonical_requests_from_runtime_outputs(
    *,
    decision_snapshot: Mapping[str, Mapping[str, Any]],
    risk_snapshot: Mapping[str, Mapping[str, Any]],
    trade_gate_snapshot: Mapping[str, Mapping[str, Any]],
    order_intents: Mapping[str, Mapping[str, Any]],
    management_observation: Mapping[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    """Consume current-run producer outputs without inventing upstream fields."""
    if not all(isinstance(x, Mapping) for x in (
        decision_snapshot, risk_snapshot, trade_gate_snapshot, order_intents
    )):
        raise ValueError("RUNTIME_OUTPUT_SNAPSHOTS_INVALID")
    if not (set(decision_snapshot) == set(risk_snapshot) == set(trade_gate_snapshot)):
        raise ValueError("RUNTIME_OUTPUT_ASSET_COVERAGE_MISMATCH")
    if not isinstance(management_observation, Mapping):
        raise ValueError("AUTHORITATIVE_MANAGEMENT_MANDATE_SOURCE_MISSING")

    result: dict[str, dict[str, Any]] = {}
    execution_policy = load_authoritative_execution_runtime_policy()
    for raw_asset, decision in decision_snapshot.items():
        asset = str(raw_asset).strip().upper()
        risk = risk_snapshot[raw_asset]
        gate = trade_gate_snapshot[raw_asset]
        if not all(isinstance(x, Mapping) for x in (decision, risk, gate)):
            raise ValueError(f"RUNTIME_OUTPUT_RECORD_INVALID:{asset}")
        if gate.get("trade_gate_state") != "TRADE_READY":
            if asset in order_intents:
                raise ValueError(f"ORDER_INTENT_WITHOUT_TRADE_READY:{asset}")
            continue

        intent = order_intents.get(asset)
        if not isinstance(intent, Mapping):
            raise ValueError(f"AUTHORITATIVE_ORDER_INTENT_MISSING:{asset}")
        intent_id = _required(intent, "intent_id", "ORDER_INTENT_IDENTITY_MISSING")
        decision_id = _required(decision, "decision_id", "DECISION_BIRTH_IDENTITY_MISSING")
        if _required(intent, "decision_id", f"ORDER_INTENT_DECISION_BIRTH_ID_MISSING:{asset}") != decision_id:
            raise ValueError(f"ORDER_INTENT_DECISION_BIRTH_MISMATCH:{asset}")
        snapshot_id = _required(intent, "snapshot_id", "ORDER_INTENT_SNAPSHOT_ID_MISSING")
        timestamp = _required(intent, "timestamp", "ORDER_INTENT_TIMESTAMP_MISSING")
        direction = _required(intent, "direction", "ORDER_INTENT_DIRECTION_MISSING")
        entry_price = _required(intent, "entry_price", "ORDER_INTENT_ENTRY_PRICE_MISSING")

        if risk.get("risk_status") != "APPROVED":
            raise ValueError(f"RISK_NOT_APPROVED:{asset}")
        quantity = _required(risk, "position_quantity", "RISK_POSITION_QUANTITY_MISSING")
        if quantity != _required(intent, "quantity", f"ORDER_INTENT_QUANTITY_MISSING:{asset}"):
            raise ValueError(f"ORDER_INTENT_RISK_QUANTITY_MISMATCH:{asset}")
        if risk.get("quantity_unit") != "BASE_ASSET":
            raise ValueError(f"RISK_QUANTITY_UNIT_INVALID:{asset}")
        if risk.get("quantity_source") != "RISK.position_quantity":
            raise ValueError(f"RISK_QUANTITY_SOURCE_INVALID:{asset}")
        if intent.get("quantity_unit") != risk.get("quantity_unit") or intent.get("quantity_source") != risk.get("quantity_source"):
            raise ValueError(f"ORDER_INTENT_QUANTITY_PROVENANCE_MISMATCH:{asset}")

        request = build_order_request(
            asset=asset,
            direction=direction,
            order_type="MARKET",
            risk=risk,
            entry_price=entry_price,
            reference_price=intent.get("reference_price"),
            intent_id=intent_id,
            snapshot_id=snapshot_id,
            timestamp=timestamp,
            decision_id=decision_id,
        )
        valid, reason = validate_order_request(request)
        if not valid:
            raise ValueError(f"CANONICAL_REQUEST_INVALID:{asset}:{reason}")

        venue = execution_policy["venue"]
        decision_venue = decision.get("venue")
        if decision_venue is not None and str(decision_venue).strip().upper() != venue:
            raise ValueError(f"DECISION_EXECUTION_VENUE_POLICY_MISMATCH:{asset}")
        if venue == "FUTURES" and execution_policy.get("futures_exposure_allowed") is not True:
            raise ValueError(f"FUTURES_EXPOSURE_NOT_EXPLICITLY_ALLOWED:{asset}")
        instrument = build_execution_instrument_specification(asset=asset, venue=venue)
        if venue == "FUTURES":
            from dataclasses import replace
            instrument = replace(
                instrument,
                settlement_asset=execution_policy["settlement_asset"],
                instrument_type=execution_policy["instrument_type"],
                policy_version=execution_policy["policy_version"],
                selection_source="AUTHORITATIVE_DEPLOYMENT_EXECUTION_POLICY",
            )

        readiness = {
            "readiness_state": "PRE_EXECUTION_READY",
            "readiness_validation": "VALID",
            "asset": asset,
            "direction": direction,
            "entry_price": entry_price,
            "stop_price": _required(risk, "stop_price", "RISK_STOP_PRICE_MISSING"),
            "stop_distance": _required(risk, "stop_distance", "RISK_STOP_DISTANCE_MISSING"),
            "quantity": quantity,
            "exposure": _required(risk, "exposure", "RISK_EXPOSURE_MISSING"),
            "risk_state": "APPROVED",
            "trade_gate_state": "APPROVED",
            "policy_version": _required(risk, "policy_version", "RISK_POLICY_VERSION_MISSING"),
            "provenance": _required(risk, "provenance", "RISK_PROVENANCE_MISSING"),
            "observed_at": _required(risk, "observed_at", "RISK_OBSERVED_AT_MISSING"),
            "provider_binding": "DEFERRED",
        }
        package = build_execution_ready_package(readiness)
        result[asset] = {
            "request": request,
            "readiness": readiness,
            "management_observation": dict(management_observation),
            "execution_ready_package": package,
            "decision_id": decision_id,
            "intent_id": intent_id,
            "snapshot_id": snapshot_id,
            "timestamp": timestamp,
            "venue": venue,
            "execution_instrument": instrument,
            "execution_policy_id": execution_policy["policy_id"],
            "execution_policy_version": execution_policy["policy_version"],
            "futures_exposure_allowed": execution_policy.get("futures_exposure_allowed"),
        }
    return result


__all__ = ["produce_canonical_requests_from_runtime_outputs"]
