from cp46_e_execution_eligibility_v0_1 import (
    EligibilityStatus,
    ExecutionEligibilityResult,
)
from cp49_first_execution_evidence_contract_v0_1 import (
    AccountSignatureEvidence,
    RealCapitalAuthorizationEvidence,
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


def _account_evidence():
    return AccountSignatureEvidence(
        evidence_id="acct-evidence-1",
        account_id="management-bound-account",
        account_type="SPOT",
        authentication_status="AUTHENTICATED",
        source="AUTHENTICATED_ACCOUNT_READ",
        source_id="TOOBIT:/api/v1/account",
        observed_at="2026-10-01T00:00:00+00:00",
    )


def _capital_evidence():
    return RealCapitalAuthorizationEvidence(
        authorization_id="auth-1",
        account_id="management-bound-account",
        capital_scope="REAL_CAPITAL:SPOT",
        authorized_by="MANAGEMENT",
        authorized_at="2026-10-01T00:00:00+00:00",
        source="MANAGEMENT_AUTHORIZATION",
    )


def _base_readiness(**overrides):
    values = dict(
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
        account_signature_evidence=_account_evidence(),
        capital_authorization_evidence=_capital_evidence(),
        authorized_account_id="management-bound-account",
    )
    values.update(overrides)
    return FirstExecutionReadinessInput(**values)


def test_readiness_blocks_on_account_signature_but_not_capital():
    request = _request()

    result = evaluate_first_execution_readiness(
        readiness=_base_readiness(
            signature_verified=False,
            capital_authorized=False,
            account_signature_evidence=None,
            capital_authorization_evidence=None,
            authorized_account_id=None,
        ),
        canonical_request=request,
        eligibility=_eligibility(request),
    )

    assert result.state is ReadinessState.BLOCKED
    assert "ACCOUNT_SIGNATURE_NOT_VERIFIED" in result.blockers
    assert "REAL_CAPITAL_NOT_AUTHORIZED" not in result.blockers


def test_readiness_is_ready_without_capital_or_management_authorization():
    request = _request()

    result = evaluate_first_execution_readiness(
        readiness=_base_readiness(
            capital_authorized=False,
            management_authorized=False,
            capital_authorization_evidence=None,
            authorized_account_id=None,
        ),
        canonical_request=request,
        eligibility=_eligibility(request),
    )

    assert result.state is ReadinessState.READY_FOR_AUTHORIZATION
    assert result.blockers == ()
    assert result.canonical_request_valid is True
    assert result.eligibility_passed is True


def test_readiness_can_be_ready_without_enabling_execution():
    request = _request()
    result = evaluate_first_execution_readiness(
        readiness=_base_readiness(),
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
        readiness=_base_readiness(
            execution_enabled=True,
        ),
        canonical_request=request,
        eligibility=_eligibility(request),
    )

    assert result.state is ReadinessState.BLOCKED
    assert "EXECUTION_ALREADY_ENABLED_DURING_READINESS" in result.blockers
