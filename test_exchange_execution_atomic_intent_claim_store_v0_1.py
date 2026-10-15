"""Offline tests against the actual SQLite unique-key claim implementation."""
from concurrent.futures import ProcessPoolExecutor
import multiprocessing

import pytest

from exchange_execution_atomic_intent_claim_store_v0_1 import (
    CLAIMED,
    PROVIDER_ACCEPTED,
    RECONCILIATION_REQUIRED,
    SUBMISSION_OUTCOME_UNKNOWN,
    SQLiteIntentClaimStore,
)


def _claim_in_child(args):
    path, intent, client_id = args
    store = SQLiteIntentClaimStore(path)
    result = store.claim(
        provider_namespace="TOOBIT-FUTURES",
        intent_id=intent,
        client_order_id=client_id,
    )
    return result.outcome


def test_first_claim_wins_and_duplicate_is_not_reclaimed(tmp_path):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    first = store.claim(provider_namespace="toobit-futures", intent_id="I-1", client_order_id="AR-1")
    second = store.claim(provider_namespace="TOOBIT-FUTURES", intent_id="I-1", client_order_id="AR-1")
    assert first.outcome == "CLAIMED"
    assert second.outcome == "ALREADY_CLAIMED"
    assert second.status == CLAIMED


def test_different_client_id_for_same_intent_is_identity_conflict(tmp_path):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    result = store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-2")
    assert result.outcome == "IDENTITY_CONFLICT"


def test_unique_client_id_cannot_be_reused_for_another_intent(tmp_path):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    result = store.claim(provider_namespace="P", intent_id="I-2", client_order_id="C-1")
    assert result.outcome == "CLIENT_ORDER_ID_COLLISION"


def test_claim_is_durable_across_store_reconstruction(tmp_path):
    path = tmp_path / "claims.sqlite3"
    SQLiteIntentClaimStore(path).claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    reopened = SQLiteIntentClaimStore(path)
    assert reopened.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1").outcome == "ALREADY_CLAIMED"


def test_actual_sqlite_unique_key_allows_only_one_process_to_claim(tmp_path):
    path = str(tmp_path / "concurrent.sqlite3")
    SQLiteIntentClaimStore(path)
    workers = 8
    args = [(path, "SAME-INTENT", "SAME-CLIENT-ID") for _ in range(workers)]
    with ProcessPoolExecutor(max_workers=workers, mp_context=multiprocessing.get_context("spawn")) as pool:
        outcomes = list(pool.map(_claim_in_child, args))
    assert outcomes.count("CLAIMED") == 1
    assert outcomes.count("ALREADY_CLAIMED") == workers - 1


def test_different_intents_can_claim_distinct_ids(tmp_path):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    a = store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    b = store.claim(provider_namespace="P", intent_id="I-2", client_order_id="C-2")
    assert (a.outcome, b.outcome) == ("CLAIMED", "CLAIMED")


def test_unknown_submission_outcome_remains_claimed_after_restart(tmp_path):
    path = tmp_path / "claims.sqlite3"
    store = SQLiteIntentClaimStore(path)
    store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    store.transition(provider_namespace="P", intent_id="I-1", status=SUBMISSION_OUTCOME_UNKNOWN)
    reopened = SQLiteIntentClaimStore(path)
    assert reopened.get(provider_namespace="P", intent_id="I-1").status == SUBMISSION_OUTCOME_UNKNOWN
    assert reopened.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1").outcome == "ALREADY_CLAIMED"


def test_reconciliation_state_cannot_be_reopened_as_claimed(tmp_path):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    store.transition(provider_namespace="P", intent_id="I-1", status=RECONCILIATION_REQUIRED)
    with pytest.raises(ValueError, match="CLAIM_STATE_TRANSITION_INVALID"):
        store.transition(provider_namespace="P", intent_id="I-1", status=CLAIMED)


def test_provider_evidence_identity_mapping_is_persisted(tmp_path):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    claim = store.transition(
        provider_namespace="P", intent_id="I-1", status=PROVIDER_ACCEPTED,
        trade_event_id="TE-1", decision_id="D-1", exchange_order_id="EX-1",
        provider_status="NEW", evidence_event_id="EV-1",
    )
    assert claim.trade_event_id == "TE-1"
    assert claim.decision_id == "D-1"
    assert claim.exchange_order_id == "EX-1"
    assert claim.provider_status == "NEW"
    assert claim.evidence_event_id == "EV-1"


def test_terminal_provider_acceptance_cannot_be_changed_to_rejected(tmp_path):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    store.transition(provider_namespace="P", intent_id="I-1", status=PROVIDER_ACCEPTED, trade_event_id="TE-1", decision_id="D-1", exchange_order_id="EX-1", provider_status="NEW", evidence_event_id="EV-1")
    from exchange_execution_atomic_intent_claim_store_v0_1 import PROVIDER_REJECTED
    with pytest.raises(ValueError, match="TERMINAL_CLAIM_STATE_CANNOT_CHANGE"):
        store.transition(provider_namespace="P", intent_id="I-1", status=PROVIDER_REJECTED)


@pytest.mark.parametrize(
    ("provider", "intent", "client_id", "reason"),
    [
        ("", "I-1", "C-1", "PROVIDER_NAMESPACE_REQUIRED"),
        ("P", " ", "C-1", "CANONICAL_INTENT_ID_REQUIRED"),
        ("P", "I-1", "", "CLIENT_ORDER_ID_REQUIRED"),
    ],
)
def test_missing_claim_identity_fails_closed(tmp_path, provider, intent, client_id, reason):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    with pytest.raises(ValueError, match=reason):
        store.claim(provider_namespace=provider, intent_id=intent, client_order_id=client_id)


def test_memory_database_is_rejected_as_not_durable():
    with pytest.raises(ValueError, match="DURABLE_SQLITE_PATH_REQUIRED"):
        SQLiteIntentClaimStore(":memory:")


def test_missing_parent_directory_fails_closed(tmp_path):
    with pytest.raises(ValueError, match="CLAIM_STORE_PARENT_DIRECTORY_MISSING"):
        SQLiteIntentClaimStore(tmp_path / "missing" / "claims.sqlite3")


def test_invalid_status_is_rejected(tmp_path):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    with pytest.raises(ValueError, match="CLAIM_STATUS_INVALID"):
        store.transition(provider_namespace="P", intent_id="I-1", status="RELEASED")


def test_no_release_or_delete_api_exists():
    assert not hasattr(SQLiteIntentClaimStore, "release")
    assert not hasattr(SQLiteIntentClaimStore, "delete")


def test_provider_acceptance_requires_order_identity_evidence(tmp_path):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    with pytest.raises(ValueError, match="ACCEPTED_ORDER_EVIDENCE_REQUIRED"):
        store.transition(provider_namespace="P", intent_id="I-1", status=PROVIDER_ACCEPTED)


def test_identical_provider_evidence_is_idempotent(tmp_path):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    args = dict(
        provider_namespace="P", intent_id="I-1", status=PROVIDER_ACCEPTED,
        trade_event_id="TE-1", decision_id="D-1", exchange_order_id="EX-1",
        provider_status="NEW", evidence_event_id="EV-1",
    )
    first = store.transition(**args)
    second = store.transition(**args)
    assert first.exchange_order_id == second.exchange_order_id == "EX-1"
    assert first.evidence_event_id == second.evidence_event_id == "EV-1"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("decision_id", "D-OTHER"),
        ("exchange_order_id", "EX-OTHER"),
        ("evidence_event_id", "EV-OTHER"),
        ("trade_event_id", "TE-OTHER"),
    ],
)
def test_conflicting_evidence_cannot_overwrite_existing_claim(tmp_path, field, value):
    store = SQLiteIntentClaimStore(tmp_path / "claims.sqlite3")
    store.claim(provider_namespace="P", intent_id="I-1", client_order_id="C-1")
    store.transition(
        provider_namespace="P", intent_id="I-1", status=PROVIDER_ACCEPTED,
        trade_event_id="TE-1", decision_id="D-1", exchange_order_id="EX-1",
        provider_status="NEW", evidence_event_id="EV-1",
    )
    update = {
        "provider_namespace": "P", "intent_id": "I-1", "status": PROVIDER_ACCEPTED,
        "trade_event_id": "TE-1", "decision_id": "D-1", "exchange_order_id": "EX-1",
        "provider_status": "NEW", "evidence_event_id": "EV-1",
    }
    update[field] = value
    with pytest.raises(ValueError, match="EVIDENCE_IDENTITY_CONFLICT"):
        store.transition(**update)
    current = store.get(provider_namespace="P", intent_id="I-1")
    assert current.decision_id == "D-1"
    assert current.exchange_order_id == "EX-1"
    assert current.evidence_event_id == "EV-1"
