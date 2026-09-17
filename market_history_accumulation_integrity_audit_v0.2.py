
import sqlite3
from datetime import datetime, timezone


# =============================================================================
# CONFIGURATION
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
# TIME
# =============================================================================

def utc_now():
    return datetime.now(timezone.utc).isoformat()


# =============================================================================
# DATABASE
# =============================================================================

def connect_read_only():
    uri = f"file:{DB_PATH}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=30
    )


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
# PRINT HELPERS
# =============================================================================

def section(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def pass_check(label, detail=""):
    if detail:
        print(f"[PASS] {label} :: {detail}")
    else:
        print(f"[PASS] {label}")


def fail_check(label, detail=""):
    if detail:
        print(f"[FAIL] {label} :: {detail}")
    else:
        print(f"[FAIL] {label}")


def warn_check(label, detail=""):
    if detail:
        print(f"[WARN] {label} :: {detail}")
    else:
        print(f"[WARN] {label}")


# =============================================================================
# SCHEMA AUDIT
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

    columns = get_columns(
        conn,
        "market_universe"
    )

    required = {
        "cmc_id",
        "symbol",
        "name",
        "rank",
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

def global_history_statistics(conn):

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

    return total_rows, snapshots, cmc_ids


def audit_global_history(conn):

    section("GLOBAL HISTORY STATISTICS")

    total_rows, snapshots, cmc_ids = \
        global_history_statistics(conn)

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


# =============================================================================
# V0.4 BASELINE
# =============================================================================

def find_v04_baseline(conn):

    row = conn.execute(
        """
        SELECT MIN(timestamp)
        FROM market_history
        WHERE engine_version = ?
          AND source = ?
        """,
        (
            WRITER_ENGINE,
            SOURCE_NAME,
        )
    ).fetchone()

    return row[0]


def audit_v04_baseline(conn):

    section("V0.4 PRODUCTION BASELINE")

    baseline = find_v04_baseline(conn)

    if baseline is None:

        fail_check(
            "v0.4 baseline exists",
            "No snapshot found with expected source and engine"
        )

        return None

    print("Baseline Timestamp :", baseline)
    print("Baseline Source    :", SOURCE_NAME)
    print("Baseline Engine    :", WRITER_ENGINE)

    pass_check(
        "v0.4 baseline exists",
        baseline
    )

    return baseline


# =============================================================================
# V0.4 SNAPSHOT LIST
# =============================================================================

def load_v04_snapshots(conn, baseline):

    return conn.execute(
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


# =============================================================================
# SNAPSHOT STRUCTURAL AUDIT
# =============================================================================

def audit_v04_snapshots(conn, baseline):

    section("V0.4 PRODUCTION SNAPSHOT STRUCTURAL AUDIT")

    timestamps = load_v04_snapshots(
        conn,
        baseline
    )

    snapshot_count = len(timestamps)

    print("Baseline Timestamp :", baseline)
    print("Snapshots Audited  :", snapshot_count)

    invalid_rows = []
    invalid_cmc = []
    invalid_symbols = []
    invalid_collisions = []

    for (timestamp,) in timestamps:

        row_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_history
            WHERE timestamp = ?
              AND source = ?
              AND engine_version = ?
            """,
            (
                timestamp,
                SOURCE_NAME,
                WRITER_ENGINE,
            )
        ).fetchone()[0]

        cmc_count = conn.execute(
            """
            SELECT COUNT(DISTINCT cmc_id)
            FROM market_history
            WHERE timestamp = ?
              AND source = ?
              AND engine_version = ?
            """,
            (
                timestamp,
                SOURCE_NAME,
                WRITER_ENGINE,
            )
        ).fetchone()[0]

        symbol_count = conn.execute(
            """
            SELECT COUNT(DISTINCT symbol)
            FROM market_history
            WHERE timestamp = ?
              AND source = ?
              AND engine_version = ?
            """,
            (
                timestamp,
                SOURCE_NAME,
                WRITER_ENGINE,
            )
        ).fetchone()[0]

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
            f"snapshots={snapshot_count}"
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

        print()
        print("INVALID CMC COUNTS")

        for timestamp, count in invalid_cmc:
            print(
                f"  {timestamp} => {count}"
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

        print()
        print("INVALID SYMBOL COUNTS")

        for timestamp, count in invalid_symbols:
            print(
                f"  {timestamp} => {count}"
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

        print()
        print("COLLISION ANOMALIES")

        for timestamp, count in invalid_collisions:
            print(
                f"  {timestamp} => {count}"
            )

    return {
        "timestamps": timestamps,
        "invalid_rows": invalid_rows,
        "invalid_cmc": invalid_cmc,
        "invalid_symbols": invalid_symbols,
        "invalid_collisions": invalid_collisions,
    }


# =============================================================================
# V0.4 IDENTITY INTEGRITY
# =============================================================================

def audit_v04_identity(conn, baseline):

    section("V0.4 CMC IDENTITY INTEGRITY")

    duplicate_groups = conn.execute(
        """
        SELECT COUNT(*)
        FROM (
            SELECT timestamp, cmc_id
            FROM market_history
            WHERE timestamp >= ?
              AND source = ?
              AND engine_version = ?
            GROUP BY timestamp, cmc_id
            HAVING COUNT(*) > 1
        )
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchone()[0]

    null_ids = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
          AND cmc_id IS NULL
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
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

    return (
        null_ids == 0
        and duplicate_groups == 0
    )


# =============================================================================
# V0.4 PRICE INTEGRITY
# =============================================================================

def audit_v04_price(conn, baseline):

    section("V0.4 PRICE INTEGRITY")

    null_prices = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
          AND price IS NULL
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchone()[0]

    invalid_prices = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
          AND price <= 0
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
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

    return (
        null_prices == 0
        and invalid_prices == 0
    )


# =============================================================================
# V0.4 SOURCE / ENGINE
# =============================================================================

def audit_v04_provenance(conn, baseline):

    section("V0.4 SOURCE / ENGINE INTEGRITY")

    bad_source = conn.execute(
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

    bad_engine = conn.execute(
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

    if bad_source == 0:
        pass_check(
            "All rows at/after baseline have expected source",
            f"source={SOURCE_NAME}"
        )
    else:
        fail_check(
            "All rows at/after baseline have expected source",
            f"invalid_rows={bad_source}"
        )

    if bad_engine == 0:
        pass_check(
            "All rows at/after baseline have expected engine",
            f"engine={WRITER_ENGINE}"
        )
    else:
        fail_check(
            "All rows at/after baseline have expected engine",
            f"invalid_rows={bad_engine}"
        )

    return (
        bad_source == 0
        and bad_engine == 0
    )


# =============================================================================
# V0.4 TIMESTAMP METADATA
# =============================================================================

def audit_v04_timestamp_metadata(conn, baseline):

    section("V0.4 TIMESTAMP METADATA INTEGRITY")

    null_source_timestamp = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
          AND source_timestamp IS NULL
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchone()[0]

    source_timestamp_mismatch = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
          AND source_timestamp != timestamp
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchone()[0]

    null_created_at = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
          AND created_at IS NULL
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchone()[0]

    created_at_mismatch = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
          AND created_at != timestamp
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchone()[0]

    if null_source_timestamp == 0:
        pass_check(
            "No NULL source_timestamp",
            "null_rows=0"
        )
    else:
        fail_check(
            "No NULL source_timestamp",
            f"null_rows={null_source_timestamp}"
        )

    if source_timestamp_mismatch == 0:
        pass_check(
            "timestamp equals source_timestamp",
            "mismatch_rows=0"
        )
    else:
        fail_check(
            "timestamp equals source_timestamp",
            f"mismatch_rows={source_timestamp_mismatch}"
        )

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

    if created_at_mismatch == 0:
        pass_check(
            "created_at equals snapshot timestamp",
            "mismatch_rows=0"
        )
    else:
        fail_check(
            "created_at equals snapshot timestamp",
            f"mismatch_rows={created_at_mismatch}"
        )

    return (
        null_source_timestamp == 0
        and source_timestamp_mismatch == 0
        and null_created_at == 0
        and created_at_mismatch == 0
    )


# =============================================================================
# TEMPORAL SEQUENCE
# =============================================================================

def audit_v04_temporal_sequence(conn, baseline):

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

    invalid_parse = []

    parsed = []

    for timestamp in timestamps:

        try:
            value = datetime.fromisoformat(
                timestamp
            )

            if value.tzinfo is None:
                value = value.replace(
                    tzinfo=timezone.utc
                )

            parsed.append(
                (timestamp, value)
            )

        except Exception:
            invalid_parse.append(
                timestamp
            )

    if not invalid_parse:
        pass_check(
            "All v0.4 timestamps parse as ISO timestamps",
            "all timestamps valid"
        )
    else:
        fail_check(
            "All v0.4 timestamps parse as ISO timestamps",
            f"invalid_timestamps={len(invalid_parse)}"
        )

    chronological = True
    interval_anomalies = []

    for index in range(1, len(parsed)):

        previous_text, previous = parsed[index - 1]
        current_text, current = parsed[index]

        delta = (
            current - previous
        ).total_seconds()

        if delta <= 0:
            chronological = False

        if abs(
            delta - EXPECTED_INTERVAL_SECONDS
        ) > INTERVAL_TOLERANCE_SECONDS:

            interval_anomalies.append(
                (
                    previous_text,
                    current_text,
                    delta
                )
            )

    if chronological:
        pass_check(
            "v0.4 snapshot timestamps strictly increase",
            "chronological order valid"
        )
    else:
        fail_check(
            "v0.4 snapshot timestamps strictly increase"
        )

    if not interval_anomalies:
        pass_check(
            "60-second interval consistency",
            "no anomalies"
        )
    else:
        warn_check(
            "60-second interval consistency",
            f"interval_anomalies={len(interval_anomalies)} "
            f"tolerance={INTERVAL_TOLERANCE_SECONDS}s"
        )

        print()
        print("V0.4 INTERVAL ANOMALIES")

        for previous, current, delta in interval_anomalies:
            print()
            print("Previous :", previous)
            print("Current  :", current)
            print("Delta    :", delta, "seconds")

    return {
        "timestamps": timestamps,
        "chronological": chronological,
        "interval_anomalies": interval_anomalies,
    }


# =============================================================================
# RECENT SNAPSHOT AUDIT
# =============================================================================

def audit_recent_v04_snapshots(conn, baseline):

    section(
        f"RECENT {RECENT_SNAPSHOTS} V0.4 SNAPSHOT DETAILED AUDIT"
    )

    timestamps = conn.execute(
        """
        SELECT DISTINCT timestamp
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
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
        for row in timestamps
    ]

    print(
        "Snapshots Selected :",
        len(timestamps)
    )

    failures = []

    for timestamp in timestamps:

        rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_history
            WHERE timestamp = ?
              AND source = ?
              AND engine_version = ?
            """,
            (
                timestamp,
                SOURCE_NAME,
                WRITER_ENGINE,
            )
        ).fetchone()[0]

        cmc = conn.execute(
            """
            SELECT COUNT(DISTINCT cmc_id)
            FROM market_history
            WHERE timestamp = ?
              AND source = ?
              AND engine_version = ?
            """,
            (
                timestamp,
                SOURCE_NAME,
                WRITER_ENGINE,
            )
        ).fetchone()[0]

        symbols = conn.execute(
            """
            SELECT COUNT(DISTINCT symbol)
            FROM market_history
            WHERE timestamp = ?
              AND source = ?
              AND engine_version = ?
            """,
            (
                timestamp,
                SOURCE_NAME,
                WRITER_ENGINE,
            )
        ).fetchone()[0]

        source_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_history
            WHERE timestamp = ?
              AND source = ?
            """,
            (
                timestamp,
                SOURCE_NAME,
            )
        ).fetchone()[0]

        engine_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_history
            WHERE timestamp = ?
              AND engine_version = ?
            """,
            (
                timestamp,
                WRITER_ENGINE,
            )
        ).fetchone()[0]

        collisions = rows - symbols

        valid = (
            rows == EXPECTED_ROWS
            and cmc == EXPECTED_CMC_IDS
            and symbols == EXPECTED_SYMBOLS
            and collisions == EXPECTED_COLLISIONS
            and source_rows == EXPECTED_ROWS
            and engine_rows == EXPECTED_ROWS
        )

        if not valid:
            failures.append(
                (
                    timestamp,
                    rows,
                    cmc,
                    symbols,
                    source_rows,
                    engine_rows,
                    collisions,
                )
            )

    if not failures:

        pass_check(
            "Recent v0.4 snapshots pass detailed identity audit",
            f"invalid_snapshots=0"
        )

    else:

        fail_check(
            "Recent v0.4 snapshots pass detailed identity audit",
            f"invalid_snapshots={len(failures)}"
        )

        print()
        print("RECENT V0.4 SNAPSHOT FAILURES")

        for (
            timestamp,
            rows,
            cmc,
            symbols,
            source_rows,
            engine_rows,
            collisions,
        ) in failures:

            print()
            print("Timestamp       :", timestamp)
            print("Rows            :", rows)
            print("CMC IDs         :", cmc)
            print("Symbols         :", symbols)
            print("Source Rows     :", source_rows)
            print("Engine Rows     :", engine_rows)
            print("Collision Rows  :", collisions)
            print("-" * 80)

    return len(failures) == 0


# =============================================================================
# GROWTH AUDIT
# =============================================================================

def audit_recent_growth(conn, baseline):

    section("V0.4 RECENT ACCUMULATION GROWTH AUDIT")

    timestamps = conn.execute(
        """
        SELECT DISTINCT timestamp
        FROM market_history
        WHERE timestamp >= ?
          AND source = ?
          AND engine_version = ?
        ORDER BY timestamp DESC
        LIMIT 10
        """,
        (
            baseline,
            SOURCE_NAME,
            WRITER_ENGINE,
        )
    ).fetchall()

    if not timestamps:

        fail_check(
            "Recent v0.4 accumulation exists"
        )

        return False

    all_valid = True

    print("Recent v0.4 snapshots:")

    for (timestamp,) in timestamps:

        rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_history
            WHERE timestamp = ?
              AND source = ?
              AND engine_version = ?
            """,
            (
                timestamp,
                SOURCE_NAME,
                WRITER_ENGINE,
            )
        ).fetchone()[0]

        print(
            f"  {timestamp} => {rows} rows"
        )

        if rows != EXPECTED_ROWS:
            all_valid = False

    if all_valid:

        pass_check(
            "Recent v0.4 snapshots all contain 1000 rows",
            f"last {len(timestamps)} snapshots"
        )

    else:

        fail_check(
            "Recent v0.4 snapshots all contain 1000 rows"
        )

    return all_valid


# =============================================================================
# LATEST FINGERPRINT
# =============================================================================

def latest_v04_fingerprint(conn, baseline):

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

        return False

    timestamp = row[0]

    rows = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp = ?
        """,
        (timestamp,)
    ).fetchone()[0]

    cmc = conn.execute(
        """
        SELECT COUNT(DISTINCT cmc_id)
        FROM market_history
        WHERE timestamp = ?
        """,
        (timestamp,)
    ).fetchone()[0]

    symbols = conn.execute(
        """
        SELECT COUNT(DISTINCT symbol)
        FROM market_history
        WHERE timestamp = ?
        """,
        (timestamp,)
    ).fetchone()[0]

    source_cmc = conn.execute(
        """
        SELECT COUNT(DISTINCT cmc_id)
        FROM market_history
        WHERE timestamp = ?
          AND source = ?
        """,
        (
            timestamp,
            SOURCE_NAME,
        )
    ).fetchone()[0]

    engine_cmc = conn.execute(
        """
        SELECT COUNT(DISTINCT cmc_id)
        FROM market_history
        WHERE timestamp = ?
          AND engine_version = ?
        """,
        (
            timestamp,
            WRITER_ENGINE,
        )
    ).fetchone()[0]

    collisions = rows - symbols

    print("Timestamp          :", timestamp)
    print("Rows               :", rows)
    print("Distinct CMC IDs   :", cmc)
    print("Distinct Symbols   :", symbols)
    print("Source CMC IDs     :", source_cmc)
    print("Engine CMC IDs     :", engine_cmc)
    print("Collision Rows     :", collisions)

    valid = (
        rows == EXPECTED_ROWS
        and cmc == EXPECTED_CMC_IDS
        and symbols == EXPECTED_SYMBOLS
        and source_cmc == EXPECTED_CMC_IDS
        and engine_cmc == EXPECTED_CMC_IDS
        and collisions == EXPECTED_COLLISIONS
    )

    if valid:
        pass_check(
            "Latest v0.4 snapshot fingerprint"
        )
    else:
        fail_check(
            "Latest v0.4 snapshot fingerprint"
        )

    return valid


# =============================================================================
# LEGACY REPORT
# =============================================================================

def audit_legacy_history(conn, baseline):

    section("LEGACY HISTORY SEPARATE REPORT")

    total_legacy = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp < ?
        """,
        (baseline,)
    ).fetchone()[0]

    legacy_snapshots = conn.execute(
        """
        SELECT COUNT(DISTINCT timestamp)
        FROM market_history
        WHERE timestamp < ?
        """,
        (baseline,)
    ).fetchone()[0]

    legacy_null_source = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp < ?
          AND source IS NULL
        """,
        (baseline,)
    ).fetchone()[0]

    legacy_null_engine = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp < ?
          AND engine_version IS NULL
        """,
        (baseline,)
    ).fetchone()[0]

    legacy_null_source_timestamp = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp < ?
          AND source_timestamp IS NULL
        """,
        (baseline,)
    ).fetchone()[0]

    legacy_null_created_at = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE timestamp < ?
          AND created_at IS NULL
        """,
        (baseline,)
    ).fetchone()[0]

    print("Legacy Baseline    :", baseline)
    print("Legacy Rows        :", total_legacy)
    print("Legacy Snapshots   :", legacy_snapshots)
    print("NULL Source        :", legacy_null_source)
    print("NULL Engine        :", legacy_null_engine)
    print(
        "NULL Source TS     :",
        legacy_null_source_timestamp
    )
    print(
        "NULL Created At    :",
        legacy_null_created_at
    )

    print()
    print(
        "LEGACY STATUS      : REPORTED SEPARATELY"
    )
    print(
        "V0.4 DECISION      : LEGACY DOES NOT AFFECT V0.4 RESULT"
    )


# =============================================================================
# WRITE SAFETY
# =============================================================================

def audit_write_safety(conn):

    section("READ-ONLY SAFETY AUDIT")

    journal_mode = conn.execute(
        "PRAGMA journal_mode"
    ).fetchone()[0]

    print(
        "Journal Mode       :",
        journal_mode
    )

    pass_check(
        "Database opened in read-only mode"
    )

    return True


# =============================================================================
# MAIN
# =============================================================================

def main():

    section(
        "ARUNDA MARKET HISTORY ACCUMULATION INTEGRITY AUDIT v0.2"
    )

    print("Mode                : READ ONLY")
    print("Database            :", DB_PATH)
    print("Writer Engine       :", WRITER_ENGINE)
    print("Source              :", SOURCE_NAME)

    print("Production Contract : V0.4 BASELINE -> FORWARD")
    print("Expected Rows       :", EXPECTED_ROWS)
    print("Expected CMC IDs    :", EXPECTED_CMC_IDS)
    print("Expected Symbols    :", EXPECTED_SYMBOLS)
    print("Expected Collisions :", EXPECTED_COLLISIONS)
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
    print("WRITE OPERATIONS    : NONE")
    print("INSERT              : NONE")
    print("UPDATE              : NONE")
    print("DELETE              : NONE")
    print("ALTER               : NONE")
    print("CREATE              : NONE")
    print("DROP                : NONE")

    section(
        "AUDIT START"
    )

    print(
        "Audit Started       :",
        utc_now()
    )

    conn = connect_read_only()

    try:

        print(
            "Database            : CONNECTED READ-ONLY"
        )

        audit_write_safety(
            conn
        )

        history_ok = audit_history_schema(
            conn
        )

        universe_ok = audit_universe_schema(
            conn
        )

        if not history_ok or not universe_ok:

            section(
                "ACCUMULATION INTEGRITY AUDIT RESULT"
            )

            print("RESULT             : FAIL")
            print(
                "STATUS             : SCHEMA CONTRACT NOT VERIFIED"
            )

            return

        audit_global_history(
            conn
        )

        baseline = audit_v04_baseline(
            conn
        )

        if baseline is None:

            section(
                "ACCUMULATION INTEGRITY AUDIT RESULT"
            )

            print("RESULT             : FAIL")
            print(
                "STATUS             : V0.4 PRODUCTION BASELINE NOT FOUND"
            )

            return

        structural = audit_v04_snapshots(
            conn,
            baseline
        )

        identity_ok = audit_v04_identity(
            conn,
            baseline
        )

        price_ok = audit_v04_price(
            conn,
            baseline
        )

        provenance_ok = audit_v04_provenance(
            conn,
            baseline
        )

        timestamp_ok = audit_v04_timestamp_metadata(
            conn,
            baseline
        )

        temporal = audit_v04_temporal_sequence(
            conn,
            baseline
        )

        recent_ok = audit_recent_v04_snapshots(
            conn,
            baseline
        )

        growth_ok = audit_recent_growth(
            conn,
            baseline
        )

        latest_ok = latest_v04_fingerprint(
            conn,
            baseline
        )

        audit_legacy_history(
            conn,
            baseline
        )

        section(
            "ACCUMULATION INTEGRITY AUDIT RESULT"
        )

        checks = 0
        passed = 0
        failed = 0
        warnings = 0

        # Structural checks
        structural_checks = [
            len(structural["invalid_rows"]) == 0,
            len(structural["invalid_cmc"]) == 0,
            len(structural["invalid_symbols"]) == 0,
            len(structural["invalid_collisions"]) == 0,
        ]

        checks += len(structural_checks)
        passed += sum(structural_checks)
        failed += (
            len(structural_checks)
            - sum(structural_checks)
        )

        # Core checks
        core_checks = [
            identity_ok,
            price_ok,
            provenance_ok,
            timestamp_ok,
            temporal["chronological"],
            recent_ok,
            growth_ok,
            latest_ok,
        ]

        checks += len(core_checks)
        passed += sum(core_checks)
        failed += (
            len(core_checks)
            - sum(core_checks)
        )

        warnings += len(
            temporal["interval_anomalies"]
        ) > 0

        print("Baseline            :", baseline)
        print("Checks              :", checks)
        print("Passed              :", passed)
        print("Failed              :", failed)
        print(
            "Warnings            :",
            int(warnings)
        )

        print()

        if failed == 0:

            print(
                "RESULT              : PASS"
            )

            if warnings == 0:

                print(
                    "STATUS              : "
                    "V0.4 PRODUCTION ACCUMULATION INTEGRITY VERIFIED"
                )

            else:

                print(
                    "STATUS              : "
                    "V0.4 PRODUCTION ACCUMULATION VERIFIED "
                    "WITH TEMPORAL GAP WARNINGS"
                )

        else:

            print(
                "RESULT              : FAIL"
            )

            print(
                "STATUS              : "
                "V0.4 PRODUCTION ACCUMULATION INTEGRITY NOT VERIFIED"
            )

        print()
        print(
            "LEGACY HISTORY      : "
            "REPORTED SEPARATELY / NOT USED FOR V0.4 PASS-FAIL"
        )

        print()
        print(
            "WRITE OPERATIONS    : NONE"
        )

    finally:

        conn.close()

        print()
        print(
            "Database            : CONNECTION CLOSED"
        )
        print(
            "Audit Mode          : READ ONLY"
        )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()

