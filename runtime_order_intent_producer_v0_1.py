"""Create OrderIntent records from authentic current-run Decision/Risk/Gate/Opportunity inputs.

Identity is born here as OI-<authoritative decision_id>. Market snapshot identity
uses the same real candle/source fields as the Decision-Birth boundary. No order
is submitted and no missing upstream field is guessed.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _required(record: Mapping[str, Any], key: str, reason: str) -> Any:
    value = record.get(key)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(reason)
    return value


def _asset_map(values: Mapping[str, Any], name: str) -> dict[str, Any]:
    if not isinstance(values, Mapping):
        raise ValueError(f"{name}_INVALID")
    result: dict[str, Any] = {}
    for raw_key, value in values.items():
        key = str(raw_key).strip().upper()
        if not key or key in result:
            raise ValueError(f"{name}_ASSET_IDENTITY_INVALID")
        result[key] = value
    return result


def _snapshot_id(asset: str, market_data: Any) -> str:
    source = getattr(market_data, "source", None)
    candles = tuple(getattr(market_data, "candles", ()) or ())
    if not isinstance(source, str) or not source.strip():
        raise ValueError(f"ORDER_INTENT_MARKET_SOURCE_MISSING:{asset}")
    if not candles:
        raise ValueError(f"ORDER_INTENT_REAL_CANDLES_MISSING:{asset}")
    last = candles[-1]
    timestamp = last.get("timestamp") if isinstance(last, Mapping) else getattr(last, "timestamp", None)
    if not isinstance(timestamp, (int, float)) or isinstance(timestamp, bool):
        raise ValueError(f"ORDER_INTENT_MARKET_TIMESTAMP_MISSING:{asset}")
    # Same canonical market-snapshot identity convention as Decision Birth.
    return f"{source.strip()}|{asset}/USDT|1h|{int(timestamp)}"


def produce_runtime_order_intents(
    *,
    decision_snapshot: Mapping[str, Mapping[str, Any]],
    risk_snapshot: Mapping[str, Mapping[str, Any]],
    trade_gate_snapshot: Mapping[str, Mapping[str, Any]],
    opportunity_by_asset: Mapping[str, Mapping[str, Any]],
    market_data_by_symbol: Mapping[str, Any],
) -> dict[str, dict[str, Any]]:
    decisions = _asset_map(decision_snapshot, "DECISION_SNAPSHOT")
    risks = _asset_map(risk_snapshot, "RISK_SNAPSHOT")
    gates = _asset_map(trade_gate_snapshot, "TRADE_GATE_SNAPSHOT")
    opportunities = _asset_map(opportunity_by_asset, "OPPORTUNITY_MAP")
    market_data = _asset_map(market_data_by_symbol, "MARKET_DATA_MAP")
    if not (set(decisions) == set(risks) == set(gates)):
        raise ValueError("ORDER_INTENT_RUNTIME_ASSET_COVERAGE_MISMATCH")

    result: dict[str, dict[str, Any]] = {}
    for asset, decision in decisions.items():
        gate = gates[asset]
        if not all(isinstance(row, Mapping) for row in (decision, risks[asset], gate)):
            raise ValueError(f"ORDER_INTENT_RUNTIME_RECORD_INVALID:{asset}")
        if gate.get("trade_gate_state") != "TRADE_READY":
            continue

        opportunity = opportunities.get(asset)
        if not isinstance(opportunity, Mapping):
            raise ValueError(f"ORDER_INTENT_OPPORTUNITY_MISSING:{asset}")
        if str(opportunity.get("status", "")).strip().upper() != "ELIGIBLE":
            raise ValueError(f"ORDER_INTENT_OPPORTUNITY_NOT_ELIGIBLE:{asset}")

        risk = risks[asset]
        if str(risk.get("risk_status", "")).strip().upper() != "APPROVED":
            raise ValueError(f"ORDER_INTENT_RISK_NOT_APPROVED:{asset}")
        quantity = _required(risk, "position_quantity", f"ORDER_INTENT_RISK_QUANTITY_MISSING:{asset}")
        if risk.get("quantity_unit") != "BASE_ASSET":
            raise ValueError(f"ORDER_INTENT_QUANTITY_UNIT_INVALID:{asset}")
        if risk.get("quantity_source") != "RISK.position_quantity":
            raise ValueError(f"ORDER_INTENT_QUANTITY_SOURCE_INVALID:{asset}")

        decision_id = _required(decision, "decision_id", f"ORDER_INTENT_DECISION_BIRTH_ID_MISSING:{asset}")
        direction = str(_required(decision, "direction", f"ORDER_INTENT_DIRECTION_MISSING:{asset}")).strip().upper()
        if direction not in {"LONG", "SHORT"}:
            raise ValueError(f"ORDER_INTENT_DIRECTION_INVALID:{asset}")
        entry_price = _required(opportunity, "price", f"ORDER_INTENT_ENTRY_PRICE_MISSING:{asset}")
        timestamp = _required(opportunity, "timestamp", f"ORDER_INTENT_TIMESTAMP_MISSING:{asset}")
        confidence = _required(opportunity, "confidence", f"ORDER_INTENT_CONFIDENCE_MISSING:{asset}")
        regime = _required(decision, "regime", f"ORDER_INTENT_REGIME_MISSING:{asset}")
        market = market_data.get(f"{asset}/USDT")
        if market is None:
            raise ValueError(f"ORDER_INTENT_MARKET_DATA_MISSING:{asset}")
        snapshot_id = _snapshot_id(asset, market)
        intent_id = f"OI-{decision_id}"

        result[asset] = {
            "asset": asset,
            "direction": direction,
            "entry_price": entry_price,
            "confidence": confidence,
            "regime": regime,
            "timestamp": timestamp,
            "snapshot_id": snapshot_id,
            "intent_id": intent_id,
            "decision_id": decision_id,
            "quantity": quantity,
            "quantity_unit": risk["quantity_unit"],
            "quantity_source": risk["quantity_source"],
            "source": "CURRENT_RUNTIME_DECISION_RISK_TRADE_GATE_OPPORTUNITY",
        }
    return result


__all__ = ["produce_runtime_order_intents"]
