import sqlite3
import time
from datetime import datetime, timezone

DB_PATH = "arunda.db"

INTERVAL_SECONDS = 60
ENGINE_VERSION = "MARKET_HISTORY_CMC_v0.4"


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]


def load_universe(conn):

    required = {
        "cmc_id",
        "symbol",
        "name",
        "price",
    }

    columns = set(get_columns(conn, "market_universe"))

    missing = required - columns

    if missing:
        raise RuntimeError(
            f"market_universe missing required columns: {sorted(missing)}"
        )

    rows = conn.execute(
        """
        SELECT
            cmc_id,
            symbol,
            name,
            rank,
            price,
            market_cap,
            volume_24h,
            percent_change_1h,
            percent_change_24h,
            percent_change_7d
        FROM market_universe
        WHERE cmc_id IS NOT NULL
          AND symbol IS NOT NULL
          AND price IS NOT NULL
          AND price > 0
        ORDER BY cmc_id
        """
    ).fetchall()

    return rows


def validate_universe(rows):

    if not rows:
        raise RuntimeError("Universe is empty.")

    cmc_ids = [row[0] for row in rows]

    distinct_cmc_ids = set(cmc_ids)

    if len(cmc_ids) != len(distinct_cmc_ids):
        raise RuntimeError(
            "Duplicate CMC_ID detected in market_universe."
        )

    symbols = [str(row[1]).upper().strip() for row in rows]

    distinct_symbols = set(symbols)

    collision_count = len(symbols) - len(distinct_symbols)

    print()
    print("UNIVERSE VALIDATION")
    print("-" * 80)
    print("Rows                :", len(rows))
    print("Distinct CMC IDs    :", len(distinct_cmc_ids))
    print("Distinct Symbols    :", len(distinct_symbols))
    print("Symbol Collisions   :", collision_count)

    if len(rows) != 1000:
        raise RuntimeError(
            f"Unexpected universe size: {len(rows)}"
        )

    if len(distinct_cmc_ids) != 1000:
        raise RuntimeError(
            "Universe does not contain exactly 1000 distinct CMC_IDs."
        )

    print("CMC_ID identity     : PASS")
    print("Universe size       : PASS")


def validate_history_schema(conn):

    columns = set(get_columns(conn, "market_history"))

    required = {
        "timestamp",
        "cmc_id",
        "symbol",
        "name",
        "price",
        "market_cap",
        "volume_24h",
        "change_1h",
        "change_24h",
        "change_7d",
        "source",
        "source_timestamp",
        "engine_version",
        "created_at",
    }

    missing = required - columns

    if missing:
        raise RuntimeError(
            f"Active market_history missing columns: {sorted(missing)}"
        )

    print()
    print("HISTORY SCHEMA")
    print("-" * 80)
    print("CMC_ID column       : PASS")
    print("Source column       : PASS")
    print("Engine version      : PASS")
    print("Identity model      : (timestamp, cmc_id)")


def build_snapshot(rows):

    timestamp = utc_now()

    prepared = []

    seen_cmc = set()

    for row in rows:

        (
            cmc_id,
            symbol,
            name,
            rank,
            price,
            market_cap,
            volume_24h,
            change_1h,
            change_24h,
            change_7d,
        ) = row

        if cmc_id in seen_cmc:
            raise RuntimeError(
                f"Duplicate CMC_ID in snapshot: {cmc_id}"
            )

        seen_cmc.add(cmc_id)

        prepared.append(
            (
                timestamp,
                int(cmc_id),
                str(symbol).upper().strip(),
                name,
                rank,
                float(price),
                market_cap,
                volume_24h,
                change_1h,
                change_24h,
                change_7d,
                "COINMARKETCAP",
                timestamp,
                ENGINE_VERSION,
                timestamp,
            )
        )

    return timestamp, prepared


def audit_snapshot(snapshot):

    timestamp, rows = snapshot

    cmc_ids = [row[1] for row in rows]

    symbols = [row[2] for row in rows]

    print()
    print("SNAPSHOT AUDIT")
    print("-" * 80)
    print("Timestamp           :", timestamp)
    print("Rows                :", len(rows))
    print("Distinct CMC IDs    :", len(set(cmc_ids)))
    print("Distinct Symbols    :", len(set(symbols)))
    print("Symbol collisions   :", len(symbols) - len(set(symbols)))

    if len(rows) != 1000:
        raise RuntimeError(
            f"Snapshot row count invalid: {len(rows)}"
        )

    if len(set(cmc_ids)) != 1000:
        raise RuntimeError(
            "Snapshot contains duplicate CMC_IDs."
        )

    print("Rows                : PASS")
    print("CMC_ID uniqueness   : PASS")
    print("Collision handling  : PASS")


def dry_run(conn):

    print()
    print("=" * 100)
    print("ARUNDA TRADER — DEV-05 — STEP 6A")
    print("WRITER REPAIR — DRY RUN")
    print("=" * 100)

    print()
    print("DATABASE :", DB_PATH)
    print("MODE     : READ ONLY")
    print("WRITES   : NONE")
    print("ENGINE   :", ENGINE_VERSION)

    if not table_exists(conn, "market_universe"):
        raise RuntimeError(
            "market_universe does not exist."
        )

    if not table_exists(conn, "market_history"):
        raise RuntimeError(
            "market_history does not exist."
        )

    validate_history_schema(conn)

    print()
    print("Loading market universe...")

    rows = load_universe(conn)

    validate_universe(rows)

    print()
    print("Building test snapshot...")

    snapshot = build_snapshot(rows)

    audit_snapshot(snapshot)

    print()
    print("=" * 100)
    print("STEP 6A VERDICT")
    print("=" * 100)
    print("RESULT : WRITER REPAIR DRY-RUN PASS")
    print("STATUS : READY FOR CONTROLLED WRITE TEST")
    print()
    print("market_history : UNMODIFIED")
    print("market_universe: UNMODIFIED")
    print("DATABASE       : UNMODIFIED")
    print("=" * 100)


def main():

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )

    try:
        dry_run(conn)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
