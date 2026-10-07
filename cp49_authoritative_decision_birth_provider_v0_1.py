"""CP49 authoritative Decision Birth provider boundary.

A concrete provider must return an already-existing authoritative Decision
Birth event. This boundary validates that event through the canonical birth
source contract and exposes its identity unchanged.

It never generates, derives, hashes, timestamps, persists, or mutates identity.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from cp49_canonical_decision_birth_source_v0_1 import (
    require_canonical_decision_birth,
)


class CanonicalDecisionBirthProvider(Protocol):
    """Authoritative external source of an already-existing decision birth."""

    def get_decision_birth(
        self,
        *,
        asset: str,
        snapshot_id: str,
        decision_timestamp_ms: int,
    ) -> Mapping[str, Any]:
        ...


def read_authoritative_birth(
    provider: CanonicalDecisionBirthProvider,
    *,
    asset: str,
    snapshot_id: str,
    decision_timestamp_ms: int,
) -> dict[str, Any]:
    if provider is None or not callable(
        getattr(provider, "get_decision_birth", None)
    ):
        raise RuntimeError(
            "CANONICAL_DECISION_BIRTH_PROVIDER_MISSING"
        )

    event = provider.get_decision_birth(
        asset=asset,
        snapshot_id=snapshot_id,
        decision_timestamp_ms=decision_timestamp_ms,
    )

    if not isinstance(event, Mapping):
        raise RuntimeError(
            "CANONICAL_DECISION_BIRTH_PROVIDER_INVALID"
        )

    try:
        return require_canonical_decision_birth(event)
    except ValueError as exc:
        raise RuntimeError(
            f"CANONICAL_DECISION_BIRTH_EVENT_INVALID:{exc}"
        ) from exc


def require_authoritative_decision_id(
    provider: CanonicalDecisionBirthProvider,
    *,
    asset: str,
    snapshot_id: str,
    decision_timestamp_ms: int,
) -> str:
    event = read_authoritative_birth(
        provider,
        asset=asset,
        snapshot_id=snapshot_id,
        decision_timestamp_ms=decision_timestamp_ms,
    )
    return event["decision_id"]
