
from typing import Any, Optional

from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from exchange_execution_contract import (
    CanonicalOrderRequest,
    CanonicalExecutionResult,
    validate_order_request,
    blocked_execution_result,
    EXECUTION_ENABLED,
    ORDER_SUBMISSION_ENABLED,
)
from cp49_first_execution_contract_v0_1 import (
    AttemptState,
    ExecutionSafetyGate,
)
from mcp01_trade_event_identity_v0_1 import issue_trade_event_id
from dataclasses import replace

CAPABILITY_ORDER_SUBMISSION = "ORDER_SUBMISSION"


def execute_order(
    request: Optional[CanonicalOrderRequest] = None,
    adapter: Any = None,
    *,
    eligibility: Optional[ExecutionEligibilityResult] = None,
    safety_gate: Optional[ExecutionSafetyGate] = None,
) -> CanonicalExecutionResult:

    # ============================================================
    # 1. CP46-E EXECUTION ELIGIBILITY GATE
    #
    # A CanonicalOrderRequest must never reach the execution path
    # without an explicit successful provider-preflight eligibility
    # result. This is the mandatory CP46-E predecessor.
    # ============================================================
    if not isinstance(
        eligibility,
        ExecutionEligibilityResult,
    ):
        return blocked_execution_result(
            asset=(request.asset if isinstance(request, CanonicalOrderRequest) else None),
            direction=(request.direction if isinstance(request, CanonicalOrderRequest) else None),
            error_code="CP46_E_REQUIRED",
            error_message="Execution eligibility is required before execution boundary.",
        )

    if eligibility.status != EligibilityStatus.PASS:
        return blocked_execution_result(
            error_code="CP46_E_BLOCKED",
            error_message=eligibility.message,
        )

    eligible_request = eligibility.canonical_request

    if not isinstance(eligible_request, CanonicalOrderRequest):
        return blocked_execution_result(
            error_code="CP46_E_REQUEST_MISSING",
            error_message="Successful execution eligibility has no canonical request.",
        )

    if request is not None and request is not eligible_request:
        return blocked_execution_result(
            asset=eligible_request.asset,
            direction=eligible_request.direction,
            error_code="CP46_E_REQUEST_MISMATCH",
            error_message="Supplied request does not match eligible canonical request.",
        )

    request = eligible_request

    # ============================================================
    # 2. CANONICAL REQUEST TYPE GATE
    # ============================================================
    if not isinstance(request, CanonicalOrderRequest):
        return blocked_execution_result(
            error_code="INVALID_REQUEST",
            error_message="Invalid canonical order request.",
        )

    # ============================================================
    # 3. CANONICAL REQUEST VALIDATION
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
    # 4. CP49 FIRST-EXECUTION AUTHORIZATION GATE
    #
    # Module-level execution flags remain fail-closed defaults.
    # Only a READY CP49 gate may authorize the existing
    # adapter/transport for this execution path.
    # ============================================================
    if not isinstance(safety_gate, ExecutionSafetyGate):
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="CP49_SAFETY_GATE_REQUIRED",
            error_message="CP49 first-execution safety gate is required.",
        )

    if safety_gate.validate() is not AttemptState.READY:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="CP49_SAFETY_GATE_BLOCKED",
            error_message="CP49 first-execution safety gate is not READY.",
        )

    # ============================================================
    # 5. ADAPTER PRESENCE
    # ============================================================
    if adapter is None:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="MISSING_ADAPTER",
            error_message="Configured adapter is missing.",
        )

    # ============================================================
    # 6. AUTHORIZE EXISTING ADAPTER / TRANSPORT
    # ============================================================
    authorize = getattr(adapter, "authorize_first_execution", None)
    already_active = (
        getattr(adapter, "live_order_transport_enabled", False) is True
        and getattr(adapter, "execution_enabled", False) is True
        and getattr(adapter, "order_submission_enabled", False) is True
        and getattr(adapter, "exchange_write_enabled", False) is True
    )
    if not already_active:
        if not callable(authorize) or authorize(safety_gate) is not True:
            return blocked_execution_result(
                asset=request.asset,
                direction=request.direction,
                error_code="CP49_EXECUTION_ACTIVATION_FAILED",
                error_message="Existing adapter/transport could not be authorized by CP49 gate.",
            )

    # ============================================================
    # 7. CAPABILITY GATE
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
    # 7. CANONICAL SUBMISSION INTERFACE
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
    # 8. QUANTITY IMMUTABILITY
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
    # 9. CANONICAL ADAPTER SUBMISSION
    # ============================================================
    # Authoritative trade-event birth occurs at the exact execution-boundary
    # attempt point. It is not derived from provider response/order IDs.
    trade_event_id = issue_trade_event_id()

    try:
        result = submit(request)
    except Exception as exc:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="ADAPTER_SUBMISSION_ERROR",
            error_message=str(exc),
            trade_event_id=trade_event_id,
        )

    # ============================================================
    # 10. CANONICAL RESULT CONTRACT
    # ============================================================
    if not isinstance(result, CanonicalExecutionResult):
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="NON_CANONICAL_RESULT",
            error_message="Adapter returned a non-canonical execution result.",
            trade_event_id=trade_event_id,
        )

    # ============================================================
    # 11. QUANTITY IMMUTABILITY POST-CONDITION
    # ============================================================
    if request.quantity != original_quantity:
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="QUANTITY_MUTATION",
            error_message="Order quantity changed during submission.",
            trade_event_id=trade_event_id,
        )

    # ============================================================
    # 12. RETURN CANONICAL EXECUTION RESULT
    # ============================================================
    # The execution boundary owns trade-event identity. Any provider-side
    # exchange_order_id remains a separate provider identity.
    return replace(result, trade_event_id=trade_event_id)