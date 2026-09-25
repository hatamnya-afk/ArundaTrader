"""CP49 Authoritative Decision Birth Issuer v0.1.

Management-selected identity semantics:
- UUIDv4 opaque identity
- identity belongs to Authoritative Decision Birth
- uniqueness is enforced by the authoritative Birth persistence boundary
- no business-data derivation
- no downstream replacement

This module does not touch the production DB by itself. The caller must perform
the canonical Birth persistence operation and enforce UNIQUE(decision_id).
Runtime integration remains a separate gate.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any


ISSUER_CONTRACT = "CP49-AUTHORITATIVE-DECISION-BIRTH-UUID4-v0.1"


def issue_canonical_decision_id(
    birth_context: Mapping[str, Any],
) -> str:
    """Issue a new opaque identity for an authoritative Birth transition.

    The semantic decision must already exist in birth_context. This function
    does not persist the Birth Event; persistence must atomically enforce the
    UNIQUE(decision_id) constraint before the Birth becomes canonical.
    """
    if not isinstance(birth_context, Mapping):
        raise ValueError("AUTHORITATIVE_BIRTH_CONTEXT_INVALID")

    if not birth_context.get("decision"):
        raise ValueError("AUTHORITATIVE_BIRTH_SEMANTIC_DECISION_REQUIRED")

    return str(uuid.uuid4())


def build_birth_identity_record(
    birth_context: Mapping[str, Any],
    *,
    decision_id: str,
) -> dict[str, Any]:
    """Bind an issued identity to an already-evaluated Birth context."""
    if not isinstance(decision_id, str) or not decision_id.strip():
        raise ValueError("AUTHORITATIVE_BIRTH_DECISION_ID_INVALID")

    required = (
        "asset",
        "decision_timestamp_ms",
        "snapshot_id",
        "source",
        "decision",
    )
    missing = [field for field in required if field not in birth_context]
    if missing:
        raise ValueError(
            "AUTHORITATIVE_BIRTH_CONTEXT_FIELDS_MISSING:"
            + ",".join(missing)
        )

    return {
        "decision_id": decision_id.strip(),
        "asset": birth_context["asset"],
        "decision_timestamp_ms": birth_context["decision_timestamp_ms"],
        "snapshot_id": birth_context["snapshot_id"],
        "source": birth_context["source"],
        "decision": birth_context["decision"],
        "issuer_contract": ISSUER_CONTRACT,
    }


def assert_issuer_contract() -> None:
    candidate = issue_canonical_decision_id(
        {
            "asset": "TEST",
            "decision_timestamp_ms": 1,
            "snapshot_id": "SNAPSHOT",
            "source": "STATIC_TEST",
            "decision": {"state": "HOLD"},
        }
    )
    parsed = uuid.UUID(candidate)
    if parsed.version != 4:
        raise AssertionError("ISSUER_UUID_VERSION_MISMATCH")
