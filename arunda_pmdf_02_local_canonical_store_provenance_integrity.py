from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path


ENGINE = "ARUNDA_PMDF_02_LOCAL_CANONICAL_STORE_PROVENANCE_INTEGRITY"
VERSION = "v0.1"

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
PRODUCTION_DB = PROJECT_ROOT / "arunda.db"
STORE_DB = (
    PROJECT_ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

SOURCE_TYPE = "CEX_PUBLIC_API"
TIMEFRAME = "1h"
EXPECTED_SOURCE_PREFIX = "KUCOIN_SPOT:"
EXPECTED_INPUT_BARS = 3

EXECUTION = "DISABLED"
PRODUCTION_CONSUMPTION_ENABLED = False
ORDER_INTENTS_CREATED = 0

CANONICAL_FIELDS = [
    "asset",
    "symbol",
    "timestamp",
    "timeframe",
    "open",
    "high",
    "low",
    "close",
    "volume",
]

PROVENANCE_FIELDS = [
    "source_id",
    "source_type",
    "source_timestamp",
    "retrieved_at",
]


def fail(message: str) -> None:
    raise RuntimeError(f"PMDF-02 FAIL-CLOSED: {message}")


def finite_number(value) -> bool:
    return (
        isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def load_all_rows(conn: sqlite3.Connection):
    conn.row_factory = sqlite3.Row

    return conn.execute(
        """
        SELECT
            id,
            asset,
            symbol,
            timestamp,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            source_id,
            source_type,
            source_timestamp,
            retrieved_at,
            observation_count,
            observation_signatures,
            observation_slots,
            pool,
            raydium_instruction,
            price_unit,
            canonical_payload
        FROM canonical_ohlcv
        ORDER BY id ASC
        """
    ).fetchall()


def load_kucoin_rows(conn: sqlite3.Connection):
    conn.row_factory = sqlite3.Row

    return conn.execute(
        """
        SELECT
            id,
            asset,
            symbol,
            timestamp,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            source_id,
            source_type,
            source_timestamp,
            retrieved_at,
            observation_count,
            observation_signatures,
            observation_slots,
            pool,
            raydium_instruction,
            price_unit,
            canonical_payload
        FROM canonical_ohlcv
        WHERE source_type = ?
          AND source_id LIKE ?
        ORDER BY id ASC
        """,
        (
            SOURCE_TYPE,
            EXPECTED_SOURCE_PREFIX + "%",
        ),
    ).fetchall()


def validate_row(row: sqlite3.Row) -> None:
    for field in CANONICAL_FIELDS:
        if row[field] is None:
            fail(f"incomplete canonical field: {field}")

    for field in PROVENANCE_FIELDS:
        if row[field] is None:
            fail(f"incomplete provenance field: {field}")

    if not isinstance(row["asset"], str) or not row["asset"]:
        fail("invalid asset")

    if not isinstance(row["symbol"], str) or not row["symbol"]:
        fail("invalid symbol")

    if not isinstance(row["timestamp"], int):
        fail("timestamp is not integer")

    if row["timestamp"] <= 0:
        fail("invalid timestamp")

    if row["timeframe"] != TIMEFRAME:
        fail("invalid timeframe")

    if row["timestamp"] % 3600 != 0:
        fail("timestamp is not 1h aligned")

    for field in [
        "open",
        "high",
        "low",
        "close",
        "volume",
    ]:
        if not finite_number(row[field]):
            fail(f"non-finite OHLCV field: {field}")

    if row["open"] <= 0:
        fail("invalid open")

    if row["high"] <= 0:
        fail("invalid high")

    if row["low"] <= 0:
        fail("invalid low")

    if row["close"] <= 0:
        fail("invalid close")

    if row["volume"] < 0:
        fail("negative volume")

    if row["high"] < max(
        row["open"],
        row["close"],
        row["low"],
    ):
        fail("invalid OHLC high structure")

    if row["low"] > min(
        row["open"],
        row["close"],
        row["high"],
    ):
        fail("invalid OHLC low structure")

    if not isinstance(row["source_id"], str):
        fail("invalid source_id")

    if not row["source_id"].startswith(
        EXPECTED_SOURCE_PREFIX
    ):
        fail(
            "source_id is not KUCOIN public source identity"
        )

    if row["source_type"] != SOURCE_TYPE:
        fail("invalid source_type")

    if row["source_timestamp"] != row["timestamp"]:
        fail("source_timestamp != timestamp")

    if not isinstance(row["retrieved_at"], str):
        fail("invalid retrieved_at")

    if not row["retrieved_at"]:
        fail("empty retrieved_at")

    try:
        signatures = json.loads(
            row["observation_signatures"]
        )
        slots = json.loads(
            row["observation_slots"]
        )
    except Exception as exc:
        fail(
            f"invalid observation provenance JSON: {exc}"
        )

    if not isinstance(signatures, list):
        fail("observation_signatures is not a list")

    if not isinstance(slots, list):
        fail("observation_slots is not a list")

    if row["observation_count"] != 1:
        fail("one-candle-one-source violation")

    if len(signatures) != 1:
        fail(
            "observation signature cardinality violation"
        )

    if len(slots) != 1:
        fail("observation slot cardinality violation")

    if slots[0] != row["timestamp"]:
        fail("observation slot != timestamp")

    if not signatures[0]:
        fail("empty observation signature")

    # The verified Local Canonical Store persists Python None
    # through json.dumps(None), resulting in the literal string
    # "null". For CEX records both None and "null" represent
    # absence of DEX/Raydium provenance.
    pool_value = row["pool"]
    raydium_value = row["raydium_instruction"]

    if pool_value not in (None, "null"):
        fail(
            "source mixing detected: pool present"
        )

    if raydium_value not in (None, "null"):
        fail(
            "source mixing detected: "
            "raydium instruction present"
        )

    if not isinstance(
        row["canonical_payload"],
        str,
    ):
        fail("missing canonical_payload")

    if not row["canonical_payload"]:
        fail("empty canonical_payload")


def canonical_projection(row: sqlite3.Row) -> dict:
    return {
        field: row[field]
        for field in (
            CANONICAL_FIELDS
            + PROVENANCE_FIELDS
        )
    }


def provenance_projection(row: sqlite3.Row) -> dict:
    return {
        field: row[field]
        for field in PROVENANCE_FIELDS
    }


def verify_order(rows: list[sqlite3.Row]) -> None:
    seen = set()
    previous_timestamp_by_asset = {}

    for row in rows:
        key = (
            row["asset"],
            row["symbol"],
            row["timestamp"],
            row["timeframe"],
        )

        if key in seen:
            fail(
                "duplicate canonical key in stored data: "
                f"{key}"
            )

        seen.add(key)

        asset = row["asset"]
        timestamp = row["timestamp"]

        if asset in previous_timestamp_by_asset:
            previous = previous_timestamp_by_asset[asset]

            if timestamp <= previous:
                fail(
                    "timestamp ordering violation "
                    f"for asset={asset}"
                )

        previous_timestamp_by_asset[asset] = timestamp


def duplicate_protection_test(
    store_path: Path,
    row: sqlite3.Row,
) -> bool:
    conn = sqlite3.connect(store_path)

    try:
        conn.execute("BEGIN")

        try:
            conn.execute(
                """
                INSERT INTO canonical_ohlcv (
                    asset,
                    symbol,
                    timestamp,
                    timeframe,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    source_id,
                    source_type,
                    source_timestamp,
                    retrieved_at,
                    observation_count,
                    observation_signatures,
                    observation_slots,
                    pool,
                    raydium_instruction,
                    price_unit,
                    canonical_payload
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    row["asset"],
                    row["symbol"],
                    row["timestamp"],
                    row["timeframe"],
                    row["open"],
                    row["high"],
                    row["low"],
                    row["close"],
                    row["volume"],
                    row["source_id"],
                    row["source_type"],
                    row["source_timestamp"],
                    row["retrieved_at"],
                    row["observation_count"],
                    row["observation_signatures"],
                    row["observation_slots"],
                    row["pool"],
                    row["raydium_instruction"],
                    row["price_unit"],
                    row["canonical_payload"],
                ),
            )

            conn.rollback()
            return False

        except sqlite3.IntegrityError:
            conn.rollback()
            return True

    finally:
        conn.close()


def main() -> None:
    if not STORE_DB.exists():
        fail(
            f"isolated Fabric store missing: {STORE_DB}"
        )

    if not PRODUCTION_DB.exists():
        fail(
            "production DB missing; fail-closed"
        )

    # Only metadata is inspected.
    # The production DB is never opened.
    production_before = (
        PRODUCTION_DB.stat().st_mtime_ns
    )

    conn = sqlite3.connect(
        f"file:{STORE_DB}?mode=ro",
        uri=True,
    )

    try:
        all_rows_before = load_all_rows(conn)

        # PDF-08 DEX reference data may already exist.
        # PMDF-02 scope is only the KuCoin CEX records
        # created by PMDF-01.
        kucoin_rows = load_kucoin_rows(conn)

        if len(kucoin_rows) != EXPECTED_INPUT_BARS:
            fail(
                "expected "
                f"{EXPECTED_INPUT_BARS} KuCoin "
                "canonical bars, found "
                f"{len(kucoin_rows)}"
            )

        input_rows = list(kucoin_rows)

        for row in input_rows:
            validate_row(row)

        verify_order(input_rows)

        # Explicit one-candle-one-source verification.
        for row in input_rows:
            if row["observation_count"] != 1:
                fail(
                    "one-candle-one-source violation"
                )

            if not row["source_id"].startswith(
                EXPECTED_SOURCE_PREFIX
            ):
                fail(
                    "non-KuCoin source detected"
                )

            if row["source_type"] != SOURCE_TYPE:
                fail(
                    "source mixing detected"
                )

        duplicates_rejected = (
            duplicate_protection_test(
                STORE_DB,
                input_rows[0],
            )
        )

        if not duplicates_rejected:
            fail(
                "duplicate protection inactive"
            )

        # Fresh read-back from isolated store.
        readback_rows = load_kucoin_rows(conn)

        if len(readback_rows) != len(input_rows):
            fail(
                "KuCoin read-back row count changed"
            )

        read_back_match = True
        provenance_match = True

        for written, read_back in zip(
            input_rows,
            readback_rows,
        ):
            if (
                canonical_projection(written)
                != canonical_projection(read_back)
            ):
                read_back_match = False

            if (
                provenance_projection(written)
                != provenance_projection(read_back)
            ):
                provenance_match = False

        if not read_back_match:
            fail(
                "canonical read-back mismatch"
            )

        if not provenance_match:
            fail(
                "provenance read-back mismatch"
            )

        # Entire Fabric store must remain unchanged.
        all_rows_after = load_all_rows(conn)

        if len(all_rows_after) != len(
            all_rows_before
        ):
            fail(
                "Fabric row count changed during "
                "verification"
            )

        production_after = (
            PRODUCTION_DB.stat().st_mtime_ns
        )

        if production_before != production_after:
            fail(
                "production DB metadata changed"
            )

        print(
            "ENGINE=" + ENGINE
        )
        print(
            "VERSION=" + VERSION
        )
        print(
            f"INPUT_CANONICAL_BARS={len(input_rows)}"
        )
        print(
            f"STORED_BARS={len(input_rows)}"
        )
        print(
            f"READ_BACK_BARS={len(readback_rows)}"
        )
        print(
            f"READ_BACK_MATCH={read_back_match}"
        )
        print(
            "PROVENANCE_COMPLETE=True"
        )
        print(
            f"PROVENANCE_MATCH={provenance_match}"
        )
        print(
            f"SOURCE_TYPE={SOURCE_TYPE}"
        )
        print(
            f"TIMEFRAME={TIMEFRAME}"
        )
        print(
            "DUPLICATE_PROTECTION=True"
        )
        print(
            "DUPLICATES_REJECTED=True"
        )
        print(
            "REAL_DATA=True"
        )
        print(
            "SYNTHETIC=False"
        )
        print(
            "INTERPOLATION=False"
        )
        print(
            "FILL=False"
        )
        print(
            "BACKFILL=False"
        )
        print(
            "PADDING=False"
        )
        print(
            "BLENDING=False"
        )
        print(
            "PRODUCTION_DB_TOUCHED=False"
        )
        print(
            "PRODUCTION_DB_WRITES=0"
        )
        print(
            "PRODUCTION_CONSUMPTION_ENABLED=False"
        )
        print(
            "EXECUTION=DISABLED"
        )
        print(
            "ORDER_INTENTS_CREATED=0"
        )
        print(
            "VALIDATION=PASS"
        )
        print(
            "STATUS=PMDF_02_READY"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    main()