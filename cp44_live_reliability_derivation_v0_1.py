from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping
from math import prod


FORBIDDEN_LIVE_FIELDS = frozenset(
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


@dataclass(frozen=True)
class LiveReliabilityEvidence:
    asset: str
    source: str
    observed_at: str
    provenance: str
    evidence_quality: float
    temporal_integrity: float
    source_integrity: float
    continuity_integrity: float
    validation: str = "VALID"


def _reject_forbidden_live_input(observation: Mapping[str, Any]) -> None:
    forbidden = sorted(
        set(observation.keys()).intersection(
            FORBIDDEN_LIVE_FIELDS
        )
    )

    if forbidden:
        raise ValueError(
            "FORBIDDEN_LIVE_INFORMATION:" + ",".join(forbidden)
        )


def _finite_unit(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"INVALID_{field.upper()}"
        ) from exc

    if not isfinite(result):
        raise ValueError(
            f"INVALID_{field.upper()}"
        )

    if not 0.0 <= result <= 1.0:
        raise ValueError(
            f"{field.upper()}_OUT_OF_RANGE"
        )

    return result


def build_live_reliability_evidence(
    *,
    observation: Mapping[str, Any],
) -> LiveReliabilityEvidence:
    _reject_forbidden_live_input(observation)

    required = (
        "asset",
        "source",
        "observed_at",
        "provenance",
        "evidence_quality",
        "temporal_integrity",
        "source_integrity",
        "continuity_integrity",
    )

    missing = [
        field
        for field in required
        if field not in observation
    ]

    if missing:
        raise ValueError(
            "MISSING_REQUIRED_FIELDS:" + ",".join(missing)
        )

    asset = str(observation["asset"]).strip()
    source = str(observation["source"]).strip()
    observed_at = str(observation["observed_at"]).strip()
    provenance = str(observation["provenance"]).strip()

    if not asset or not source or not observed_at or not provenance:
        raise ValueError("EMPTY_REQUIRED_FIELD")

    return LiveReliabilityEvidence(
        asset=asset,
        source=source,
        observed_at=observed_at,
        provenance=provenance,
        evidence_quality=_finite_unit(
            observation["evidence_quality"],
            "evidence_quality",
        ),
        temporal_integrity=_finite_unit(
            observation["temporal_integrity"],
            "temporal_integrity",
        ),
        source_integrity=_finite_unit(
            observation["source_integrity"],
            "source_integrity",
        ),
        continuity_integrity=_finite_unit(
            observation["continuity_integrity"],
            "continuity_integrity",
        ),
    )


def derive_live_reliability(
    evidence: LiveReliabilityEvidence,
) -> float:
    values = (
        evidence.evidence_quality,
        evidence.temporal_integrity,
        evidence.source_integrity,
        evidence.continuity_integrity,
    )

    if any(
        not isfinite(value)
        or not 0.0 <= value <= 1.0
        for value in values
    ):
        raise ValueError("INVALID_RELIABILITY_EVIDENCE")

    return round(
        prod(values) ** 0.25,
        6,
    )


def inspect_governance() -> dict[str, Any]:
    return {
        "component": "CP44_LIVE_RELIABILITY_DERIVATION_V0_1",
        "semantic_role": "LIVE_CAUSAL_RELIABILITY_DERIVATION_BOUNDARY",
        "formula": "GEOMETRIC_MEAN_OF_FOUR_CAUSAL_INTEGRITY_COMPONENTS",
        "formula_frozen": False,
        "future_information_used": False,
        "historical_outcomes_used": False,
        "calibration_used": False,
        "probability_claim": False,
        "confidence_reinterpretation": False,
        "database_writes": 0,
        "execution": False,
        "smart_risk_modified": False,
    }
