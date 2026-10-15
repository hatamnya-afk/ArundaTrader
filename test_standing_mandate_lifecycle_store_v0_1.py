import pytest

from standing_mandate_lifecycle_store_v0_1 import (
    append_lifecycle_event,
    read_lifecycle_events,
    require_active_mandate,
)


def _event(event_id, event_type, mandate_id, **extra):
    return {
        "event_id": event_id,
        "event_type": event_type,
        "mandate_id": mandate_id,
        "authority": "MANAGEMENT",
        **extra,
    }


def test_journal_persists_activation_and_revocation_append_only(tmp_path):
    journal = tmp_path / "mandate-lifecycle.jsonl"
    activation = _event("activate-1", "ACTIVATE", "M-1")
    append_lifecycle_event(journal, activation)
    assert require_active_mandate(journal, expected_mandate_id="M-1")[0] == activation

    append_lifecycle_event(journal, _event("revoke-1", "REVOKE", "M-1"))
    with pytest.raises(ValueError, match="MANDATE_NOT_ACTIVE"):
        require_active_mandate(journal, expected_mandate_id="M-1")
    assert len(read_lifecycle_events(journal)) == 2


def test_journal_replacement_activates_new_identity_and_rejects_old(tmp_path):
    journal = tmp_path / "mandate-lifecycle.jsonl"
    append_lifecycle_event(journal, _event("activate-1", "ACTIVATE", "M-1"))
    append_lifecycle_event(
        journal,
        _event("replace-1", "REPLACE", "M-1", replacement_mandate_id="M-2"),
    )
    with pytest.raises(ValueError, match="MANDATE_NOT_ACTIVE"):
        require_active_mandate(journal, expected_mandate_id="M-1")
    events = require_active_mandate(journal, expected_mandate_id="M-2")
    assert len(events) == 2


def test_journal_rejects_duplicate_ids_and_bad_transitions_before_append(tmp_path):
    journal = tmp_path / "mandate-lifecycle.jsonl"
    activation = _event("activate-1", "ACTIVATE", "M-1")
    append_lifecycle_event(journal, activation)
    with pytest.raises(ValueError, match="MANDATE_LIFECYCLE_DUPLICATE_EVENT"):
        append_lifecycle_event(journal, activation)
    with pytest.raises(ValueError, match="MANDATE_LIFECYCLE_REVOKE_NOT_ACTIVE"):
        append_lifecycle_event(journal, _event("revoke-wrong", "REVOKE", "M-2"))
    assert len(read_lifecycle_events(journal)) == 1


def test_journal_rejects_untrusted_event_authority(tmp_path):
    journal = tmp_path / "mandate-lifecycle.jsonl"
    event = _event("activate-1", "ACTIVATE", "M-1")
    event["authority"] = "UNTRUSTED"
    with pytest.raises(ValueError, match="MANDATE_LIFECYCLE_AUTHORITY_INVALID"):
        append_lifecycle_event(journal, event)
    assert read_lifecycle_events(journal) == ()
