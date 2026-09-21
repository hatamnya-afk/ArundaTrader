"""
CP44 Production Intelligence Boundary v0.1

Purpose
-------
Provider-neutral, read-only boundary for CP44 live predictive evidence,
reliability/uncertainty, relative conviction and allocation candidate flow.

Governance
----------
- Production formula remains UNFROZEN.
- No outcome/future-label leakage into live evidence.
- No probability semantics.
- No capital/risk/position-size/exposure semantics.
- No database writes.
- No runtime execution.
- No Smart Risk modification.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from cp44_predictive_evidence_contract_v0_1 import (
    PredictiveEvidence,
)
from cp44_reliability_uncertainty_contract_v0_1 import (
    ReliabilityUncertainty,
)
from cp44_relative_conviction_contract_v0_1 import (
    RelativeConviction,
)
from cp44_relative_allocation_intent_v0_1 import (
    METHOD_UNFROZEN,
    build_relative_allocation_intent,
)


EXECUTION = False
DB_WRITES = 0
RUNTIME_EXECUTED = False
PRODUCTION_FORMULA_FROZEN = False

FORBIDDEN_LIVE_FIELDS = {
    "outcome",
    "future_outcome",
    "label",
    "future_label",
    "realized_return",
    "pnl",
    "exit_price",
    "post_outcome",
    "calibrated_probability",
}

ALLOWED_DIRECTIONS = {"LONG", "SHORT"}


def _finite(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _reject_forbidden_live_input(record: Mapping[str, Any]) -> None:
    if not isinstance(record, Mapping):
        raise ValueError("LIVE_INPUT_MUST_BE_MAPPING")

    present = {
        str(key).strip().lower()
        for key in record.keys()
    }

    forbidden = sorted(present & FORBIDDEN_LIVE_FIELDS)

    if forbidden:
        raise ValueError(
            "FUTURE_OUTCOME_LEAKAGE_FORBIDDEN:"
            + ",".join(forbidden)
        )


def build_live_predictive_evidence(
    *,
    asset: str,
    direction: str,
    evidence: float,
    source: str,
    observed_at: str,
    provenance: str,
) -> dict[str, Any]:
    """
    Construct validated live predictive evidence.

    The evidence is deliberately NOT interpreted as probability.
    """
    direction = str(direction).upper()

    if direction not in ALLOWED_DIRECTIONS:
        raise ValueError("INVALID_DIRECTION")

    observation = PredictiveEvidence(
        asset=str(asset),
        direction=direction,
        evidence=float(evidence),
        source=str(source),
        observed_at=str(observed_at),
        provenance=str(provenance),
        validation="VALID",
    )

    return {
        "asset": observation.asset,
        "direction": observation.direction,
        "evidence": observation.evidence,
        "source": observation.source,
        "observed_at": observation.observed_at,
        "provenance": observation.provenance,
        "validation": observation.validation,
        "probability": False,
        "future_outcome_used": False,
        "db_writes": 0,
        "execution": False,
    }


def build_live_reliability_uncertainty(
    *,
    asset: str,
    reliability: float,
    uncertainty: float,
    source: str,
    observed_at: str,
    provenance: str,
) -> dict[str, Any]:
    """
    Construct validated current-time reliability and uncertainty.

    These are bounded quality signals, not probabilities.
    """
    if not _finite(reliability) or not 0.0 <= float(reliability) <= 1.0:
        raise ValueError("INVALID_RELIABILITY")

    if not _finite(uncertainty) or not 0.0 <= float(uncertainty) <= 1.0:
        raise ValueError("INVALID_UNCERTAINTY")

    observation = ReliabilityUncertainty(
        asset=str(asset),
        reliability=float(reliability),
        uncertainty=float(uncertainty),
        source=str(source),
        observed_at=str(observed_at),
        provenance=str(provenance),
        validation="VALID",
    )

    return {
        "asset": observation.asset,
        "reliability": observation.reliability,
        "uncertainty": observation.uncertainty,
        "source": observation.source,
        "observed_at": observation.observed_at,
        "provenance": observation.provenance,
        "validation": observation.validation,
        "probability": False,
        "future_outcome_used": False,
        "db_writes": 0,
        "execution": False,
    }


def build_candidate_relative_conviction(
    *,
    evidence_record: Mapping[str, Any],
    reliability_record: Mapping[str, Any],
    method: str = "EVIDENCE_RELIABILITY_UNCERTAINTY_CANDIDATE",
) -> dict[str, Any]:
    """
    Candidate-only conviction construction.

    IMPORTANT:
    This does not freeze or activate a production formula.

    Candidate decomposition:
        conviction ∝ evidence × reliability × (1 - uncertainty)

    The result is explicitly marked candidate/unfrozen.
    """
    _reject_forbidden_live_input(evidence_record)
    _reject_forbidden_live_input(reliability_record)

    asset = str(evidence_record.get("asset", ""))
    if not asset:
        raise ValueError("MISSING_ASSET")

    if asset != str(reliability_record.get("asset", "")):
        raise ValueError("ASSET_MISMATCH")

    evidence = evidence_record.get("evidence")
    reliability = reliability_record.get("reliability")
    uncertainty = reliability_record.get("uncertainty")

    if not _finite(evidence):
        raise ValueError("INVALID_EVIDENCE")

    if not _finite(reliability) or not 0.0 <= float(reliability) <= 1.0:
        raise ValueError("INVALID_RELIABILITY")

    if not _finite(uncertainty) or not 0.0 <= float(uncertainty) <= 1.0:
        raise ValueError("INVALID_UNCERTAINTY")

    raw = abs(float(evidence)) * float(reliability)
    raw *= 1.0 - float(uncertainty)

    # Candidate normalization only.
    # This is intentionally NOT a frozen production formula.
    conviction = max(0.0, min(1.0, raw))

    observation = RelativeConviction(
        asset=asset,
        conviction=conviction,
        evidence=float(evidence),
        reliability=float(reliability),
        uncertainty=float(uncertainty),
        method=str(method),
        source=(
            f"{evidence_record.get('source', '')}|"
            f"{reliability_record.get('source', '')}"
        ),
        provenance=(
            f"{evidence_record.get('provenance', '')}|"
            f"{reliability_record.get('provenance', '')}"
        ),
        validation="VALID",
    )

    return {
        "asset": observation.asset,
        "conviction": observation.conviction,
        "evidence": observation.evidence,
        "reliability": observation.reliability,
        "uncertainty": observation.uncertainty,
        "method": observation.method,
        "source": observation.source,
        "provenance": observation.provenance,
        "validation": observation.validation,
        "candidate_only": True,
        "production_formula_frozen": False,
        "db_writes": 0,
        "execution": False,
    }


def build_production_allocation_intent(
    convictions: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Production allocation entry point.

    Since the formula is NOT frozen, this function MUST fail closed.
    No candidate formula is silently promoted to production.
    """
    if PRODUCTION_FORMULA_FROZEN:
        raise RuntimeError(
            "UNEXPECTED_STATE_PRODUCTION_FORMULA_FLAG"
        )

    # Explicitly invoke the existing boundary with the unfrozen method.
    # Its contract is expected to fail closed.
    return build_relative_allocation_intent(
        convictions,
        method=METHOD_UNFROZEN,
    )


def inspect_governance() -> dict[str, Any]:
    return {
        "status": "READY_BOUNDARY_ONLY",
        "execution": EXECUTION,
        "db_writes": DB_WRITES,
        "runtime_executed": RUNTIME_EXECUTED,
        "production_formula_frozen": PRODUCTION_FORMULA_FROZEN,
        "future_outcome_used": False,
        "probability_created": False,
        "capital_used": False,
        "risk_budget_used": False,
        "position_size_used": False,
        "exposure_used": False,
        "smart_risk_modified": False,
        "production_allocation_activation": False,
    }
