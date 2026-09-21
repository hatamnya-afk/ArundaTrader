from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class LiveUncertaintyMapping:
    asset: str
    source: str
    observed_at: str
    provenance: str
    technical_available: bool
    news_available: bool
    whale_available: bool
    microstructure_available: bool
    data_completeness: float
    validation: str = "VALID"


def build_live_uncertainty_mapping(
    *,
    observation: Mapping[str, Any],
) -> LiveUncertaintyMapping:

    required = (
        "asset",
        "source",
        "observed_at",
        "provenance",
        "technical_available",
        "news_available",
        "whale_available",
        "microstructure_available",
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

    availability = (
        bool(observation["technical_available"]),
        bool(observation["news_available"]),
        bool(observation["whale_available"]),
        bool(observation["microstructure_available"]),
    )

    data_completeness = round(
        sum(1.0 for value in availability if value) / 4.0,
        6,
    )

    return LiveUncertaintyMapping(
        asset=asset,
        source=source,
        observed_at=observed_at,
        provenance=provenance,
        technical_available=availability[0],
        news_available=availability[1],
        whale_available=availability[2],
        microstructure_available=availability[3],
        data_completeness=data_completeness,
    )


def inspect_governance() -> dict[str, Any]:
    return {
        "component": "CP44_LIVE_UNCERTAINTY_MAPPING_V0_1",
        "semantic_role": "LIVE_INFORMATION_AVAILABILITY_MAPPING",
        "formula_frozen": False,
        "uncertainty_formula_frozen": False,
        "probability_claim": False,
        "confidence_reinterpretation": False,
        "historical_outcomes_used": False,
        "future_information_used": False,
        "calibration_used": False,
        "database_writes": 0,
        "execution": False,
        "smart_risk_modified": False,
    }
