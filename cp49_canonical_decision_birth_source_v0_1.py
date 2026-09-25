"""CP49 canonical Decision Birth Source.

The canonical decision_id must originate outside this module from an
authoritative Decision Birth event. This module validates and binds that
identity; it never generates, derives, hashes, timestamps, or synthesizes it.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any


REQUIRED_FIELDS = (
    "decision_id",
    "asset",
    "decision_timestamp_ms",
    "snapshot_id",
    "source",
)


def require_canonical_decision_birth(
    birth_event: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(birth_event, Mapping):
        raise ValueError("CANONICAL_DECISION_BIRTH_INPUT_INVALID")

    missing = [
        field for field in REQUIRED_FIELDS
        if field not in birth_event
    ]
    if missing:
        raise ValueError(
            "CANONICAL_DECISION_BIRTH_FIELDS_MISSING:"
            + ",".join(missing)
        )

    decision_id = birth_event["decision_id"]
    if not isinstance(decision_id, str) or not decision_id.strip():
        raise ValueError("CANONICAL_DECISION_ID_MISSING_AT_BIRTH_SOURCE")

    asset = birth_event["asset"]
    if not isinstance(asset, str) or not asset.strip():
        raise ValueError("CANONICAL_DECISION_BIRTH_ASSET_INVALID")

    timestamp = birth_event["decision_timestamp_ms"]
    if (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, int)
        or timestamp <= 0
    ):
        raise ValueError(
            "CANONICAL_DECISION_BIRTH_TIMESTAMP_INVALID"
        )

    snapshot_id = birth_event["snapshot_id"]
    if not isinstance(snapshot_id, str) or not snapshot_id.strip():
        raise ValueError("CANONICAL_DECISION_BIRTH_SNAPSHOT_INVALID")

    source = birth_event["source"]
    if not isinstance(source, str) or not source.strip():
        raise ValueError("CANONICAL_DECISION_BIRTH_SOURCE_INVALID")

    bound = dict(birth_event)
    bound["decision_id"] = decision_id.strip()
    bound["asset"] = asset.strip()
    bound["snapshot_id"] = snapshot_id.strip()
    bound["source"] = source.strip()

    return bound


def propagate_canonical_decision_id(
    birth_event: Mapping[str, Any],
) -> str:
    bound = require_canonical_decision_birth(birth_event)
    return bound["decision_id"]
