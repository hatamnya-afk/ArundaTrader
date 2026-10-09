"""ARUNDA TRADER — PROVIDER-NEUTRAL ORDER ATTEMPT BOUNDARY v0.1.

Final provider-neutral gate between a prepared adapter order and a future
provider order attempt.

NO automatic authorization.
NO exchange-specific logic.
NO database write.
The selected adapter owns provider submission behavior.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any, Mapping

from mcp01_trade_event_identity_v0_1 import issue_trade_event_id

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
) -> CanonicalExecutionResult:
    """Fail closed unless explicit valid authorization is present.

    Preparation is performed before submission so the provider-owned request
    exists at the final boundary. Authorization is never inferred from
    readiness, adapter capability, account state, or provider metadata.
    """

    # Decision identity is mandatory at this boundary and must be rejected
    # before adapter validation, preparation, or submission.
    decision_id = getattr(request, "decision_id", None)
    if not isinstance(decision_id, str) or not decision_id.strip():
        reason = "DECISION_ID_MISSING" if decision_id is None else "DECISION_ID_INVALID"
        return blocked_execution_result(
            asset=getattr(request, "asset", None),
            direction=getattr(request, "direction", None),
            error_code=reason,
            error_message=f"Canonical order request rejected: {reason}.",
        )

    valid, reason = validate_order_request(request)
    if not valid:
        return blocked_execution_result(
            asset=getattr(request, "asset", None),
            direction=getattr(request, "direction", None),
            error_code=reason,
            error_message=f"Canonical order request rejected: {reason}.",
            decision_id=request.decision_id,
        )

    contract_valid, contract_reason = validate_adapter_contract(adapter)
    if not contract_valid:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code=contract_reason,
            error_message=f"Execution adapter contract rejected: {contract_reason}.",
            decision_id=request.decision_id,
        )

    if execution_ready_package is not None:
        try:
            readiness_observation = evaluate_execution_attempt_readiness(
                execution_ready_package=execution_ready_package,
                request=request,
            )
        except ValueError as exc:
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                error_code=str(exc),
                error_message=f"Execution-attempt readiness rejected: {exc}.",
                decision_id=request.decision_id,
            )

    # Bind the selected execution context consistently, whether readiness
    # came from a ready package or an existing readiness observation.
    readiness_observation = dict(readiness_observation)
    readiness_observation["order_type"] = request.order_type
    readiness_observation["execution_instrument"] = execution_instrument
    readiness_observation["venue"] = venue

    # Bind the standing mandate to the selected provider before any adapter
    # preparation or submission. A valid market scope alone is insufficient.
    mandate_provider = (
        authorization_observation.get("provider")
        if isinstance(authorization_observation, Mapping)
        else None
    )
    adapter_provider = getattr(adapter, "adapter_name", None)
    if (
        not isinstance(mandate_provider, str)
        or not mandate_provider.strip()
        or not isinstance(adapter_provider, str)
        or not adapter_provider.strip()
        or mandate_provider.strip().casefold() != adapter_provider.strip().casefold()
    ):
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="AUTHORIZATION_PROVIDER_MISMATCH",
            error_message="Standing mandate provider does not match the selected execution adapter.",
            decision_id=request.decision_id,
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
            decision_id=request.decision_id,
        )

    if authorization.get("authorization_state") != "AUTHORIZED":
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="AUTHORIZATION_INVALID",
            error_message="Explicit execution authorization is required.",
            decision_id=request.decision_id,
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
            decision_id=request.decision_id,
        )

    # Issue the authoritative identity at the actual adapter-attempt boundary,
    # after all local validation, authorization, and preparation gates pass.
    # It is never copied from a provider response or exchange order identifier.
    trade_event_id = issue_trade_event_id()

    try:
        result = adapter.submit_prepared_order(
            prepared,
            canonical_request=request,
        )
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="ADAPTER_SUBMIT_PREPARED_FAILED",
            error_message=str(exc),
            trade_event_id=trade_event_id,
        decision_id=request.decision_id,
        )

    if not isinstance(result, CanonicalExecutionResult):
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            adapter=getattr(adapter, "adapter_name", None),
            error_code="ADAPTER_EXECUTION_RESULT_INVALID",
            error_message="Adapter returned an invalid canonical execution result.",
            trade_event_id=trade_event_id,
        decision_id=request.decision_id,
        )

    # The boundary owns the attempt identity. Ignore any adapter-supplied value.
    return replace(
        result,
        trade_event_id=trade_event_id,
        decision_id=request.decision_id,
    )


__all__ = ["attempt_prepared_order"]
