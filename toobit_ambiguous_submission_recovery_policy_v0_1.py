"""Fail-closed decision policy for ambiguous Toobit Futures submissions.

Pure policy only: no network, database, or exchange writes. Once a POST may
have reached Toobit, absence from lookup is not evidence of non-acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class LookupObservation:
    state: str  # FOUND, NOT_FOUND, MULTIPLE, ERROR
    client_order_id: Optional[str] = None
    exchange_order_id: Optional[str] = None
    provider_status: Optional[str] = None
    detail_code: Optional[str] = None


@dataclass(frozen=True)
class RecoveryPlan:
    state: str
    safe_read_only_actions: tuple[str, ...]
    may_submit: bool
    retry_allowed: bool
    claim_release_allowed: bool
    requires_human_reconciliation: bool
    reason_code: str


def plan_ambiguous_submission_recovery(
    *, prior_post_may_have_reached_provider: bool,
    expected_client_order_id: str,
    lookup: Optional[LookupObservation],
) -> RecoveryPlan:
    """Return a safe plan; this function can never authorize a POST or retry."""
    expected = expected_client_order_id.strip() if isinstance(expected_client_order_id, str) else ""
    if not expected:
        return RecoveryPlan(
            "BLOCKED", ("PRESERVE_EVIDENCE",), False, False, False, True,
            "CLIENT_ORDER_ID_REQUIRED",
        )

    if not prior_post_may_have_reached_provider:
        return RecoveryPlan(
            "PRE_SUBMISSION_ONLY", ("VERIFY_DURABLE_CLAIM_AND_AUTHORIZATION",),
            False, False, False, False, "SEPARATE_SUBMISSION_BOUNDARY_REQUIRED",
        )

    if lookup is not None and lookup.state == "FOUND":
        if lookup.client_order_id != expected or not lookup.exchange_order_id:
            return RecoveryPlan(
                "IDENTITY_UNVERIFIED", ("PRESERVE_EVIDENCE", "ESCALATE_FOR_RECONCILIATION"),
                False, False, False, True, "FOUND_ORDER_IDENTITY_INCOMPLETE_OR_MISMATCH",
            )
        return RecoveryPlan(
            "ORDER_MATCHED",
            ("PERSIST_MATCHED_ORDER_EVIDENCE", "CONTINUE_READ_ONLY_STATUS_RECONCILIATION"),
            False, False, False, False, "MATCHED_ORDER_NEVER_RESUBMIT",
        )

    if lookup is not None and lookup.state == "MULTIPLE":
        return RecoveryPlan(
            "AMBIGUOUS_MULTIPLE_MATCHES", ("PRESERVE_ALL_MATCHES", "ESCALATE_FOR_RECONCILIATION"),
            False, False, False, True, "MULTIPLE_PROVIDER_MATCHES",
        )

    if lookup is not None and lookup.state == "ERROR":
        code = (lookup.detail_code or "").upper()
        if code in {"ORDER_DUPLICATED", "-1141"}:
            reason = "DUPLICATE_ERROR_DOES_NOT_REPLAY_ORIGINAL_ORDER"
        else:
            reason = "PROVIDER_ERROR_NOT_PROOF_OF_NON_ACCEPTANCE"
        return RecoveryPlan(
            "OUTCOME_UNRESOLVED",
            ("REPEAT_READ_ONLY_ORDER_LOOKUP", "MANUAL_HISTORY_INVESTIGATION", "ESCALATE_FOR_RECONCILIATION"),
            False, False, False, True, reason,
        )

    # NOT_FOUND or no lookup: Toobit supplies no propagation bound or official
    # recovery procedure; history is not an exhaustive client-ID lookup.
    return RecoveryPlan(
        "QUARANTINED_OUTCOME_UNKNOWN",
        ("REPEAT_READ_ONLY_ORDER_LOOKUP", "MANUAL_HISTORY_INVESTIGATION", "ESCALATE_FOR_RECONCILIATION"),
        False, False, False, True, "NO_SUCH_ORDER_DOES_NOT_PROVE_NON_ACCEPTANCE",
    )


__all__ = ["LookupObservation", "RecoveryPlan", "plan_ambiguous_submission_recovery"]
