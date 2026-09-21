"""CP44 Live Predictive Evidence Bridge v0.1.

Purpose
-------
Create a live PredictiveEvidence contract only when an upstream producer
supplies an explicit evidence observation.

Governance
----------
- Opportunity score is NOT evidence.
- Score/confidence are never reinterpreted as evidence.
- No probability semantics.
- No future/outcome/calibration fields.
- No historical DB reads.
- No database writes.
- No execution.
- No production formula activation.
"""

from __future__ import annotations

from math import isfinite
from typing import Any, Mapping

from cp44_predictive_evidence_contract_v0_1 import PredictiveEvidence


EXECUTION = False
DB_WRITES = 0
RUNTIME_EXECUTED = False
PRODUCTION_FORMULA_FROZEN = False

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

REJECTED_REINTERPRETATION_FIELDS = frozenset(
    {
        "score",
        "opportunity_score",
        "confidence",
        "opportunity_confidence",
    }
)


def _finite(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("EVIDENCE_VALUE_INVALID") from exc

    if not isfinite(result):
        raise ValueError("EVIDENCE_VALUE_INVALID")

    return result


def _validate_input(observation: Mapping[str, Any]) -> None:
    if not isinstance(observation, Mapping):
        raise ValueError("LIVE_INPUT_MUST_BE_MAPPING")

    keys = {
        str(key).strip().lower()
        for key in observation.keys()
    }

    forbidden = sorted(
        keys.intersection(FORBIDDEN_LIVE_FIELDS)
    )
    if forbidden:
        raise ValueError(
            "FUTURE_OUTCOME_LEAKAGE_FORBIDDEN:"
            + ",".join(forbidden)
        )

    reinterpretation = sorted(
        keys.intersection(REJECTED_REINTERPRETATION_FIELDS)
    )
    if reinterpretation:
        raise ValueError(
            "EVIDENCE_REINTERPRETATION_FORBIDDEN:"
            + ",".join(reinterpretation)
        )

    required = (
        "asset",
        "direction",
        "evidence",
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
            "MISSING_EXPLICIT_EVIDENCE_FIELDS:"
            + ",".join(missing)
        )


def build_live_predictive_evidence_bridge(
    *,
    observation: Mapping[str, Any],
) -> PredictiveEvidence:
    """Build validated live evidence from an explicit evidence observation.

    The bridge deliberately refuses score/confidence/opportunity fields.
    Therefore it cannot silently convert an existing live score into
    PredictiveEvidence.
    """
    _validate_input(observation)

    evidence = PredictiveEvidence(
        asset=str(observation["asset"]).strip(),
        direction=str(observation["direction"]).strip().upper(),
        evidence=_finite(observation["evidence"]),
        source=str(observation["source"]).strip(),
        observed_at=str(observation["observed_at"]).strip(),
        provenance=str(observation["provenance"]).strip(),
        validation="VALID",
    )
    evidence.validate()
    return evidence


def inspect_governance() -> dict[str, Any]:
    return {
        "component": "CP44_LIVE_PREDICTIVE_EVIDENCE_BRIDGE_V0_1",
        "status": "READY_CONTRACT_PRESERVING_BRIDGE",
        "explicit_evidence_required": True,
        "opportunity_score_reinterpreted": False,
        "confidence_reinterpreted": False,
        "score_used_as_evidence": False,
        "probability_created": False,
        "future_information_used": False,
        "historical_outcomes_used": False,
        "calibration_used": False,
        "production_formula_frozen": PRODUCTION_FORMULA_FROZEN,
        "database_writes": DB_WRITES,
        "execution": EXECUTION,
        "runtime_executed": RUNTIME_EXECUTED,
        "smart_risk_modified": False,
    }


__all__ = [
    "build_live_predictive_evidence_bridge",
    "inspect_governance",
]
