"""Durable append-only JSONL store for standing-mandate lifecycle events.

This module is an explicit persistence adapter, not a production wiring change.
The caller chooses and protects the storage path. No database/provider/runtime
integration is performed here.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from collections.abc import Mapping
from typing import Any

from standing_mandate_lifecycle_v0_1 import reduce_mandate_lifecycle

_LOCKS: dict[str, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()


def _thread_lock(path: Path) -> threading.RLock:
    key = str(path.resolve())
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(key, threading.RLock())


def _read_unlocked(path: Path) -> tuple[dict[str, Any], ...]:
    if not path.exists():
        return ()
    events = []
    with path.open("r", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"MANDATE_LIFECYCLE_STORE_CORRUPT:{line_number}") from exc
            if not isinstance(event, dict):
                raise ValueError(f"MANDATE_LIFECYCLE_STORE_CORRUPT:{line_number}")
            events.append(event)
    return tuple(events)


def read_lifecycle_events(path: str | os.PathLike[str]) -> tuple[dict[str, Any], ...]:
    """Read the append-only lifecycle journal; malformed rows fail closed."""
    target = Path(path)
    with _thread_lock(target):
        return _read_unlocked(target)


def append_lifecycle_event(
    path: str | os.PathLike[str],
    event: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Validate and durably append one lifecycle event, never rewrite history.

    Uses an OS file lock on a sibling lock file, fsyncs the appended journal
    row, and validates the complete prospective lifecycle before committing.
    """
    if not isinstance(event, Mapping):
        raise ValueError("MANDATE_LIFECYCLE_EVENT_INVALID")
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lock_path = target.with_name(target.name + ".lock")

    with _thread_lock(target):
        with lock_path.open("a+b") as lock_stream:
            if os.name == "nt":
                import msvcrt
                lock_stream.seek(0, os.SEEK_END)
                if lock_stream.tell() == 0:
                    lock_stream.write(b"0")
                    lock_stream.flush()
                lock_stream.seek(0)
                msvcrt.locking(lock_stream.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock_stream.fileno(), fcntl.LOCK_EX)
            try:
                existing = _read_unlocked(target)
                candidate = tuple(existing) + (dict(event),)
                _validate_history(candidate)
                encoded = json.dumps(dict(event), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                with target.open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(encoded + "\n")
                    stream.flush()
                    os.fsync(stream.fileno())
                return candidate
            finally:
                if os.name == "nt":
                    lock_stream.seek(0)
                    msvcrt.locking(lock_stream.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock_stream.fileno(), fcntl.LOCK_UN)


def _validate_history(events: tuple[dict[str, Any], ...]) -> None:
    active: str | None = None
    terminal: set[str] = set()
    seen: set[str] = set()
    for event in events:
        event_id = event.get("event_id")
        kind = event.get("event_type")
        mandate_id = event.get("mandate_id")
        if not all(isinstance(x, str) and x.strip() for x in (event_id, kind, mandate_id)):
            raise ValueError("MANDATE_LIFECYCLE_EVENT_INVALID")
        if event_id in seen:
            raise ValueError("MANDATE_LIFECYCLE_DUPLICATE_EVENT")
        seen.add(event_id)
        if event.get("authority") != "MANAGEMENT":
            raise ValueError("MANDATE_LIFECYCLE_AUTHORITY_INVALID")
        if kind == "ACTIVATE":
            if active is not None:
                raise ValueError("MANDATE_LIFECYCLE_ACTIVE_MANDATE_EXISTS")
            if mandate_id in terminal:
                raise ValueError("MANDATE_LIFECYCLE_TERMINAL_MANDATE_REACTIVATION")
            active = mandate_id
        elif kind == "REVOKE":
            if active != mandate_id:
                raise ValueError("MANDATE_LIFECYCLE_REVOKE_NOT_ACTIVE")
            terminal.add(mandate_id)
            active = None
        elif kind == "REPLACE":
            replacement = event.get("replacement_mandate_id")
            if active != mandate_id:
                raise ValueError("MANDATE_LIFECYCLE_REPLACE_NOT_ACTIVE")
            if not isinstance(replacement, str) or not replacement.strip() or replacement == mandate_id:
                raise ValueError("MANDATE_LIFECYCLE_REPLACEMENT_ID_INVALID")
            terminal.add(mandate_id)
            active = replacement
        else:
            raise ValueError("MANDATE_LIFECYCLE_EVENT_TYPE_INVALID")


def record_management_phase_entry(
    path: str | os.PathLike[str],
    management_result: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Persist the activation event from a validated management phase-entry result.

    This is an explicit management action; runtime authorization never creates
    or repairs a missing journal automatically.
    """
    if not isinstance(management_result, Mapping):
        raise ValueError("MANAGEMENT_PHASE_ENTRY_RESULT_INVALID")
    if management_result.get("management_state") != "AUTHORIZED":
        raise ValueError("MANAGEMENT_PHASE_ENTRY_NOT_AUTHORIZED")
    if management_result.get("execution_authorization") != "AUTHORIZED_STANDING_MANDATE":
        raise ValueError("MANAGEMENT_STANDING_MANDATE_REQUIRED")
    observation = management_result.get("authorization_observation")
    if not isinstance(observation, Mapping):
        raise ValueError("MANAGEMENT_AUTHORIZATION_OBSERVATION_INVALID")
    if observation.get("authorization_mode") != "STANDING_MANDATE":
        raise ValueError("MANAGEMENT_STANDING_MANDATE_REQUIRED")
    if observation.get("environment") != "REAL_PRODUCTION":
        raise ValueError("MANAGEMENT_ENVIRONMENT_INVALID")
    mandate_id = observation.get("mandate_id")
    if not isinstance(mandate_id, str) or not mandate_id.strip():
        raise ValueError("MANAGEMENT_MANDATE_ID_INVALID")
    return append_lifecycle_event(
        path,
        {
            "event_id": f"PHASE_ENTRY_ACTIVATE:{mandate_id.strip()}",
            "event_type": "ACTIVATE",
            "mandate_id": mandate_id.strip(),
            "authority": "MANAGEMENT",
        },
    )


def require_active_mandate(
    path: str | os.PathLike[str],
    *,
    expected_mandate_id: str,
) -> tuple[dict[str, Any], ...]:
    """Return authoritative history only if the requested identity is active."""
    events = read_lifecycle_events(path)
    reduce_mandate_lifecycle(events, expected_mandate_id=expected_mandate_id)
    return events


__all__ = ["append_lifecycle_event", "read_lifecycle_events", "record_management_phase_entry", "require_active_mandate"]
