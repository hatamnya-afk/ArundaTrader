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

    try:
        result = adapter.submit_prepared_order(
            prepared,
            canonical_request=request,
        )
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="ADAPTER_SUBMIT_PREPARED_FAILED",
            error_message=str(exc),
        )

    if not isinstance(result, CanonicalExecutionResult):
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="ADAPTER_EXECUTION_RESULT_INVALID",
            error_message="Adapter returned an invalid canonical execution result.",
        )

    return result


__all__ = ["attempt_prepared_order"]
