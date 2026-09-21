from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any


FORBIDDEN_LIVE_FIELDS = {
    "future_outcome",
    "future_label",
    "realized_return",
    "pnl",
    "exit_price",
    "post_outcome",
    "calibrated_probability",
}


@dataclass(frozen=True)
class LiveReliabilityObservation:
    asset: str
    reliability: float
    source: str
    observed_at: str
    provenance: str
    validation: str = "VALID"


def _reject_forbidden_live_input(observation: dict[str, Any]) -> None:
    leaked = sorted(
        field
        for field in FORBIDDEN_LIVE_FIELDS
        if field in observation
    )

    if leaked:
        raise ValueError(
            "FORBIDDEN_LIVE_INPUT:" + ",".join(leaked)
        )


def build_live_reliability(
    *,
    observation: dict[str, Any],
) -> LiveReliabilityObservation:

    _reject_forbidden_live_input(observation)

    required = (
        "asset",
        "reliability",
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
            "MISSING_RELIABILITY_FIELDS:"
            + ",".join(missing)
        )

    asset = str(observation["asset"]).strip()
    source = str(observation["source"]).strip()
    observed_at = str(observation["observed_at"]).strip()
    provenance = str(observation["provenance"]).strip()

    if not asset or not source or not observed_at or not provenance:
        raise ValueError(
            "INVALID_RELIABILITY_IDENTITY"
        )

    reliability = float(observation["reliability"])

    if not isfinite(reliability):
        raise ValueError(
            "INVALID_RELIABILITY_NONFINITE"
        )

    if not 0.0 <= reliability <= 1.0:
        raise ValueError(
            "INVALID_RELIABILITY_BOUNDS"
        )

    return LiveReliabilityObservation(
        asset=asset,
        reliability=reliability,
        source=source,
        observed_at=observed_at,
        provenance=provenance,
    )


def inspect_governance() -> dict[str, Any]:
    return {
        "producer": "CP44_LIVE_RELIABILITY_PRODUCER_V0_1",
        "semantic_role": "LIVE_SOURCE_RELIABILITY",
        "historical_outcomes_used": False,
        "future_information_used": False,
        "calibration_used": False,
        "probability_claim": False,
        "confidence_reinterpretation": False,
        "uncertainty_manufactured": False,
        "database_writes": 0,
        "execution": False,
        "smart_risk_modified": False,
    }
