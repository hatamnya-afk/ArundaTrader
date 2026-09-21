from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from cp44_live_reliability_derivation_v0_1 import (
    LiveReliabilityEvidence,
    build_live_reliability_evidence,
)


@dataclass(frozen=True)
class LiveReliabilityMapping:
    asset: str
    source: str
    observed_at: str
    provenance: str
    evidence_quality: float
    temporal_integrity: float
    source_integrity: float
    continuity_integrity: float
    validation: str = "VALID"


def _binary(value: bool) -> float:
    return 1.0 if bool(value) else 0.0


def build_live_reliability_mapping(
    *,
    observation: Mapping[str, Any],
) -> LiveReliabilityEvidence:

    required = (
        "asset",
        "source",
        "observed_at",
        "provenance",
        "evidence_quality_valid",
        "temporal_integrity_valid",
        "source_integrity_valid",
        "continuity_integrity_valid",
    )

    missing = [
        field for field in required
        if field not in observation
    ]

    if missing:
        raise ValueError(
            "MISSING_REQUIRED_FIELDS:" + ",".join(missing)
        )

    mapped = {
        "asset": str(observation["asset"]).strip(),
        "source": str(observation["source"]).strip(),
        "observed_at": str(observation["observed_at"]).strip(),
        "provenance": str(observation["provenance"]).strip(),
        "evidence_quality": _binary(
            observation["evidence_quality_valid"]
        ),
        "temporal_integrity": _binary(
            observation["temporal_integrity_valid"]
        ),
        "source_integrity": _binary(
            observation["source_integrity_valid"]
        ),
        "continuity_integrity": _binary(
            observation["continuity_integrity_valid"]
        ),
    }

    return build_live_reliability_evidence(
        observation=mapped
    )


def inspect_governance() -> dict[str, Any]:
    return {
        "component": "CP44_LIVE_RELIABILITY_MAPPING_V0_1",
        "semantic_role": "LIVE_CAUSAL_RELIABILITY_SOURCE_MAPPING",
        "formula_frozen": False,
        "probability_claim": False,
        "confidence_reinterpretation": False,
        "historical_outcomes_used": False,
        "future_information_used": False,
        "calibration_used": False,
        "database_writes": 0,
        "execution": False,
        "smart_risk_modified": False,
    }
