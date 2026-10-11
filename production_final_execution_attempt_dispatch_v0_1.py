"""Production binding for the final execution-attempt contract.

This dispatcher is wired into the production pipeline but remains fail-closed
while execution is disabled. It never infers authorization or constructs
provider/account evidence. When a future, separately approved activation
supplies the complete context and enables the execution gate, it delegates to
the existing final contract rather than bypassing its readiness/mandate checks.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
    blocked_execution_result,
)
from final_execution_attempt_contract_v0_1 import run_final_execution_attempt_contract


def dispatch_final_execution_attempt(
    *,
    request: CanonicalOrderRequest,
    execution_enabled: bool,
    execution_ready_package: Mapping[str, Any] | None = None,
    management_observation: Mapping[str, Any] | None = None,
    adapter: Any = None,
    venue: str | None = None,
    execution_instrument: Any = None,
) -> CanonicalExecutionResult:
    """Route production requests to the final contract only behind its gate."""
    if execution_enabled is not True:
        return blocked_execution_result(
            asset=getattr(request, "asset", None),
            direction=getattr(request, "direction", None),
            error_code="EXECUTION_DISABLED",
            error_message="Production final-attempt dispatch is disabled by the execution gate.",
            decision_id=getattr(request, "decision_id", None),
        )

    if (
        not isinstance(request, CanonicalOrderRequest)
        or not isinstance(execution_ready_package, Mapping)
        or not isinstance(management_observation, Mapping)
        or adapter is None
        or not isinstance(venue, str)
        or not venue.strip()
        or execution_instrument is None
    ):
        return blocked_execution_result(
            asset=getattr(request, "asset", None),
            direction=getattr(request, "direction", None),
            error_code="FINAL_ATTEMPT_CONTEXT_INCOMPLETE",
            error_message="Final-attempt dispatch requires a canonical request, validated readiness package, standing mandate, adapter, venue, and instrument.",
            decision_id=getattr(request, "decision_id", None),
        )

    result = run_final_execution_attempt_contract(
        execution_ready_package=execution_ready_package,
        request=request,
        management_observation=management_observation,
        adapter=adapter,
        venue=venue.strip(),
        execution_instrument=execution_instrument,
    )
    if not isinstance(result, CanonicalExecutionResult):
        return blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="FINAL_ATTEMPT_RESULT_INVALID",
            error_message="Final execution-attempt contract returned an invalid result.",
            decision_id=request.decision_id,
        )
    return result


__all__ = ["dispatch_final_execution_attempt"]
