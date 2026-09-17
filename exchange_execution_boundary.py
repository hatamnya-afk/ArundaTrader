
from typing import Any

from exchange_execution_contract import (
    CanonicalOrderRequest,
    CanonicalExecutionResult,
    validate_order_request,
    blocked_execution_result,
    EXECUTION_ENABLED,
    ORDER_SUBMISSION_ENABLED,
)

CAPABILITY_ORDER_SUBMISSION = "ORDER_SUBMISSION"


def execute_order(
    request: CanonicalOrderRequest,
    adapter: Any,
) -> CanonicalExecutionResult:

    # ============================================================
    # 1. CANONICAL REQUEST TYPE GATE
    # ============================================================
    if not isinstance(request, CanonicalOrderRequest):
        return blocked_execution_result(
            error_code="INVALID_REQUEST",
            error_message="Invalid canonical order request.",
        )

    # ============================================================
    # 2. CANONICAL REQUEST VALIDATION
    # ============================================================
    try:
        valid, reason = validate_order_request(request)
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="INVALID_REQUEST",
            error_message=str(exc),
        )

    if not valid:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="INVALID_REQUEST",
            error_message=reason,
        )

    # ============================================================
    # 3. GLOBAL EXECUTION SAFETY LOCK
    #
    # Must happen BEFORE any adapter interaction.
    # ============================================================
    if EXECUTION_ENABLED is not True:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="EXECUTION_DISABLED",
            error_message="Execution is disabled.",
        )

    if ORDER_SUBMISSION_ENABLED is not True:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="ORDER_SUBMISSION_DISABLED",
            error_message="Order submission is disabled.",
        )

    # ============================================================
    # 4. ADAPTER PRESENCE
    # ============================================================
    if adapter is None:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="MISSING_ADAPTER",
            error_message="Configured adapter is missing.",
        )

    # ============================================================
    # 5. CAPABILITY GATE
    # ============================================================
    try:
        capabilities = adapter.capabilities()
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="CAPABILITY_ERROR",
            error_message=str(exc),
        )

    if not isinstance(capabilities, dict):
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="INVALID_CAPABILITIES",
            error_message="Adapter capabilities are invalid.",
        )

    if capabilities.get(CAPABILITY_ORDER_SUBMISSION) is not True:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="ORDER_SUBMISSION_DISABLED",
            error_message="ORDER_SUBMISSION capability is disabled.",
        )

    # ============================================================
    # 6. CANONICAL SUBMISSION INTERFACE
    # ============================================================
    submit = getattr(adapter, "submit_order", None)

    if not callable(submit):
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="SUBMIT_ORDER_UNAVAILABLE",
            error_message="Canonical submit_order interface unavailable.",
        )

    # ============================================================
    # 7. QUANTITY IMMUTABILITY
    #
    # Execution boundary MUST NOT:
    # - calculate quantity
    # - normalize quantity
    # - round quantity
    # - rescale quantity
    # - clip quantity
    # - mutate quantity
    # ============================================================
    original_quantity = request.quantity

    # ============================================================
    # 8. CANONICAL ADAPTER SUBMISSION
    # ============================================================
    try:
        result = submit(request)
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="ADAPTER_SUBMISSION_ERROR",
            error_message=str(exc),
        )

    # ============================================================
    # 9. CANONICAL RESULT CONTRACT
    # ============================================================
    if not isinstance(result, CanonicalExecutionResult):
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="NON_CANONICAL_RESULT",
            error_message="Adapter returned a non-canonical execution result.",
        )

    # ============================================================
    # 10. QUANTITY IMMUTABILITY POST-CONDITION
    # ============================================================
    if request.quantity != original_quantity:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="QUANTITY_MUTATION",
            error_message="Order quantity changed during submission.",
        )

    # ============================================================
    # 11. RETURN CANONICAL EXECUTION RESULT
    # ============================================================
    return result