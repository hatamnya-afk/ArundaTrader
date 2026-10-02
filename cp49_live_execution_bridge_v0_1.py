"""CP49 live execution bridge.

Connects an already-built CanonicalOrderRequest to the existing execution
boundary and Toobit live spot transport.

Capital is deliberately absent from this bridge. Account capital is an
external provider state; provider rejection is preserved as execution
evidence.

Default management execution authorization is FAIL-CLOSED and must be
explicitly enabled with ARUNDA_EXECUTION_MANAGEMENT_AUTHORIZED=TRUE.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any

from account_balance_observation_v0_1 import build_account_balance_observation
from cp46_e_execution_eligibility_v0_1 import build_execution_eligibility
from cp49_first_execution_evidence_contract_v0_1 import (
    build_account_signature_evidence,
)
from cp49_first_execution_readiness_v0_1 import (
    FirstExecutionReadinessInput,
    evaluate_first_execution_readiness,
)
from cp49_readiness_to_execution_gate_binding_v0_1 import (
    build_execution_safety_gate,
)
from exchange_execution_boundary import execute_order
from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
)
from toobit_spot_order_live_transport_v0_1 import (
    ToobitSpotOrderLiveTransport,
)


MANAGEMENT_AUTH_ENV = "ARUNDA_EXECUTION_MANAGEMENT_AUTHORIZED"


def management_execution_authorized() -> bool:
    return os.getenv(MANAGEMENT_AUTH_ENV, "").strip().upper() == "TRUE"


def attach_live_transport(adapter: Any) -> Any:
    if adapter is None:
        raise RuntimeError("TOOBIT_ADAPTER_REQUIRED")

    transport = getattr(adapter, "live_order_transport", None)
    if transport is None:
        transport = ToobitSpotOrderLiveTransport(
            api_key=getattr(adapter, "api_key", None),
            api_secret=getattr(adapter, "api_secret", None),
            session=getattr(adapter, "session", None),
        )
        adapter.live_order_transport = transport

    return adapter


def _evidence_id(
    request: CanonicalOrderRequest,
    account_id: str,
) -> str:
    raw = "|".join(
        (
            request.intent_id,
            request.snapshot_id,
            account_id,
            "AUTHENTICATED_ACCOUNT_READ",
        )
    )
    return "EVID-" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def execute_canonical_request(
    *,
    adapter: Any,
    request: CanonicalOrderRequest,
    provider_preflight_result: Any,
    management_authorized: bool | None = None,
) -> CanonicalExecutionResult:
    if not isinstance(request, CanonicalOrderRequest):
        raise TypeError("CANONICAL_REQUEST_REQUIRED")

    if management_authorized is None:
        management_authorized = management_execution_authorized()

    attach_live_transport(adapter)

    account_observation = build_account_balance_observation(adapter)
    api_key_result = adapter.api_key_check()

    account_signature_evidence = build_account_signature_evidence(
        api_key_result=api_key_result,
        account_observation=account_observation,
        evidence_id=_evidence_id(
            request,
            account_observation.account.account_id or "UNKNOWN",
        ),
        observed_at=account_observation.account.retrieved_at,
    )

    signature_verified = (
        account_signature_evidence is not None
        and account_signature_evidence.validate()
    )
    account_read_verified = (
        account_observation.account.status == "PASS"
        and account_observation.account.account_id is not None
    )

    handoff = getattr(provider_preflight_result, "handoff", None)
    eligibility = build_execution_eligibility(
        request,
        handoff,
    )

    readiness = evaluate_first_execution_readiness(
        readiness=FirstExecutionReadinessInput(
            implementation_verified=True,
            prior_attempt_exists=False,
            automatic_retry_enabled=False,
            account_read_verified=account_read_verified,
            signature_verified=signature_verified,
            # Capital is intentionally not an execution prerequisite.
            capital_authorized=False,
            provider_constraints_verified=(
                getattr(provider_preflight_result, "status", None) == "PASS"
            ),
            management_authorized=management_authorized,
            execution_enabled=False,
            order_submission_enabled=False,
            exchange_write_enabled=False,
            database_write_enabled=False,
            account_signature_evidence=account_signature_evidence,
            capital_authorization_evidence=None,
            authorized_account_id=(
                account_observation.account.account_id
            ),
        ),
        canonical_request=request,
        eligibility=eligibility,
    )

    if readiness.state.value != "READY_FOR_AUTHORIZATION":
        from exchange_execution_contract import blocked_execution_result

        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="CP49_READINESS_BLOCKED",
            error_message=";".join(readiness.blockers),
            adapter="TOOBIT",
        )

    gate = build_execution_safety_gate(
        readiness=readiness,
        management_authorized=management_authorized,
        prior_attempt_exists=False,
        automatic_retry_enabled=False,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
    )

    return execute_order(
        request=request,
        adapter=adapter,
        eligibility=eligibility,
        safety_gate=gate,
    )


__all__ = [
    "MANAGEMENT_AUTH_ENV",
    "management_execution_authorized",
    "attach_live_transport",
    "execute_canonical_request",
]
