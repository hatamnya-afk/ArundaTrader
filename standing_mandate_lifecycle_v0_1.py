"""Standing phase-entry mandate lifecycle reducer.

Pure contract: no persistence, database, provider, or runtime side effects.
The caller must supply the authoritative append-only lifecycle event history.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

ACTIVE = "ACTIVE"
REVOKED = "REVOKED"
SUPERSEDED = "SUPERSEDED"


def reduce_mandate_lifecycle(
    events: Sequence[Mapping[str, Any]],
    *,
    expected_mandate_id: str,
) -> dict[str, Any]:
    """Resolve whether expected_mandate_id is the currently active mandate.

    Event kinds:
      ACTIVATE: {"event_id", "event_type", "mandate_id", "authority"}
      REVOKE:   {"event_id", "event_type", "mandate_id", "authority"}
      REPLACE:  {"event_id", "event_type", "mandate_id",
                 "replacement_mandate_id", "authority"}

    Event order is the supplied append-only order. Duplicate event IDs,
    unknown events, wrong authority, and invalid transitions fail closed.
    """
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes)) or not events:
        raise ValueError("MANDATE_LIFECYCLE_EVENTS_REQUIRED")
    if not isinstance(expected_mandate_id, str) or not expected_mandate_id.strip():
        raise ValueError("MANDATE_ID_INVALID")

    seen: set[str] = set()
    active_id: str | None = None
    state = "UNINITIALIZED"
    revoked_ids: set[str] = set()
    superseded: dict[str, str] = {}

    for event in events:
        if not isinstance(event, Mapping):
            raise ValueError("MANDATE_LIFECYCLE_EVENT_INVALID")
        event_id = event.get("event_id")
        event_type = event.get("event_type")
        mandate_id = event.get("mandate_id")
        authority = event.get("authority")
        if not all(isinstance(x, str) and x.strip() for x in (event_id, event_type, mandate_id, authority)):
            raise ValueError("MANDATE_LIFECYCLE_EVENT_INVALID")
        if event_id in seen:
            raise ValueError("MANDATE_LIFECYCLE_DUPLICATE_EVENT")
        seen.add(event_id)
        if authority != "MANAGEMENT":
            raise ValueError("MANDATE_LIFECYCLE_AUTHORITY_INVALID")

        if event_type == "ACTIVATE":
            if active_id is not None:
                raise ValueError("MANDATE_LIFECYCLE_ACTIVE_MANDATE_EXISTS")
            if mandate_id in revoked_ids or mandate_id in superseded:
                raise ValueError("MANDATE_LIFECYCLE_TERMINAL_MANDATE_REACTIVATION")
            active_id = mandate_id
            state = ACTIVE
        elif event_type == "REVOKE":
            if active_id != mandate_id or state != ACTIVE:
                raise ValueError("MANDATE_LIFECYCLE_REVOKE_NOT_ACTIVE")
            active_id = None
            state = REVOKED
            revoked_ids.add(mandate_id)
        elif event_type == "REPLACE":
            replacement = event.get("replacement_mandate_id")
            if active_id != mandate_id or state != ACTIVE:
                raise ValueError("MANDATE_LIFECYCLE_REPLACE_NOT_ACTIVE")
            if not isinstance(replacement, str) or not replacement.strip() or replacement == mandate_id:
                raise ValueError("MANDATE_LIFECYCLE_REPLACEMENT_ID_INVALID")
            active_id = replacement
            state = ACTIVE
            superseded[mandate_id] = replacement
        else:
            raise ValueError("MANDATE_LIFECYCLE_EVENT_TYPE_INVALID")

    if active_id != expected_mandate_id or state != ACTIVE:
        raise ValueError("MANDATE_NOT_ACTIVE")
    return {
        "mandate_id": active_id,
        "mandate_state": ACTIVE,
        "revoked_mandate_ids": tuple(sorted(revoked_ids)),
        "superseded_mandates": dict(superseded),
        "lifecycle_event_count": len(seen),
    }


__all__ = ["ACTIVE", "REVOKED", "SUPERSEDED", "reduce_mandate_lifecycle"]
