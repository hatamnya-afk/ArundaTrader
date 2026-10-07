"""CP49 Readiness -> Single Execution Gate binding v0.1.

Pure provider-neutral contract.

This module:
- accepts a verified CP49 readiness result
- requires explicit management authorization separately
- constructs the existing ExecutionSafetyGate
- never enables execution
- never submits an order
- never contacts an exchange
- never writes a database
"""

from __future__ import annotations

from cp49_first_execution_contract_v0_1 import (
    AttemptState,
    ExecutionSafetyGate,
)
from cp49_first_execution_readiness_v0_1 import (
    FirstExecutionReadinessResult,
    ReadinessState,
)


def build_execution_safety_gate(
    *,
    readiness: FirstExecutionReadinessResult,
    management_authorized: bool,
    prior_attempt_exists: bool,
    automatic_retry_enabled: bool,
    execution_enabled: bool,
    order_submission_enabled: bool,
    exchange_write_enabled: bool,
) -> ExecutionSafetyGate:
    """Bind technical readiness to the existing single execution gate.

    READY_FOR_AUTHORIZATION is necessary but is not itself authorization.
    Management authorization remains a separate explicit input.
    """

    if not isinstance(readiness, FirstExecutionReadinessResult):
        raise ValueError("READINESS_RESULT_INVALID")

    if readiness.state is not ReadinessState.READY_FOR_AUTHORIZATION:
        raise ValueError("READINESS_NOT_READY_FOR_AUTHORIZATION")

    return ExecutionSafetyGate(
        management_authorized=management_authorized,
        implementation_verified=True,
        prior_attempt_exists=prior_attempt_exists,
        execution_enabled=execution_enabled,
        order_submission_enabled=order_submission_enabled,
        exchange_write_enabled=exchange_write_enabled,
        automatic_retry_enabled=automatic_retry_enabled,
    )


__all__ = [
    "build_execution_safety_gate",
]