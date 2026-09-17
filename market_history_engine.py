import sqlite3
import time
from datetime import datetime, timezone


# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH = "arunda.db"

INTERVAL_SECONDS = 60
BATCH_SIZE = 500

SOURCE_NAME = "COINMARKETCAP"
ENGINE_VERSION = "MARKET_HISTORY_CMC_v0.4"

EXPECTED_UNIVERSE_ROWS = 1000
EXPECTED_DISTINCT_CMC_IDS = 1000
EXPECTED_DISTINCT_SYMBOLS = 987
EXPECTED_SYMBOL_COLLISIONS = 13


# =============================================================================
# TIME
# =============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    return {
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    }


# =============================================================================
# HISTORY SCHEMA VALIDATION
# =============================================================================

def validate_history_schema(conn):

    if not table_exists(conn, "market_history"):
        raise RuntimeError(
            "market_history table does not exist."
        )

    columns = get_columns(
        conn,
        "market_history"
    )

    required = {
        "timestamp",
        "cmc_id",
        "symbol",
        "name",
        "rank",
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
            "market_history schema missing columns: "
            + ", ".join(sorted(missing))
        )

    print("History Schema     : VALID")
    print("CMC_ID             : PRESENT")
    print("Source             : PRESENT")
    print("Engine Version     : PRESENT")
    print("Source Timestamp   : PRESENT")
    print("Created At         : PRESENT")


# =============================================================================
# MARKET UNIVERSE SCHEMA VALIDATION
# =============================================================================

def validate_universe_schema(conn):

    if not table_exists(conn, "market_universe"):
        raise RuntimeError(
            "market_universe table does not exist."
        )

    columns = get_columns(
        conn,
        "market_universe"
    )

    # -------------------------------------------------------------------------
    # IMPORTANT:
    #
    # These are the ACTUAL columns in the production database.
    #
    # rank                 -> cmc_rank
    # change_1h            -> percent_change_1h
    # change_24h           -> percent_change_24h
    # change_7d            -> percent_change_7d
    # -------------------------------------------------------------------------

    required = {
        "cmc_id",
        "symbol",
        "name",
        "cmc_rank",
        "price",
        "market_cap",
        "volume_24h",
        "percent_change_1h",
        "percent_change_24h",
        "percent_change_7d",
    }

    missing = required - columns

    if missing:
        raise RuntimeError(
            "market_universe schema missing columns: "
            + ", ".join(sorted(missing))
        )

    print()
    print("Universe Schema    : VALID")
    print("CMC_ID             : PRESENT")
    print("Symbol             : PRESENT")
    print("Name               : PRESENT")
    print("CMC Rank           : PRESENT")
    print("Price              : PRESENT")
    print("Market Cap         : PRESENT")
    print("Volume 24h         : PRESENT")
    print("Change 1h          : PRESENT")
    print("Change 24h         : PRESENT")
    print("Change 7d          : PRESENT")


# =============================================================================
# UNIVERSE LOADER
# =============================================================================

def load_universe(conn):

    rows = conn.execute(
        """
        SELECT
            cmc_id,
            symbol,
            name,
            cmc_rank,
            price,
            market_cap,
            volume_24h,
            percent_change_1h,
            percent_change_24h,
            percent_change_7d
        FROM market_universe
        WHERE cmc_id IS NOT NULL
          AND symbol IS NOT NULL
          AND name IS NOT NULL
          AND price IS NOT NULL
          AND price > 0
        """
    ).fetchall()

    if not rows:
        raise RuntimeError(
            "market_universe returned zero valid rows."
        )

    identity_map = {}

    cmc_ids = set()
    symbols = set()

    for row in rows:

        (
            cmc_id,
            symbol,
            name,
            cmc_rank,
            price,
            market_cap,
            volume_24h,
            percent_change_1h,
            percent_change_24h,
            percent_change_7d,
        ) = row

        # ---------------------------------------------------------------------
        # Identity validation
        # ---------------------------------------------------------------------

        try:
            cmc_id = int(cmc_id)
        except (TypeError, ValueError):
            raise RuntimeError(
                f"Invalid CMC_ID: {cmc_id}"
            )

        symbol = str(
            symbol
        ).upper().strip()

        name = str(
            name
        ).strip()

        if not symbol:
            raise RuntimeError(
                f"Empty symbol for CMC_ID {cmc_id}"
            )

        if not name:
            raise RuntimeError(
                f"Empty name for CMC_ID {cmc_id}"
            )

        if price is None:
            raise RuntimeError(
                f"Missing price for CMC_ID {cmc_id}"
            )

        try:
            price = float(price)
        except (TypeError, ValueError):
            raise RuntimeError(
                f"Invalid price for CMC_ID {cmc_id}: {price}"
            )

        if price <= 0:
            raise RuntimeError(
                f"Non-positive price for CMC_ID {cmc_id}: {price}"
            )

        # ---------------------------------------------------------------------
        # Symbol/name identity
        # ---------------------------------------------------------------------

        key = (
            symbol,
            name,
        )

        if key in identity_map:

            previous = identity_map[key]

            if previous["cmc_id"] != cmc_id:

                raise RuntimeError(
                    "Ambiguous universe identity: "
                    f"{key} -> "
                    f"{previous['cmc_id']} / {cmc_id}"
                )

        identity_map[key] = {
            "cmc_id": cmc_id,
            "symbol": symbol,
            "name": name,
            "rank": cmc_rank,
            "price": price,
            "market_cap": market_cap,
            "volume_24h": volume_24h,
            "change_1h": percent_change_1h,
            "change_24h": percent_change_24h,
            "change_7d": percent_change_7d,
        }

        cmc_ids.add(
            cmc_id
        )

        symbols.add(
            symbol
        )

    # -------------------------------------------------------------------------
    # Universe cardinality
    # -------------------------------------------------------------------------

    if len(rows) != EXPECTED_UNIVERSE_ROWS:

        raise RuntimeError(
            "Universe size invalid: "
            f"expected {EXPECTED_UNIVERSE_ROWS}, "
            f"got {len(rows)}"
        )

    if len(cmc_ids) != EXPECTED_DISTINCT_CMC_IDS:

        raise RuntimeError(
            "Universe CMC_ID identity invalid: "
            f"expected {EXPECTED_DISTINCT_CMC_IDS}, "
            f"got {len(cmc_ids)}"
        )

    collision_count = (
        len(rows)
        - len(symbols)
    )

    print()
    print("UNIVERSE")
    print("-" * 100)

    print(
        "Universe rows     :",
        len(rows)
    )

    print(
        "Distinct CMC IDs  :",
        len(cmc_ids)
    )

    print(
        "Distinct Symbols   :",
        len(symbols)
    )

    print(
        "Symbol Collisions  :",
        collision_count
    )

    if collision_count != EXPECTED_SYMBOL_COLLISIONS:

        raise RuntimeError(
            "Unexpected symbol collision count: "
            f"expected {EXPECTED_SYMBOL_COLLISIONS}, "
            f"got {collision_count}"
        )

    return identity_map


# =============================================================================
# SNAPSHOT BUILD
# =============================================================================

def build_snapshot(
    identity_map,
    timestamp
):

    snapshot = []

    for record in identity_map.values():

        cmc_id = record["cmc_id"]
        symbol = record["symbol"]
        name = record["name"]
        price = record["price"]

        if cmc_id is None:
            raise RuntimeError(
                f"Missing CMC_ID for {symbol} / {name}"
            )

        if not symbol:
            raise RuntimeError(
                f"Missing symbol for CMC_ID {cmc_id}"
            )

        if not name:
            raise RuntimeError(
                f"Missing name for CMC_ID {cmc_id}"
            )

        if price is None:
            raise RuntimeError(
                f"Missing price for CMC_ID {cmc_id}"
            )

        try:
            price = float(price)
        except (TypeError, ValueError):

            raise RuntimeError(
                f"Invalid price for CMC_ID "
                f"{cmc_id}: {price}"
            )

        if price <= 0:

            raise RuntimeError(
                f"Non-positive price for CMC_ID "
                f"{cmc_id}: {price}"
            )

        snapshot.append(
            {
                "timestamp": timestamp,

                "cmc_id": cmc_id,

                "symbol": symbol,

                "name": name,

                "rank": record["rank"],

                "price": price,

                "market_cap": record["market_cap"],

                "volume_24h": record["volume_24h"],

                "change_1h": record["change_1h"],

                "change_24h": record["change_24h"],

                "change_7d": record["change_7d"],

                "source": SOURCE_NAME,

                "source_timestamp": timestamp,

                "engine_version": ENGINE_VERSION,

                "created_at": timestamp,
            }
        )

    return snapshot


# =============================================================================
# SNAPSHOT VALIDATION
# =============================================================================

def validate_snapshot(snapshot):

    if len(snapshot) != EXPECTED_UNIVERSE_ROWS:

        raise RuntimeError(
            "Snapshot row count invalid: "
            f"expected {EXPECTED_UNIVERSE_ROWS}, "
            f"got {len(snapshot)}"
        )

    cmc_ids = [
        row["cmc_id"]
        for row in snapshot
    ]

    symbols = [
        row["symbol"]
        for row in snapshot
    ]

    # -------------------------------------------------------------------------
    # CMC identity
    # -------------------------------------------------------------------------

    if len(set(cmc_ids)) != EXPECTED_DISTINCT_CMC_IDS:

        raise RuntimeError(
            "Snapshot contains duplicate CMC_ID values."
        )

    # -------------------------------------------------------------------------
    # Symbol collision preservation
    # -------------------------------------------------------------------------

    distinct_symbols = len(
        set(symbols)
    )

    if distinct_symbols != EXPECTED_DISTINCT_SYMBOLS:

        raise RuntimeError(
            "Snapshot symbol count invalid: "
            f"expected {EXPECTED_DISTINCT_SYMBOLS}, "
            f"got {distinct_symbols}"
        )

    collision_rows = (
        len(symbols)
        - distinct_symbols
    )

    if collision_rows != EXPECTED_SYMBOL_COLLISIONS:

        raise RuntimeError(
            "Snapshot collision count invalid: "
            f"expected {EXPECTED_SYMBOL_COLLISIONS}, "
            f"got {collision_rows}"
        )

    # -------------------------------------------------------------------------
    # Row-level validation
    # -------------------------------------------------------------------------

    for row in snapshot:

        if row["source"] != SOURCE_NAME:

            raise RuntimeError(
                f"Invalid source for CMC_ID "
                f"{row['cmc_id']}"
            )

        if row["engine_version"] != ENGINE_VERSION:

            raise RuntimeError(
                f"Invalid engine version for CMC_ID "
                f"{row['cmc_id']}"
            )

        if row["timestamp"] is None:

            raise RuntimeError(
                "Snapshot timestamp is NULL."
            )

        if row["cmc_id"] is None:

            raise RuntimeError(
                "Snapshot CMC_ID is NULL."
            )

    return {
        "rows": len(snapshot),
        "cmc_ids": len(set(cmc_ids)),
        "symbols": distinct_symbols,
        "collision_rows": collision_rows,
    }


# =============================================================================
# EXISTING SNAPSHOT CHECK
# =============================================================================

def snapshot_exists(
    conn,
    timestamp
):

    row = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp = ?
        """,
        (timestamp,),
    ).fetchone()

    return row[0] > 0


# =============================================================================
# BATCH WRITE
# =============================================================================

def write_snapshot(
    conn,
    snapshot
):

    if not snapshot:

        raise RuntimeError(
            "Cannot write empty snapshot."
        )

    timestamp = snapshot[0]["timestamp"]

    # -------------------------------------------------------------------------
    # Existing timestamp protection
    # -------------------------------------------------------------------------

    if snapshot_exists(
        conn,
        timestamp
    ):

        raise RuntimeError(
            f"Snapshot timestamp already exists: "
            f"{timestamp}"
        )

    insert_sql = """
        INSERT INTO market_history (
            timestamp,
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
            source,
            source_timestamp,
            engine_version,
            created_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?
        )
    """

    values = []

    for row in snapshot:

        values.append(
            (
                row["timestamp"],
                row["cmc_id"],
                row["symbol"],
                row["name"],
                row["rank"],
                row["price"],
                row["market_cap"],
                row["volume_24h"],
                row["change_1h"],
                row["change_24h"],
                row["change_7d"],
                row["source"],
                row["source_timestamp"],
                row["engine_version"],
                row["created_at"],
            )
        )

    # -------------------------------------------------------------------------
    # Atomic transaction
    # -------------------------------------------------------------------------

    conn.execute(
        "BEGIN"
    )

    try:

        inserted_total = 0

        # ---------------------------------------------------------------------
        # Real batch writing
        # ---------------------------------------------------------------------

        for start in range(
            0,
            len(values),
            BATCH_SIZE
        ):

            batch = values[
                start:start + BATCH_SIZE
            ]

            conn.executemany(
                insert_sql,
                batch
            )

            inserted_total += len(
                batch
            )

        # ---------------------------------------------------------------------
        # Snapshot verification
        # ---------------------------------------------------------------------

        inserted = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_history
            WHERE timestamp = ?
            """,
            (timestamp,),
        ).fetchone()[0]

        distinct_cmc = conn.execute(
            """
            SELECT COUNT(DISTINCT cmc_id)
            FROM market_history
            WHERE timestamp = ?
            """,
            (timestamp,),
        ).fetchone()[0]

        duplicate_ids = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT cmc_id
                FROM market_history
                WHERE timestamp = ?
                GROUP BY cmc_id
                HAVING COUNT(*) > 1
            )
            """,
            (timestamp,),
        ).fetchone()[0]

        source_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_history
            WHERE timestamp = ?
              AND source = ?
            """,
            (
                timestamp,
                SOURCE_NAME,
            ),
        ).fetchone()[0]

        engine_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_history
            WHERE timestamp = ?
              AND engine_version = ?
            """,
            (
                timestamp,
                ENGINE_VERSION,
            ),
        ).fetchone()[0]

        # ---------------------------------------------------------------------
        # Verification
        # ---------------------------------------------------------------------

        if inserted_total != EXPECTED_UNIVERSE_ROWS:

            raise RuntimeError(
                "Batch insertion count failed: "
                f"expected {EXPECTED_UNIVERSE_ROWS}, "
                f"got {inserted_total}"
            )

        if inserted != EXPECTED_UNIVERSE_ROWS:

            raise RuntimeError(
                "Write verification failed: "
                f"expected {EXPECTED_UNIVERSE_ROWS}, "
                f"got {inserted}"
            )

        if distinct_cmc != EXPECTED_DISTINCT_CMC_IDS:

            raise RuntimeError(
                "CMC_ID verification failed: "
                f"expected {EXPECTED_DISTINCT_CMC_IDS}, "
                f"got {distinct_cmc}"
            )

        if duplicate_ids != 0:

            raise RuntimeError(
                "Duplicate CMC_ID identities detected: "
                f"{duplicate_ids}"
            )

        if source_count != EXPECTED_UNIVERSE_ROWS:

            raise RuntimeError(
                "Source verification failed: "
                f"expected {EXPECTED_UNIVERSE_ROWS}, "
                f"got {source_count}"
            )

        if engine_count != EXPECTED_UNIVERSE_ROWS:

            raise RuntimeError(
                "Engine verification failed: "
                f"expected {EXPECTED_UNIVERSE_ROWS}, "
                f"got {engine_count}"
            )

        # ---------------------------------------------------------------------
        # Commit ONLY after every verification succeeds.
        # ---------------------------------------------------------------------

        conn.commit()

        return {
            "inserted": inserted,
            "distinct_cmc_ids": distinct_cmc,
            "duplicate_ids": duplicate_ids,
            "source_rows": source_count,
            "engine_rows": engine_count,
            "batches": (
                (
                    len(values)
                    + BATCH_SIZE
                    - 1
                )
                // BATCH_SIZE
            ),
        }

    except Exception:

        conn.rollback()

        raise


# =============================================================================
# HISTORY STATISTICS
# =============================================================================

def history_statistics(conn):

    total = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        """
    ).fetchone()[0]

    snapshots = conn.execute(
        """
        SELECT COUNT(DISTINCT timestamp)
        FROM market_history
        """
    ).fetchone()[0]

    assets = conn.execute(
        """
        SELECT COUNT(DISTINCT cmc_id)
        FROM market_history
        """
    ).fetchone()[0]

    return (
        total,
        snapshots,
        assets,
    )


# =============================================================================
# STATUS
# =============================================================================

def print_statistics(conn):

    (
        total,
        snapshots,
        assets,
    ) = history_statistics(
        conn
    )

    print()
    print("=" * 100)
    print("HISTORICAL ACCUMULATION STATUS")
    print("=" * 100)

    print(
        "Total History Rows :",
        total
    )

    print(
        "Snapshots          :",
        snapshots
    )

    print(
        "Distinct CMC IDs   :",
        assets
    )

    print("=" * 100)


# =============================================================================
# SINGLE PRODUCTION CYCLE
# =============================================================================

def collect_snapshot(conn):

    timestamp = utc_now()

    print()
    print("=" * 100)
    print("PRODUCTION SNAPSHOT")
    print("=" * 100)

    print(
        "Timestamp          :",
        timestamp
    )

    print()
    print("Loading market universe...")

    identity_map = load_universe(
        conn
    )

    print()
    print("Building snapshot...")

    snapshot = build_snapshot(
        identity_map,
        timestamp
    )

    fingerprint = validate_snapshot(
        snapshot
    )

    print()
    print("SNAPSHOT VALIDATION")
    print("-" * 100)

    print(
        "Rows               :",
        fingerprint["rows"]
    )

    print(
        "Distinct CMC IDs   :",
        fingerprint["cmc_ids"]
    )

    print(
        "Distinct Symbols   :",
        fingerprint["symbols"]
    )

    print(
        "Collision rows     :",
        fingerprint["collision_rows"]
    )

    print()
    print("Writing production snapshot...")

    result = write_snapshot(
        conn,
        snapshot
    )

    print()
    print("WRITE VERIFICATION")
    print("-" * 100)

    print(
        "Inserted           :",
        result["inserted"]
    )

    print(
        "CMC IDs            :",
        result["distinct_cmc_ids"]
    )

    print(
        "Duplicate IDs      :",
        result["duplicate_ids"]
    )

    print(
        "Source Rows        :",
        result["source_rows"]
    )

    print(
        "Engine Rows        :",
        result["engine_rows"]
    )

    print(
        "Batches            :",
        result["batches"]
    )

    print(
        "Batch Size         :",
        BATCH_SIZE
    )

    print(
        "Source             :",
        SOURCE_NAME
    )

    print(
        "Engine             :",
        ENGINE_VERSION
    )

    print()
    print("PRODUCTION SNAPSHOT PASS")

    return {
        "timestamp": timestamp,
        **fingerprint,
        **result,
    }


# =============================================================================
# MAIN
# =============================================================================

def main():

    print()
    print("=" * 100)
    print("ARUNDA MARKET HISTORY ENGINE v0.4")
    print("=" * 100)

    print(
        "Source              :",
        SOURCE_NAME
    )

    print(
        "Engine              :",
        ENGINE_VERSION
    )

    print(
        "Database            :",
        DB_PATH
    )

    print(
        "Mode                :",
        "CONTINUOUS HISTORICAL ACCUMULATION"
    )

    print(
        "Interval             :",
        INTERVAL_SECONDS,
        "seconds"
    )

    print(
        "Batch Size           :",
        BATCH_SIZE
    )

    print(
        "Identity             :",
        "(timestamp, cmc_id)"
    )

    print(
        "CMC_ID               :",
        "REQUIRED"
    )

    print(
        "Symbol Collisions    :",
        "PRESERVED"
    )

    print(
        "Overwrite            :",
        "DISABLED"
    )

    print(
        "Deduplication        :",
        "TIMESTAMP + CMC_ID"
    )

    print(
        "Price Validation     :",
        "ENABLED"
    )

    print(
        "Atomic Snapshot      :",
        "ENABLED"
    )

    print(
        "Batch Write          :",
        "ENABLED"
    )

    print()
    print(
        "Technical            :",
        "NOT USED"
    )

    print(
        "News                 :",
        "NOT USED"
    )

    print(
        "Whale                :",
        "NOT USED"
    )

    print(
        "Microstructure       :",
        "NOT USED"
    )

    print(
        "Opportunity          :",
        "NOT USED"
    )

    print(
        "Signal               :",
        "NOT USED"
    )

    print(
        "Prediction           :",
        "NOT USED"
    )

    print(
        "Risk                 :",
        "NOT USED"
    )

    print(
        "Execution            :",
        "NOT USED"
    )

    print("=" * 100)

    conn = sqlite3.connect(
        DB_PATH,
        timeout=30
    )

    try:

        print()
        print(
            "Database            :",
            "CONNECTED"
        )

        # ---------------------------------------------------------------------
        # Production contracts
        # ---------------------------------------------------------------------

        validate_history_schema(
            conn
        )

        validate_universe_schema(
            conn
        )

        print()
        print(
            "Production Writer   :",
            "ACTIVE"
        )

        print(
            "Press Ctrl+C to stop."
        )

        print()

        cycle = 0
        successful = 0
        failed = 0
        total_inserted = 0

        while True:

            cycle += 1

            print()
            print("=" * 100)

            print(
                f"PRODUCTION COLLECTION CYCLE #{cycle}"
            )

            print(
                "Time                :",
                utc_now()
            )

            print("=" * 100)

            try:

                result = collect_snapshot(
                    conn
                )

                successful += 1

                total_inserted += result[
                    "inserted"
                ]

                print()
                print("=" * 100)
                print("WRITER STATUS")
                print("=" * 100)

                print(
                    "Total Cycles        :",
                    cycle
                )

                print(
                    "Successful          :",
                    successful
                )

                print(
                    "Failed              :",
                    failed
                )

                print(
                    "Total Inserted      :",
                    total_inserted
                )

                print(
                    "Interval             :",
                    INTERVAL_SECONDS
                )

                print(
                    "History              :",
                    "ACTIVE"
                )

                print(
                    "CMC Identity         :",
                    "ACTIVE"
                )

                print(
                    "Symbol Collisions    :",
                    "PRESERVED"
                )

                print(
                    "Writer               :",
                    ENGINE_VERSION
                )

                print("=" * 100)

                print_statistics(
                    conn
                )

            except Exception as exc:

                failed += 1

                print()
                print("=" * 100)
                print("PRODUCTION COLLECTION ERROR")
                print("=" * 100)

                print(
                    type(exc).__name__ + ":",
                    exc
                )

                print()
                print(
                    "Transaction           :",
                    "ROLLED BACK"
                )

                print(
                    "Database              :",
                    "PRESERVED"
                )

                print("=" * 100)

            print()
            print(
                f"Waiting {INTERVAL_SECONDS} seconds..."
            )

            try:

                time.sleep(
                    INTERVAL_SECONDS
                )

            except KeyboardInterrupt:

                raise

    except KeyboardInterrupt:

        print()
        print()
        print("=" * 100)
        print(
            "ARUNDA MARKET HISTORY ENGINE STOPPED"
        )
        print("=" * 100)

        try:

            (
                total,
                snapshots,
                assets,
            ) = history_statistics(
                conn
            )

            print(
                "Total History Rows :",
                total
            )

            print(
                "Snapshots          :",
                snapshots
            )

            print(
                "Distinct CMC IDs   :",
                assets
            )

        except Exception as exc:

            print(
                "Statistics Error   :",
                exc
            )

        print(
            "Database            :",
            "PRESERVED"
        )

        print(
            "Reason              :",
            "USER INTERRUPT"
        )

        print("=" * 100)

    finally:

        conn.close()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()