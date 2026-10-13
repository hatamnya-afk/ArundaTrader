"""Runtime handoff from authoritative dynamic gates to the fail-closed execution boundary.

This module creates OrderIntent and CanonicalOrderRequest only from current-cycle
runtime evidence. It never enables execution or contacts a provider.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
import math
from typing import Any

import exchange_execution_contract as contract
from exchange_execution_boundary import execute_order


_APPROVED_RISK = {"ACCEPTED", "APPROVED", "PASS"}
_READY = "TRADE_READY"


def _asset(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("EXECUTION_HANDOFF_ASSET_INVALID")
    return value.strip().upper().split("/", 1)[0]


def _mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(code)
    return value


def _get_risk_rows(risk_snapshot: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows: dict[str, Mapping[str, Any]] = {}
    for raw_asset, raw_row in risk_snapshot.items():
        asset = _asset(str(raw_asset))
        row = _mapping(raw_row, f"EXECUTION_HANDOFF_RISK_ROW_INVALID:{asset}")
        if asset in rows:
            raise ValueError(f"EXECUTION_HANDOFF_DUPLICATE_RISK:{asset}")
        rows[asset] = row
    return rows


def build_order_intents_and_boundary_results(
    *,
    decision_snapshot: Mapping[str, Mapping[str, Any]],
    trade_gate_snapshot: Mapping[str, Mapping[str, Any]],
    risk_snapshot: Mapping[str, Any],
    opportunity_by_asset: Mapping[str, Mapping[str, Any]],
    ready_opportunity_assets: Sequence[str],
    market_data_by_symbol: Mapping[str, Any],
) -> tuple[dict[str, dict[str, Any]], dict[str, contract.CanonicalOrderRequest], dict[str, contract.CanonicalExecutionResult], dict[str, str]]:
    """Build validated intents/requests for TRADE_READY assets, then call the
    exchange-agnostic boundary. With current safety flags, results are blocked;
    this function cannot submit an exchange order.
    """
    if not isinstance(decision_snapshot, Mapping) or not isinstance(trade_gate_snapshot, Mapping):
        raise ValueError("EXECUTION_HANDOFF_RUNTIME_SNAPSHOTS_INVALID")
    if not isinstance(opportunity_by_asset, Mapping):
        raise ValueError("EXECUTION_HANDOFF_OPPORTUNITIES_INVALID")

    decisions = {_asset(str(k)): _mapping(v, f"EXECUTION_HANDOFF_DECISION_INVALID:{k}") for k, v in decision_snapshot.items()}
    gates = {_asset(str(k)): _mapping(v, f"EXECUTION_HANDOFF_GATE_INVALID:{k}") for k, v in trade_gate_snapshot.items()}
    risks = _get_risk_rows(_mapping(risk_snapshot, "EXECUTION_HANDOFF_RISK_SNAPSHOT_INVALID"))
    opportunities = {_asset(str(k)): _mapping(v, f"EXECUTION_HANDOFF_OPPORTUNITY_INVALID:{k}") for k, v in opportunity_by_asset.items()}
    ready_opportunities = {_asset(str(v)) for v in ready_opportunity_assets}

    intents: dict[str, dict[str, Any]] = {}
    requests: dict[str, contract.CanonicalOrderRequest] = {}
    results: dict[str, contract.CanonicalExecutionResult] = {}
    blocked: dict[str, str] = {}

    for asset, gate in gates.items():
        if str(gate.get("trade_gate_state", gate.get("trade_gate_status", ""))).strip().upper() != _READY:
            continue
        try:
            decision = decisions.get(asset)
            if decision is None:
                raise ValueError("DECISION_MISSING")
            decision_id = decision.get("decision_id")
            if not isinstance(decision_id, str) or not decision_id.strip():
                raise ValueError("AUTHORITATIVE_DECISION_ID_MISSING")
            gate_decision_id = gate.get("decision_id")
            if gate_decision_id is not None and gate_decision_id != decision_id:
                raise ValueError("DECISION_ID_LINEAGE_MISMATCH")
            direction = str(gate.get("direction", decision.get("direction", ""))).strip().upper()
            if direction not in contract.VALID_DIRECTIONS:
                raise ValueError("DIRECTION_INVALID")

            opportunity = opportunities.get(asset)
            if opportunity is None or asset not in ready_opportunities:
                raise ValueError("CURRENT_ELIGIBLE_OPPORTUNITY_MISSING")
            price = opportunity.get("price", opportunity.get("entry_price"))
            confidence = opportunity.get("confidence")
            opportunity_timestamp = opportunity.get("timestamp")
            if price is None or confidence is None or not isinstance(opportunity_timestamp, str) or not opportunity_timestamp.strip():
                raise ValueError("OPPORTUNITY_PRICE_CONFIDENCE_TIMESTAMP_MISSING")
            for field_name, numeric_value in (("price", price), ("confidence", confidence)):
                if isinstance(numeric_value, bool) or not isinstance(numeric_value, (int, float)) or not math.isfinite(float(numeric_value)):
                    raise ValueError(f"OPPORTUNITY_{field_name.upper()}_INVALID")
            if float(price) <= 0:
                raise ValueError("OPPORTUNITY_PRICE_NOT_POSITIVE")
            if float(confidence) < 0 or float(confidence) > 1:
                raise ValueError("OPPORTUNITY_CONFIDENCE_OUT_OF_RANGE")

            risk = risks.get(asset)
            if risk is None:
                raise ValueError("RISK_RECORD_MISSING")
            risk_status = str(risk.get("risk_status", risk.get("status", risk.get("decision", "")))).strip().upper()
            if risk_status not in _APPROVED_RISK:
                raise ValueError("RISK_NOT_APPROVED")
            quantity = risk.get("position_quantity")
            if quantity is None:
                raise ValueError("RISK_POSITION_QUANTITY_MISSING")
            if isinstance(quantity, bool) or not isinstance(quantity, (int, float)) or not math.isfinite(float(quantity)):
                raise ValueError("RISK_POSITION_QUANTITY_INVALID")
            if float(quantity) <= 0:
                raise ValueError("RISK_POSITION_QUANTITY_NOT_POSITIVE")
            if risk.get("quantity_unit", contract.QUANTITY_UNIT_BASE_ASSET) != contract.QUANTITY_UNIT_BASE_ASSET:
                raise ValueError("RISK_QUANTITY_UNIT_INVALID")
            if risk.get("quantity_source", contract.QUANTITY_SOURCE_RISK_POSITION) != contract.QUANTITY_SOURCE_RISK_POSITION:
                raise ValueError("RISK_QUANTITY_PROVENANCE_INVALID")
            for flag in ("quantity_changed", "quantity_recomputed", "quantity_rescaled", "quantity_rounded", "quantity_clipped"):
                if risk.get(flag, False) is not False:
                    raise ValueError(f"RISK_QUANTITY_TRANSFORMED:{flag}")

            market_data = market_data_by_symbol.get(f"{asset}/USDT")
            candles = tuple(getattr(market_data, "candles", ()) or ())
            if not candles:
                raise ValueError("CURRENT_MARKET_SNAPSHOT_MISSING")
            last = candles[-1]
            market_ts = last.get("timestamp") if isinstance(last, Mapping) else getattr(last, "timestamp", None)
            source = getattr(market_data, "source", None)
            if not isinstance(market_ts, (int, float)) or not isinstance(source, str) or not source.strip():
                raise ValueError("CURRENT_MARKET_SNAPSHOT_PROVENANCE_INVALID")
            snapshot_id = f"{source.strip()}|{asset}/USDT|1h|{int(market_ts)}"
            regime = decision.get("regime")
            if not isinstance(regime, str) or not regime.strip():
                raise ValueError("DECISION_REGIME_MISSING")

            intent_id = f"OI-{decision_id.strip()}"
            intent = {
                "asset": asset,
                "direction": direction,
                "entry_price": price,
                "confidence": confidence,
                "regime": regime.strip(),
                "timestamp": opportunity_timestamp.strip(),
                "snapshot_id": snapshot_id,
                "intent_id": intent_id,
            }
            required_intent_fields = {
                "asset", "direction", "entry_price", "confidence",
                "regime", "timestamp", "snapshot_id", "intent_id",
            }
            if set(intent) != required_intent_fields:
                raise ValueError("ORDER_INTENT_FIELD_CONTRACT_MISMATCH")
            request = contract.build_order_request(
                asset=asset,
                direction=direction,
                order_type=contract.ORDER_TYPE_MARKET,
                risk=risk,
                entry_price=price,
                reference_price=price,
                intent_id=intent_id,
                snapshot_id=snapshot_id,
                timestamp=opportunity_timestamp.strip(),
                decision_id=decision_id.strip(),
            )
            valid, reason = contract.validate_order_request(request)
            if not valid:
                raise ValueError(f"CANONICAL_REQUEST_INVALID:{reason}")
            if request.quantity != quantity:
                raise ValueError("CANONICAL_QUANTITY_MISMATCH")
            if request.snapshot_id != snapshot_id or request.decision_id != decision_id.strip():
                raise ValueError("CANONICAL_IDENTITY_LINEAGE_MISMATCH")

            intents[asset] = intent
            requests[asset] = request
            # This is a contract-boundary call only. Current contract returns
            # EXECUTION_DISABLED and cannot perform network I/O or submit orders.
            results[asset] = execute_order(request=request, adapter=None)
        except (TypeError, ValueError, AttributeError) as exc:
            blocked[asset] = str(exc) or type(exc).__name__

    return intents, requests, results, blocked
