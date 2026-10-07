"""MCP-01.2 — compact runtime projection.

Pure management-view projection. It does not alter Trader decisions, order
generation, execution, or persistence. Full CP69 remains the canonical forensic
observation; this projection is only the bounded runtime summary.
"""
from __future__ import annotations
from typing import Any

SCHEMA = "arunda.compact_runtime_projection"
SCHEMA_VERSION = "1.0"

def project_runtime(
    *,
    cycle_id: str,
    emitted_at: str,
    universe_size: int,
    opportunity_ready: int,
    signal_ready: int,
    validation_ready: int,
    fusion_ready: int,
    decision_ready: int,
    risk_ready: int,
    trade_gate_ready: int,
    trade_ready: int,
    order_intents_created: int,
    canonical_order_requests_created: int,
    execution: str,
    real_order: bool,
    real_trade: bool,
    status_counts: dict[str, int] | None = None,
    failure_reasons: dict[str, int] | None = None,
    selected_assets: list[str] | None = None,
) -> dict[str, Any]:
    counts = {
        "universe": universe_size,
        "opportunity": opportunity_ready,
        "signal": signal_ready,
        "validation": validation_ready,
        "fusion": fusion_ready,
        "decision": decision_ready,
        "risk": risk_ready,
        "trade_gate": trade_gate_ready,
        "trade_ready": trade_ready,
        "order_intents": order_intents_created,
        "canonical_orders": canonical_order_requests_created,
    }
    for name, value in counts.items():
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name} must be a non-negative integer")
    if not isinstance(cycle_id, str) or not cycle_id.strip():
        raise ValueError("cycle_id must be non-empty")
    if not isinstance(emitted_at, str) or not emitted_at.strip():
        raise ValueError("emitted_at must be non-empty")
    if execution not in {"ON", "OFF"}:
        raise ValueError("execution must be ON or OFF")
    if not isinstance(real_order, bool) or not isinstance(real_trade, bool):
        raise ValueError("real_order and real_trade must be bool")
    if execution == "OFF" and (real_order or real_trade):
        raise ValueError("OFF execution cannot report real order/trade")
    if real_trade and not real_order:
        raise ValueError("real_trade requires real_order")
    if canonical_order_requests_created > order_intents_created:
        raise ValueError("canonical orders cannot exceed order intents")
    if trade_ready > trade_gate_ready:
        raise ValueError("trade_ready cannot exceed trade_gate_ready")
    if status_counts is not None:
        _validate_counts(status_counts, "status_counts")
    if failure_reasons is not None:
        _validate_counts(failure_reasons, "failure_reasons")
    assets = sorted({str(a).strip() for a in (selected_assets or []) if str(a).strip()})
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "cycle_id": cycle_id,
        "emitted_at": emitted_at,
        "counts": counts,
        "execution": {
            "EXECUTION": execution,
            "REAL_ORDER": real_order,
            "REAL_TRADE": real_trade,
        },
        "selection": {
            "count": len(assets),
            "assets": assets,
        },
        "status_counts": dict(sorted((status_counts or {}).items())),
        "failure_reasons": dict(sorted((failure_reasons or {}).items())),
    }

def render_runtime_line(projection: dict[str, Any]) -> str:
    _validate_projection(projection)
    c = projection["counts"]
    e = projection["execution"]
    return (
        f"RUNTIME cycle={projection['cycle_id']} "
        f"universe={c['universe']} decision={c['decision']} "
        f"trade_ready={c['trade_ready']} orders={c['canonical_orders']} "
        f"EXECUTION={e['EXECUTION']} REAL_ORDER={e['REAL_ORDER']} "
        f"REAL_TRADE={e['REAL_TRADE']}"
    )

def _validate_counts(values: dict[str, int], name: str) -> None:
    if not isinstance(values, dict):
        raise ValueError(f"{name} must be a dict")
    for key, value in values.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"{name} contains invalid key")
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"{name}.{key} must be a non-negative integer")

def _validate_projection(projection: dict[str, Any]) -> None:
    if projection.get("schema") != SCHEMA or projection.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("invalid MCP-01.2 projection")
    if not isinstance(projection.get("counts"), dict):
        raise ValueError("projection counts missing")
