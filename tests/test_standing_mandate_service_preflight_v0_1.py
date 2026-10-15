from __future__ import annotations

import json

import pytest

from standing_mandate_lifecycle_store_v0_1 import append_lifecycle_event
from standing_mandate_service_preflight_v0_1 import (
    JOURNAL_PATH_ENV,
    verify_mandate_service_configuration,
)


def _active_journal(path, mandate_id="M-1"):
    append_lifecycle_event(
        path,
        {
            "event_id": f"activate-{mandate_id}",
            "event_type": "ACTIVATE",
            "mandate_id": mandate_id,
            "authority": "MANAGEMENT",
        },
    )
    return path


def test_preflight_passes_for_existing_persistent_journal_and_active_mandate(tmp_path, monkeypatch):
    journal = _active_journal(tmp_path / "mandate.jsonl")
    monkeypatch.setenv(JOURNAL_PATH_ENV, str(journal))

    result = verify_mandate_service_configuration(expected_mandate_id="M-1")

    assert result["status"] == "PASS"
    assert result["active_mandate_id"] == "M-1"
    assert result["lifecycle_event_count"] == 1
    assert result["provider_calls"] == 0
    assert result["database_writes"] == 0
    assert result["journal_mutated"] is False


def test_preflight_fails_when_path_is_not_configured(monkeypatch):
    monkeypatch.delenv(JOURNAL_PATH_ENV, raising=False)
    with pytest.raises(ValueError, match="MANDATE_LIFECYCLE_STORE_PATH_REQUIRED"):
        verify_mandate_service_configuration(expected_mandate_id="M-1")


def test_preflight_rejects_relative_path(tmp_path):
    with pytest.raises(ValueError, match="MUST_BE_ABSOLUTE"):
        verify_mandate_service_configuration(
            expected_mandate_id="M-1",
            journal_path="relative/mandate.jsonl",
        )


def test_preflight_fails_when_journal_missing_without_creating_it(tmp_path):
    journal = tmp_path / "missing.jsonl"
    with pytest.raises(ValueError, match="MANDATE_LIFECYCLE_STORE_MISSING"):
        verify_mandate_service_configuration(
            expected_mandate_id="M-1",
            journal_path=journal,
        )
    assert not journal.exists()


def test_preflight_fails_for_revoked_or_replaced_mandate(tmp_path):
    journal = tmp_path / "mandate.jsonl"
    _active_journal(journal, "M-1")
    append_lifecycle_event(
        journal,
        {
            "event_id": "replace-M-1",
            "event_type": "REPLACE",
            "mandate_id": "M-1",
            "replacement_mandate_id": "M-2",
            "authority": "MANAGEMENT",
        },
    )
    with pytest.raises(ValueError, match="MANDATE_NOT_ACTIVE"):
        verify_mandate_service_configuration(
            expected_mandate_id="M-1",
            journal_path=journal,
        )
    assert len(journal.read_text(encoding="utf-8").splitlines()) == 2


def test_preflight_fails_closed_on_corrupt_journal(tmp_path):
    journal = tmp_path / "mandate.jsonl"
    journal.write_text('{"event_id": "ok"}\nnot-json\n', encoding="utf-8")
    with pytest.raises(ValueError, match="STORE_CORRUPT"):
        verify_mandate_service_configuration(
            expected_mandate_id="M-1",
            journal_path=journal,
        )


def test_preflight_rejects_symlinked_journal_when_supported(tmp_path):
    actual = _active_journal(tmp_path / "actual.jsonl")
    link = tmp_path / "alias.jsonl"
    try:
        link.symlink_to(actual)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation is unavailable in this environment")
    with pytest.raises(ValueError, match="SYMLINK_FORBIDDEN"):
        verify_mandate_service_configuration(
            expected_mandate_id="M-1",
            journal_path=link,
        )
