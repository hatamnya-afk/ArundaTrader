"""CP49 authoritative Decision Birth source interface.

This module defines the only acceptable runtime entry for canonical decision
identity. A concrete provider must supply an already-existing authoritative
decision_id. This interface never generates, derives, hashes, timestamps,
or persists identity.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol


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

    decision_id = event.get("decision_id")

    if not isinstance(decision_id, str) or not decision_id.strip():
        raise RuntimeError(
            "CANONICAL_DECISION_ID_MISSING_FROM_AUTHORITATIVE_SOURCE"
        )

    bound = dict(event)
    bound["decision_id"] = decision_id.strip()

    return bound
