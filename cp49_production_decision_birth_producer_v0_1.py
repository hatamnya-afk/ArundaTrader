"""CP49 production Decision Birth producer boundary.

This is the production integration point for canonical Decision Birth.
It accepts only an already-existing authoritative birth event per asset.
It never generates, derives, hashes, timestamps, persists, or mutates identity.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from cp49_canonical_decision_birth_source_v0_1 import (
    require_canonical_decision_birth,
)


def produce_canonical_decision_ids(
    birth_events: Mapping[str, Mapping[str, Any]],
) -> dict[str, str]:
    if not isinstance(birth_events, Mapping):
        raise RuntimeError("CANONICAL_DECISION_BIRTH_EVENTS_INVALID")

    result: dict[str, str] = {}

    for asset, event in birth_events.items():
        if not isinstance(asset, str) or not asset.strip():
            raise RuntimeError("CANONICAL_DECISION_BIRTH_ASSET_INVALID")

        try:
            bound = require_canonical_decision_birth(event)
        except ValueError as exc:
            raise RuntimeError(
                f"CANONICAL_DECISION_BIRTH_EVENT_INVALID:{asset}:{exc}"
            ) from exc

        event_asset = bound["asset"].strip().upper()
        if event_asset != asset.strip().upper():
            raise RuntimeError(
                f"CANONICAL_DECISION_BIRTH_ASSET_MISMATCH:{asset}"
            )

        result[asset.strip().upper()] = bound["decision_id"]

    if set(result) != {str(key).strip().upper() for key in birth_events}:
        raise RuntimeError("CANONICAL_DECISION_BIRTH_CARDINALITY_MISMATCH")

    return result


def require_production_decision_birth(
    birth_events: Mapping[str, Mapping[str, Any]],
    *,
    expected_assets: set[str],
) -> dict[str, str]:
    decision_ids = produce_canonical_decision_ids(birth_events)

    if decision_ids.keys() != {asset.upper() for asset in expected_assets}:
        raise RuntimeError(
            "CANONICAL_DECISION_BIRTH_PRODUCER_COVERAGE_MISMATCH"
        )

    return decision_ids
