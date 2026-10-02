"""CP49 — exchange rejection is a provider outcome, not a Trader capital gate.

Pure contract test:
    A valid canonical order may reach the execution boundary when the
    execution/safety prerequisites are READY. If the provider returns
    INSUFFICIENT_BALANCE, that rejection is returned unchanged as the
    canonical execution result. The Trader does not pre-block on account
    capital.

No network, exchange, database, or order I/O occurs in this test.
"""

from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from cp49_first_execution_contract_v0_1 import (
    ExecutionSafetyGate,
)
from exchange_execution_boundary import execute_order
from exchange_execution_contract import (
    CanonicalExecutionResult,
    CanonicalOrderRequest,
)


class _ProviderRejectingAdapter:
    def __init__(self):
        self.authorized = False

    def authorize_first_execution(self, safety_gate):
        self.authorized = safety_gate.validate().value == "READY"
        return self.authorized

    def capabilities(self):
        return {"ORDER_SUBMISSION": self.authorized}

    def submit_order(self, request):
        assert request.quantity == 0.01
        return CanonicalExecutionResult(
            accepted=False,
            exchange_order_id=None,
            status="REJECTED",
            asset=request.asset,
            direction=request.direction,
            executed_quantity=None,
            executed_price=None,
            timestamp=request.timestamp,
            adapter="TOOBIT",
            error_code="INSUFFICIENT_BALANCE",
            error_message="Insufficient balance.",
        )


def run() -> None:
    request = CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=0.01,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=None,
        reference_price=None,
        intent_id="OI-CP49-CAPITAL-INDEPENDENCE-BTC",
        snapshot_id="RS-CP49-CAPITAL-INDEPENDENCE",
        timestamp="1770000000000",
        decision_id="00000000-0000-4000-8000-000000000049",
    )

    # Capital is deliberately absent from this execution contract.
    # It is an external provider/account state, not a Trader gate.
    eligibility = ExecutionEligibilityResult(
        status=EligibilityStatus.PASS,
        reason="PASS",
        message="Provider preflight passed.",
        canonical_request=request,
    )

    safety_gate = ExecutionSafetyGate(
        management_authorized=True,
        implementation_verified=True,
        prior_attempt_exists=False,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
        automatic_retry_enabled=False,
    )

    adapter = _ProviderRejectingAdapter()

    result = execute_order(
        request=request,
        adapter=adapter,
        eligibility=eligibility,
        safety_gate=safety_gate,
    )

    assert result.accepted is False
    assert result.status == "REJECTED"
    assert result.error_code == "INSUFFICIENT_BALANCE"
    assert result.adapter == "TOOBIT"
    assert result.asset == "BTC"
    assert result.direction == "LONG"

    print("CAPITAL_INDEPENDENT_EXECUTION_REJECTION_CONTRACT=PASS")


if __name__ == "__main__":
    run()
