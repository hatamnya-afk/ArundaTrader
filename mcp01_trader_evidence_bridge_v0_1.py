"""MCP-01 Trader evidence bridge.

Builds compact evidence events from already-produced Trader runtime state.
This is an adapter only: it does not create Trader identities, alter strategy,
execute orders, write the production DB, or infer trade_event_id.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from mcp01_compact_event_evidence_v0_1 import (
    EVENT_DATA_QUALITY,
    EVENT_FILL_OUTCOME,
    EVENT_ORDER_ATTEMPTED,
    EVENT_PROVIDER_RESULT,
    EVENT_SELECTED,
    EVENT_TRADE_READY,
    build_event,
    deterministic_event_id,
)


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _text(value, field)


def build_runtime_evidence_events(
    *,
    cycle_id: str,
    emitted_at: str,
    decision_snapshot: Mapping[str, Mapping[str, Any]],
    trade_gate_snapshot: Mapping[str, Mapping[str, Any]],
    trade_ready_assets: Iterable[str],
    execution_results: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Build compact events from authoritative runtime outputs.

    Selection and Trade Ready use the canonical decision_id already issued by
    Trader/CP49. Provider/order evidence is emitted only when an authoritative
    trade_event_id is supplied by an upstream execution boundary. No fallback
    to exchange_order_id or any other field is permitted.
    """
    cycle_id = _text(cycle_id, "cycle_id")
    emitted_at = _text(emitted_at, "emitted_at")
    ready_assets = {str(asset).strip() for asset in trade_ready_assets if str(asset).strip()}
    results = execution_results or {}
    events: list[dict[str, Any]] = []

    for asset in sorted(decision_snapshot):
        decision = decision_snapshot[asset]
        decision_id = _text(decision.get("decision_id"), f"{asset}.decision_id")
        gate = trade_gate_snapshot.get(asset)
        if not isinstance(gate, Mapping):
            raise ValueError(f"trade_gate_snapshot missing asset: {asset}")

        gate_decision_id = gate.get("decision_id")
        if gate_decision_id is not None and _text(
            gate_decision_id, f"{asset}.trade_gate.decision_id"
        ) != decision_id:
            raise ValueError(f"decision_id lineage mismatch: {asset}")

        common = {
            "cycle_id": cycle_id,
            "event_timestamp": emitted_at,
            "decision_id": decision_id,
            "asset": _text(asset, "asset"),
            "direction": _optional_text(gate.get("direction"), f"{asset}.direction"),
            "stage": "DECISION",
        }

        if gate.get("trade_gate_status") == "TRADE_READY":
            if asset not in ready_assets:
                raise ValueError(
                    f"Trade Gate is TRADE_READY but asset is absent from trade_ready_assets: {asset}"
                )
            payload = {**common, "event_type": EVENT_TRADE_READY, "status": "TRADE_READY"}
            payload["event_id"] = deterministic_event_id(**payload)
            events.append(build_event(**payload).to_dict())
        elif asset in ready_assets:
            raise ValueError(f"trade_ready_assets disagrees with Trade Gate: {asset}")

        payload = {
            **common,
            "event_type": EVENT_SELECTED,
            "status": _optional_text(decision.get("decision"), f"{asset}.decision"),
        }
        payload["event_id"] = deterministic_event_id(**payload)
        events.append(build_event(**payload).to_dict())

    for asset, result in sorted(results.items()):
        if not isinstance(result, Mapping):
            raise ValueError(f"execution_results[{asset}] must be a mapping")
        if asset not in decision_snapshot:
            raise ValueError(
                f"execution_results asset missing from decision_snapshot: {asset}"
            )

        trade_event_id = result.get("trade_event_id")
        if trade_event_id is None:
            payload = {
                "event_type": EVENT_DATA_QUALITY,
                "event_timestamp": emitted_at,
                "cycle_id": cycle_id,
                "asset": _text(asset, "asset"),
                "stage": "DATA_QUALITY",
                "status": result.get("status"),
                "reason_code": "TRADE_EVENT_ID_MISSING_AT_EXECUTION_RESULT",
            }
            payload["event_id"] = deterministic_event_id(**payload)
            events.append(build_event(**payload).to_dict())
            continue

        trade_event_id = _text(trade_event_id, f"{asset}.trade_event_id")
        decision_id = _text(decision_snapshot[asset].get("decision_id"), f"{asset}.decision_id")
        direction = _optional_text(result.get("direction"), f"{asset}.direction")

        order_payload = {
            "event_type": EVENT_ORDER_ATTEMPTED,
            "event_timestamp": emitted_at,
            "cycle_id": cycle_id,
            "decision_id": decision_id,
            "trade_event_id": trade_event_id,
            "asset": _text(asset, "asset"),
            "direction": direction,
            "stage": "ORDER",
            "status": _optional_text(result.get("status"), f"{asset}.status"),
            "provider": _optional_text(result.get("adapter"), f"{asset}.adapter"),
        }
        order_payload["event_id"] = deterministic_event_id(**order_payload)
        events.append(build_event(**order_payload).to_dict())

        provider_payload = {
            **order_payload,
            "event_type": EVENT_PROVIDER_RESULT,
            "stage": "EXECUTION",
            "reason_code": _optional_text(result.get("error_code"), f"{asset}.error_code"),
        }
        provider_payload["event_id"] = deterministic_event_id(**provider_payload)
        events.append(build_event(**provider_payload).to_dict())

        # Fill state must be explicit authoritative input. Provider acceptance,
        # status text, or absence of a fill field is never interpreted as a fill.
        fill_outcome = result.get("fill_outcome")
        if fill_outcome is not None:
            if fill_outcome not in {"FILLED", "NOT_FILLED"}:
                raise ValueError(
                    f"{asset}.fill_outcome must be explicit FILLED or NOT_FILLED"
                )
            fill_payload = {
                **order_payload,
                "event_type": EVENT_FILL_OUTCOME,
                "stage": "EXECUTION",
                "status": fill_outcome,
                "reason_code": _optional_text(
                    result.get("fill_reason_code"), f"{asset}.fill_reason_code"
                ),
            }
            fill_payload["event_id"] = deterministic_event_id(**fill_payload)
            events.append(build_event(**fill_payload).to_dict())

    return events


def deduplicate_events(events: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return one event per event_id, preserving first occurrence."""
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in events:
        event_id = _text(event.get("event_id"), "event_id")
        if event_id in seen:
            continue
        seen.add(event_id)
        result.append(dict(event))
    return result
