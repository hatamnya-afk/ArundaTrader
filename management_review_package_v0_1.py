"""Management review package for the one-time real-production phase-entry decision.

This module is review packaging only. It is NOT an authorization producer and
must never issue, mirror, or synthesize an execution-authorization result.
The single canonical management authorization owner is
management_execution_authorization_v0_1.py.

This module does not submit orders, contact providers, mutate databases, enable
execution, or infer provider acceptance. It packages the management decision
inputs and policy evidence for review. Individual trade decisions remain the
responsibility of the existing decision/risk/trade-gate chain, while the
provider remains authoritative for acceptance/rejection.

IMPORTANT: execution_authorization and per-trade authorization state are
intentionally absent from this package. A management review package is not a
second authorization boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


REAL_PRODUCTION = "REAL_PRODUCTION"
ALLOWED_MARKETS = frozenset({"SPOT", "FUTURES"})


@dataclass(frozen=True)
class ManagementReviewPackage:
    mandate_id: str
    decision: str
    authorized_by: str
    authorization_source: str
    environment: str
    allowed_markets: tuple[str, ...]
    provider: str
    autonomous_operation: bool
    provider_rejection_is_authoritative: bool
    capital_policy: str
    evidence_required_before: tuple[str, ...]
    evidence_required_after: tuple[str, ...]


def build_management_review_package(
    *,
    mandate_id: str,
    decision: str,
    authorized_by: str,
    authorization_source: str,
    environment: str,
    allowed_markets: Sequence[str],
    provider: str,
    capital_policy: str,
    evidence_required_before: Sequence[str],
    evidence_required_after: Sequence[str],
) -> dict[str, Any]:
    if decision not in {"AUTHORIZED", "DENIED", "DEFERRED"}:
        raise ValueError("invalid management decision")
    if not mandate_id.strip() or not authorized_by.strip():
        raise ValueError("mandate identity and authorized_by are required")
    if not authorization_source.strip():
        raise ValueError("authorization_source is required")
    if environment != REAL_PRODUCTION:
        raise ValueError("management mandate requires REAL_PRODUCTION")
    if not provider.strip():
        raise ValueError("provider is required")
    if not capital_policy.strip():
        raise ValueError("capital_policy is required")

    markets = tuple(dict.fromkeys(str(m).upper() for m in allowed_markets))
    if not markets or not set(markets).issubset(ALLOWED_MARKETS):
        raise ValueError("allowed_markets must contain only SPOT and/or FUTURES")

    before = tuple(str(x).strip() for x in evidence_required_before if str(x).strip())
    after = tuple(str(x).strip() for x in evidence_required_after if str(x).strip())
    if not before or not after:
        raise ValueError("before/after evidence requirements are mandatory")

    return {
        "management_state": decision,
        "mandate_id": mandate_id,
        "authorized_by": authorized_by,
        "authorization_source": authorization_source,
        "environment": environment,
        "allowed_markets": markets,
        "provider": provider,
        "autonomous_operation_after_phase_entry": decision == "AUTHORIZED",
        "per_trade_management_authorization_required": False,
        "provider_rejection_is_authoritative": True,
        "capital_policy": capital_policy,
        "evidence_required_before": before,
        "evidence_required_after": after,
    }
