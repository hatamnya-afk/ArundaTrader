"""Focused CP49 issuer contract tests. No runtime, DB, or exchange access."""

from __future__ import annotations

import uuid

from cp49_authoritative_decision_birth_issuer_v0_1 import (
    ISSUER_CONTRACT,
    assert_issuer_contract,
    build_birth_identity_record,
    issue_canonical_decision_id,
)


CONTEXT = {
    "asset": "BTC",
    "decision_timestamp_ms": 1779830400000,
    "snapshot_id": "SNAP-CP49-TEST",
    "source": "CP49_STATIC_TEST",
    "decision": {"state": "ACTIONABLE", "direction": "LONG"},
}


def main() -> None:
    first = issue_canonical_decision_id(CONTEXT)
    second = issue_canonical_decision_id(CONTEXT)

    assert first != second
    assert uuid.UUID(first).version == 4
    assert uuid.UUID(second).version == 4

    record = build_birth_identity_record(CONTEXT, decision_id=first)
    assert record["decision_id"] == first
    assert record["issuer_contract"] == ISSUER_CONTRACT
    assert record["decision"] == CONTEXT["decision"]

    try:
        issue_canonical_decision_id({**CONTEXT, "decision": None})
    except ValueError as exc:
        assert str(exc) == "AUTHORITATIVE_BIRTH_SEMANTIC_DECISION_REQUIRED"
    else:
        raise AssertionError("missing semantic decision must block")

    assert_issuer_contract()

    print("CP49_ISSUER_CONTRACT=PASS")
    print("ISSUER=UUIDv4")
    print("SEMANTIC_DECISION_REQUIRED=PASS")
    print("DOWNSTREAM_SUBSTITUTION=FORBIDDEN")
    print("PRODUCTION_DB_TOUCHED=FALSE")
    print("RUNTIME_EXECUTED=FALSE")


if __name__ == "__main__":
    main()
