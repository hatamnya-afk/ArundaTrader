"""CP44 Explicit Live Predictive Evidence Producer v0.1.

Creates PredictiveEvidence only from an explicit upstream evidence
observation. No score/confidence reinterpretation and no side effects.
"""
from dataclasses import dataclass
from math import isfinite

from cp44_predictive_evidence_contract_v0_1 import PredictiveEvidence


FORBIDDEN_FIELDS = frozenset(
    {
        "future_outcome",
        "future_label",
        "realized_return",
        "pnl",
        "exit_price",
        "post_outcome",
        "calibrated_probability",
        "outcome",
        "label",
    }
)

REINTERPRETATION_FIELDS = frozenset(
    {
        "score",
        "opportunity_score",
        "confidence",
        "opportunity_confidence",
    }
)


@dataclass(frozen=True)
class LiveEvidenceObservation:
    asset: str
    direction: str
    evidence: float
    source: str
    observed_at: str
    provenance: str


def _validate_observation(observation: LiveEvidenceObservation) -> None:
    if not isinstance(observation.asset, str) or not observation.asset.strip():
        raise ValueError("EVIDENCE_ASSET_INVALID")
    if observation.direction not in ("LONG", "SHORT"):
        raise ValueError("EVIDENCE_DIRECTION_INVALID")
    if (
        isinstance(observation.evidence, bool)
        or not isinstance(observation.evidence, (int, float))
        or not isfinite(float(observation.evidence))
    ):
        raise ValueError("EVIDENCE_VALUE_INVALID")
    if not isinstance(observation.source, str) or not observation.source.strip():
        raise ValueError("EVIDENCE_SOURCE_INVALID")
    if (
        not isinstance(observation.observed_at, str)
        or not observation.observed_at.strip()
    ):
        raise ValueError("EVIDENCE_TIME_INVALID")
    if (
        not isinstance(observation.provenance, str)
        or not observation.provenance.strip()
    ):
        raise ValueError("EVIDENCE_PROVENANCE_INVALID")


def build_live_predictive_evidence(
    *,
    observation: LiveEvidenceObservation,
) -> PredictiveEvidence:
    _validate_observation(observation)
    evidence = PredictiveEvidence(
        asset=observation.asset,
        direction=observation.direction,
        evidence=float(observation.evidence),
        source=observation.source,
        observed_at=observation.observed_at,
        provenance=observation.provenance,
    )
    evidence.validate()
    return evidence


def inspect_governance() -> dict[str, object]:
    return {
        "explicit_evidence_required": True,
        "score_reinterpretation_forbidden": True,
        "confidence_reinterpretation_forbidden": True,
        "probability_created": False,
        "future_information_used": False,
        "outcome_information_used": False,
        "calibration_used": False,
        "production_formula_frozen": False,
        "db_writes": 0,
        "execution": False,
        "runtime_executed": False,
        "smart_risk_modified": False,
    }


__all__ = [
    "FORBIDDEN_FIELDS",
    "REINTERPRETATION_FIELDS",
    "LiveEvidenceObservation",
    "build_live_predictive_evidence",
    "inspect_governance",
]
