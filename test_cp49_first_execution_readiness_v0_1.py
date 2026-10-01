from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from cp49_first_execution_readiness_v0_1 import (
    FirstExecutionReadinessInput,
    ReadinessState,
    evaluate_first_execution_readiness,
)
from exchange_execution_contract import CanonicalOrderRequest


def _request():
    return CanonicalOrderRequest(
        asset="BTC",
        direction="LONG",
        order_type="MARKET",
        quantity=1.0,
        quantity_unit="BASE_ASSET",
        quantity_source="RISK.position_quantity",
        entry_price=100.0,
        reference_price=100.0,
        intent_id="intent-1",
        snapshot_id="snapshot-1",
        timestamp="2026-10-01T00:00:00+00:00",
    )


def _eligibility(request):
    return ExecutionEligibilityResult(
        status=EligibilityStatus.PASS,
        reason="PASS",
        message="provider preflight passed",
        canonical_request=request,
    )


def test_readiness_blocks_on_account_signature_and_capital():
    request = _request()
    result = evaluate_first_execution_readiness(
        readiness=FirstExecutionReadinessInput(
            implementation_verified=True,
            prior_attempt_exists=False,
            automatic_retry_enabled=False,
            account_read_verified=True,
            signature_verified=False,
            capital_authorized=False,
            provider_constraints_verified=True,
            management_authorized=True,
            execution_enabled=False,
            order_submission_enabled=False,
            exchange_write_enabled=False,
            database_write_enabled=False,
        ),
        canonical_request=request,
        eligibility=_eligibility(request),
    )

    assert result.state is ReadinessState.BLOCKED
    assert "ACCOUNT_SIGNATURE_NOT_VERIFIED" in result.blockers
    assert "REAL_CAPITAL_NOT_AUTHORIZED" in result.blockers


def test_readiness_can_be_ready_without_enabling_execution():
    request = _request()
    result = evaluate_first_execution_readiness(
        readiness=FirstExecutionReadinessInput(
            implementation_verified=True,
            prior_attempt_exists=False,
            automatic_retry_enabled=False,
            account_read_verified=True,
            signature_verified=True,
            capital_authorized=True,
            provider_constraints_verified=True,
            management_authorized=True,
            execution_enabled=False,
            order_submission_enabled=False,
            exchange_write_enabled=False,
            database_write_enabled=False,
        ),
        canonical_request=request,
        eligibility=_eligibility(request),
    )

    assert result.state is ReadinessState.READY_FOR_AUTHORIZATION
    assert result.blockers == ()
    assert result.canonical_request_valid is True
    assert result.eligibility_passed is True


def test_readiness_rejects_pre_enabled_execution():
    request = _request()
    result = evaluate_first_execution_readiness(
        readiness=FirstExecutionReadinessInput(
            implementation_verified=True,
            prior_attempt_exists=False,
            automatic_retry_enabled=False,
            account_read_verified=True,
            signature_verified=True,
            capital_authorized=True,
            provider_constraints_verified=True,
            management_authorized=True,
            execution_enabled=True,
            order_submission_enabled=False,
            exchange_write_enabled=False,
            database_write_enabled=False,
        ),
        canonical_request=request,
        eligibility=_eligibility(request),
    )

    assert result.state is ReadinessState.BLOCKED
    assert "EXECUTION_ALREADY_ENABLED_DURING_READINESS" in result.blockers
