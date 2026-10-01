from cp49_first_execution_contract_v0_1 import AttemptState
from cp49_first_execution_readiness_v0_1 import (
    FirstExecutionReadinessResult,
    ReadinessState,
)
from cp49_readiness_to_execution_gate_binding_v0_1 import (
    build_execution_safety_gate,
)


def _ready_readiness():
    return FirstExecutionReadinessResult(
        state=ReadinessState.READY_FOR_AUTHORIZATION,
        blockers=(),
        canonical_request_valid=True,
        eligibility_passed=True,
    )


def _blocked_readiness():
    return FirstExecutionReadinessResult(
        state=ReadinessState.BLOCKED,
        blockers=("ACCOUNT_SIGNATURE_NOT_VERIFIED",),
        canonical_request_valid=True,
        eligibility_passed=True,
    )


def test_ready_readiness_binds_to_existing_single_gate():
    gate = build_execution_safety_gate(
        readiness=_ready_readiness(),
        management_authorized=True,
        prior_attempt_exists=False,
        automatic_retry_enabled=False,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
    )

    assert gate.validate() is AttemptState.READY


def test_readiness_alone_does_not_authorize_execution():
    gate = build_execution_safety_gate(
        readiness=_ready_readiness(),
        management_authorized=False,
        prior_attempt_exists=False,
        automatic_retry_enabled=False,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
    )

    assert gate.validate() is AttemptState.BLOCKED


def test_execution_flags_alone_do_not_bypass_readiness():
    try:
        build_execution_safety_gate(
            readiness=_blocked_readiness(),
            management_authorized=True,
            prior_attempt_exists=False,
            automatic_retry_enabled=False,
            execution_enabled=True,
            order_submission_enabled=True,
            exchange_write_enabled=True,
        )
    except ValueError as exc:
        assert str(exc) == "READINESS_NOT_READY_FOR_AUTHORIZATION"
    else:
        raise AssertionError(
            "Blocked readiness must never reach the execution gate."
        )


def test_no_prior_attempt_and_no_retry_remain_required():
    gate = build_execution_safety_gate(
        readiness=_ready_readiness(),
        management_authorized=True,
        prior_attempt_exists=True,
        automatic_retry_enabled=False,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
    )

    assert gate.validate() is AttemptState.BLOCKED


def test_retry_enabled_blocks_first_execution():
    gate = build_execution_safety_gate(
        readiness=_ready_readiness(),
        management_authorized=True,
        prior_attempt_exists=False,
        automatic_retry_enabled=True,
        execution_enabled=True,
        order_submission_enabled=True,
        exchange_write_enabled=True,
    )

    assert gate.validate() is AttemptState.BLOCKED