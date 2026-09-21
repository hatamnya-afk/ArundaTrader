from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from cp44_predictive_evidence_contract_v0_1 import PredictiveEvidence
from cp44_reliability_uncertainty_contract_v0_1 import (
    ReliabilityUncertainty,
)
from cp44_relative_conviction_contract_v0_1 import (
    RelativeConviction,
)
from cp44_production_intelligence_boundary_v0_1 import (
    build_candidate_relative_conviction,
)
from cp44_relative_allocation_intent_v0_1 import (
    METHOD_UNFROZEN,
    build_relative_allocation_intent,
)


EXECUTION_ENABLED = False
DB_WRITES = 0
RUNTIME_EXECUTED = False
PRODUCTION_FORMULA_FROZEN = False


@dataclass(frozen=True)
class LiveIntelligenceInput:
    """
    Provider-neutral live intelligence input.

    This boundary accepts already-validated live observations/evidence.
    It does not read historical DB state and does not create future outcomes.
    """
    predictive_evidence: PredictiveEvidence
    reliability_uncertainty: ReliabilityUncertainty
    provenance: Mapping[str, Any]


@dataclass(frozen=True)
class LiveIntelligenceResult:
    """
    Candidate-only intelligence result.

    Allocation remains an intent, not capital, exposure, position size,
    order quantity, or execution instruction.
    """
    conviction: RelativeConviction
    allocation_intent: dict[str, object]
    production_formula_frozen: bool
    execution_enabled: bool
    db_writes: int
    runtime_executed: bool


def _validate_live_input(
    item: LiveIntelligenceInput,
) -> None:
    if not isinstance(item.provenance, Mapping):
        raise ValueError("INVALID_PROVENANCE")

    if not item.provenance:
        raise ValueError("MISSING_PROVENANCE")

    for key in ("source", "observed_at"):
        value = item.provenance.get(key)
        if value in (None, ""):
            raise ValueError(f"MISSING_PROVENANCE:{key}")

    forbidden = {
        "future_outcome",
        "future_label",
        "realized_return",
        "pnl",
        "exit_price",
        "post_outcome",
        "calibrated_probability",
    }

    for key in forbidden:
        if key in item.provenance:
            raise ValueError(f"FORBIDDEN_LIVE_FIELD:{key}")


def build_live_intelligence_candidate(
    item: LiveIntelligenceInput,
) -> LiveIntelligenceResult:
    """
    Contractual integration boundary only.

    Flow:
        live observation/evidence
        -> reliability + uncertainty
        -> relative conviction
        -> candidate allocation intent

    Production allocation remains fail-closed while the formula is unfrozen.
    No capital, risk budget, position sizing, exposure, order or execution
    semantics are introduced here.
    """
    _validate_live_input(item)

    conviction_candidate = build_candidate_relative_conviction(
        evidence_record={
            "asset": item.predictive_evidence.asset,
            "evidence": item.predictive_evidence.evidence,
            "source": item.predictive_evidence.source,
            "observed_at": item.predictive_evidence.observed_at,
            "provenance": item.predictive_evidence.provenance,
        },
        reliability_record={
            "asset": item.reliability_uncertainty.asset,
            "reliability": item.reliability_uncertainty.reliability,
            "uncertainty": item.reliability_uncertainty.uncertainty,
            "source": item.reliability_uncertainty.source,
            "observed_at": item.reliability_uncertainty.observed_at,
            "provenance": item.reliability_uncertainty.provenance,
        },
    )

    conviction = RelativeConviction(
        asset=conviction_candidate["asset"],
        conviction=conviction_candidate["conviction"],
        evidence=conviction_candidate["evidence"],
        reliability=conviction_candidate["reliability"],
        uncertainty=conviction_candidate["uncertainty"],
        method=conviction_candidate["method"],
        source=conviction_candidate["source"],
        provenance=conviction_candidate["provenance"],
        validation=conviction_candidate["validation"],
    )

    conviction.validate()

    try:
        allocation_intent = build_relative_allocation_intent(
            {conviction.asset: conviction},
            method=METHOD_UNFROZEN,
        )
    except ValueError as exc:
        if str(exc) != "ALLOCATION_METHOD_NOT_APPROVED":
            raise

        allocation_intent = {
            "state": "UNFROZEN",
            "method": METHOD_UNFROZEN,
            "allocation_intent": None,
            "dynamic_universe": True,
            "fixed_15_used": False,
            "capital_used": False,
            "risk_budget_used": False,
            "position_size_used": False,
            "exposure_used": False,
            "production_formula_frozen": False,
            "validation": "FAIL_CLOSED",
            "reason": "ALLOCATION_METHOD_NOT_APPROVED",
        }

    return LiveIntelligenceResult(
        conviction=conviction,
        allocation_intent=allocation_intent,
        production_formula_frozen=PRODUCTION_FORMULA_FROZEN,
        execution_enabled=EXECUTION_ENABLED,
        db_writes=DB_WRITES,
        runtime_executed=RUNTIME_EXECUTED,
    )


def inspect_governance() -> dict[str, Any]:
    return {
        "status": "READY_CANDIDATE_BOUNDARY",
        "execution_enabled": EXECUTION_ENABLED,
        "db_writes": DB_WRITES,
        "runtime_executed": RUNTIME_EXECUTED,
        "production_formula_frozen": PRODUCTION_FORMULA_FROZEN,
        "historical_db_required": False,
        "capital_semantics": False,
        "risk_budget_semantics": False,
        "position_size_semantics": False,
        "exposure_semantics": False,
        "order_semantics": False,
        "execution_semantics": False,
        "method": METHOD_UNFROZEN,
    }
