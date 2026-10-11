"""Offline tests for fail-closed provider order reconciliation policy."""
from exchange_execution_order_reconciliation_contract_v0_1 import (
    ProviderOrderLookup,
    evaluate_order_reconciliation,
)


def test_matching_provider_order_blocks_resubmission():
    result = evaluate_order_reconciliation(
        expected_client_order_id="intent-abc",
        prior_attempt="PRIOR_ATTEMPT_FOUND",
        lookup=ProviderOrderLookup(
            state="FOUND",
            client_order_id="intent-abc",
            exchange_order_id="exchange-123",
            provider_status="NEW",
        ),
    )
    assert result.state == "MATCHED"
    assert result.exchange_order_id == "exchange-123"
    assert result.may_submit is False
    assert result.retry_allowed is False


def test_not_found_after_prior_attempt_is_not_permission_to_retry():
    result = evaluate_order_reconciliation(
        expected_client_order_id="intent-abc",
        prior_attempt="PRIOR_ATTEMPT_FOUND",
        lookup=ProviderOrderLookup(state="NOT_FOUND"),
    )
    assert result.state == "RECONCILIATION_REQUIRED"
    assert result.reason_code == "NOT_FOUND_DOES_NOT_PROVE_NON_ACCEPTANCE"
    assert result.may_submit is False
    assert result.retry_allowed is False


def test_provider_id_mismatch_is_ambiguous_and_blocked():
    result = evaluate_order_reconciliation(
        expected_client_order_id="intent-abc",
        prior_attempt="PRIOR_ATTEMPT_FOUND",
        lookup=ProviderOrderLookup(
            state="FOUND",
            client_order_id="different-id",
            exchange_order_id="exchange-123",
        ),
    )
    assert result.state == "AMBIGUOUS"
    assert result.may_submit is False
    assert result.retry_allowed is False


def test_multiple_matches_are_blocked():
    result = evaluate_order_reconciliation(
        expected_client_order_id="intent-abc",
        prior_attempt="PRIOR_ATTEMPT_FOUND",
        lookup=ProviderOrderLookup(state="MULTIPLE"),
    )
    assert result.state == "AMBIGUOUS"
    assert result.may_submit is False
    assert result.retry_allowed is False


def test_lookup_error_is_blocked():
    result = evaluate_order_reconciliation(
        expected_client_order_id="intent-abc",
        prior_attempt="PRIOR_ATTEMPT_FOUND",
        lookup=ProviderOrderLookup(state="ERROR"),
    )
    assert result.state == "RECONCILIATION_REQUIRED"
    assert result.may_submit is False
    assert result.retry_allowed is False


def test_unknown_attempt_history_is_blocked_without_lookup():
    result = evaluate_order_reconciliation(
        expected_client_order_id="intent-abc",
        prior_attempt="UNKNOWN",
        lookup=None,
    )
    assert result.reason_code == "PRIOR_ATTEMPT_HISTORY_UNKNOWN"
    assert result.may_submit is False
    assert result.retry_allowed is False


def test_missing_client_order_id_fails_closed():
    result = evaluate_order_reconciliation(
        expected_client_order_id=" ",
        prior_attempt="NO_PRIOR_ATTEMPT",
        lookup=None,
    )
    assert result.reason_code == "CLIENT_ORDER_ID_REQUIRED"
    assert result.may_submit is False
    assert result.retry_allowed is False


def test_no_prior_attempt_does_not_authorize_submission():
    result = evaluate_order_reconciliation(
        expected_client_order_id="intent-abc",
        prior_attempt="NO_PRIOR_ATTEMPT",
        lookup=None,
    )
    assert result.state == "PRECHECK_ONLY"
    assert result.reason_code == "SEPARATE_ATOMIC_CLAIM_AND_AUTHORIZATION_REQUIRED"
    assert result.may_submit is False
    assert result.retry_allowed is False


def test_found_order_with_missing_exchange_id_is_ambiguous():
    result = evaluate_order_reconciliation(
        expected_client_order_id="intent-abc",
        prior_attempt="PRIOR_ATTEMPT_FOUND",
        lookup=ProviderOrderLookup(
            state="FOUND",
            client_order_id="intent-abc",
            exchange_order_id=None,
        ),
    )
    assert result.state == "AMBIGUOUS"
    assert result.reason_code == "PROVIDER_ORDER_ID_MISSING"
    assert result.may_submit is False
    assert result.retry_allowed is False
