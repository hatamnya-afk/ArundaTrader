"""MCP-01.6 compact 24H intelligence aggregator.

Pure aggregation over compact event evidence and projections. This module does
not activate 24/7 operation, create trades, cap trades, or invent outcomes.
Repeated evidence is counted once per authoritative identity where possible.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping


SCHEMA = "arunda.24h_intelligence"
SCHEMA_VERSION = "1.0"


def _text(value: object, field: str, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise ValueError(f"{field} must be non-empty text")
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _int(value: object, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value


def aggregate_24h(
    *,
    period_start: str,
    period_end: str,
    cycle_ids: Iterable[str],
    case_projections: Iterable[Mapping[str, object]] = (),
    trade_projections: Iterable[Mapping[str, object]] = (),
    reconciliation_projections: Iterable[Mapping[str, object]] = (),
    runtime_projections: Iterable[Mapping[str, object]] = (),
    data_quality_events: Iterable[Mapping[str, object]] = (),
) -> dict:
    period_start = _text(period_start, "period_start", True)
    period_end = _text(period_end, "period_end", True)
    cycles = {_text(value, "cycle_id", True) for value in cycle_ids}

    cases = list(case_projections)
    trades = list(trade_projections)
    reconciliations = list(reconciliation_projections)
    runtimes = list(runtime_projections)
    dq_events = list(data_quality_events)

    unique_cases = {
        _text(row.get("case_id"), "case_id", True)
        for row in cases
        if row.get("case_id") is not None
    }
    unique_trades = {
        _text(row.get("trade_event_id"), "trade_event_id", True)
        for row in trades
        if row.get("trade_event_id") is not None
    }

    lifecycle_counts = Counter(
        _text(row.get("lifecycle"), "lifecycle", True) for row in cases
    )
    trade_lifecycle_counts = Counter(
        _text(row.get("lifecycle"), "lifecycle", True) for row in trades
    )

    provider_status_counts = Counter()
    provider_counts = Counter()
    reconciliation_state_counts = Counter()
    reason_counts = Counter()
    data_quality_reason_counts = Counter()
    selection_assets = set()

    for row in reconciliations:
        state = _text(row.get("state"), "state")
        if state:
            reconciliation_state_counts[state] += 1
        provider = _text(row.get("provider"), "provider")
        if provider:
            provider_counts[provider] += 1
        status = _text(row.get("provider_status"), "provider_status")
        if status:
            provider_status_counts[status] += 1
        reason = _text(row.get("provider_reason_code"), "provider_reason_code")
        if reason:
            reason_counts[reason] += 1

    for row in cases:
        asset = _text(row.get("asset"), "asset")
        if asset:
            selection_assets.add(asset)

    for row in dq_events:
        reason = _text(row.get("reason_code"), "reason_code")
        if reason:
            data_quality_reason_counts[reason] += 1

    complete_reconciliations = sum(
        1 for row in reconciliations if row.get("complete") is True
    )
    market_outcomes = sum(
        1 for row in reconciliations if row.get("market_outcome") is not None
    )
    case_outcomes = sum(
        1 for row in reconciliations if row.get("case_outcome") is not None
    )

    execution_flags = {
        str(row.get("execution", "UNKNOWN")) for row in runtimes
    }

    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "period": {
            "start": period_start,
            "end": period_end,
        },
        "cycles": {
            "count": len(cycles),
        },
        "cases": {
            "unique_count": len(unique_cases),
            "lifecycle_counts": dict(sorted(lifecycle_counts.items())),
            "selected_asset_count": len(selection_assets),
        },
        "trades": {
            "unique_count": len(unique_trades),
            "lifecycle_counts": dict(sorted(trade_lifecycle_counts.items())),
        },
        "execution": {
            "provider_counts": dict(sorted(provider_counts.items())),
            "provider_status_counts": dict(sorted(provider_status_counts.items())),
            "execution_modes_seen": sorted(execution_flags),
        },
        "reconciliation": {
            "records": len(reconciliations),
            "complete_provider_chains": complete_reconciliations,
            "market_outcomes": market_outcomes,
            "case_outcomes": case_outcomes,
            "state_counts": dict(sorted(reconciliation_state_counts.items())),
            "reason_counts": dict(sorted(reason_counts.items())),
        },
        "data_quality": {
            "event_count": len(dq_events),
            "reason_counts": dict(sorted(data_quality_reason_counts.items())),
        },
        "runtime": {
            "projection_count": len(runtimes),
        },
    }
