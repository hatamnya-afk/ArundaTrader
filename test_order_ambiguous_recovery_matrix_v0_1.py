"""Offline recovery matrix for ambiguous order submission and lookup evidence.

These tests exercise only local policy helpers and SQLite under pytest tmp_path.
They do not call Toobit, submit/cancel orders, or authorize execution.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from exchange_execution_atomic_intent_claim_store_v0_1 import (
    CLAIMED,
    RECONCILIATION_REQUIRED,
    SUBMISSION_OUTCOME_UNKNOWN,
    SQLiteIntentClaimStore,
)
from exchange_execution_order_reconciliation_contract_v0_1 import (
    ProviderOrderLookup,
    evaluate_order_reconciliation,
)


CLIENT_ID = "AR-RECOVERY-MATRIX-001"
PROVIDER = "TOOBIT-FUTURES"
INTENT = "INTENT-RECOVERY-MATRIX-001"


def _evaluate(lookup, prior_attempt="PRIOR_ATTEMPT_FOUND"):
    return evaluate_order_reconciliation(
        expected_client_order_id=CLIENT_ID,
        prior_attempt=prior_attempt,
        lookup=lookup,
    )


@pytest.mark.parametrize(
    "lookup",
    [
        None,
        ProviderOrderLookup(state="ERROR", detail_code="TRANSPORT_TIMEOUT"),
        ProviderOrderLookup(state="ERROR", detail_code="PROVIDER_5XX"),
        ProviderOrderLookup(state="NOT_FOUND", detail_code="TOOBIT_NO_SUCH_ORDER"),
    ],
    ids=["no-lookup-result", "lookup-timeout", "provider-error", "not-found"],
)
def test_ambiguous_submission_or_lookup_never_authorizes_resubmission(lookup):
    decision = _evaluate(lookup)
    assert decision.may_submit is False
    assert decision.retry_allowed is False
    assert decision.state == "RECONCILIATION_REQUIRED"


def test_found_order_after_submission_timeout_is_matched_without_resubmit():
    decision = _evaluate(
        ProviderOrderLookup(
            state="FOUND",
            client_order_id=CLIENT_ID,
            exchange_order_id="EX-FOUND-001",
            provider_status="NEW",
        )
    )
    assert decision.state == "MATCHED"
    assert decision.exchange_order_id == "EX-FOUND-001"
    assert decision.may_submit is False
    assert decision.retry_allowed is False


@pytest.mark.parametrize("terminal_status", ["FILLED", "CANCELED", "REJECTED"])
def test_found_terminal_order_is_evidence_not_permission_to_submit_again(terminal_status):
    decision = _evaluate(
        ProviderOrderLookup(
            state="FOUND",
            client_order_id=CLIENT_ID,
            exchange_order_id=f"EX-{terminal_status}-001",
            provider_status=terminal_status,
        )
    )
    assert decision.state == "MATCHED"
    assert decision.may_submit is False
    assert decision.retry_allowed is False


@pytest.mark.parametrize(
    "lookup, expected_reason",
    [
        (
            ProviderOrderLookup(
                state="FOUND",
                client_order_id="OTHER-CLIENT-ID",
                exchange_order_id="EX-MISMATCH",
                provider_status="NEW",
            ),
            "PROVIDER_CLIENT_ORDER_ID_MISMATCH",
        ),
        (
            ProviderOrderLookup(
                state="FOUND",
                client_order_id=CLIENT_ID,
                exchange_order_id=None,
                provider_status="NEW",
            ),
            "PROVIDER_ORDER_ID_MISSING",
        ),
    ],
)
def test_incomplete_or_mismatched_identity_fails_closed(lookup, expected_reason):
    decision = _evaluate(lookup)
    assert decision.state == "AMBIGUOUS"
    assert decision.reason_code == expected_reason
    assert decision.may_submit is False
    assert decision.retry_allowed is False


def test_multiple_matches_are_ambiguous_and_never_trigger_retry():
    decision = _evaluate(ProviderOrderLookup(state="MULTIPLE"))
    assert decision.state == "AMBIGUOUS"
    assert decision.reason_code == "MULTIPLE_PROVIDER_ORDERS_FOUND"
    assert decision.may_submit is False
    assert decision.retry_allowed is False


def test_unknown_attempt_history_stays_blocked_even_if_lookup_says_not_found():
    decision = _evaluate(
        ProviderOrderLookup(state="NOT_FOUND"),
        prior_attempt="UNKNOWN",
    )
    assert decision.state == "RECONCILIATION_REQUIRED"
    assert decision.reason_code == "PRIOR_ATTEMPT_HISTORY_UNKNOWN"
    assert decision.may_submit is False
    assert decision.retry_allowed is False


def test_durable_claim_survives_unknown_outcome_and_not_found(tmp_path: Path):
    path = tmp_path / "isolated-claims.sqlite3"
    store = SQLiteIntentClaimStore(path)
    first = store.claim(
        provider_namespace=PROVIDER,
        intent_id=INTENT,
        client_order_id=CLIENT_ID,
    )
    assert first.outcome == "CLAIMED"

    store.transition(
        provider_namespace=PROVIDER,
        intent_id=INTENT,
        status=SUBMISSION_OUTCOME_UNKNOWN,
        detail_code="SUBMISSION_TIMEOUT_OUTCOME_UNKNOWN",
    )
    decision = _evaluate(ProviderOrderLookup(state="NOT_FOUND"))
    assert decision.may_submit is False
    assert decision.retry_allowed is False

    reopened = SQLiteIntentClaimStore(path)
    persisted = reopened.get(provider_namespace=PROVIDER, intent_id=INTENT)
    replay = reopened.claim(
        provider_namespace=PROVIDER,
        intent_id=INTENT,
        client_order_id=CLIENT_ID,
    )
    assert persisted is not None
    assert persisted.status == SUBMISSION_OUTCOME_UNKNOWN
    assert replay.outcome == "ALREADY_CLAIMED"
    assert replay.status == SUBMISSION_OUTCOME_UNKNOWN


def test_claim_collision_for_different_intent_cannot_reuse_same_client_id(tmp_path: Path):
    store = SQLiteIntentClaimStore(tmp_path / "isolated-claims.sqlite3")
    first = store.claim(
        provider_namespace=PROVIDER,
        intent_id="INTENT-ONE",
        client_order_id=CLIENT_ID,
    )
    second = store.claim(
        provider_namespace=PROVIDER,
        intent_id="INTENT-TWO",
        client_order_id=CLIENT_ID,
    )
    assert first.outcome == "CLAIMED"
    assert second.outcome == "CLIENT_ORDER_ID_COLLISION"


def test_concurrent_claims_for_same_intent_produce_one_durable_claim(tmp_path: Path):
    path = tmp_path / "concurrent-claims.sqlite3"

    def attempt_claim(_):
        return SQLiteIntentClaimStore(path).claim(
            provider_namespace=PROVIDER,
            intent_id=INTENT,
            client_order_id=CLIENT_ID,
        )

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(attempt_claim, range(8)))

    outcomes = [result.outcome for result in results]
    assert outcomes.count("CLAIMED") == 1
    assert outcomes.count("ALREADY_CLAIMED") == 7
    assert all(result.client_order_id == CLIENT_ID for result in results)
    stored = SQLiteIntentClaimStore(path).get(
        provider_namespace=PROVIDER,
        intent_id=INTENT,
    )
    assert stored is not None
    assert stored.status == CLAIMED


def test_reconciliation_contract_is_policy_only_and_never_grants_submit_permission():
    # Even the no-prior-attempt branch is only a precheck; authorization and
    # durable claim are separate prerequisites outside this pure helper.
    decision = evaluate_order_reconciliation(
        expected_client_order_id=CLIENT_ID,
        prior_attempt="NO_PRIOR_ATTEMPT",
        lookup=None,
    )
    assert decision.state == "PRECHECK_ONLY"
    assert decision.reason_code == "SEPARATE_ATOMIC_CLAIM_AND_AUTHORIZATION_REQUIRED"
    assert decision.may_submit is False
    assert decision.retry_allowed is False
