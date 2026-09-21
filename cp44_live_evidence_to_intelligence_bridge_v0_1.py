"""CP44 Live Evidence -> Intelligence Bridge v0.1.

Connects an explicit live evidence producer to the existing candidate-only
intelligence integration boundary. No score/confidence reinterpretation,
formula freezing, DB writes, runtime, or execution.
"""
from typing import Any, Mapping


SEMANTIC_FORBIDDEN_PROVENANCE_FIELDS = frozenset(
    {
        "outcome",
        "label",
    }
)


def _reject_semantic_leakage(value: Any) -> None:
    """Reject semantic outcome/label fields anywhere in provenance mappings."""
    if isinstance(value, Mapping):
        for key, nested in value.items():
            normalized_key = str(key).strip().lower()
            if normalized_key in SEMANTIC_FORBIDDEN_PROVENANCE_FIELDS:
                raise ValueError(f"FORBIDDEN_LIVE_FIELD:{normalized_key}")
            _reject_semantic_leakage(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_semantic_leakage(nested)

from cp44_live_predictive_evidence_producer_v0_1 import (
    LiveEvidenceObservation,
    build_live_predictive_evidence,
)
from cp44_live_intelligence_contract_integration_v0_1 import (
    LiveIntelligenceInput,
    LiveIntelligenceResult,
    build_live_intelligence_candidate,
)


def build_live_intelligence_from_explicit_evidence(
    *,
    observation: LiveEvidenceObservation,
    reliability_uncertainty: Any,
    provenance: Mapping[str, Any],
) -> LiveIntelligenceResult:
    """Produce PredictiveEvidence explicitly, then enter the candidate boundary."""
    _reject_semantic_leakage(provenance)
    predictive_evidence = build_live_predictive_evidence(
        observation=observation,
    )

    return build_live_intelligence_candidate(
        LiveIntelligenceInput(
            predictive_evidence=predictive_evidence,
            reliability_uncertainty=reliability_uncertainty,
            provenance=provenance,
        )
    )


def inspect_governance() -> dict[str, object]:
    return {
        "explicit_evidence_producer_required": True,
        "producer_output_is_predictive_evidence": True,
        "score_reinterpretation": False,
        "confidence_reinterpretation": False,
        "probability_created": False,
        "future_information_used": False,
        "outcome_information_used": False,
        "calibration_used": False,
        "production_formula_frozen": False,
        "capital_semantics": False,
        "risk_budget_semantics": False,
        "position_size_semantics": False,
        "exposure_semantics": False,
        "order_semantics": False,
        "execution_semantics": False,
        "db_writes": 0,
        "runtime_executed": False,
    }


__all__ = [
    "build_live_intelligence_from_explicit_evidence",
    "inspect_governance",
]
