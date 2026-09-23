"""CP46-G binding-to-execution consumer handoff contract.

Provider-neutral handoff from a verified CP46-F binding to the existing
canonical execution consumer.

No network, database write, exchange write, order submission, quantity
conversion, rounding, estimation, normalization, or mutation is performed
by this contract. The existing execution boundary remains the sole consumer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from cp46_f_provider_execution_binding_v0_1 import (
    BindingStatus,
    ProviderExecutionBindingResult,
)
from exchange_execution_boundary import execute_order
from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
    blocked_execution_result,
)


class ConsumerHandoffStatus:
    PASS = "PASS"
    BLOCK = "BLOCK"


@dataclass(frozen=True)
class ProviderExecutionConsumerHandoffResult:
    status: str
    reason: str
    message: str
    canonical_request: Optional[CanonicalOrderRequest] = None
    provider_request: Any = None
    execution_result: Optional[CanonicalExecutionResult] = None


def _block(
    reason: str,
    message: str,
    *,
    request: Optional[CanonicalOrderRequest] = None,
) -> ProviderExecutionConsumerHandoffResult:
    return ProviderExecutionConsumerHandoffResult(
        status=ConsumerHandoffStatus.BLOCK,
        reason=reason,
        message=message,
        canonical_request=request,
        provider_request=None,
        execution_result=None,
    )


def handoff_binding_to_execution_consumer(
    binding: ProviderExecutionBindingResult,
    eligibility: ExecutionEligibilityResult,
    *,
    adapter: Any = None,
) -> ProviderExecutionConsumerHandoffResult:
    """Hand an exact CP46-F PASS to the existing execution consumer.

    CP46-G does not reconstruct eligibility or translate provider data.
    The original CP46-E eligibility object is required and must reference
    the exact canonical request carried by CP46-F.

    A BLOCK never calls the execution boundary.
    A PASS delegates only the canonical request and original eligibility to
    the existing execute_order() consumer. ProviderOrderRequest is preserved
    as provenance but is not reinterpreted by this handoff.
    """

    if not isinstance(binding, ProviderExecutionBindingResult):
        return _block(
            "BINDING_INVALID",
            "CP46-F provider execution binding result is required.",
        )

    if binding.status != BindingStatus.PASS:
        return _block(
            "BINDING_NOT_PASS",
            "CP46-F provider execution binding must be PASS.",
        )

    canonical = binding.canonical_request

    if not isinstance(canonical, CanonicalOrderRequest):
        return _block(
            "CANONICAL_REQUEST_MISSING",
            "A successful CP46-F binding must contain CanonicalOrderRequest.",
        )

    if binding.provider_request is None:
        return _block(
            "PROVIDER_REQUEST_MISSING",
            "A successful CP46-F binding must contain ProviderOrderRequest.",
            request=canonical,
        )

    if not isinstance(eligibility, ExecutionEligibilityResult):
        return _block(
            "ELIGIBILITY_INVALID",
            "Original CP46-E execution eligibility result is required.",
            request=canonical,
        )

    if eligibility.status != EligibilityStatus.PASS:
        return _block(
            "ELIGIBILITY_NOT_PASS",
            "Original CP46-E execution eligibility must be PASS.",
            request=canonical,
        )

    eligible_request = eligibility.canonical_request

    if not isinstance(eligible_request, CanonicalOrderRequest):
        return _block(
            "ELIGIBLE_REQUEST_MISSING",
            "Successful CP46-E eligibility must contain CanonicalOrderRequest.",
            request=canonical,
        )

    if eligible_request is not canonical:
        return _block(
            "CANONICAL_IDENTITY_MISMATCH",
            "CP46-E and CP46-F do not reference the exact same canonical request.",
            request=canonical,
        )

    # The provider request is deliberately not transformed or revalidated
    # here. CP46-F already proved its binding. CP46-G only carries it as
    # immutable provenance while the canonical consumer receives the exact
    # request and original CP46-E eligibility object.
    execution_result = execute_order(
        request=canonical,
        adapter=adapter,
        eligibility=eligibility,
    )

    return ProviderExecutionConsumerHandoffResult(
        status=ConsumerHandoffStatus.PASS,
        reason="EXECUTION_CONSUMER_HANDOFF_COMPLETE",
        message="CP46-F binding handed to the existing execution consumer.",
        canonical_request=canonical,
        provider_request=binding.provider_request,
        execution_result=execution_result,
    )


__all__ = [
    "ConsumerHandoffStatus",
    "ProviderExecutionConsumerHandoffResult",
    "handoff_binding_to_execution_consumer",
]
