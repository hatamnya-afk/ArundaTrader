"""Provider-neutral, read-only order-attempt reconciliation policy.

This module is a pure contract/policy helper. It performs no network or file I/O,
does not submit/cancel orders, and is NOT wired into the production pipeline.

Safety rule: a missing result from a provider lookup is not proof that a prior
submission was rejected or never accepted. Unknown/ambiguous states stay blocked.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


LookupState = Literal["FOUND", "NOT_FOUND", "MULTIPLE", "ERROR"]
AttemptHistory = Literal["NO_PRIOR_ATTEMPT", "PRIOR_ATTEMPT_FOUND", "UNKNOWN"]


@dataclass(frozen=True)
class ProviderOrderLookup:
    """One read-only lookup observation from an adapter-owned provider query."""

    state: LookupState
    client_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    provider_status: Optional[str] = None
    detail_code: Optional[str] = None


@dataclass(frozen=True)
class ReconciliationDecision:
    """Fail-closed decision; this contract never authorizes a resubmission."""

    state: str
    may_submit: bool
    retry_allowed: bool
    reason_code: str
    exchange_order_id: Optional[str] = None


def evaluate_order_reconciliation(
    *,
    expected_client_order_id: str,
    prior_attempt: AttemptHistory,
    lookup: Optional[ProviderOrderLookup],
) -> ReconciliationDecision:
    """Classify available evidence without ever authorizing automatic retry.

    The adapter must generate the stable provider client-order ID deterministically
    from the canonical intent and provider constraints. The caller must persist it
    with the attempt evidence. This helper only compares the observed identifier;
    it cannot prove provider-side idempotency or lookup consistency.
    """
    expected = expected_client_order_id.strip() if isinstance(expected_client_order_id, str) else ""
    if not expected:
        return ReconciliationDecision(
            state="BLOCKED", may_submit=False, retry_allowed=False,
            reason_code="CLIENT_ORDER_ID_REQUIRED",
        )

    if prior_attempt == "UNKNOWN":
        return ReconciliationDecision(
            state="RECONCILIATION_REQUIRED", may_submit=False, retry_allowed=False,
            reason_code="PRIOR_ATTEMPT_HISTORY_UNKNOWN",
        )

    if prior_attempt == "PRIOR_ATTEMPT_FOUND":
        if lookup is None:
            return ReconciliationDecision(
                state="RECONCILIATION_REQUIRED", may_submit=False, retry_allowed=False,
                reason_code="PRIOR_ATTEMPT_REQUIRES_PROVIDER_LOOKUP",
            )
        if lookup.state == "FOUND":
            if lookup.client_order_id != expected:
                return ReconciliationDecision(
                    state="AMBIGUOUS", may_submit=False, retry_allowed=False,
                    reason_code="PROVIDER_CLIENT_ORDER_ID_MISMATCH",
                    exchange_order_id=lookup.exchange_order_id,
                )
            if not lookup.exchange_order_id:
                return ReconciliationDecision(
                    state="AMBIGUOUS", may_submit=False, retry_allowed=False,
                    reason_code="PROVIDER_ORDER_ID_MISSING",
                )
            return ReconciliationDecision(
                state="MATCHED", may_submit=False, retry_allowed=False,
                reason_code="PRIOR_ORDER_MATCHED_NO_RESUBMIT",
                exchange_order_id=lookup.exchange_order_id,
            )
        if lookup.state == "NOT_FOUND":
            return ReconciliationDecision(
                state="RECONCILIATION_REQUIRED", may_submit=False, retry_allowed=False,
                reason_code="NOT_FOUND_DOES_NOT_PROVE_NON_ACCEPTANCE",
            )
        if lookup.state == "MULTIPLE":
            return ReconciliationDecision(
                state="AMBIGUOUS", may_submit=False, retry_allowed=False,
                reason_code="MULTIPLE_PROVIDER_ORDERS_FOUND",
            )
        return ReconciliationDecision(
            state="RECONCILIATION_REQUIRED", may_submit=False, retry_allowed=False,
            reason_code="PROVIDER_LOOKUP_FAILED",
        )

    # No prior attempt is the only state where this *policy helper* does not
    # identify an existing attempt. It still does not authorize submission:
    # authorization/readiness and an atomic durable intent claim are separate.
    if prior_attempt == "NO_PRIOR_ATTEMPT":
        if lookup is not None and lookup.state == "FOUND":
            if lookup.client_order_id != expected or not lookup.exchange_order_id:
                return ReconciliationDecision(
                    state="AMBIGUOUS", may_submit=False, retry_allowed=False,
                    reason_code="PROVIDER_ORDER_IDENTITY_UNVERIFIED",
                    exchange_order_id=lookup.exchange_order_id,
                )
            return ReconciliationDecision(
                state="MATCHED", may_submit=False, retry_allowed=False,
                reason_code="PROVIDER_ORDER_ALREADY_EXISTS_NO_RESUBMIT",
                exchange_order_id=lookup.exchange_order_id,
            )
        if lookup is not None and lookup.state in ("MULTIPLE", "ERROR"):
            return ReconciliationDecision(
                state="AMBIGUOUS" if lookup.state == "MULTIPLE" else "RECONCILIATION_REQUIRED",
                may_submit=False, retry_allowed=False,
                reason_code="PROVIDER_LOOKUP_AMBIGUOUS" if lookup.state == "MULTIPLE" else "PROVIDER_LOOKUP_FAILED",
            )
        if lookup is not None and lookup.state == "NOT_FOUND":
            return ReconciliationDecision(
                state="RECONCILIATION_REQUIRED", may_submit=False, retry_allowed=False,
                reason_code="NOT_FOUND_NOT_AN_IDEMPOTENCY_GUARANTEE",
            )
        return ReconciliationDecision(
            state="PRECHECK_ONLY", may_submit=False, retry_allowed=False,
            reason_code="SEPARATE_ATOMIC_CLAIM_AND_AUTHORIZATION_REQUIRED",
        )

    return ReconciliationDecision(
        state="BLOCKED", may_submit=False, retry_allowed=False,
        reason_code="PRIOR_ATTEMPT_STATE_INVALID",
    )


__all__ = [
    "ProviderOrderLookup",
    "ReconciliationDecision",
    "evaluate_order_reconciliation",
]
