"""CP72 — deterministic ArundaTrader runtime observation analysis.

Read-only analysis of canonical CP69 observations. This module never trades,
executes, mutates ArundaTrader, or changes the observation source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arundatrader_observation_consumer import (
    CanonicalRuntimeObservation,
    CanonicalRuntimeObservationConsumer,
)


@dataclass(frozen=True)
class RuntimeAnalysisResult:
    observation_id: str
    runtime_snapshot_id: str
    emitted_at: str
    asset_count: int
    opportunity_count: int
    signal_count: int
    validation_count: int
    fusion_count: int
    score_count: int
    decision_count: int
    risk_count: int
    trade_gate_candidate_count: int
    trade_ready_count: int | None
    trade_gate_status_counts: dict[str, int]
    predicate_failures: dict[str, int]
    reason_counts: dict[str, int]
    db_writes: int
    db_write_boundary: str | None
    execution: str
    real_order: bool
    real_trade: bool

    @property
    def safe_for_model_context(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "runtime_snapshot_id": self.runtime_snapshot_id,
            "emitted_at": self.emitted_at,
            "coverage": {
                "assets": self.asset_count,
                "opportunities": self.opportunity_count,
                "signals": self.signal_count,
                "validation": self.validation_count,
                "fusion": self.fusion_count,
                "score": self.score_count,
                "decision": self.decision_count,
                "risk": self.risk_count,
                "trade_gate": self.trade_gate_candidate_count,
                "trade_ready": self.trade_ready_count,
            },
            "trade_gate_status_counts": dict(self.trade_gate_status_counts),
            "failure_attribution": {
                "predicate_failures": dict(self.predicate_failures),
                "reason_counts": dict(self.reason_counts),
            },
            "execution_state": {
                "EXECUTION": self.execution,
                "REAL_ORDER": self.real_order,
                "REAL_TRADE": self.real_trade,
                "DB_WRITES": self.db_writes,
                "DB_WRITE_BOUNDARY": self.db_write_boundary,
            },
        }


def analyze_stream(stream_path: Path) -> RuntimeAnalysisResult:
    """Analyze the latest valid record in the append-only canonical CP69 stream.

    The stream is read-only and historical records are preserved. Every
    non-empty record is parsed and identity/safety-validated by the consumer;
    an empty stream or any malformed record fails closed. Only the final
    observation is projected as the current state.
    """
    observations = CanonicalRuntimeObservationConsumer().read_events(Path(stream_path))
    if not observations:
        raise ValueError("runtime observation stream contains no observations")
    return analyze_runtime_observation(observations[-1])


def analyze_runtime_observation(
    observation: CanonicalRuntimeObservation,
) -> RuntimeAnalysisResult:
    if not isinstance(observation, CanonicalRuntimeObservation):
        raise TypeError("observation must be CanonicalRuntimeObservation")

    state = observation.state
    attribution = state.get("failure_attribution", {})
    trade_gate = state.get("trade_gate_snapshot", {})

    rows = _rows(trade_gate)
    status_counts: dict[str, int] = {}
    for row in rows:
        status = row.get("trade_gate_status", row.get("trade_gate_state"))
        if status is not None:
            key = str(status)
            status_counts[key] = status_counts.get(key, 0) + 1

    return RuntimeAnalysisResult(
        observation_id=observation.observation_id,
        runtime_snapshot_id=str(observation.provenance["runtime_snapshot_id"]),
        emitted_at=observation.emitted_at,
        asset_count=_count(state.get("universe_assets")),
        opportunity_count=_count(state.get("opportunity_by_asset")),
        signal_count=_count(state.get("dynamic_signals")),
        validation_count=_count(state.get("validation_results")),
        fusion_count=_count(state.get("fusion_snapshot")),
        score_count=_count(state.get("score_snapshot")),
        decision_count=_count(state.get("decision_snapshot")),
        risk_count=_count(state.get("risk_snapshot")),
        trade_gate_candidate_count=len(rows),
        trade_ready_count=_int_or_none(attribution.get("trade_ready_count")),
        trade_gate_status_counts=dict(sorted(status_counts.items())),
        predicate_failures=_mapping_ints(attribution.get("predicate_failures")),
        reason_counts=_mapping_ints(attribution.get("reason_counts")),
        db_writes=int(observation.execution_state["DB_WRITES"]),
        db_write_boundary=observation.provenance.get("db_write_boundary"),
        execution=str(observation.execution_state["EXECUTION"]),
        real_order=bool(observation.execution_state["REAL_ORDER"]),
        real_trade=bool(observation.execution_state["REAL_TRADE"]),
    )


def _count(value: Any) -> int:
    if isinstance(value, (dict, list, tuple)):
        return len(value)
    return 0


def _rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [row for row in value.values() if isinstance(row, dict)]
    if isinstance(value, (list, tuple)):
        return [row for row in value if isinstance(row, dict)]
    return []


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _mapping_ints(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        str(key): int(number)
        for key, number in value.items()
        if isinstance(number, int) and not isinstance(number, bool)
    }


__all__ = ["RuntimeAnalysisResult", "analyze_runtime_observation", "analyze_stream"]
