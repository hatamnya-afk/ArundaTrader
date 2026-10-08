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


def run_final_execution_attempt_contract(
    *,
    execution_ready_package: Mapping[str, Any],
    request: CanonicalOrderRequest,
    authorization_observation: Mapping[str, Any],
    adapter: Any,
    venue: str,
    execution_instrument: Any,
) -> CanonicalExecutionResult:
    """Compose the final contract path and fail closed on invalid inputs.

    No management authorization is requested or inferred here. The only
    management authorization input is the active standing phase-entry mandate;
    this boundary performs technical validation of that mandate against the
    current execution-ready request.
    """
    try:
        if not isinstance(execution_ready_package, Mapping):
            raise ValueError("EXECUTION_READY_PACKAGE_INVALID")
        if not isinstance(authorization_observation, Mapping):
            raise ValueError("AUTHORIZATION_INPUT_INVALID")

        # The order-attempt boundary performs the authoritative readiness
        # alignment and explicit authorization checks before adapter submission.
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
