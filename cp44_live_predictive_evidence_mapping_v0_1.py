from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping


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
class LivePredictiveEvidenceMapping:
    asset: str
    direction: str
    opportunity_score: float
    momentum_1h: float
    momentum_24h: float
    rsi14: float
    structure_direction: str | None
    structure_strength: str | None
    structure_confidence: str | None
    source: str
    observed_at: str
    provenance: str
    validation: str = "VALID"


def _reject_forbidden_live_input(
    observation: Mapping[str, Any],
) -> None:
    forbidden = sorted(
        set(observation.keys()).intersection(
            FORBIDDEN_LIVE_FIELDS
        )
    )

    if forbidden:
        raise ValueError(
            "FORBIDDEN_LIVE_INFORMATION:"
            + ",".join(forbidden)
        )


def _finite(
    value: Any,
    field: str,
) -> float:
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

    return result


def build_live_predictive_evidence_mapping(
    *,
    observation: Mapping[str, Any],
) -> LivePredictiveEvidenceMapping:

    _reject_forbidden_live_input(observation)

    required = (
        "asset",
        "direction",
        "opportunity_score",
        "momentum_1h",
        "momentum_24h",
        "rsi14",
        "source",
        "observed_at",
        "provenance",
    )

    missing = [
        field
        for field in required
        if field not in observation
    ]

    if missing:
        raise ValueError(
            "MISSING_REQUIRED_FIELDS:"
            + ",".join(missing)
        )

    asset = str(observation["asset"]).strip()
    direction = str(observation["direction"]).strip().upper()
    source = str(observation["source"]).strip()
    observed_at = str(
        observation["observed_at"]
    ).strip()
    provenance = str(
        observation["provenance"]
    ).strip()

    if not asset or not source or not observed_at or not provenance:
        raise ValueError("EMPTY_REQUIRED_FIELD")

    if direction not in {"LONG", "SHORT"}:
        raise ValueError("INVALID_DIRECTION")

    opportunity_score = _finite(
        observation["opportunity_score"],
        "opportunity_score",
    )

    if not 0.0 <= opportunity_score <= 100.0:
        raise ValueError("OPPORTUNITY_SCORE_OUT_OF_RANGE")

    return LivePredictiveEvidenceMapping(
        asset=asset,
        direction=direction,
        opportunity_score=opportunity_score,
        momentum_1h=_finite(
            observation["momentum_1h"],
            "momentum_1h",
        ),
        momentum_24h=_finite(
            observation["momentum_24h"],
            "momentum_24h",
        ),
        rsi14=_finite(
            observation["rsi14"],
            "rsi14",
        ),
        structure_direction=(
            str(observation["structure_direction"]).strip().upper()
            if observation.get("structure_direction") is not None
            else None
        ),
        structure_strength=(
            str(observation["structure_strength"]).strip().upper()
            if observation.get("structure_strength") is not None
            else None
        ),
        structure_confidence=(
            str(observation["structure_confidence"]).strip().upper()
            if observation.get("structure_confidence") is not None
            else None
        ),
        source=source,
        observed_at=observed_at,
        provenance=provenance,
    )


def inspect_governance() -> dict[str, Any]:
    return {
        "component": (
            "CP44_LIVE_PREDICTIVE_EVIDENCE_MAPPING_V0_1"
        ),
        "semantic_role": (
            "LIVE_CAUSAL_PREDICTIVE_EVIDENCE_MAPPING_BOUNDARY"
        ),
        "opportunity_score_used_as_observation": True,
        "opportunity_score_normalized_to_probability": False,
        "reliability_used": False,
        "confidence_reinterpreted": False,
        "formula_frozen": False,
        "probability_claim": False,
        "historical_outcomes_used": False,
        "future_information_used": False,
        "calibration_used": False,
        "database_writes": 0,
        "execution": False,
        "smart_risk_modified": False,
    }