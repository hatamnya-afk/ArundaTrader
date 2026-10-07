"""
ARUNDA TRADER
EXCHANGE-AGNOSTIC EXECUTION BOUNDARY v0.1

Fail-closed contract boundary between the exchange-neutral Core and any
future replaceable exchange adapter.

NO NETWORK.
NO EXCHANGE WRITE.
NO ORDER SUBMISSION.
NO DATABASE WRITE.
NO EXECUTION.

Toobit is intentionally not imported or referenced here.
"""

from __future__ import annotations

from typing import Any

import exchange_execution_contract as contract


def execute_order(
    *,
    request: contract.CanonicalOrderRequest,
    adapter: Any = None,
) -> contract.CanonicalExecutionResult:
    """
    Validate the canonical request, then fail closed while execution is off.

    The boundary does not size, round, clamp, normalize, translate, or mutate
    quantity. Provider binding is a later lifecycle gate.
    """
    valid, reason = contract.validate_order_request(request)

    if not valid:
        return contract.blocked_execution_result(
            asset=getattr(request, "asset", None),
            direction=getattr(request, "direction", None),
            error_code=reason,
            error_message=f"Canonical order request rejected: {reason}.",
        )

    if adapter is not None:
        # Adapter presence never overrides the execution safety contract.
        # Provider binding is deliberately deferred until the Project
        # Completion Gate is closed and Toobit Binding is explicitly opened.
        pass

    if not contract.EXECUTION_ENABLED:
        return contract.blocked_execution_result(
            asset=request.asset,
            direction=request.direction,
            error_code="EXECUTION_DISABLED",
            error_message="Execution is disabled by exchange-agnostic contract.",
        )

    # This branch is intentionally unreachable while execution is disabled.
    return contract.blocked_execution_result(
        asset=request.asset,
        direction=request.direction,
        error_code="EXECUTION_DISABLED",
        error_message="Execution is disabled by exchange-agnostic contract.",
    )


__all__ = ["execute_order"]
