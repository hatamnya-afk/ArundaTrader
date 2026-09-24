"""CP44 Real Risk Allocation Observation Boundary v0.1.

This module does NOT calculate risk allocation.
It only validates an explicitly observed real portfolio allocation.

Forbidden:
    - capital_config
    - risk_budget_engine
    - position_sizing_engine
    - notional -> risk conversion
    - locked balance -> risk conversion
    - PnL -> risk conversion
    - synthetic allocation
    - fallback allocation
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping


VERSION = "CP44_REAL_RISK_ALLOCATION_OBSERVATION_v0.1"

FORBIDDEN_SOURCES = {
    "CAPITAL_CONFIG",
    "RISK_BUDGET_ENGINE",
    "POSITION_SIZING_ENGINE",
    "ANALYTICAL",
    "TEST",
    "LEGACY",
    "SIMULATED",
}


@dataclass(frozen=True)
class RealRiskAllocationObservation:
    allocation_state: str
    allocated_risk: float | None
    source: str
    observed_at: str
    provenance: Mapping[str, str]
    validation: str
    reason: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "allocation_state": self.allocation_state,
            "allocated_risk": self.allocated_risk,
            "source": self.source,
            "observed_at": self.observed_at,
            "provenance": dict(self.provenance),
            "validation": self.validation,
            "reason": self.reason,
            "composition_version": VERSION,
            "synthetic": False,
            "interpolation": False,
            "fill": False,
            "backfill": False,
            "padding": False,
            "blending": False,
            "db_writes": 0,
            "execution": False,
        }


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if not isfinite(result):
        return None

    return result


def validate_real_risk_allocation(
    observation: Mapping[str, Any],
) -> RealRiskAllocationObservation:

    if not isinstance(observation, Mapping):
        raise TypeError("observation must be a Mapping")

    source = observation.get("source")
    observed_at = observation.get("observed_at")
    provenance = observation.get("provenance")

    if not isinstance(source, str) or not source:
        return RealRiskAllocationObservation(
            allocation_state="UNAVAILABLE",
            allocated_risk=None,
            source="",
            observed_at="",
            provenance={},
            validation="INVALID",
            reason="RISK_ALLOCATION_SOURCE_INVALID",
        )

    if source.upper() in FORBIDDEN_SOURCES:
        return RealRiskAllocationObservation(
            allocation_state="UNAVAILABLE",
            allocated_risk=None,
            source=source,
            observed_at=(
                observed_at
                if isinstance(observed_at, str)
                else ""
            ),
            provenance={},
            validation="INVALID",
            reason="FORBIDDEN_RISK_ALLOCATION_SOURCE",
        )

    if not isinstance(observed_at, str) or not observed_at:
        return RealRiskAllocationObservation(
            allocation_state="UNAVAILABLE",
            allocated_risk=None,
            source=source,
            observed_at="",
            provenance={},
            validation="INVALID",
            reason="RISK_ALLOCATION_TIMESTAMP_INVALID",
        )

    if not isinstance(provenance, Mapping) or not provenance:
        return RealRiskAllocationObservation(
            allocation_state="UNAVAILABLE",
            allocated_risk=None,
            source=source,
            observed_at=observed_at,
            provenance={},
            validation="INVALID",
            reason="RISK_ALLOCATION_PROVENANCE_INVALID",
        )

    normalized_provenance = {}

    for key, value in provenance.items():
        if (
            isinstance(key, str)
            and key
            and isinstance(value, str)
            and value
        ):
            normalized_provenance[key] = value

    if not normalized_provenance:
        return RealRiskAllocationObservation(
            allocation_state="UNAVAILABLE",
            allocated_risk=None,
            source=source,
            observed_at=observed_at,
            provenance={},
            validation="INVALID",
            reason="RISK_ALLOCATION_PROVENANCE_INVALID",
        )

    allocated_risk = _number(
        observation.get("allocated_risk")
    )

    if allocated_risk is None or allocated_risk < 0:
        return RealRiskAllocationObservation(
            allocation_state="UNAVAILABLE",
            allocated_risk=None,
            source=source,
            observed_at=observed_at,
            provenance=normalized_provenance,
            validation="INVALID",
            reason="ALLOCATED_RISK_INVALID",
        )

    allocation_state = observation.get("allocation_state")

    if allocation_state not in ("AVAILABLE", "REAL"):
        return RealRiskAllocationObservation(
            allocation_state="UNAVAILABLE",
            allocated_risk=None,
            source=source,
            observed_at=observed_at,
            provenance=normalized_provenance,
            validation="INVALID",
            reason="RISK_ALLOCATION_STATE_INVALID",
        )

    return RealRiskAllocationObservation(
        allocation_state="REAL",
        allocated_risk=allocated_risk,
        source=source,
        observed_at=observed_at,
        provenance=normalized_provenance,
        validation="VALID",
        reason="REAL_RISK_ALLOCATION_OBSERVED",
    )
