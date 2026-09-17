import sqlite3
from datetime import datetime, timezone


# =============================================================================
# ARUNDA MARKET HISTORY
# ACCUMULATION INTEGRITY AUDIT v0.1
# =============================================================================
#
# MODE:
#     READ ONLY FORENSIC / INTEGRITY AUDIT
#
# DATABASE:
#     arunda.db
#
# WRITE OPERATIONS:
#     NONE
#     INSERT  : NONE
#     UPDATE  : NONE
#     DELETE  : NONE
#     ALTER   : NONE
#     CREATE  : NONE
#     DROP    : NONE
#
# PURPOSE:
#     Verify production historical accumulation integrity after
#     MARKET_HISTORY_CMC_v0.4 production writer activation.
#
# =============================================================================


DB_PATH = "arunda.db"

EXPECTED_SNAPSHOT_ROWS = 1000
EXPECTED_CMC_IDS = 1000
EXPECTED_SYMBOLS = 987
EXPECTED_COLLISION_ROWS = 13

EXPECTED_SOURCE = "COINMARKETCAP"
EXPECTED_ENGINE = "MARKET_HISTORY_CMC_v0.4"

EXPECTED_INTERVAL_SECONDS = 60

RECENT_SNAPSHOTS_TO_AUDIT = 20

TIME_TOLERANCE_SECONDS = 15


# =============================================================================
# READ ONLY CONNECTION
# =============================================================================

def connect_read_only():
    """
    Open SQLite database in true read-only URI mode.
    """

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
        timeout=30,
    )

    return conn


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

    return [
        row[1]
        for row in conn.execute(
            f"PRAGMA table_info({table_name})"
        ).fetchall()
    ]


# =============================================================================
# AUDIT STATE
# =============================================================================

class AuditState:

    def __init__(self):

        self.checks = 0
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def check(self, name, condition, detail=""):

        self.checks += 1

        if condition:

            self.passed += 1

            print(
                f"[PASS] {name}"
                + (f" :: {detail}" if detail else "")
            )

            return True

        self.failed += 1

        print(
            f"[FAIL] {name}"
            + (f" :: {detail}" if detail else "")
        )

        return False

    def warning(self, name, detail=""):

        self.warnings += 1

        print(
            f"[WARN] {name}"
            + (f" :: {detail}" if detail else "")
        )


AUDIT = AuditState()


# =============================================================================
# SCHEMA AUDIT
# =============================================================================

def validate_market_history_schema(conn):

    print()
    print("=" * 100)
    print("MARKET HISTORY SCHEMA AUDIT")
    print("=" * 100)

    if not AUDIT.check(
        "market_history table exists",
        table_exists(conn, "market_history"),
    ):
        return False

    columns = set(
        get_columns(
            conn,
            "market_history",
        )
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

    AUDIT.check(
        "market_history required columns",
        not missing,
        (
            "All required columns present"
            if not missing
            else "Missing: " + ", ".join(sorted(missing))
        ),
    )

    return not missing


# =============================================================================
# UNIVERSE SCHEMA AUDIT
# =============================================================================

def validate_market_universe_schema(conn):

    print()
    print("=" * 100)
    print("MARKET UNIVERSE SCHEMA AUDIT")
    print("=" * 100)

    if not AUDIT.check(
        "market_universe table exists",
        table_exists(conn, "market_universe"),
    ):
        return False

    columns = set(
        get_columns(
            conn,
            "market_universe",
        )
    )

    required = {
        "cmc_id",
        "symbol",
        "name",
        "rank",
        "price",
        "market_cap",
        "volume_24h",
        "percent_change_1h",
        "percent_change_24h",
        "percent_change_7d",
    }

    missing = required - columns

    AUDIT.check(
        "market_universe required columns",
        not missing,
        (
            "All required columns present"
            if not missing
            else "Missing: " + ", ".join(sorted(missing))
        ),
    )

    return not missing


# =============================================================================
# GLOBAL HISTORY STATISTICS
# =============================================================================

def audit_global_statistics(conn):

    print()
    print("=" * 100)
    print("GLOBAL HISTORY STATISTICS")
    print("=" * 100)

    total_rows = conn.execute(
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

    distinct_cmc = conn.execute(
        """
        SELECT COUNT(DISTINCT cmc_id)
        FROM market_history
        """
    ).fetchone()[0]

    print("Total History Rows :", total_rows)
    print("Snapshots          :", snapshots)
    print("Distinct CMC IDs   :", distinct_cmc)

    AUDIT.check(
        "History contains rows",
        total_rows > 0,
        f"rows={total_rows}",
    )

    AUDIT.check(
        "History contains snapshots",
        snapshots > 0,
        f"snapshots={snapshots}",
    )

    AUDIT.check(
        "Global CMC identity coverage",
        distinct_cmc == EXPECTED_CMC_IDS,
        (
            f"expected={EXPECTED_CMC_IDS}, "
            f"actual={distinct_cmc}"
        ),
    )

    return {
        "total_rows": total_rows,
        "snapshots": snapshots,
        "distinct_cmc": distinct_cmc,
    }


# =============================================================================
# SNAPSHOT INVENTORY
# =============================================================================

def load_snapshot_inventory(conn):

    rows = conn.execute(
        """
        SELECT
            timestamp,
            COUNT(*) AS row_count,
            COUNT(DISTINCT cmc_id) AS cmc_count,
            COUNT(DISTINCT symbol) AS symbol_count,
            SUM(
                CASE
                    WHEN source = ?
                    THEN 1
                    ELSE 0
                END
            ) AS source_count,
            SUM(
                CASE
                    WHEN engine_version = ?
                    THEN 1
                    ELSE 0
                END
            ) AS engine_count
        FROM market_history
        GROUP BY timestamp
        ORDER BY timestamp ASC
        """,
        (
            EXPECTED_SOURCE,
            EXPECTED_ENGINE,
        ),
    ).fetchall()

    return rows


# =============================================================================
# ALL SNAPSHOT STRUCTURAL AUDIT
# =============================================================================

def audit_all_snapshots(conn):

    print()
    print("=" * 100)
    print("ALL SNAPSHOT STRUCTURAL AUDIT")
    print("=" * 100)

    snapshots = load_snapshot_inventory(conn)

    print("Snapshots Audited  :", len(snapshots))

    if not snapshots:

        AUDIT.check(
            "Snapshot inventory exists",
            False,
            "No snapshots found",
        )

        return

    bad_rows = []
    bad_cmc = []
    bad_symbols = []
    bad_source = []
    bad_engine = []

    for row in snapshots:

        (
            timestamp,
            row_count,
            cmc_count,
            symbol_count,
            source_count,
            engine_count,
        ) = row

        if row_count != EXPECTED_SNAPSHOT_ROWS:
            bad_rows.append(
                (timestamp, row_count)
            )

        if cmc_count != EXPECTED_CMC_IDS:
            bad_cmc.append(
                (timestamp, cmc_count)
            )

        if symbol_count != EXPECTED_SYMBOLS:
            bad_symbols.append(
                (timestamp, symbol_count)
            )

        if source_count != EXPECTED_SNAPSHOT_ROWS:
            bad_source.append(
                (timestamp, source_count)
            )

        if engine_count != EXPECTED_SNAPSHOT_ROWS:
            bad_engine.append(
                (timestamp, engine_count)
            )

    AUDIT.check(
        "Every snapshot contains 1000 rows",
        not bad_rows,
        (
            "all snapshots valid"
            if not bad_rows
            else f"invalid_snapshots={len(bad_rows)}"
        ),
    )

    AUDIT.check(
        "Every snapshot contains 1000 CMC IDs",
        not bad_cmc,
        (
            "all snapshots valid"
            if not bad_cmc
            else f"invalid_snapshots={len(bad_cmc)}"
        ),
    )

    AUDIT.check(
        "Every snapshot contains 987 symbols",
        not bad_symbols,
        (
            "all snapshots valid"
            if not bad_symbols
            else f"invalid_snapshots={len(bad_symbols)}"
        ),
    )

    AUDIT.check(
        "Every snapshot contains expected source rows",
        not bad_source,
        (
            "all snapshots valid"
            if not bad_source
            else f"invalid_snapshots={len(bad_source)}"
        ),
    )

    AUDIT.check(
        "Every snapshot contains expected engine rows",
        not bad_engine,
        (
            "all snapshots valid"
            if not bad_engine
            else f"invalid_snapshots={len(bad_engine)}"
        ),
    )

    if bad_rows:

        print()
        print("INVALID ROW COUNTS")

        for item in bad_rows[:20]:

            print(
                " ",
                item[0],
                "=>",
                item[1],
            )

    if bad_cmc:

        print()
        print("INVALID CMC COUNTS")

        for item in bad_cmc[:20]:

            print(
                " ",
                item[0],
                "=>",
                item[1],
            )

    if bad_symbols:

        print()
        print("INVALID SYMBOL COUNTS")

        for item in bad_symbols[:20]:

            print(
                " ",
                item[0],
                "=>",
                item[1],
            )


# =============================================================================
# COLLISION AUDIT
# =============================================================================

def audit_symbol_collisions(conn):

    print()
    print("=" * 100)
    print("SYMBOL COLLISION AUDIT")
    print("=" * 100)

    rows = conn.execute(
        """
        SELECT
            timestamp,
            COUNT(*) - COUNT(DISTINCT symbol) AS collision_rows
        FROM market_history
        GROUP BY timestamp
        ORDER BY timestamp ASC
        """
    ).fetchall()

    invalid = []

    for timestamp, collision_rows in rows:

        if collision_rows != EXPECTED_COLLISION_ROWS:

            invalid.append(
                (
                    timestamp,
                    collision_rows,
                )
            )

    AUDIT.check(
        "13 symbol collision rows preserved per snapshot",
        not invalid,
        (
            "all snapshots preserve 13 collisions"
            if not invalid
            else f"invalid_snapshots={len(invalid)}"
        ),
    )

    if invalid:

        print()
        print("COLLISION ANOMALIES")

        for timestamp, count in invalid[:20]:

            print(
                " ",
                timestamp,
                "=>",
                count,
            )


# =============================================================================
# TIMESTAMP NULL AUDIT
# =============================================================================

def audit_timestamp_nulls(conn):

    print()
    print("=" * 100)
    print("TIMESTAMP INTEGRITY")
    print("=" * 100)

    null_timestamp = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp IS NULL
        """
    ).fetchone()[0]

    null_source_timestamp = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE source_timestamp IS NULL
        """
    ).fetchone()[0]

    null_created_at = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE created_at IS NULL
        """
    ).fetchone()[0]

    AUDIT.check(
        "No NULL timestamps",
        null_timestamp == 0,
        f"null_rows={null_timestamp}",
    )

    AUDIT.check(
        "No NULL source_timestamp",
        null_source_timestamp == 0,
        f"null_rows={null_source_timestamp}",
    )

    AUDIT.check(
        "No NULL created_at",
        null_created_at == 0,
        f"null_rows={null_created_at}",
    )


# =============================================================================
# CMC ID NULL / DUPLICATE AUDIT
# =============================================================================

def audit_identity_integrity(conn):

    print()
    print("=" * 100)
    print("CMC IDENTITY INTEGRITY")
    print("=" * 100)

    null_cmc = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE cmc_id IS NULL
        """
    ).fetchone()[0]

    AUDIT.check(
        "No NULL CMC IDs",
        null_cmc == 0,
        f"null_rows={null_cmc}",
    )

    duplicate_pairs = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT
                timestamp,
                cmc_id
            FROM market_history
            GROUP BY
                timestamp,
                cmc_id
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()[0]

    AUDIT.check(
        "No duplicate (timestamp, cmc_id) identities",
        duplicate_pairs == 0,
        f"duplicate_identity_groups={duplicate_pairs}",
    )


# =============================================================================
# PRICE INTEGRITY
# =============================================================================

def audit_price_integrity(conn):

    print()
    print("=" * 100)
    print("PRICE INTEGRITY")
    print("=" * 100)

    null_price = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE price IS NULL
        """
    ).fetchone()[0]

    invalid_price = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE price <= 0
        """
    ).fetchone()[0]

    AUDIT.check(
        "No NULL prices",
        null_price == 0,
        f"null_rows={null_price}",
    )

    AUDIT.check(
        "No non-positive prices",
        invalid_price == 0,
        f"invalid_rows={invalid_price}",
    )


# =============================================================================
# SOURCE / ENGINE INTEGRITY
# =============================================================================

def audit_source_engine_integrity(conn):

    print()
    print("=" * 100)
    print("SOURCE / ENGINE INTEGRITY")
    print("=" * 100)

    wrong_source = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE source != ?
           OR source IS NULL
        """,
        (EXPECTED_SOURCE,),
    ).fetchone()[0]

    wrong_engine = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE engine_version != ?
           OR engine_version IS NULL
        """,
        (EXPECTED_ENGINE,),
    ).fetchone()[0]

    AUDIT.check(
        "All rows have expected source",
        wrong_source == 0,
        f"invalid_rows={wrong_source}",
    )

    AUDIT.check(
        "All rows have expected engine",
        wrong_engine == 0,
        f"invalid_rows={wrong_engine}",
    )


# =============================================================================
# SOURCE TIMESTAMP CONSISTENCY
# =============================================================================

def audit_timestamp_consistency(conn):

    print()
    print("=" * 100)
    print("SOURCE TIMESTAMP CONSISTENCY")
    print("=" * 100)

    mismatch = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp != source_timestamp
        """
    ).fetchone()[0]

    AUDIT.check(
        "timestamp equals source_timestamp",
        mismatch == 0,
        f"mismatch_rows={mismatch}",
    )


# =============================================================================
# CREATED AT CONSISTENCY
# =============================================================================

def audit_created_at_consistency(conn):

    print()
    print("=" * 100)
    print("CREATED_AT CONSISTENCY")
    print("=" * 100)

    mismatch = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE created_at != timestamp
        """
    ).fetchone()[0]

    AUDIT.check(
        "created_at equals snapshot timestamp",
        mismatch == 0,
        f"mismatch_rows={mismatch}",
    )


# =============================================================================
# RECENT SNAPSHOT DETAILED AUDIT
# =============================================================================

def audit_recent_snapshots(conn):

    print()
    print("=" * 100)
    print(
        f"RECENT {RECENT_SNAPSHOTS_TO_AUDIT} SNAPSHOT DETAILED AUDIT"
    )
    print("=" * 100)

    snapshots = conn.execute(
        """
        SELECT timestamp
        FROM market_history
        GROUP BY timestamp
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (RECENT_SNAPSHOTS_TO_AUDIT,),
    ).fetchall()

    if not snapshots:

        AUDIT.check(
            "Recent snapshot inventory",
            False,
            "No snapshots found",
        )

        return

    snapshots = [
        row[0]
        for row in snapshots
    ]

    print("Snapshots Selected :", len(snapshots))

    invalid = []

    for timestamp in snapshots:

        row = conn.execute(
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(DISTINCT cmc_id) AS cmc_ids,
                COUNT(DISTINCT symbol) AS symbols,
                COUNT(
                    DISTINCT
                    CASE
                        WHEN source = ?
                        THEN cmc_id
                    END
                ) AS source_cmc,
                COUNT(
                    DISTINCT
                    CASE
                        WHEN engine_version = ?
                        THEN cmc_id
                    END
                ) AS engine_cmc
            FROM market_history
            WHERE timestamp = ?
            """,
            (
                EXPECTED_SOURCE,
                EXPECTED_ENGINE,
                timestamp,
            ),
        ).fetchone()

        (
            row_count,
            cmc_count,
            symbol_count,
            source_cmc,
            engine_cmc,
        ) = row

        if (
            row_count != EXPECTED_SNAPSHOT_ROWS
            or cmc_count != EXPECTED_CMC_IDS
            or symbol_count != EXPECTED_SYMBOLS
            or source_cmc != EXPECTED_CMC_IDS
            or engine_cmc != EXPECTED_CMC_IDS
        ):

            invalid.append(
                (
                    timestamp,
                    row_count,
                    cmc_count,
                    symbol_count,
                    source_cmc,
                    engine_cmc,
                )
            )

    AUDIT.check(
        "Recent snapshots pass detailed identity audit",
        not invalid,
        (
            "all recent snapshots valid"
            if not invalid
            else f"invalid_snapshots={len(invalid)}"
        ),
    )

    if invalid:

        print()
        print("RECENT SNAPSHOT FAILURES")

        for row in invalid:

            print(
                "Timestamp       :",
                row[0],
            )

            print(
                "Rows            :",
                row[1],
            )

            print(
                "CMC IDs         :",
                row[2],
            )

            print(
                "Symbols         :",
                row[3],
            )

            print(
                "Source CMC      :",
                row[4],
            )

            print(
                "Engine CMC      :",
                row[5],
            )

            print("-" * 80)


# =============================================================================
# TEMPORAL ORDER AUDIT
# =============================================================================

def parse_timestamp(value):

    if value.endswith("Z"):

        value = value[:-1] + "+00:00"

    return datetime.fromisoformat(value)


def audit_temporal_sequence(conn):

    print()
    print("=" * 100)
    print("TEMPORAL SEQUENCE AUDIT")
    print("=" * 100)

    rows = conn.execute(
        """
        SELECT timestamp
        FROM market_history
        GROUP BY timestamp
        ORDER BY timestamp ASC
        """
    ).fetchall()

    timestamps = [
        row[0]
        for row in rows
    ]

    if len(timestamps) < 2:

        AUDIT.warning(
            "Temporal interval audit",
            "Fewer than 2 snapshots available",
        )

        return

    parse_errors = []

    parsed = []

    for timestamp in timestamps:

        try:

            parsed.append(
                (
                    timestamp,
                    parse_timestamp(timestamp),
                )
            )

        except Exception:

            parse_errors.append(timestamp)

    AUDIT.check(
        "All snapshot timestamps parse as ISO timestamps",
        not parse_errors,
        (
            "all timestamps valid"
            if not parse_errors
            else f"invalid_timestamps={len(parse_errors)}"
        ),
    )

    if parse_errors:

        return

    ordering_errors = []

    interval_anomalies = []

    for i in range(1, len(parsed)):

        previous_text, previous = parsed[i - 1]
        current_text, current = parsed[i]

        delta = (
            current - previous
        ).total_seconds()

        if delta <= 0:

            ordering_errors.append(
                (
                    previous_text,
                    current_text,
                    delta,
                )
            )

        expected = EXPECTED_INTERVAL_SECONDS

        difference = abs(
            delta - expected
        )

        if difference > TIME_TOLERANCE_SECONDS:

            interval_anomalies.append(
                (
                    previous_text,
                    current_text,
                    delta,
                )
            )

    AUDIT.check(
        "Snapshot timestamps strictly increase",
        not ordering_errors,
        (
            "chronological order valid"
            if not ordering_errors
            else f"ordering_errors={len(ordering_errors)}"
        ),
    )

    if interval_anomalies:

        AUDIT.warning(
            "60-second interval consistency",
            (
                f"interval_anomalies={len(interval_anomalies)} "
                f"tolerance={TIME_TOLERANCE_SECONDS}s"
            ),
        )

        print()
        print("INTERVAL ANOMALIES")

        for row in interval_anomalies[-20:]:

            print()
            print("Previous :", row[0])
            print("Current  :", row[1])
            print("Delta    :", row[2], "seconds")

    else:

        print(
            "[PASS] 60-second interval consistency"
            " :: all intervals within tolerance"
        )

        AUDIT.checks += 1
        AUDIT.passed += 1


# =============================================================================
# RECENT SNAPSHOT GAP / GROWTH AUDIT
# =============================================================================

def audit_recent_growth(conn):

    print()
    print("=" * 100)
    print("RECENT ACCUMULATION GROWTH AUDIT")
    print("=" * 100)

    rows = conn.execute(
        """
        SELECT
            timestamp,
            COUNT(*) AS row_count
        FROM market_history
        GROUP BY timestamp
        ORDER BY timestamp DESC
        LIMIT 10
        """
    ).fetchall()

    if len(rows) < 2:

        AUDIT.warning(
            "Recent accumulation growth",
            "Fewer than 2 snapshots available",
        )

        return

    print("Recent snapshots:")

    for timestamp, row_count in rows:

        print(
            " ",
            timestamp,
            "=>",
            row_count,
            "rows",
        )

    AUDIT.check(
        "Recent snapshots all contain 1000 rows",
        all(
            row_count == EXPECTED_SNAPSHOT_ROWS
            for _, row_count in rows
        ),
        "last 10 snapshots",
    )


# =============================================================================
# FINAL FORENSIC SAMPLE
# =============================================================================

def print_recent_snapshot_fingerprint(conn):

    print()
    print("=" * 100)
    print("LATEST SNAPSHOT FINGERPRINT")
    print("=" * 100)

    row = conn.execute(
        """
        SELECT
            timestamp,
            COUNT(*) AS rows,
            COUNT(DISTINCT cmc_id) AS cmc_ids,
            COUNT(DISTINCT symbol) AS symbols,
            COUNT(
                DISTINCT
                CASE
                    WHEN source = ?
                    THEN cmc_id
                END
            ) AS source_cmc_ids,
            COUNT(
                DISTINCT
                CASE
                    WHEN engine_version = ?
                    THEN cmc_id
                END
            ) AS engine_cmc_ids
        FROM market_history
        GROUP BY timestamp
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (
            EXPECTED_SOURCE,
            EXPECTED_ENGINE,
        ),
    ).fetchone()

    if not row:

        print("No snapshot available.")
        return

    (
        timestamp,
        rows,
        cmc_ids,
        symbols,
        source_cmc_ids,
        engine_cmc_ids,
    ) = row

    print("Timestamp          :", timestamp)
    print("Rows               :", rows)
    print("Distinct CMC IDs   :", cmc_ids)
    print("Distinct Symbols   :", symbols)
    print("Source CMC IDs     :", source_cmc_ids)
    print("Engine CMC IDs     :", engine_cmc_ids)
    print(
        "Collision Rows     :",
        rows - symbols,
    )


# =============================================================================
# FINAL RESULT
# =============================================================================

def print_final_result():

    print()
    print("=" * 100)
    print("ACCUMULATION INTEGRITY AUDIT RESULT")
    print("=" * 100)

    print("Checks             :", AUDIT.checks)
    print("Passed             :", AUDIT.passed)
    print("Failed             :", AUDIT.failed)
    print("Warnings           :", AUDIT.warnings)

    print()

    if AUDIT.failed == 0:

        print("RESULT             : PASS")

        if AUDIT.warnings == 0:

            print(
                "STATUS             : "
                "PRODUCTION ACCUMULATION INTEGRITY VERIFIED"
            )

        else:

            print(
                "STATUS             : "
                "STRUCTURAL INTEGRITY VERIFIED WITH WARNINGS"
            )

    else:

        print("RESULT             : FAIL")

        print(
            "STATUS             : "
            "PRODUCTION ACCUMULATION INTEGRITY NOT VERIFIED"
        )

    print("=" * 100)


# =============================================================================
# MAIN
# =============================================================================

def main():

    print()
    print("=" * 100)
    print("ARUNDA MARKET HISTORY ACCUMULATION INTEGRITY AUDIT v0.1")
    print("=" * 100)

    print("Mode                : READ ONLY")
    print("Database            :", DB_PATH)
    print("Writer Engine       :", EXPECTED_ENGINE)
    print("Source              :", EXPECTED_SOURCE)
    print("Expected Rows       :", EXPECTED_SNAPSHOT_ROWS)
    print("Expected CMC IDs   :", EXPECTED_CMC_IDS)
    print("Expected Symbols    :", EXPECTED_SYMBOLS)
    print("Expected Collisions :", EXPECTED_COLLISION_ROWS)
    print("Expected Interval   :", EXPECTED_INTERVAL_SECONDS, "seconds")
    print(
        "Recent Snapshots   :",
        RECENT_SNAPSHOTS_TO_AUDIT,
    )

    print()
    print("WRITE OPERATIONS    : NONE")
    print("INSERT              : NONE")
    print("UPDATE              : NONE")
    print("DELETE              : NONE")
    print("ALTER               : NONE")
    print("CREATE              : NONE")
    print("DROP                : NONE")

    print("=" * 100)

    conn = None

    try:

        conn = connect_read_only()

        print()
        print("Database            : CONNECTED READ-ONLY")
        print("Audit Started       :", utc_now())

        history_ok = validate_market_history_schema(
            conn
        )

        universe_ok = validate_market_universe_schema(
            conn
        )

        if not history_ok:

            raise RuntimeError(
                "market_history schema validation failed."
            )

        if not universe_ok:

            raise RuntimeError(
                "market_universe schema validation failed."
            )

        audit_global_statistics(
            conn
        )

        audit_all_snapshots(
            conn
        )

        audit_symbol_collisions(
            conn
        )

        audit_timestamp_nulls(
            conn
        )

        audit_identity_integrity(
            conn
        )

        audit_price_integrity(
            conn
        )

        audit_source_engine_integrity(
            conn
        )

        audit_timestamp_consistency(
            conn
        )

        audit_created_at_consistency(
            conn
        )

        audit_recent_snapshots(
            conn
        )

        audit_temporal_sequence(
            conn
        )

        audit_recent_growth(
            conn
        )

        print_recent_snapshot_fingerprint(
            conn
        )

    except sqlite3.Error as exc:

        print()
        print("=" * 100)
        print("DATABASE AUDIT ERROR")
        print("=" * 100)

        print(
            type(exc).__name__ + ":",
            exc,
        )

        AUDIT.failed += 1

    except Exception as exc:

        print()
        print("=" * 100)
        print("AUDIT ERROR")
        print("=" * 100)

        print(
            type(exc).__name__ + ":",
            exc,
        )

        AUDIT.failed += 1

    finally:

        if conn is not None:

            conn.close()

        print_final_result()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()