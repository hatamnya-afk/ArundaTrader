"""CP49 provider preflight contract. Read-only and provider-neutral."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Mapping

from cp49_first_execution_contract_v0_1 import OrderIntentBoundary


@dataclass(frozen=True)
class ProviderPreflightEvidence:
    venue: str
    symbol: str
    authenticated: bool
    account_state_fresh: bool
    symbol_valid: bool
    constraints_resolved: bool
    balance_consistent: bool
    position_state_consistent: bool
    timestamp_valid: bool
    safety_consistent: bool
    metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ProviderPreflightResult:
    status: str
    reason: str
    intent_id: str
    evidence: ProviderPreflightEvidence | None = None


def evaluate_provider_preflight(
    intent: OrderIntentBoundary,
    evidence: ProviderPreflightEvidence,
) -> ProviderPreflightResult:
    if not isinstance(intent, OrderIntentBoundary):
        return ProviderPreflightResult("BLOCK", "ORDER_INTENT_INVALID", "")
    if not isinstance(evidence, ProviderPreflightEvidence):
        return ProviderPreflightResult("BLOCK", "PREFLIGHT_EVIDENCE_INVALID", intent.intent_id)
    if intent.validate().value != "READY":
        return ProviderPreflightResult("BLOCK", "ORDER_INTENT_NOT_READY", intent.intent_id)

    if str(evidence.venue).upper().strip() != str(intent.venue).upper().strip():
        return ProviderPreflightResult("BLOCK", "VENUE_MISMATCH", intent.intent_id, evidence)
    if not evidence.symbol.strip() or evidence.symbol.upper().replace("-", "") != intent.asset.upper().replace("-", ""):
        return ProviderPreflightResult("BLOCK", "SYMBOL_MISMATCH", intent.intent_id, evidence)

    checks = (
        ("AUTHENTICATION_FAILED", evidence.authenticated),
        ("PROVIDER_STATE_STALE", evidence.account_state_fresh),
        ("SYMBOL_INVALID", evidence.symbol_valid),
        ("CONSTRAINTS_UNRESOLVED", evidence.constraints_resolved),
        ("BALANCE_CONFLICT", evidence.balance_consistent),
        ("POSITION_STATE_CONFLICT", evidence.position_state_consistent),
        ("TIMESTAMP_INVALID", evidence.timestamp_valid),
        ("EXECUTION_SAFETY_INCONSISTENT", evidence.safety_consistent),
    )
    for reason, passed in checks:
        if not passed:
            return ProviderPreflightResult("BLOCK", reason, intent.intent_id, evidence)

    return ProviderPreflightResult("PASS", "PROVIDER_PREFLIGHT_PASS", intent.intent_id, evidence)
