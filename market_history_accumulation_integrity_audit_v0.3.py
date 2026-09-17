import sqlite3
from datetime import datetime, timezone


# =============================================================================
# ARUNDA MARKET HISTORY
# ACCUMULATION INTEGRITY AUDIT v0.3
# =============================================================================
#
# PURPOSE
# -------
# Read-only production accumulation integrity verification.
#
# IMPORTANT
# ---------
# - NO INSERT
# - NO UPDATE
# - NO DELETE
# - NO ALTER
# - NO CREATE
# - NO DROP
# - NO REPAIR
# - NO DATA MODIFICATION
#
# CONTRACT
# --------
# Writer Engine      : MARKET_HISTORY_CMC_v0.4
# Source             : COINMARKETCAP
# Expected Rows      : 1000 / snapshot
# Expected CMC IDs   : 1000 / snapshot
# Expected Symbols   : 987 / snapshot
# Expected Collisions: 13 / snapshot
#
# BASELINE POLICY
# ---------------
# The known source_timestamp anomaly in the v0.4 baseline snapshot
# is accepted as a KNOWN BASELINE ANOMALY and does not affect the
# post-baseline production accumulation verdict.
#
# TEMPORAL POLICY
# ---------------
# Missing 60-second intervals are reported as GAP/WARNING.
# They are NOT treated as data corruption.
#
# =============================================================================


DB_PATH = "arunda.db"

WRITER_ENGINE = "MARKET_HISTORY_CMC_v0.4"
SOURCE_NAME = "COINMARKETCAP"

EXPECTED_ROWS = 1000
EXPECTED_CMC_IDS = 1000
EXPECTED_SYMBOLS = 987
EXPECTED_COLLISIONS = 13

EXPECTED_INTERVAL_SECONDS = 60
INTERVAL_TOLERANCE_SECONDS = 15

RECENT_SNAPSHOTS = 20


# =============================================================================
# BASELINE
# =============================================================================

V04_BASELINE_ENGINE = "MARKET_HISTORY_CMC_v0.4"

KNOWN_BASELINE_TIMESTAMP = (
    "2026-08-18T12:06:12.806496+00:00"
)


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

passed = 0
failed = 0
warnings = 0
known_anomalies = 0


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def pass_check(label, detail=""):
    global passed

    passed += 1

    if detail:
        print(f"[PASS] {label} :: {detail}")
    else:
        print(f"[PASS] {label}")


def fail_check(label, detail=""):
    global failed

    failed += 1

    if detail:
        print(f"[FAIL] {label} :: {detail}")
    else:
        print(f"[FAIL] {label}")


def warn_check(label, detail=""):
    global warnings

    warnings += 1

    if detail:
        print(f"[WARN] {label} :: {detail}")
    else:
        print(f"[WARN] {label}")


def known_anomaly(label, detail=""):
    global known_anomalies

    known_anomalies += 1

    if detail:
        print(f"[KNOWN BASELINE ANOMALY] {label} :: {detail}")
    else:
        print(f"[KNOWN BASELINE ANOMALY] {label}")


# =============================================================================
# DATABASE
# =============================================================================

def connect_read_only():

    uri = f"file:{DB_PATH}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True,
        timeout=30
    )

    return conn


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
        (table_name,)
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
# READ-ONLY SAFETY
# =============================================================================

def audit_read_only_safety(conn):

    section("READ-ONLY SAFETY AUDIT")

    journal_mode = conn.execute(
        "PRAGMA journal_mode"
    ).fetchone()[0]

    print("Journal Mode       :", journal_mode)

    # SQLite URI mode=ro guarantees that the database connection
    # was opened read-only.
    pass_check(
        "Database opened in read-only mode"
    )


# =============================================================================
# MARKET HISTORY SCHEMA
# =============================================================================

def audit_history_schema(conn):

    section("MARKET HISTORY SCHEMA AUDIT")

    if not table_exists(conn, "market_history"):

        fail_check(
            "market_history table exists"
        )

        return False

    pass_check(
        "market_history table exists"
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

    columns = get_columns(
        conn,
        "market_history"
    )

    missing = required - columns

    if missing:

        fail_check(
            "market_history required columns",
            "Missing: " + ", ".join(sorted(missing))
        )

        return False

    pass_check(
        "market_history required columns",
        "All required columns present"
    )

    return True


# =============================================================================
# MARKET UNIVERSE SCHEMA
# =============================================================================

def audit_universe_schema(conn):

    section("MARKET UNIVERSE SCHEMA AUDIT")

    if not table_exists(conn, "market_universe"):

        fail_check(
            "market_universe table exists"
        )

        return False

    pass_check(
        "market_universe table exists"
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

    columns = get_columns(
        conn,
        "market_universe"
    )

    missing = required - columns

    if missing:

        fail_check(
            "market_universe required columns",
            "Missing: " + ", ".join(sorted(missing))
        )

        return False

    pass_check(
        "market_universe required columns",
        "All required columns present"
    )

    return True


# =============================================================================
# GLOBAL STATISTICS
# =============================================================================

def global_statistics(conn):

    section("GLOBAL HISTORY STATISTICS")

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

    cmc_ids = conn.execute(
        """
        SELECT COUNT(DISTINCT cmc_id)
        FROM market_history
        """
    ).fetchone()[0]

    print("Total History Rows :", total_rows)
    print("Snapshots          :", snapshots)
    print("Distinct CMC IDs   :", cmc_ids)

    if total_rows > 0:
        pass_check(
            "History contains rows",
            f"rows={total_rows}"
        )
    else:
        fail_check(
            "History contains rows"
        )

    if snapshots > 0:
        pass_check(
            "History contains snapshots",
            f"snapshots={snapshots}"
        )
    else:
        fail_check(
            "History contains snapshots"
        )

    if cmc_ids == EXPECTED_CMC_IDS:
        pass_check(
            "Global CMC identity coverage",
            f"expected={EXPECTED_CMC_IDS}, actual={cmc_ids}"
        )
    else:
        fail_check(
            "Global CMC identity coverage",
            f"expected={EXPECTED_CMC_IDS}, actual={cmc_ids}"
        )

    return total_rows, snapshots, cmc_ids


# =============================================================================
# BASELINE DISCOVERY
# =============================================================================

def find_v04_baseline(conn):

    section("V0.4 PRODUCTION BASELINE")

    row = conn.execute(
        """
        SELECT MIN(timestamp)
        FROM market_history
        WHERE engine_version = ?
          AND source = ?
        """,
        (
            V04_BASELINE_ENGINE,
            SOURCE_NAME,
        )
    ).fetchone()

    baseline = row[0]

    if baseline is None:

        fail_check(
            "v0.4 baseline exists"
        )

        return None

    print("Baseline Timestamp :", baseline)
    print("Baseline Source    :", SOURCE_NAME)
    print("Baseline Engine    :", V04_BASELINE_ENGINE)

    pass_check(
        "v0.4 baseline exists",
        baseline
    )

    return baseline


# =============================================================================
# PRODUCTION SCOPE
# =============================================================================

def production_scope(conn, baseline):

    section("V0.4 PRODUCTION SCOPE")

    row = conn.execute(
        """
        SELECT
            COUNT(*),
            COUNT(DISTINCT timestamp),
            COUNT(DISTINCT cmc_id)
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchone()

    rows, snapshots, cmc_ids = row

    print("Production Rows    :", rows)
    print("Production Snapshots:", snapshots)
    print("Production CMC IDs :", cmc_ids)

    return rows, snapshots, cmc_ids


# =============================================================================
# SNAPSHOT STRUCTURAL AUDIT
# =============================================================================

def snapshot_structural_audit(conn, baseline):

    section("V0.4 PRODUCTION SNAPSHOT STRUCTURAL AUDIT")

    print("Baseline Timestamp :", baseline)

    rows = conn.execute(
        """
        SELECT
            timestamp,
            COUNT(*) AS row_count,
            COUNT(DISTINCT cmc_id) AS cmc_count,
            COUNT(DISTINCT symbol) AS symbol_count
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
        GROUP BY timestamp
        ORDER BY timestamp ASC
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchall()

    print("Snapshots Audited  :", len(rows))

    invalid_rows = []
    invalid_cmc = []
    invalid_symbols = []
    invalid_collisions = []

    for timestamp, row_count, cmc_count, symbol_count in rows:

        collision_rows = row_count - symbol_count

        if row_count != EXPECTED_ROWS:
            invalid_rows.append(
                (timestamp, row_count)
            )

        if cmc_count != EXPECTED_CMC_IDS:
            invalid_cmc.append(
                (timestamp, cmc_count)
            )

        if symbol_count != EXPECTED_SYMBOLS:
            invalid_symbols.append(
                (timestamp, symbol_count)
            )

        if collision_rows != EXPECTED_COLLISIONS:
            invalid_collisions.append(
                (timestamp, collision_rows)
            )

    if not invalid_rows:

        pass_check(
            "Every v0.4 snapshot contains 1000 rows",
            f"snapshots={len(rows)}"
        )

    else:

        fail_check(
            "Every v0.4 snapshot contains 1000 rows",
            f"invalid_snapshots={len(invalid_rows)}"
        )

        print()
        print("INVALID ROW COUNTS")

        for timestamp, count in invalid_rows:
            print(
                f"  {timestamp} => {count}"
            )

    if not invalid_cmc:

        pass_check(
            "Every v0.4 snapshot contains 1000 CMC IDs"
        )

    else:

        fail_check(
            "Every v0.4 snapshot contains 1000 CMC IDs",
            f"invalid_snapshots={len(invalid_cmc)}"
        )

    if not invalid_symbols:

        pass_check(
            "Every v0.4 snapshot contains 987 symbols"
        )

    else:

        fail_check(
            "Every v0.4 snapshot contains 987 symbols",
            f"invalid_snapshots={len(invalid_symbols)}"
        )

    if not invalid_collisions:

        pass_check(
            "13 symbol collision rows preserved per v0.4 snapshot"
        )

    else:

        fail_check(
            "13 symbol collision rows preserved per v0.4 snapshot",
            f"invalid_snapshots={len(invalid_collisions)}"
        )

    return rows


# =============================================================================
# IDENTITY AUDIT
# =============================================================================

def identity_audit(conn, baseline):

    section("V0.4 CMC IDENTITY INTEGRITY")

    null_ids = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND cmc_id IS NULL
        """,
        (baseline,)
    ).fetchone()[0]

    if null_ids == 0:

        pass_check(
            "No NULL CMC IDs",
            "null_rows=0"
        )

    else:

        fail_check(
            "No NULL CMC IDs",
            f"null_rows={null_ids}"
        )

    duplicate_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT timestamp, cmc_id
            FROM market_history
            WHERE timestamp >= ?
            GROUP BY timestamp, cmc_id
            HAVING COUNT(*) > 1
        )
        """,
        (baseline,)
    ).fetchone()[0]

    if duplicate_groups == 0:

        pass_check(
            "No duplicate (timestamp, cmc_id) identities",
            "duplicate_identity_groups=0"
        )

    else:

        fail_check(
            "No duplicate (timestamp, cmc_id) identities",
            f"duplicate_identity_groups={duplicate_groups}"
        )


# =============================================================================
# PRICE AUDIT
# =============================================================================

def price_audit(conn, baseline):

    section("V0.4 PRICE INTEGRITY")

    null_prices = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND price IS NULL
        """,
        (baseline,)
    ).fetchone()[0]

    if null_prices == 0:

        pass_check(
            "No NULL prices",
            "null_rows=0"
        )

    else:

        fail_check(
            "No NULL prices",
            f"null_rows={null_prices}"
        )

    invalid_prices = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND (
              price IS NULL
              OR price <= 0
          )
        """,
        (baseline,)
    ).fetchone()[0]

    if invalid_prices == 0:

        pass_check(
            "No non-positive prices",
            "invalid_rows=0"
        )

    else:

        fail_check(
            "No non-positive prices",
            f"invalid_rows={invalid_prices}"
        )


# =============================================================================
# SOURCE / ENGINE AUDIT
# =============================================================================

def source_engine_audit(conn, baseline):

    section("V0.4 SOURCE / ENGINE INTEGRITY")

    invalid_source = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND (
              source IS NULL
              OR source != ?
          )
        """,
        (
            baseline,
            SOURCE_NAME,
        )
    ).fetchone()[0]

    if invalid_source == 0:

        pass_check(
            "All rows at/after baseline have expected source",
            f"source={SOURCE_NAME}"
        )

    else:

        fail_check(
            "All rows at/after baseline have expected source",
            f"invalid_rows={invalid_source}"
        )

    invalid_engine = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND (
              engine_version IS NULL
              OR engine_version != ?
          )
        """,
        (
            baseline,
            WRITER_ENGINE,
        )
    ).fetchone()[0]

    if invalid_engine == 0:

        pass_check(
            "All rows at/after baseline have expected engine",
            f"engine={WRITER_ENGINE}"
        )

    else:

        fail_check(
            "All rows at/after baseline have expected engine",
            f"invalid_rows={invalid_engine}"
        )


# =============================================================================
# TIMESTAMP METADATA AUDIT
# =============================================================================

def timestamp_metadata_audit(conn, baseline):

    section("V0.4 TIMESTAMP METADATA INTEGRITY")

    null_source_ts = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND source_timestamp IS NULL
        """,
        (baseline,)
    ).fetchone()[0]

    if null_source_ts == 0:

        pass_check(
            "No NULL source_timestamp",
            "null_rows=0"
        )

    else:

        fail_check(
            "No NULL source_timestamp",
            f"null_rows={null_source_ts}"
        )

    # -------------------------------------------------------------------------
    # IMPORTANT:
    # The baseline snapshot has a known source_timestamp anomaly.
    # We therefore exclude ONLY that exact baseline timestamp from the
    # production consistency verdict.
    # -------------------------------------------------------------------------

    baseline_mismatch = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp = ?
          AND (
              source_timestamp IS NULL
              OR timestamp != source_timestamp
          )
        """,
        (baseline,)
    ).fetchone()[0]

    baseline_rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp = ?
        """,
        (baseline,)
    ).fetchone()[0]

    if (
        baseline_mismatch == EXPECTED_ROWS
        and baseline_rows == EXPECTED_ROWS
    ):

        known_anomaly(
            "Baseline source_timestamp mismatch accepted",
            f"timestamp={baseline}, affected_rows={baseline_mismatch}"
        )

    elif baseline_mismatch == 0:

        pass_check(
            "Baseline timestamp/source_timestamp consistency",
            "baseline has no mismatch"
        )

    else:

        fail_check(
            "Baseline source_timestamp anomaly is bounded",
            (
                f"baseline_rows={baseline_rows}, "
                f"mismatch_rows={baseline_mismatch}"
            )
        )

    # -------------------------------------------------------------------------
    # POST-BASELINE ONLY
    # -------------------------------------------------------------------------

    post_baseline_mismatch = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp > ?
          AND (
              source_timestamp IS NULL
              OR timestamp != source_timestamp
          )
        """,
        (baseline,)
    ).fetchone()[0]

    if post_baseline_mismatch == 0:

        pass_check(
            "Post-baseline timestamp equals source_timestamp",
            "mismatch_rows=0"
        )

    else:

        fail_check(
            "Post-baseline timestamp equals source_timestamp",
            f"mismatch_rows={post_baseline_mismatch}"
        )

    null_created_at = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND created_at IS NULL
        """,
        (baseline,)
    ).fetchone()[0]

    if null_created_at == 0:

        pass_check(
            "No NULL created_at",
            "null_rows=0"
        )

    else:

        fail_check(
            "No NULL created_at",
            f"null_rows={null_created_at}"
        )

    created_mismatch = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND (
              created_at IS NULL
              OR created_at != timestamp
          )
        """,
        (baseline,)
    ).fetchone()[0]

    if created_mismatch == 0:

        pass_check(
            "created_at equals snapshot timestamp",
            "mismatch_rows=0"
        )

    else:

        fail_check(
            "created_at equals snapshot timestamp",
            f"mismatch_rows={created_mismatch}"
        )


# =============================================================================
# TEMPORAL AUDIT
# =============================================================================

def parse_timestamp(value):

    if value.endswith("Z"):
        value = value[:-1] + "+00:00"

    return datetime.fromisoformat(value)


def temporal_audit(conn, baseline):

    section("V0.4 TEMPORAL SEQUENCE AUDIT")

    rows = conn.execute(
        """
        SELECT DISTINCT timestamp
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
        ORDER BY timestamp ASC
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchall()

    timestamps = [
        row[0]
        for row in rows
    ]

    parse_errors = []

    parsed = []

    for timestamp in timestamps:

        try:
            parsed.append(
                parse_timestamp(timestamp)
            )

        except Exception:
            parse_errors.append(timestamp)

    if not parse_errors:

        pass_check(
            "All v0.4 timestamps parse as ISO timestamps",
            "all timestamps valid"
        )

    else:

        fail_check(
            "All v0.4 timestamps parse as ISO timestamps",
            f"invalid_timestamps={len(parse_errors)}"
        )

    if len(parsed) <= 1:

        pass_check(
            "v0.4 snapshot timestamps strictly increase",
            "insufficient snapshots for ordering anomaly"
        )

        return

    strictly_increasing = True

    for previous, current in zip(
        parsed,
        parsed[1:]
    ):

        if current <= previous:
            strictly_increasing = False
            break

    if strictly_increasing:

        pass_check(
            "v0.4 snapshot timestamps strictly increase",
            "chronological order valid"
        )

    else:

        fail_check(
            "v0.4 snapshot timestamps strictly increase",
            "chronological violation detected"
        )

    interval_anomalies = []

    for previous_ts, current_ts in zip(
        parsed,
        parsed[1:]
    ):

        delta = (
            current_ts - previous_ts
        ).total_seconds()

        if abs(
            delta - EXPECTED_INTERVAL_SECONDS
        ) > INTERVAL_TOLERANCE_SECONDS:

            interval_anomalies.append(
                (
                    previous_ts,
                    current_ts,
                    delta
                )
            )

    if not interval_anomalies:

        pass_check(
            "60-second interval consistency",
            "all intervals within tolerance"
        )

    else:

        warn_check(
            "60-second interval consistency",
            (
                f"interval_anomalies={len(interval_anomalies)} "
                f"tolerance={INTERVAL_TOLERANCE_SECONDS}s"
            )
        )

        print()
        print("V0.4 INTERVAL GAPS")

        for previous, current, delta in interval_anomalies:

            print()
            print("Previous :", previous.isoformat())
            print("Current  :", current.isoformat())
            print("Delta    :", delta, "seconds")

        print()
        print(
            "Interval gaps are warnings only and do not affect "
            "production accumulation integrity verdict."
        )


# =============================================================================
# RECENT SNAPSHOT AUDIT
# =============================================================================

def recent_snapshot_audit(conn, baseline):

    section("RECENT V0.4 SNAPSHOT DETAILED AUDIT")

    rows = conn.execute(
        """
        SELECT timestamp
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
        GROUP BY timestamp
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
            RECENT_SNAPSHOTS,
        )
    ).fetchall()

    timestamps = [
        row[0]
        for row in rows
    ]

    print("Snapshots Selected :", len(timestamps))

    invalid = []

    for timestamp in timestamps:

        result = conn.execute(
            """
            SELECT
                COUNT(*) AS rows,
                COUNT(DISTINCT cmc_id) AS cmc_ids,
                COUNT(DISTINCT symbol) AS symbols,
                SUM(
                    CASE
                        WHEN source = ?
                        THEN 1
                        ELSE 0
                    END
                ) AS source_rows,
                SUM(
                    CASE
                        WHEN engine_version = ?
                        THEN 1
                        ELSE 0
                    END
                ) AS engine_rows
            FROM market_history
            WHERE timestamp = ?
            """,
            (
                SOURCE_NAME,
                WRITER_ENGINE,
                timestamp,
            )
        ).fetchone()

        (
            row_count,
            cmc_count,
            symbol_count,
            source_rows,
            engine_rows,
        ) = result

        if (
            row_count != EXPECTED_ROWS
            or cmc_count != EXPECTED_CMC_IDS
            or symbol_count != EXPECTED_SYMBOLS
            or source_rows != EXPECTED_ROWS
            or engine_rows != EXPECTED_ROWS
        ):

            invalid.append(
                (
                    timestamp,
                    row_count,
                    cmc_count,
                    symbol_count,
                    source_rows,
                    engine_rows,
                )
            )

    if not invalid:

        pass_check(
            "Recent v0.4 snapshots pass detailed identity audit",
            f"invalid_snapshots=0"
        )

    else:

        fail_check(
            "Recent v0.4 snapshots pass detailed identity audit",
            f"invalid_snapshots={len(invalid)}"
        )

        print()
        print("RECENT SNAPSHOT FAILURES")

        for item in invalid:

            (
                timestamp,
                rows_count,
                cmc_count,
                symbol_count,
                source_rows,
                engine_rows,
            ) = item

            print()
            print("Timestamp       :", timestamp)
            print("Rows            :", rows_count)
            print("CMC IDs         :", cmc_count)
            print("Symbols         :", symbol_count)
            print("Source CMC      :", source_rows)
            print("Engine CMC      :", engine_rows)
            print("-" * 100)


# =============================================================================
# RECENT ACCUMULATION GROWTH
# =============================================================================

def recent_growth_audit(conn, baseline):

    section("V0.4 RECENT ACCUMULATION GROWTH AUDIT")

    rows = conn.execute(
        """
        SELECT
            timestamp,
            COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
        GROUP BY timestamp
        ORDER BY timestamp DESC
        LIMIT 10
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchall()

    for timestamp, count in rows:

        print(
            f"  {timestamp} => {count} rows"
        )

    invalid = [
        (timestamp, count)
        for timestamp, count in rows
        if count != EXPECTED_ROWS
    ]

    if not invalid:

        pass_check(
            "Recent v0.4 snapshots all contain 1000 rows",
            f"last {len(rows)} snapshots"
        )

    else:

        fail_check(
            "Recent v0.4 snapshots all contain 1000 rows",
            f"invalid_snapshots={len(invalid)}"
        )


# =============================================================================
# LATEST SNAPSHOT FINGERPRINT
# =============================================================================

def latest_snapshot_fingerprint(conn, baseline):

    section("LATEST V0.4 SNAPSHOT FINGERPRINT")

    row = conn.execute(
        """
        SELECT timestamp
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
        ORDER BY timestamp DESC
        LIMIT 1
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchone()

    if row is None:

        fail_check(
            "Latest v0.4 snapshot exists"
        )

        return

    timestamp = row[0]

    fingerprint = conn.execute(
        """
        SELECT
            COUNT(*) AS rows,
            COUNT(DISTINCT cmc_id) AS cmc_ids,
            COUNT(DISTINCT symbol) AS symbols,
            SUM(
                CASE
                    WHEN source = ?
                    THEN 1
                    ELSE 0
                END
            ) AS source_rows,
            SUM(
                CASE
                    WHEN engine_version = ?
                    THEN 1
                    ELSE 0
                END
            ) AS engine_rows
        FROM market_history
        WHERE timestamp = ?
        """,
        (
            SOURCE_NAME,
            WRITER_ENGINE,
            timestamp,
        )
    ).fetchone()

    rows_count = fingerprint[0]
    cmc_count = fingerprint[1]
    symbol_count = fingerprint[2]
    source_rows = fingerprint[3]
    engine_rows = fingerprint[4]

    collision_rows = (
        rows_count - symbol_count
    )

    print("Timestamp          :", timestamp)
    print("Rows               :", rows_count)
    print("Distinct CMC IDs   :", cmc_count)
    print("Distinct Symbols   :", symbol_count)
    print("Source CMC Rows    :", source_rows)
    print("Engine Rows        :", engine_rows)
    print("Collision Rows     :", collision_rows)

    if (
        rows_count == EXPECTED_ROWS
        and cmc_count == EXPECTED_CMC_IDS
        and symbol_count == EXPECTED_SYMBOLS
        and source_rows == EXPECTED_ROWS
        and engine_rows == EXPECTED_ROWS
        and collision_rows == EXPECTED_COLLISIONS
    ):

        pass_check(
            "Latest v0.4 snapshot fingerprint"
        )

    else:

        fail_check(
            "Latest v0.4 snapshot fingerprint"
        )


# =============================================================================
# LEGACY REPORT
# =============================================================================

def legacy_report(conn, baseline):

    section("LEGACY HISTORY SEPARATE REPORT")

    row = conn.execute(
        """
        SELECT
            COUNT(*),
            COUNT(DISTINCT timestamp),
            SUM(
                CASE
                    WHEN source IS NULL
                    THEN 1
                    ELSE 0
                END
            ),
            SUM(
                CASE
                    WHEN engine_version IS NULL
                    THEN 1
                    ELSE 0
                END
            ),
            SUM(
                CASE
                    WHEN source_timestamp IS NULL
                    THEN 1
                    ELSE 0
                END
            ),
            SUM(
                CASE
                    WHEN created_at IS NULL
                    THEN 1
                    ELSE 0
                END
            )
        FROM market_history
        WHERE timestamp < ?
        """,
        (baseline,)
    ).fetchone()

    (
        legacy_rows,
        legacy_snapshots,
        null_source,
        null_engine,
        null_source_ts,
        null_created,
    ) = row

    print("Legacy Baseline    :", baseline)
    print("Legacy Rows        :", legacy_rows)
    print("Legacy Snapshots   :", legacy_snapshots)
    print("NULL Source        :", null_source)
    print("NULL Engine        :", null_engine)
    print("NULL Source TS     :", null_source_ts)
    print("NULL Created At    :", null_created)

    print()
    print("LEGACY STATUS      : REPORTED SEPARATELY")
    print("V0.4 DECISION      : LEGACY DOES NOT AFFECT V0.4 RESULT")


# =============================================================================
# POST-BASELINE STRICT SOURCE/ENGINE SCOPE
# =============================================================================

def post_baseline_scope_integrity(conn, baseline):

    section("POST-BASELINE PRODUCTION SCOPE INTEGRITY")

    # Any row after baseline must belong to the v0.4 production contract.

    invalid_rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp > ?
          AND (
              source != ?
              OR engine_version != ?
              OR source IS NULL
              OR engine_version IS NULL
          )
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchone()[0]

    if invalid_rows == 0:

        pass_check(
            "All post-baseline rows belong to v0.4 production contract",
            "invalid_rows=0"
        )

    else:

        fail_check(
            "All post-baseline rows belong to v0.4 production contract",
            f"invalid_rows={invalid_rows}"
        )


# =============================================================================
# FINAL DECISION
# =============================================================================

def final_result():

    section("ACCUMULATION INTEGRITY AUDIT RESULT")

    print("Baseline            :", KNOWN_BASELINE_TIMESTAMP)
    print("Writer              :", WRITER_ENGINE)
    print("Source              :", SOURCE_NAME)

    print()
    print("Checks              :", passed + failed)
    print("Passed              :", passed)
    print("Failed              :", failed)
    print("Warnings            :", warnings)
    print("Known Anomalies     :", known_anomalies)

    print()

    if failed == 0:

        print(
            "RESULT              : PASS"
        )

        print(
            "STATUS              : "
            "V0.4 PRODUCTION ACCUMULATION VERIFIED"
        )

        print(
            "PRODUCTION          : "
            "READY FOR NEXT PRODUCTION LAYER"
        )

    else:

        print(
            "RESULT              : FAIL"
        )

        print(
            "STATUS              : "
            "V0.4 PRODUCTION ACCUMULATION NOT VERIFIED"
        )

    print()
    print(
        "BASELINE ANOMALY    : "
        "KNOWN / PRESERVED / EXCLUDED FROM V0.4 VERDICT"
    )

    print(
        "LEGACY HISTORY      : "
        "REPORTED SEPARATELY / NOT USED FOR V0.4 PASS-FAIL"
    )

    print(
        "INTERVAL GAPS       : "
        "WARNINGS ONLY / NOT DATA CORRUPTION"
    )

    print()
    print(
        "WRITE OPERATIONS    : NONE"
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    section(
        "ARUNDA MARKET HISTORY "
        "ACCUMULATION INTEGRITY AUDIT v0.3"
    )

    print(
        "Mode                : READ ONLY"
    )

    print(
        "Database            :",
        DB_PATH
    )

    print(
        "Writer Engine       :",
        WRITER_ENGINE
    )

    print(
        "Source              :",
        SOURCE_NAME
    )

    print(
        "Production Contract : V0.4 BASELINE -> FORWARD"
    )

    print(
        "Expected Rows       :",
        EXPECTED_ROWS
    )

    print(
        "Expected CMC IDs    :",
        EXPECTED_CMC_IDS
    )

    print(
        "Expected Symbols    :",
        EXPECTED_SYMBOLS
    )

    print(
        "Expected Collisions :",
        EXPECTED_COLLISIONS
    )

    print(
        "Expected Interval   :",
        EXPECTED_INTERVAL_SECONDS,
        "seconds"
    )

    print(
        "Interval Tolerance  :",
        INTERVAL_TOLERANCE_SECONDS,
        "seconds"
    )

    print(
        "Recent Snapshots    :",
        RECENT_SNAPSHOTS
    )

    print()
    print(
        "Known Baseline      :",
        KNOWN_BASELINE_TIMESTAMP
    )

    print()
    print("WRITE OPERATIONS    : NONE")
    print("INSERT              : NONE")
    print("UPDATE              : NONE")
    print("DELETE              : NONE")
    print("ALTER               : NONE")
    print("CREATE              : NONE")
    print("DROP                : NONE")
    print("REPAIR              : NONE")

    conn = None

    try:

        section("AUDIT START")

        print(
            "Audit Started       :",
            utc_now()
        )

        conn = connect_read_only()

        print(
            "Database            : CONNECTED READ-ONLY"
        )

        # ---------------------------------------------------------------------
        # SAFETY
        # ---------------------------------------------------------------------

        audit_read_only_safety(conn)

        # ---------------------------------------------------------------------
        # SCHEMAS
        # ---------------------------------------------------------------------

        history_ok = audit_history_schema(
            conn
        )

        universe_ok = audit_universe_schema(
            conn
        )

        if not history_ok:

            print()
            print(
                "CRITICAL: market_history schema invalid."
            )

            final_result()
            return

        # Universe schema is required for contract awareness,
        # but accumulation verdict is primarily based on market_history.
        # Do not terminate solely because the universe schema is unavailable
        # after the history schema itself has passed.

        # ---------------------------------------------------------------------
        # GLOBAL
        # ---------------------------------------------------------------------

        global_statistics(
            conn
        )

        # ---------------------------------------------------------------------
        # BASELINE
        # ---------------------------------------------------------------------

        baseline = find_v04_baseline(
            conn
        )

        if baseline is None:

            final_result()
            return

        # The discovered baseline must match the known v0.4 production
        # transition point for this database state.
        if baseline == KNOWN_BASELINE_TIMESTAMP:

            pass_check(
                "Baseline matches known v0.4 production transition",
                baseline
            )

        else:

            fail_check(
                "Baseline matches known v0.4 production transition",
                (
                    f"expected={KNOWN_BASELINE_TIMESTAMP}, "
                    f"actual={baseline}"
                )
            )

        # ---------------------------------------------------------------------
        # PRODUCTION SCOPE
        # ---------------------------------------------------------------------

        production_scope(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # STRUCTURAL
        # ---------------------------------------------------------------------

        snapshot_structural_audit(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # IDENTITY
        # ---------------------------------------------------------------------

        identity_audit(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # PRICE
        # ---------------------------------------------------------------------

        price_audit(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # SOURCE / ENGINE
        # ---------------------------------------------------------------------

        source_engine_audit(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # TIMESTAMP METADATA
        # ---------------------------------------------------------------------

        timestamp_metadata_audit(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # TEMPORAL
        # ---------------------------------------------------------------------

        temporal_audit(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # RECENT
        # ---------------------------------------------------------------------

        recent_snapshot_audit(
            conn,
            baseline
        )

        recent_growth_audit(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # LATEST FINGERPRINT
        # ---------------------------------------------------------------------

        latest_snapshot_fingerprint(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # STRICT POST-BASELINE SCOPE
        # ---------------------------------------------------------------------

        post_baseline_scope_integrity(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # LEGACY
        # ---------------------------------------------------------------------

        legacy_report(
            conn,
            baseline
        )

        # ---------------------------------------------------------------------
        # FINAL
        # ---------------------------------------------------------------------

        final_result()

    except sqlite3.Error as exc:

        print()
        print(
            "=" * 100
        )
        print(
            "AUDIT DATABASE ERROR"
        )
        print(
            "=" * 100
        )

        print(
            type(exc).__name__ + ":",
            exc
        )

        fail_check(
            "Database audit execution"
        )

        final_result()

    except Exception as exc:

        print()
        print(
            "=" * 100
        )
        print(
            "AUDIT ERROR"
        )
        print(
            "=" * 100
        )

        print(
            type(exc).__name__ + ":",
            exc
        )

        fail_check(
            "Audit execution"
        )

        final_result()

    finally:

        if conn is not None:

            conn.close()

            print()
            print(
                "=" * 100
            )
            print(
                "DATABASE            : CONNECTION CLOSED"
            )
            print(
                "AUDIT MODE          : READ ONLY"
            )
            print(
                "WRITE OPERATIONS    : NONE"
            )
            print(
                "=" * 100
            )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()