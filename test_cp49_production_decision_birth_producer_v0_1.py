"""Focused CP49 production Birth producer test using isolated in-memory SQLite."""

from __future__ import annotations

import sqlite3

from cp49_authoritative_decision_birth_store_v0_1 import (
    ensure_birth_schema,
    read_authoritative_birth,
)
from cp49_production_decision_birth_producer_v0_1 import (
    require_production_decision_birth,
)


BIRTH = {
    "BTC": {
        "decision_id": "11111111-1111-4111-8111-111111111111",
        "asset": "BTC",
        "decision_timestamp_ms": 1779830400000,
        "snapshot_id": "SNAP-CP49-PRODUCER-TEST",
        "source": "CP49_STATIC_TEST",
        "decision": {"state": "ACTIONABLE", "direction": "LONG"},
        "issuer_contract": "CP49-AUTHORITATIVE-DECISION-BIRTH-UUID4-v0.1",
    }
}


def main() -> None:
    conn = sqlite3.connect(":memory:")
    try:
        ensure_birth_schema(conn)

        result = require_production_decision_birth(
            BIRTH,
            expected_assets={"BTC"},
            conn=conn,
        )

        assert result == {"BTC": BIRTH["BTC"]["decision_id"]}

        loaded = read_authoritative_birth(
            conn,
            decision_id=BIRTH["BTC"]["decision_id"],
        )
        assert loaded is not None
        assert loaded["decision_id"] == BIRTH["BTC"]["decision_id"]
        assert loaded["asset"] == "BTC"

        count = conn.execute(
            "SELECT COUNT(*) FROM authoritative_decision_birth"
        ).fetchone()[0]
        assert count == 1

        print("CP49_PRODUCTION_BIRTH_PERSISTENCE=PASS")
        print("COMMITTED_ID_PROPAGATED=PASS")
        print("BIRTH_ROW_COUNT=1")
        print("PRODUCTION_DB_TOUCHED=FALSE")
        print("RUNTIME_EXECUTED=FALSE")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
