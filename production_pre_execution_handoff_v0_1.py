"""Production handoff from canonical order requests to pre-execution readiness.

This is a pure, fail-closed assembly boundary. It consumes only current-run
Decision, validation, Risk, Trade Gate and Opportunity records. Venue selection
is deliberately explicit: a standing mandate allowing SPOT and FUTURES does
not select one for an individual request.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from exchange_execution_contract import CanonicalOrderRequest
from pre_execution_readiness_v0_1 import build_pre_execution_readiness
from production_final_execution_context_v0_1 import build_production_final_attempt_context


_MANDATE_PATH = Path(__file__).resolve().parent / "management_mandates" / "real_production_standing_mandate_20261011.json"


def load_standing_mandate_observation(path: Path | None = None) -> dict[str, Any]:
    """Load the existing machine-readable standing mandate without mutation."""
    source = path or _MANDATE_PATH
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("MANAGEMENT_MANDATE_SOURCE_UNAVAILABLE") from exc
    if not isinstance(payload, dict):
        raise ValueError("MANAGEMENT_MANDATE_SOURCE_INVALID")
    return payload


def build_production_pre_execution_handoff(
    *,
    request: CanonicalOrderRequest,
    decision: Mapping[str, Any],
    validation: Mapping[str, Any],
    risk: Mapping[str, Any],
    trade_gate: Mapping[str, Any],
    opportunity: Mapping[str, Any],
    venue: str | None = None,
    management_observation: Mapping[str, Any] | None = None,
    adapter: Any = None,
    venue_selection_evidence: Mapping[str, Any] | None = None,
    instrument_evidence: Mapping[str, Any] | None = None,
    max_instrument_evidence_age_seconds: int = 60,
) -> dict[str, Any]:
    """Build readiness and, only with explicit venue/context, final-attempt context."""
    if not isinstance(request, CanonicalOrderRequest):
        raise ValueError("CANONICAL_ORDER_REQUEST_INVALID")
    for name, value in (
        ("decision", decision),
        ("validation", validation),
        ("risk", risk),
        ("trade_gate", trade_gate),
        ("opportunity", opportunity),
    ):
        if not isinstance(value, Mapping):
            raise ValueError(f"PRE_EXECUTION_{name.upper()}_MISSING")

    def base_asset(value: Any) -> str | None:
        if not isinstance(value, str) or not value.strip():
            return None
        return value.strip().upper().split("/", 1)[0]

    request_asset = base_asset(request.asset)
    for source_name, source in (
        ("decision", decision),
        ("risk", risk),
        ("trade_gate", trade_gate),
        ("opportunity", opportunity),
    ):
        source_asset = base_asset(source.get("asset"))
        if source_asset is not None and source_asset != request_asset:
            raise ValueError("PRE_EXECUTION_ASSET_MISMATCH:" + source_name)
    if decision.get("status") != "READY" or decision.get("state") != "ACTIONABLE":
        raise ValueError("PRE_EXECUTION_DECISION_NOT_ACTIONABLE_READY")
    if decision.get("direction") != request.direction:
        raise ValueError("PRE_EXECUTION_DECISION_DIRECTION_MISMATCH")
    if risk.get("direction") != request.direction:
        raise ValueError("PRE_EXECUTION_RISK_DIRECTION_MISMATCH")
    gate_direction = trade_gate.get("direction")
    if gate_direction is not None and gate_direction != request.direction:
        raise ValueError("PRE_EXECUTION_TRADE_GATE_DIRECTION_MISMATCH")
    if opportunity.get("price") != request.entry_price:
        raise ValueError("PRE_EXECUTION_OPPORTUNITY_ENTRY_PRICE_MISMATCH")
    if validation.get("valid") is not True:
        raise ValueError("PRE_EXECUTION_DECISION_VALIDATION_FAILED")
    if opportunity.get("status") != "ELIGIBLE":
        raise ValueError("PRE_EXECUTION_OPPORTUNITY_NOT_ELIGIBLE")
    if risk.get("risk_state") != "APPROVED":
        raise ValueError("PRE_EXECUTION_RISK_NOT_APPROVED")
    if risk.get("position_sizing_state") != "CALCULATED":
        raise ValueError("PRE_EXECUTION_POSITION_SIZING_NOT_CALCULATED")
    if trade_gate.get("trade_gate_state") != "TRADE_READY":
        raise ValueError("PRE_EXECUTION_TRADE_GATE_NOT_READY")

    observed_at = opportunity.get("timestamp")
    if not isinstance(observed_at, str) or not observed_at.strip():
        raise ValueError("PRE_EXECUTION_CURRENT_RUN_TIMESTAMP_MISSING")

    readiness = build_pre_execution_readiness({
        "decision_state": "READY",
        "decision_validation": "VALID",
        "asset": request.asset,
        "direction": request.direction,
        "entry_price": risk.get("entry_price"),
        "stop_price": risk.get("stop_price"),
        "stop_distance": risk.get("stop_distance"),
        "quantity": risk.get("position_quantity"),
        "exposure": risk.get("exposure"),
        "risk_state": "APPROVED",
        "trade_gate_state": "APPROVED",
        "policy_version": str(risk.get(
            "position_sizing_reason",
            "EXISTING_RISK_BUDGET_AND_POSITION_SIZE_POLICY",
        )),
        "provenance": "REAL_MARKET_CURRENT_RUN",
        "observed_at": observed_at,
    })

    aligned = {
        "asset": request.asset,
        "direction": request.direction,
        "entry_price": request.entry_price,
        "quantity": request.quantity,
    }
    for field, expected in aligned.items():
        if readiness.get(field) != expected:
            raise ValueError(f"PRE_EXECUTION_REQUEST_MISMATCH:{field}")

    if management_observation is None:
        management_observation = load_standing_mandate_observation()
    if not isinstance(management_observation, Mapping):
        raise ValueError("MANAGEMENT_MANDATE_SOURCE_INVALID")

    # The mandate allows both markets; only the evidence resolver may select
    # one for this intent. Missing producer evidence remains explicitly blocked.
    from evidence_based_venue_selection_v0_1 import resolve_authoritative_venue

    venue_resolution = resolve_authoritative_venue(
        asset=request.asset,
        expected_intent_id=request.intent_id,
        mandate=management_observation,
        selection_evidence=venue_selection_evidence,
        instrument_evidence=instrument_evidence,
        now=datetime.now(timezone.utc).isoformat(),
        max_evidence_age_seconds=max_instrument_evidence_age_seconds,
    )
    result: dict[str, Any] = {
        "readiness": readiness,
        "context": None,
        "venue_resolution": venue_resolution,
        "status": "PRE_EXECUTION_READY_VENUE_SELECTION_BLOCKED",
    }
    if venue_resolution.get("status") != "VENUE_SELECTED":
        return result
    selected_venue = venue_resolution.get("venue")
    if venue is not None and (
        not isinstance(venue, str) or venue.strip().upper() != selected_venue
    ):
        result["status"] = "PRE_EXECUTION_BLOCKED_VENUE_EVIDENCE_MISMATCH"
        result["venue_resolution"] = {
            **venue_resolution,
            "status": "VENUE_SELECTION_BLOCKED",
            "venue": None,
            "reason": "EXPLICIT_VENUE_DIFFERS_FROM_AUTHORITATIVE_SELECTION",
        }
        return result
    venue = selected_venue
    if not isinstance(management_observation, Mapping):
        raise ValueError("MANAGEMENT_MANDATE_SOURCE_INVALID")
    if adapter is None:
        raise ValueError("EXECUTION_ADAPTER_INVALID")

    context = build_production_final_attempt_context(
        request=request,
        pre_execution_readiness=readiness,
        management_observation=management_observation,
        adapter=adapter,
        venue=venue,
    )
    result["context"] = context
    result["status"] = "FINAL_ATTEMPT_CONTEXT_READY_EXECUTION_STILL_GATED"
    return result


__all__ = ["build_production_pre_execution_handoff", "load_standing_mandate_observation"]
