"""ARUNDA TRADER — CONTROLLED FIRST-EXECUTION READINESS v0.1.

Provider-neutral, pure pre-activation readiness contract.

This module MUST NOT:
- enable execution
- enable order submission
- enable exchange writes
- contact an exchange
- write a database
- mutate a canonical order request
- authorize a first execution attempt

It only determines whether independently required prerequisites are satisfied
before Management may consider activation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from exchange_execution_contract import (
    CanonicalOrderRequest,
    validate_order_request,
)
from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from cp49_first_execution_evidence_contract_v0_1 import (
    AccountSignatureEvidence,
    RealCapitalAuthorizationEvidence,
)


class ReadinessState(str, Enum):
    BLOCKED = "BLOCKED"
    READY_FOR_AUTHORIZATION = "READY_FOR_AUTHORIZATION"


@dataclass(frozen=True)
class FirstExecutionReadinessInput:
    implementation_verified: bool
    prior_attempt_exists: bool
    automatic_retry_enabled: bool

    account_read_verified: bool
    signature_verified: bool
    capital_authorized: bool
    provider_constraints_verified: bool
    management_authorized: bool

    execution_enabled: bool
    order_submission_enabled: bool
    exchange_write_enabled: bool
    database_write_enabled: bool

    # These are authoritative evidence objects, not flags that grant access.
    # Readiness requires them whenever the corresponding verification flag is
    # asserted true.
    account_signature_evidence: Optional[AccountSignatureEvidence] = None
    capital_authorization_evidence: Optional[
        RealCapitalAuthorizationEvidence
    ] = None
    authorized_account_id: Optional[str] = None


@dataclass(frozen=True)
class FirstExecutionReadinessResult:
    state: ReadinessState
    blockers: tuple[str, ...]
    canonical_request_valid: bool
    eligibility_passed: bool


def evaluate_first_execution_readiness(
    *,
    readiness: FirstExecutionReadinessInput,
    canonical_request: Optional[CanonicalOrderRequest],
    eligibility: Optional[ExecutionEligibilityResult],
) -> FirstExecutionReadinessResult:
    """Pure readiness evaluation; no activation and no I/O."""

    blockers: list[str] = []

    if not readiness.implementation_verified:
        blockers.append("IMPLEMENTATION_NOT_VERIFIED")

    if readiness.prior_attempt_exists:
        blockers.append("PRIOR_ATTEMPT_EXISTS")

    if readiness.automatic_retry_enabled:
        blockers.append("AUTOMATIC_RETRY_ENABLED")

    if not readiness.account_read_verified:
        blockers.append("ACCOUNT_READ_NOT_VERIFIED")

    if not readiness.signature_verified:
        blockers.append("ACCOUNT_SIGNATURE_NOT_VERIFIED")
    elif readiness.account_signature_evidence is None:
        blockers.append("ACCOUNT_SIGNATURE_EVIDENCE_MISSING")
    elif not readiness.account_signature_evidence.validate():
        blockers.append("ACCOUNT_SIGNATURE_EVIDENCE_INVALID")

    if not readiness.provider_constraints_verified:
        blockers.append("PROVIDER_CONSTRAINTS_NOT_VERIFIED")

    if not readiness.capital_authorized:
        blockers.append("REAL_CAPITAL_NOT_AUTHORIZED")
    elif readiness.capital_authorization_evidence is None:
        blockers.append("REAL_CAPITAL_AUTHORIZATION_EVIDENCE_MISSING")
    elif not readiness.capital_authorization_evidence.validate():
        blockers.append("REAL_CAPITAL_AUTHORIZATION_EVIDENCE_INVALID")
    elif (
        readiness.authorized_account_id is None
        or readiness.capital_authorization_evidence.account_id
        != readiness.authorized_account_id
    ):
        blockers.append("CAPITAL_AUTHORIZATION_ACCOUNT_MISMATCH")

    if not readiness.management_authorized:
        blockers.append("MANAGEMENT_AUTHORIZATION_NOT_VERIFIED")

    if readiness.execution_enabled:
        blockers.append("EXECUTION_ALREADY_ENABLED_DURING_READINESS")

    if readiness.order_submission_enabled:
        blockers.append("ORDER_SUBMISSION_ALREADY_ENABLED_DURING_READINESS")

    if readiness.exchange_write_enabled:
        blockers.append("EXCHANGE_WRITE_ALREADY_ENABLED_DURING_READINESS")

    if readiness.database_write_enabled:
        blockers.append("DATABASE_WRITE_ENABLED")

    canonical_request_valid = False
    if not isinstance(canonical_request, CanonicalOrderRequest):
        blockers.append("CANONICAL_REQUEST_MISSING")
    else:
        canonical_request_valid, reason = validate_order_request(
            canonical_request
        )
        if not canonical_request_valid:
            blockers.append(f"CANONICAL_REQUEST_INVALID:{reason}")

    eligibility_passed = (
        isinstance(eligibility, ExecutionEligibilityResult)
        and eligibility.status == EligibilityStatus.PASS
    )

    if not eligibility_passed:
        blockers.append("CP46_E_ELIGIBILITY_NOT_PASSED")
    elif eligibility.canonical_request is not canonical_request:
        blockers.append("CP46_E_CANONICAL_REQUEST_MISMATCH")

    state = (
        ReadinessState.READY_FOR_AUTHORIZATION
        if not blockers
        else ReadinessState.BLOCKED
    )

    return FirstExecutionReadinessResult(
        state=state,
        blockers=tuple(blockers),
        canonical_request_valid=canonical_request_valid,
        eligibility_passed=eligibility_passed,
    )


__all__ = [
    "FirstExecutionReadinessInput",
    "FirstExecutionReadinessResult",
    "ReadinessState",
    "evaluate_first_execution_readiness",
]
