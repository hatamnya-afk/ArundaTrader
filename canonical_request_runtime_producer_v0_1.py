"""Build canonical requests only from already-produced Decision/Risk/Trade-Gate records.

No sizing, identity invention, timestamp creation, price inference, or state
recomputation occurs here. Missing upstream fields cause a per-asset block.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from exchange_execution_contract import CanonicalOrderRequest, build_order_request, validate_order_request
from execution_ready_package_v0_1 import build_execution_ready_package


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
) -> dict[str, dict[str, Any]]:
    """Return requests/context only where the existing outputs are complete and aligned.

    Records are read-only inputs. A request is emitted only when an upstream
    OrderIntent identity (intent_id) and Decision-Birth identity already exist.
    """
    if not all(isinstance(x, Mapping) for x in (decision_snapshot, risk_snapshot, trade_gate_snapshot)):
        raise ValueError("RUNTIME_OUTPUT_SNAPSHOTS_INVALID")
    if not (set(decision_snapshot) == set(risk_snapshot) == set(trade_gate_snapshot)):
        raise ValueError("RUNTIME_OUTPUT_ASSET_COVERAGE_MISMATCH")

    result: dict[str, dict[str, Any]] = {}
    for raw_asset, decision in decision_snapshot.items():
        asset = str(raw_asset).strip().upper()
        risk = risk_snapshot[raw_asset]
        gate = trade_gate_snapshot[raw_asset]
        if not all(isinstance(x, Mapping) for x in (decision, risk, gate)):
            continue
        if gate.get("trade_gate_state") != "TRADE_READY":
            continue

        # Do not manufacture an OrderIntent. This stage only consumes an
        # upstream-issued intent identity if that producer has actually emitted one.
        intent_id = _required(decision, "intent_id", "ORDER_INTENT_IDENTITY_MISSING")
        decision_id = _required(decision, "decision_id", "DECISION_BIRTH_IDENTITY_MISSING")
        snapshot_id = _required(decision, "snapshot_id", "DECISION_SNAPSHOT_ID_MISSING")
        timestamp = _required(decision, "timestamp", "DECISION_TIMESTAMP_MISSING")
        direction = _required(decision, "direction", "DECISION_DIRECTION_MISSING")
        entry_price = _required(decision, "entry_price", "DECISION_ENTRY_PRICE_MISSING")

        if risk.get("risk_status") != "APPROVED":
            raise ValueError(f"RISK_NOT_APPROVED:{asset}")
        quantity = _required(risk, "position_quantity", "RISK_POSITION_QUANTITY_MISSING")
        for field in ("quantity_unit", "quantity_source"):
            _required(risk, field, f"RISK_{field.upper()}_MISSING")
        if risk["quantity_unit"] != "BASE_ASSET":
            raise ValueError(f"RISK_QUANTITY_UNIT_INVALID:{asset}")
        if risk["quantity_source"] != "RISK.position_quantity":
            raise ValueError(f"RISK_QUANTITY_SOURCE_INVALID:{asset}")

        request = build_order_request(
            asset=asset,
            direction=direction,
            order_type="MARKET",
            risk=risk,
            entry_price=entry_price,
            reference_price=decision.get("reference_price"),
            intent_id=intent_id,
            snapshot_id=snapshot_id,
            timestamp=timestamp,
            decision_id=decision_id,
        )
        valid, reason = validate_order_request(request)
        if not valid:
            raise ValueError(f"CANONICAL_REQUEST_INVALID:{asset}:{reason}")

        # The package is made only from fields already present in the upstream
        # records. No stop, exposure, policy, provenance or timestamp is inferred.
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
            "execution_ready_package": package,
            "decision_id": decision_id,
            "intent_id": intent_id,
            "snapshot_id": snapshot_id,
            "timestamp": timestamp,
            "venue": decision.get("venue"),
            "execution_instrument": decision.get("execution_instrument"),
        }
    return result


__all__ = ["produce_canonical_requests_from_runtime_outputs"]
