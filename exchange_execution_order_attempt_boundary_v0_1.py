"""ARUNDA TRADER — PROVIDER-NEUTRAL ORDER ATTEMPT BOUNDARY v0.1.

Final provider-neutral gate between a prepared adapter order and a future
provider order attempt.

NO automatic authorization.
NO exchange-specific logic.
NO database write.
The selected adapter owns provider submission behavior.
"""

from __future__ import annotations

from typing import Any, Mapping
from uuid import uuid4

from exchange_execution_adapter_contract_v0_1 import (
    AdapterOrderPreparation,
    validate_adapter_contract,
)
from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
    blocked_execution_result,
    validate_order_request,
)
from execution_authorization_boundary_v0_1 import evaluate_execution_authorization
from execution_attempt_readiness_contract_v0_1 import evaluate_execution_attempt_readiness
from exchange_execution_order_preparation_v0_1 import prepare_order_for_adapter


def attempt_prepared_order(
    *,
    request: CanonicalOrderRequest,
    readiness_observation: Mapping[str, Any],
    authorization_observation: Mapping[str, Any],
    adapter: Any,
    venue: str,
    execution_instrument: Any,
    execution_ready_package: Mapping[str, Any] | None = None,
    claim_store: Any = None,
) -> CanonicalExecutionResult:
    """Fail closed unless explicit valid authorization is present.

    Preparation is performed before submission so the provider-owned request
    exists at the final boundary. Authorization is never inferred from
    readiness, adapter capability, account state, or provider metadata.
    """

    valid, reason = validate_order_request(request)
    if not valid:
        return blocked_execution_result(
            asset=getattr(request, "asset", None),
            direction=getattr(request, "direction", None),
            error_code=reason,
            error_message=f"Canonical order request rejected: {reason}.",
        )

    contract_valid, contract_reason = validate_adapter_contract(adapter)
    if not contract_valid:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code=contract_reason,
            error_message=f"Execution adapter contract rejected: {contract_reason}.",
        )

    # Reject read-only adapters before claiming/quarantining an intent.
    # Capability discovery is local adapter metadata; it must not submit.
    try:
        capabilities = adapter.capabilities()
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="ADAPTER_CAPABILITIES_UNAVAILABLE",
            error_message=f"Adapter capability check failed closed: {exc}",
        )
    if getattr(capabilities, "order_submission", None) is not True:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="ADAPTER_ORDER_SUBMISSION_UNSUPPORTED",
            error_message="Selected adapter does not advertise order-submission capability; no claim or provider call was made.",
        )

    if execution_ready_package is not None:
        try:
            readiness_observation = evaluate_execution_attempt_readiness(
                execution_ready_package=execution_ready_package,
                request=request,
            )
            readiness_observation = dict(readiness_observation)
            readiness_observation["order_type"] = request.order_type
            readiness_observation["execution_instrument"] = execution_instrument
            readiness_observation["venue"] = venue
        except ValueError as exc:
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                error_code=str(exc),
                error_message=f"Execution-attempt readiness rejected: {exc}.",
            )

    try:
        authorization = evaluate_execution_authorization(
            readiness_observation,
            authorization_observation,
        )
    except ValueError as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code=str(exc),
            error_message=f"Explicit execution authorization rejected: {exc}.",
        )

    if authorization.get("authorization_state") != "AUTHORIZED":
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="AUTHORIZATION_INVALID",
            error_message="Explicit execution authorization is required.",
        )

    prepared = prepare_order_for_adapter(
        request=request,
        adapter=adapter,
        venue=venue,
        execution_instrument=execution_instrument,
    )
    if not isinstance(prepared, AdapterOrderPreparation) or not prepared.ready:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code=getattr(prepared, "reason", "ORDER_PREPARATION_BLOCKED"),
            error_message="Provider order preparation did not reach READY.",
        )

    # Core-owned namespace prevents an adapter/venue switch from reopening an intent.
    if claim_store is None:
        return blocked_execution_result(
            asset=request.asset, direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="DURABLE_INTENT_CLAIM_STORE_REQUIRED",
            error_message="Provider submission requires a durable Core intent claim store.",
        )
    client_order_id = getattr(prepared, "client_order_id", None)
    if not isinstance(client_order_id, str) or not client_order_id.strip():
        return blocked_execution_result(
            asset=request.asset, direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="STABLE_CLIENT_ORDER_ID_REQUIRED",
            error_message="Adapter must provide a stable client order ID before submission.",
        )
    try:
        claim = claim_store.claim(
            provider_namespace="ARUNDA-EXECUTION",
            intent_id=request.intent_id,
            client_order_id=client_order_id,
        )
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset, direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="DURABLE_INTENT_CLAIM_FAILED",
            error_message=str(exc),
        )
    if getattr(claim, "outcome", None) != "CLAIMED":
        return blocked_execution_result(
            asset=request.asset, direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="INTENT_ALREADY_CLAIMED_NO_RESUBMIT",
            error_message=f"Intent claim outcome={getattr(claim, 'outcome', 'INVALID')}; submission suppressed.",
        )

    # Allocate a local attempt/evidence identity before crossing the provider
    # boundary. A crash after the durable fence never permits a second POST.
    trade_event_id = str(uuid4())
    evidence_event_id = f"{trade_event_id}:provider-response"
    try:
        claim_store.transition(
            provider_namespace="ARUNDA-EXECUTION",
            intent_id=request.intent_id,
            status="SUBMISSION_OUTCOME_UNKNOWN",
            trade_event_id=trade_event_id,
            decision_id=request.decision_id,
            detail_code="SUBMISSION_BOUNDARY_ENTERED_OUTCOME_PENDING",
        )
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset, direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="INTENT_OUTCOME_FENCE_FAILED",
            error_message=str(exc),
        )

    # Exactly one invocation; no retry loop. Claim remains held for every outcome.
    try:
        result = adapter.submit_prepared_order(prepared, canonical_request=request)
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset, direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="SUBMISSION_OUTCOME_UNKNOWN",
            error_message=f"Provider call raised after attempt fence; do not resubmit. {exc}",
        )

    if not isinstance(result, CanonicalExecutionResult):
        return blocked_execution_result(
            asset=request.asset, direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="SUBMISSION_OUTCOME_UNKNOWN",
            error_message="Invalid response after the single allowed call; keep claim quarantined and reconcile read-only.",
        )

    # Persist authoritative provider outcome when the adapter returned a
    # complete, classified response. Unknown/malformed outcomes stay fenced.
    try:
        if result.accepted is True and result.exchange_order_id and result.status:
            claim_store.transition(
                provider_namespace="ARUNDA-EXECUTION",
                intent_id=request.intent_id,
                status="PROVIDER_ACCEPTED",
                trade_event_id=trade_event_id,
                decision_id=request.decision_id,
                exchange_order_id=str(result.exchange_order_id),
                provider_status=str(result.status),
                evidence_event_id=evidence_event_id,
                detail_code="PROVIDER_ACCEPTANCE_RESPONSE_CAPTURED",
            )
        elif result.status == "PROVIDER_REJECTED" and result.error_code:
            claim_store.transition(
                provider_namespace="ARUNDA-EXECUTION",
                intent_id=request.intent_id,
                status="PROVIDER_REJECTED",
                trade_event_id=trade_event_id,
                decision_id=request.decision_id,
                exchange_order_id=(str(result.exchange_order_id) if result.exchange_order_id else None),
                provider_status=str(result.status),
                evidence_event_id=evidence_event_id,
                detail_code=str(result.error_code),
            )
    except Exception as exc:
        # The provider call has already happened; never retry to repair evidence.
        return CanonicalExecutionResult(
            accepted=result.accepted,
            exchange_order_id=result.exchange_order_id,
            status="OUTCOME_EVIDENCE_PERSISTENCE_FAILED",
            asset=result.asset,
            direction=result.direction,
            executed_quantity=result.executed_quantity,
            executed_price=result.executed_price,
            timestamp=result.timestamp,
            adapter=result.adapter,
            error_code="CLAIM_EVIDENCE_PERSISTENCE_FAILED",
            error_message=f"Provider response returned but durable evidence update failed: {exc}",
            trade_event_id=trade_event_id,
        )

    return CanonicalExecutionResult(
        accepted=result.accepted,
        exchange_order_id=result.exchange_order_id,
        status=result.status,
        asset=result.asset,
        direction=result.direction,
        executed_quantity=result.executed_quantity,
        executed_price=result.executed_price,
        timestamp=result.timestamp,
        adapter=result.adapter,
        error_code=result.error_code,
        error_message=result.error_message,
        trade_event_id=trade_event_id,
    )


__all__ = ["attempt_prepared_order"]
