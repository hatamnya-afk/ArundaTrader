"""MCP-01 management intelligence flow.

Composes the already-verified MCP-01 projections over canonical compact
evidence. This module is an adapter/management view only: it never creates
Trader identities, executes orders, sends email, starts a scheduler, or mutates
Trader state.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Mapping

from mcp01_compact_event_evidence_v0_1 import (
    DEFAULT_STREAM_PATH,
    EVENT_CLOSED,
    EVENT_DATA_QUALITY,
    EVENT_MARKET_OUTCOME,
    EVENT_NEW,
    EVENT_ORDER_ATTEMPTED,
    EVENT_PROVIDER_RESULT,
    EVENT_SELECTED,
    EVENT_TRADE_READY,
    build_event,
)
from mcp01_runtime_projection_v0_1 import project_runtime
from mcp01_case_projection_v0_1 import assign_case_ids, aggregate_cases
from mcp01_trade_projection_v0_1 import aggregate_trades
from mcp01_outcome_reconciliation_v0_1 import reconcile_outcomes
from mcp01_24h_aggregator_v0_1 import aggregate_24h
from mcp01_24h_email_v0_1 import build_24h_email


LIFECYCLE_EVENT_TYPES = frozenset(
    {
        EVENT_NEW,
        EVENT_SELECTED,
        EVENT_TRADE_READY,
        EVENT_ORDER_ATTEMPTED,
        EVENT_PROVIDER_RESULT,
        EVENT_MARKET_OUTCOME,
        EVENT_CLOSED,
    }
)


def _parse_timestamp(value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("event_timestamp must be non-empty text")
    normalized = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("event_timestamp must be timezone-aware")
    return parsed.astimezone(timezone.utc)


def read_compact_events(
    *,
    stream_path: Path = DEFAULT_STREAM_PATH,
) -> list[dict]:
    path = Path(stream_path)
    if not path.exists():
        return []

    events: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"invalid compact evidence JSON at line {line_number}"
                ) from exc
            if not isinstance(payload, dict):
                raise ValueError(
                    f"compact evidence line {line_number} must be an object"
                )
            event = build_event(**payload)
            events.append(event.to_dict())
    return events


def _within_period(
    event: Mapping[str, object],
    *,
    period_start: datetime,
    period_end: datetime,
) -> bool:
    timestamp = _parse_timestamp(event.get("event_timestamp"))
    return period_start <= timestamp <= period_end


def _projectable(events: Iterable[Mapping[str, object]]) -> list[dict]:
    return [
        dict(event)
        for event in events
        if event.get("event_type") in LIFECYCLE_EVENT_TYPES
    ]


def build_management_intelligence(
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
    selected_assets: Iterable[str] = (),
    status_counts: Mapping[str, int] | None = None,
    failure_reasons: Mapping[str, int] | None = None,
    current_events: Iterable[Mapping[str, object]] = (),
    stream_path: Path = DEFAULT_STREAM_PATH,
) -> dict:
    """Build compact management artifacts from the real Trader evidence flow.

    The current runtime projection is derived from already-produced Trader
    runtime counters. The 24H intelligence report is derived from the
    append-only compact evidence stream, so persisted evidence is the
    management source for the 24H view.
    """
    emitted_dt = _parse_timestamp(emitted_at)
    period_start_dt = emitted_dt - timedelta(hours=24)

    runtime_projection = project_runtime(
        cycle_id=cycle_id,
        emitted_at=emitted_at,
        universe_size=universe_size,
        opportunity_ready=opportunity_ready,
        signal_ready=signal_ready,
        validation_ready=validation_ready,
        fusion_ready=fusion_ready,
        decision_ready=decision_ready,
        risk_ready=risk_ready,
        trade_gate_ready=trade_gate_ready,
        trade_ready=trade_ready,
        order_intents_created=order_intents_created,
        canonical_order_requests_created=canonical_order_requests_created,
        execution=execution,
        real_order=real_order,
        real_trade=real_trade,
        status_counts=dict(status_counts or {}),
        failure_reasons=dict(failure_reasons or {}),
        selected_assets=list(selected_assets),
    )

    current = [dict(event) for event in current_events]
    persisted = read_compact_events(stream_path=stream_path)

    all_projectable = _projectable(persisted)
    enriched_all = assign_case_ids(all_projectable)
    period_events = [
        event
        for event in enriched_all
        if _within_period(
            event,
            period_start=period_start_dt,
            period_end=emitted_dt,
        )
    ]

    case_projections = aggregate_cases(period_events)
    trade_projections = aggregate_trades(period_events)
    reconciliation_projections = reconcile_outcomes(period_events)
    data_quality_events = [
        event
        for event in persisted
        if event.get("event_type") == EVENT_DATA_QUALITY
        and _within_period(
            event,
            period_start=period_start_dt,
            period_end=emitted_dt,
        )
    ]

    cycle_ids = {
        str(event["cycle_id"])
        for event in period_events
        if event.get("cycle_id")
    }

    intelligence = aggregate_24h(
        period_start=period_start_dt.isoformat(),
        period_end=emitted_dt.isoformat(),
        cycle_ids=cycle_ids,
        case_projections=case_projections,
        trade_projections=trade_projections,
        reconciliation_projections=reconciliation_projections,
        runtime_projections=[runtime_projection],
        data_quality_events=data_quality_events,
    )

    email = build_24h_email(intelligence)

    current_projectable = _projectable(current)
    current_enriched = assign_case_ids(current_projectable)
    current_cases = aggregate_cases(current_enriched) if current_enriched else []
    current_trades = aggregate_trades(current_enriched) if current_enriched else []
    current_reconciliation = (
        reconcile_outcomes(current_enriched) if current_enriched else []
    )

    return {
        "runtime_projection": runtime_projection,
        "current_case_projections": current_cases,
        "current_trade_projections": current_trades,
        "current_reconciliation": current_reconciliation,
        "intelligence_24h": intelligence,
        "email_24h": email,
        "persisted_event_count": len(persisted),
        "period_event_count": len(period_events),
        "data_quality_event_count": len(data_quality_events),
    }


def render_management_summary(result: Mapping[str, object]) -> str:
    runtime = result["runtime_projection"]
    intelligence = result["intelligence_24h"]
    cases = intelligence["cases"]
    trades = intelligence["trades"]
    reconciliation = intelligence["reconciliation"]
    dq = intelligence["data_quality"]
    delivery = result["email_24h"]["delivery"]
    return (
        "MCP01_MANAGEMENT "
        f"cycle={runtime['cycle_id']} "
        f"cycles_24h={intelligence['cycles']['count']} "
        f"cases_24h={cases['unique_count']} "
        f"trades_24h={trades['unique_count']} "
        f"provider_chains={reconciliation['complete_provider_chains']} "
        f"market_outcomes={reconciliation['market_outcomes']} "
        f"case_outcomes={reconciliation['case_outcomes']} "
        f"dq_events={dq['event_count']} "
        f"email_enabled={delivery['enabled']}"
    )
