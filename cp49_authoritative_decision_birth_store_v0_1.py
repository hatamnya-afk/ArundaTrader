"""CP49 authoritative Decision Birth persistence contract v0.1.

Persistence is deliberately explicit and caller-owned. This module never opens
the production database implicitly. The caller supplies a sqlite3 connection.

Transaction contract:
- Call ensure_birth_schema(conn) before beginning a Birth batch; schema setup commits its DDL separately.
- The caller MUST own the data transaction, e.g. with conn: around the complete producer/batch operation. persist_authoritative_birth() does not commit.
- A successful return means the INSERT was accepted in the caller's current transaction, not that it is durable until the caller commits.
- On a decision_id collision, this function rolls back the caller's entire active transaction; callers must not catch the error and continue that batch.

Canonical Birth persistence guarantees:
- decision_id is UNIQUE
- the Birth Event is inserted as one logical record
- persisted decision_id is immutable because there is no update API
- IntegrityError is fail-closed
- no downstream replacement is permitted
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Mapping
from typing import Any


SCHEMA_VERSION = "CP49-AUTHORITATIVE-DECISION-BIRTH-STORE-v0.1"

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS authoritative_decision_birth (
    decision_id TEXT PRIMARY KEY,
    asset TEXT NOT NULL,
    decision_timestamp_ms INTEGER NOT NULL,
    snapshot_id TEXT NOT NULL,
    source TEXT NOT NULL,
    decision_payload TEXT NOT NULL,
    issuer_contract TEXT NOT NULL,
    birth_created_at_ms INTEGER NOT NULL
);
"""


def ensure_birth_schema(conn: sqlite3.Connection) -> None:
    """Install the Birth table on the explicitly supplied SQLite connection."""
    conn.execute(CREATE_SQL)
    conn.commit()


def persist_authoritative_birth(
    conn: sqlite3.Connection,
    birth_event: Mapping[str, Any],
) -> dict[str, Any]:
    """Insert one canonical Birth Event into the caller-owned transaction.

    The caller must commit the transaction (preferably around the complete
    batch, using ``with conn:``) before treating this identity as durable.
    This function deliberately does not commit. A duplicate decision_id is
    never replaced: the entire active connection transaction is rolled back
    and the Birth batch fails closed.
    """
    required = (
        "decision_id",
        "asset",
        "decision_timestamp_ms",
        "snapshot_id",
        "source",
        "decision",
        "issuer_contract",
    )
    missing = [field for field in required if field not in birth_event]
    if missing:
        raise ValueError(
            "AUTHORITATIVE_BIRTH_PERSISTENCE_FIELDS_MISSING:"
            + ",".join(missing)
        )

    decision_id = birth_event["decision_id"]
    if not isinstance(decision_id, str) or not decision_id.strip():
        raise ValueError("AUTHORITATIVE_BIRTH_PERSISTENCE_ID_INVALID")

    timestamp = birth_event["decision_timestamp_ms"]
    if (
        isinstance(timestamp, bool)
        or not isinstance(timestamp, int)
        or timestamp <= 0
    ):
        raise ValueError("AUTHORITATIVE_BIRTH_PERSISTENCE_TIMESTAMP_INVALID")

    decision_payload = json.dumps(
        birth_event["decision"],
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )

    try:
        conn.execute(
            """
            INSERT INTO authoritative_decision_birth (
                decision_id,
                asset,
                decision_timestamp_ms,
                snapshot_id,
                source,
                decision_payload,
                issuer_contract,
                birth_created_at_ms
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decision_id.strip(),
                birth_event["asset"],
                timestamp,
                birth_event["snapshot_id"],
                birth_event["source"],
                decision_payload,
                birth_event["issuer_contract"],
                timestamp,
            ),
        )
        # The caller owns the transaction boundary. Do not commit here:
        # producers may persist multiple Birth Events as one atomic batch.
    except sqlite3.IntegrityError as exc:
        # Fail closed for the whole caller-owned transaction, including any
        # earlier Birth rows inserted in the same batch.
        conn.rollback()
        raise RuntimeError(
            "AUTHORITATIVE_DECISION_BIRTH_ID_COLLISION"
        ) from exc

    return {
        "decision_id": decision_id.strip(),
        "birth_persisted": True,
        "schema_version": SCHEMA_VERSION,
    }


def read_authoritative_birth(
    conn: sqlite3.Connection,
    *,
    decision_id: str,
) -> dict[str, Any] | None:
    if not isinstance(decision_id, str) or not decision_id.strip():
        raise ValueError("AUTHORITATIVE_BIRTH_READ_ID_INVALID")

    row = conn.execute(
        """
        SELECT
            decision_id,
            asset,
            decision_timestamp_ms,
            snapshot_id,
            source,
            decision_payload,
            issuer_contract,
            birth_created_at_ms
        FROM authoritative_decision_birth
        WHERE decision_id = ?
        """,
        (decision_id.strip(),),
    ).fetchone()

    if row is None:
        return None

    return {
        "decision_id": row[0],
        "asset": row[1],
        "decision_timestamp_ms": row[2],
        "snapshot_id": row[3],
        "source": row[4],
        "decision": json.loads(row[5]),
        "issuer_contract": row[6],
        "birth_created_at_ms": row[7],
    }
