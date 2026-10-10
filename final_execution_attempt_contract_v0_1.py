"""ARUNDA TRADER — FINAL EXECUTION ATTEMPT CONTRACT v0.1.

Provider-neutral composition of the final pre-execution path:

Execution Ready Package
    -> Execution-Attempt Readiness
    -> Technical Authorization Against Active Standing Mandate
    -> Order Preparation
    -> Replaceable Adapter Attempt

This is a contract/orchestration boundary only. It does not enable execution,
wire the production pipeline, call an exchange directly, or mutate a database.
The selected adapter remains responsible for provider behavior.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
    blocked_execution_result,
)
from exchange_execution_order_attempt_boundary_v0_1 import attempt_prepared_order
from management_execution_authorization_v0_1 import evaluate_management_phase_entry


def run_final_execution_attempt_contract(
    *,
    execution_ready_package: Mapping[str, Any],
    request: CanonicalOrderRequest,
    management_observation: Mapping[str, Any],
    adapter: Any,
    venue: str,
    execution_instrument: Any,
) -> CanonicalExecutionResult:
    """Compose the final contract path and fail closed on invalid inputs.

    The canonical one-time management phase-entry observation is passed to
    the authoritative management producer here. Only the producer's validated
    standing-mandate output is forwarded to the technical authorization
    boundary; handcrafted technical authorization mappings cannot bypass it.
    """
    try:
        if not isinstance(execution_ready_package, Mapping):
            raise ValueError("EXECUTION_READY_PACKAGE_INVALID")
        if not isinstance(management_observation, Mapping):
            raise ValueError("MANAGEMENT_PHASE_ENTRY_INPUT_INVALID")

        management_result = evaluate_management_phase_entry(management_observation)
        authorization_observation = management_result.get("authorization_observation")
        if management_result.get("execution_authorization") != "AUTHORIZED_STANDING_MANDATE":
            raise ValueError("MANAGEMENT_PHASE_ENTRY_NOT_AUTHORIZED")
        if not isinstance(authorization_observation, Mapping):
            raise ValueError("MANAGEMENT_AUTHORIZATION_HANDOFF_INVALID")

        # The order-attempt boundary performs authoritative readiness alignment
        # and technical authorization checks before adapter preparation/submission.
        return attempt_prepared_order(
            request=request,
            readiness_observation={},
            authorization_observation=authorization_observation,
            adapter=adapter,
            venue=venue,
            execution_instrument=execution_instrument,
            execution_ready_package=execution_ready_package,
        )
    except Exception as exc:
        return blocked_execution_result(
            asset=getattr(request, "asset", None),
            direction=getattr(request, "direction", None),
            error_code="FINAL_EXECUTION_ATTEMPT_CONTRACT_FAILED",
            error_message=str(exc),
        )


__all__ = ["run_final_execution_attempt_contract"]
