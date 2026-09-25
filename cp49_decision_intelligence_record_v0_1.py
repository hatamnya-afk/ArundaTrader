"""CP49 decision-intelligence record contract.

Read-only, provider-neutral packaging of canonical decision evidence.
No score calculation, decision reconstruction, persistence, network, or execution.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping
import math


@dataclass(frozen=True)
class DecisionIntelligenceRecord:
    decision_id: str
    snapshot_id: str
    decision_timestamp_ms: int
    knowledge_cutoff_ms: int
    asset: str
    direction: str
    decision_state: str
    decision_score: float
    decision_reason: str
    layer_scores: tuple[tuple[str, float], ...]
    selection_reasons: tuple[str, ...]
    rejection_reasons: tuple[str, ...]
    provenance: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class DecisionIntelligenceResult:
    status: str
    reason: str
    record: DecisionIntelligenceRecord | None = None


def _block(reason: str) -> DecisionIntelligenceResult:
    return DecisionIntelligenceResult("BLOCK", reason)


def _text(value: Any) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def _finite_number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _pairs(value: Any) -> tuple[tuple[str, str], ...] | None:
    if not isinstance(value, Mapping):
        return None
    items: list[tuple[str, str]] = []
    for key, item in value.items():
        k = _text(key)
        v = _text(item)
        if k is None or v is None:
            return None
        items.append((k, v))
    return tuple(sorted(items))


def _score_pairs(value: Any) -> tuple[tuple[str, float], ...] | None:
    if not isinstance(value, Mapping):
        return None
    items: list[tuple[str, float]] = []
    for key, item in value.items():
        k = _text(key)
        v = _finite_number(item)
        if k is None or v is None:
            return None
        items.append((k, v))
    return tuple(sorted(items))


def _reasons(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, (list, tuple)):
        return None
    result = []
    for item in value:
        text = _text(item)
        if text is None:
            return None
        result.append(text)
    return tuple(result)


def build_decision_intelligence_record(
    data: Mapping[str, Any],
) -> DecisionIntelligenceResult:
    if not isinstance(data, Mapping):
        return _block("CANONICAL_DECISION_RECORD_INVALID")

    decision_id = _text(data.get("decision_id"))
    if decision_id is None:
        return _block("CANONICAL_DECISION_ID_MISSING")

    snapshot_id = _text(data.get("snapshot_id"))
    asset = _text(data.get("asset"))
    direction = _text(data.get("direction"))
    state = _text(data.get("decision_state"))
    decision_reason = _text(data.get("decision_reason"))
    if None in (snapshot_id, asset, direction, state, decision_reason):
        return _block("CANONICAL_DECISION_IDENTITY_OR_REASON_MISSING")

    try:
        decision_timestamp_ms = int(data["decision_timestamp_ms"])
        knowledge_cutoff_ms = int(data["knowledge_cutoff_ms"])
    except (KeyError, TypeError, ValueError):
        return _block("DECISION_TIMESTAMP_INVALID")
    if decision_timestamp_ms <= 0 or knowledge_cutoff_ms <= 0:
        return _block("DECISION_TIMESTAMP_INVALID")
    if knowledge_cutoff_ms > decision_timestamp_ms:
        return _block("KNOWLEDGE_CUTOFF_AFTER_DECISION")

    decision_score = _finite_number(data.get("decision_score"))
    if decision_score is None:
        return _block("DECISION_SCORE_INVALID")

    layer_scores = _score_pairs(data.get("layer_scores"))
    if layer_scores is None:
        return _block("LAYER_SCORES_INVALID")
    selection_reasons = _reasons(data.get("selection_reasons"))
    rejection_reasons = _reasons(data.get("rejection_reasons"))
    provenance = _pairs(data.get("provenance"))
    if selection_reasons is None or rejection_reasons is None or provenance is None:
        return _block("DECISION_EVIDENCE_INVALID")

    required_provenance = {"decision", "risk", "allocation", "position_size", "quantity"}
    if not required_provenance.issubset({k.lower() for k, _ in provenance}):
        return _block("UPSTREAM_PROVENANCE_INCOMPLETE")

    return DecisionIntelligenceResult(
        "PASS",
        "DECISION_INTELLIGENCE_RECORD_VALID",
        DecisionIntelligenceRecord(
            decision_id=decision_id,
            snapshot_id=snapshot_id,
            decision_timestamp_ms=decision_timestamp_ms,
            knowledge_cutoff_ms=knowledge_cutoff_ms,
            asset=asset,
            direction=direction,
            decision_state=state,
            decision_score=decision_score,
            decision_reason=decision_reason,
            layer_scores=layer_scores,
            selection_reasons=selection_reasons,
            rejection_reasons=rejection_reasons,
            provenance=provenance,
        ),
    )
