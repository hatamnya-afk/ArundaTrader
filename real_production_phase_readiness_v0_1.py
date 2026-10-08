"""Real-production phase-entry readiness contract.

Pure governance/readiness validation. No provider calls, no order submission,
no DB mutation, no pipeline wiring, and no execution activation.

The contract validates whether the project has enough evidence to present ONE
phase-entry decision to management. If that decision is later AUTHORIZED, the
standing mandate applies to autonomous Spot/Futures operation; no per-trade
management approval is required.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


REAL_PRODUCTION = "REAL_PRODUCTION"
REQUIRED_MARKETS = frozenset({"SPOT", "FUTURES"})


def evaluate_phase_entry_readiness(
    *,
    environment: str,
    management_decision: str,
    allowed_markets: Sequence[str],
    canonical_order_path_verified: bool,
    execution_attempt_contract_verified: bool,
    provider_read_only_evidence_verified: bool,
    decision_risk_trade_gate_verified: bool,
    zero_balance_allowed: bool,
    no_per_trade_management_approval: bool,
    evidence_requirements: Sequence[str],
) -> dict[str, Any]:
    if environment != REAL_PRODUCTION:
        return {"ready": False, "blocker": "ENVIRONMENT_NOT_REAL_PRODUCTION"}
    if management_decision not in {"PENDING", "AUTHORIZED", "DENIED", "DEFERRED"}:
        return {"ready": False, "blocker": "INVALID_MANAGEMENT_DECISION"}

    markets = frozenset(str(x).upper() for x in allowed_markets)
    if not REQUIRED_MARKETS.issubset(markets):
        return {"ready": False, "blocker": "SPOT_FUTURES_SCOPE_INCOMPLETE"}
    if not canonical_order_path_verified:
        return {"ready": False, "blocker": "CANONICAL_ORDER_PATH_NOT_VERIFIED"}
    if not execution_attempt_contract_verified:
        return {"ready": False, "blocker": "EXECUTION_ATTEMPT_CONTRACT_NOT_VERIFIED"}
    if not provider_read_only_evidence_verified:
        return {"ready": False, "blocker": "PROVIDER_READ_ONLY_EVIDENCE_NOT_VERIFIED"}
    if not decision_risk_trade_gate_verified:
        return {"ready": False, "blocker": "DECISION_RISK_TRADE_GATE_NOT_VERIFIED"}
    if not zero_balance_allowed:
        return {"ready": False, "blocker": "ZERO_BALANCE_POLICY_MUST_BE_ALLOWED"}
    if not no_per_trade_management_approval:
        return {"ready": False, "blocker": "PER_TRADE_MANAGEMENT_APPROVAL_MUST_BE_DISABLED"}

    evidence = tuple(str(x).strip() for x in evidence_requirements if str(x).strip())
    if not evidence:
        return {"ready": False, "blocker": "EVIDENCE_REQUIREMENTS_EMPTY"}

    return {
        "ready": True,
        "management_decision": management_decision,
        "phase": "REAL_PRODUCTION_TRADING",
        "allowed_markets": tuple(sorted(markets)),
        "autonomous_operation_after_authorization": True,
        "per_trade_management_approval_required": False,
        "zero_balance_is_not_local_trade_blocker": True,
        "provider_acceptance_rejection_is_authoritative": True,
        "evidence_requirements": evidence,
        "execution_authorization": (
            "AUTHORIZED_STANDING_MANDATE"
            if management_decision == "AUTHORIZED"
            else False
        ),
    }
