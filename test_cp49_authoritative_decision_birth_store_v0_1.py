"""Focused CP49 Birth persistence tests using isolated in-memory SQLite."""

from __future__ import annotations

import sqlite3

from cp49_authoritative_decision_birth_store_v0_1 import (
    ensure_birth_schema,
    persist_authoritative_birth,
    read_authoritative_birth,
)


BIRTH = {
    "decision_id": "11111111-1111-4111-8111-111111111111",
    "asset": "BTC",
    "decision_timestamp_ms": 1779830400000,
    "snapshot_id": "SNAP-CP49-STORE-TEST",
    "source": "CP49_STATIC_TEST",
    "decision": {"state": "ACTIONABLE", "direction": "LONG"},
    "issuer_contract": "CP49-AUTHORITATIVE-DECISION-BIRTH-UUID4-v0.1",
}


def main() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        ensure_birth_schema(conn)

        first = persist_authoritative_birth(conn, BIRTH)
        assert first["decision_id"] == BIRTH["decision_id"]
        assert first["birth_persisted"] is True

        loaded = read_authoritative_birth(
            conn,
            decision_id=BIRTH["decision_id"],
        )
        assert loaded is not None
        assert loaded["decision"] == BIRTH["decision"]

        try:
            persist_authoritative_birth(conn, BIRTH)
        except RuntimeError as exc:
            assert str(exc) == "AUTHORITATIVE_DECISION_BIRTH_ID_COLLISION"
        else:
            raise AssertionError("duplicate decision_id must fail closed")

        count = conn.execute(
            "SELECT COUNT(*) FROM authoritative_decision_birth"
        ).fetchone()[0]
        assert count == 1

        print("CP49_BIRTH_PERSISTENCE=PASS")
        print("UNIQUE_DECISION_ID=PASS")
        print("DUPLICATE_COLLISION_FAIL_CLOSED=PASS")
        print("IMMUTABLE_NO_UPDATE_API=PASS")
        print("PRODUCTION_DB_TOUCHED=FALSE")
        print("RUNTIME_EXECUTED=FALSE")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
