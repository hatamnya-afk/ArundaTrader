# =============================================================================
# ARUNDA TRADER — HISTORY LINEAGE ORIGIN AUDIT v0.1
# =============================================================================
#
# PURPOSE:
#   Discover the origin/pattern of contaminated market_history records.
#
# MODE:
#   READ ONLY
#
# GUARANTEES:
#   - NO INSERT
#   - NO UPDATE
#   - NO DELETE
#   - NO CREATE
#   - NO ALTER
#   - NO VACUUM
#   - NO PRAGMA that modifies the database
#   - SQLite opened using immutable READ-ONLY URI
#
# DATABASE:
#   C:\Users\ASUS\ArundaTrader\arunda.db
#
# =============================================================================

import sqlite3
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime


# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

TABLE_NAME = "market_history"

NULL_TOKEN = "<NULL>"

CONTAMINATED_ASSETS = {
    "AI",
    "AVA",
    "BOB",
    "EDGE",
    "FRAX",
    "GUSD",
    "LIGHT",
    "LUSD",
    "U",
    "UP",
    "USDF",
    "VELO",
    "XAI",
}

DISPLAY_LIMIT = 30


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def line(char="=", width=100):
    print(char * width)


def section(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


def value_or_null(value):
    if value is None:
        return NULL_TOKEN
    return str(value)


def parse_timestamp(value):
    if not value:
        return None

    try:
        text = str(value)

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        return datetime.fromisoformat(text)
    except Exception:
        return None


def format_seconds(seconds):
    if seconds is None:
        return "N/A"

    seconds = float(seconds)

    if seconds < 60:
        return f"{seconds:.2f}s"

    minutes = seconds / 60

    if minutes < 60:
        return f"{minutes:.2f}m"

    hours = minutes / 60

    if hours < 24:
        return f"{hours:.2f}h"

    days = hours / 24
    return f"{days:.2f}d"


# =============================================================================
# READ ONLY CONNECTION
# =============================================================================

def get_connection():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found:\n{DB_PATH}"
        )

    # SQLite immutable URI.
    # This is stronger than relying on a non-standard read_only argument.
    uri = f"file:{DB_PATH}?mode=ro&immutable=1"

    conn = sqlite3.connect(
        uri,
        uri=True,
        timeout=5,
    )

    conn.row_factory = sqlite3.Row

    return conn


# =============================================================================
# DATABASE VALIDATION
# =============================================================================

def validate_table(conn):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (TABLE_NAME,),
    ).fetchone()

    if row is None:
        raise RuntimeError(
            f"Required table '{TABLE_NAME}' does not exist."
        )


def get_columns(conn):
    rows = conn.execute(
        f"PRAGMA table_info({TABLE_NAME})"
    ).fetchall()

    return [row["name"] for row in rows]


# =============================================================================
# BASIC OVERVIEW
# =============================================================================

def print_database_overview(conn):
    section("DATABASE / MARKET HISTORY OVERVIEW")

    total = conn.execute(
        f"SELECT COUNT(*) FROM {TABLE_NAME}"
    ).fetchone()[0]

    assets = conn.execute(
        f"""
        SELECT COUNT(DISTINCT symbol)
        FROM {TABLE_NAME}
        """
    ).fetchone()[0]

    first_ts = conn.execute(
        f"""
        SELECT MIN(timestamp)
        FROM {TABLE_NAME}
        """
    ).fetchone()[0]

    last_ts = conn.execute(
        f"""
        SELECT MAX(timestamp)
        FROM {TABLE_NAME}
        """
    ).fetchone()[0]

    print(f"Total History Rows : {total:,}")
    print(f"Historical Assets  : {assets:,}")
    print(f"First Timestamp    : {value_or_null(first_ts)}")
    print(f"Last Timestamp     : {value_or_null(last_ts)}")


# =============================================================================
# GLOBAL LINEAGE DISTRIBUTION
# =============================================================================

def print_global_lineage_distribution(conn):
    section("GLOBAL LINEAGE DISTRIBUTION")

    rows = conn.execute(
        f"""
        SELECT
            source,
            engine_version,
            COUNT(*) AS count
        FROM {TABLE_NAME}
        GROUP BY source, engine_version
        ORDER BY count DESC
        """
    ).fetchall()

    print(
        f"{'SOURCE':<32}"
        f"{'ENGINE':<40}"
        f"{'ROWS':>12}"
    )
    print("-" * 86)

    for row in rows:
        source = value_or_null(row["source"])
        engine = value_or_null(row["engine_version"])

        print(
            f"{source:<32}"
            f"{engine:<40}"
            f"{row['count']:>12,}"
        )


# =============================================================================
# NULL LINEAGE TEMPORAL ORIGIN
# =============================================================================

def print_null_lineage_origin(conn):
    section("NULL-LINEAGE TEMPORAL ORIGIN")

    row = conn.execute(
        f"""
        SELECT
            COUNT(*) AS total,
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp
        FROM {TABLE_NAME}
        WHERE source IS NULL
           OR engine_version IS NULL
        """
    ).fetchone()

    print(
        f"NULL-lineage rows : {row['total']:,}"
    )
    print(
        f"First timestamp   : {value_or_null(row['first_timestamp'])}"
    )
    print(
        f"Last timestamp    : {value_or_null(row['last_timestamp'])}"
    )

    # Count by date.
    rows = conn.execute(
        f"""
        SELECT
            substr(timestamp, 1, 10) AS day,
            COUNT(*) AS count
        FROM {TABLE_NAME}
        WHERE source IS NULL
           OR engine_version IS NULL
        GROUP BY day
        ORDER BY day
        """
    ).fetchall()

    print()
    print("NULL-lineage rows by date:")

    for row in rows:
        print(
            f"  {value_or_null(row['day']):<15}"
            f"{row['count']:>12,}"
        )


# =============================================================================
# LINEAGE FIRST / LAST PER GROUP
# =============================================================================

def print_lineage_windows(conn):
    section("LINEAGE WINDOWS")

    rows = conn.execute(
        f"""
        SELECT
            source,
            engine_version,
            COUNT(*) AS count,
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp
        FROM {TABLE_NAME}
        GROUP BY source, engine_version
        ORDER BY first_timestamp
        """
    ).fetchall()

    print(
        f"{'SOURCE':<28}"
        f"{'ENGINE':<36}"
        f"{'ROWS':>10}"
        f"{'FIRST':<30}"
        f"{'LAST':<30}"
    )
    print("-" * 140)

    for row in rows:
        source = value_or_null(row["source"])
        engine = value_or_null(row["engine_version"])

        print(
            f"{source:<28}"
            f"{engine:<36}"
            f"{row['count']:>10,}"
            f"{value_or_null(row['first_timestamp']):<30}"
            f"{value_or_null(row['last_timestamp']):<30}"
        )


# =============================================================================
# ASSET LINEAGE SUMMARY
# =============================================================================

def get_asset_lineage_summary(conn, symbol):
    rows = conn.execute(
        f"""
        SELECT
            source,
            engine_version,
            COUNT(*) AS count,
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp
        FROM {TABLE_NAME}
        WHERE symbol = ?
        GROUP BY source, engine_version
        ORDER BY count DESC
        """,
        (symbol,),
    ).fetchall()

    return rows


def print_contaminated_assets():
    section("TARGET CONTAMINATED ASSETS")

    print(
        f"{'ASSET':<12}"
        f"{'LINEAGE GROUPS':>16}"
        f"{'TOTAL ROWS':>14}"
        f"{'NULL ROWS':>14}"
        f"{'IDENTIFIED':>14}"
    )
    print("-" * 72)

    # This function intentionally only prints the asset list.
    # Actual values are produced by print_asset_lineage_details().
    for symbol in sorted(CONTAMINATED_ASSETS):
        print(f"{symbol:<12}")


# =============================================================================
# CONTAMINATED ASSET LINEAGE DETAILS
# =============================================================================

def print_asset_lineage_details(conn):
    section("CONTAMINATED ASSET LINEAGE DETAILS")

    for symbol in sorted(CONTAMINATED_ASSETS):

        rows = get_asset_lineage_summary(conn, symbol)

        total = sum(row["count"] for row in rows)

        null_rows = sum(
            row["count"]
            for row in rows
            if row["source"] is None
            or row["engine_version"] is None
        )

        identified_rows = total - null_rows

        print()
        print(f"ASSET : {symbol}")
        print(
            f"  Total rows       : {total:,}"
        )
        print(
            f"  NULL lineage     : {null_rows:,}"
        )
        print(
            f"  Identified       : {identified_rows:,}"
        )

        for row in rows:
            print(
                f"    source={value_or_null(row['source'])}"
                f" | engine={value_or_null(row['engine_version'])}"
                f" | rows={row['count']:,}"
                f" | first={value_or_null(row['first_timestamp'])}"
                f" | last={value_or_null(row['last_timestamp'])}"
            )


# =============================================================================
# SOURCE TIMESTAMP AUDIT
# =============================================================================

def print_source_timestamp_audit(conn):
    section("SOURCE TIMESTAMP AUDIT")

    rows = conn.execute(
        f"""
        SELECT
            CASE
                WHEN source_timestamp IS NULL
                    THEN 'NULL'
                ELSE 'IDENTIFIED'
            END AS status,
            COUNT(*) AS count
        FROM {TABLE_NAME}
        GROUP BY status
        ORDER BY count DESC
        """
    ).fetchall()

    for row in rows:
        print(
            f"{row['status']:<15}"
            f"{row['count']:>15,}"
        )

    print()

    # By lineage.
    rows = conn.execute(
        f"""
        SELECT
            source,
            engine_version,
            COUNT(*) AS total,
            SUM(
                CASE
                    WHEN source_timestamp IS NULL THEN 1
                    ELSE 0
                END
            ) AS null_source_timestamp
        FROM {TABLE_NAME}
        GROUP BY source, engine_version
        ORDER BY total DESC
        """
    ).fetchall()

    print(
        f"{'SOURCE':<28}"
        f"{'ENGINE':<36}"
        f"{'ROWS':>12}"
        f"{'NULL SOURCE TS':>18}"
    )
    print("-" * 96)

    for row in rows:
        print(
            f"{value_or_null(row['source']):<28}"
            f"{value_or_null(row['engine_version']):<36}"
            f"{row['total']:>12,}"
            f"{row['null_source_timestamp']:>18,}"
        )


# =============================================================================
# CREATED_AT AUDIT
# =============================================================================

def print_created_at_audit(conn):
    section("CREATED_AT AUDIT")

    rows = conn.execute(
        f"""
        SELECT
            source,
            engine_version,
            COUNT(*) AS count,
            MIN(created_at) AS first_created,
            MAX(created_at) AS last_created
        FROM {TABLE_NAME}
        GROUP BY source, engine_version
        ORDER BY first_created
        """
    ).fetchall()

    print(
        f"{'SOURCE':<28}"
        f"{'ENGINE':<36}"
        f"{'ROWS':>12}"
        f"{'FIRST CREATED':<30}"
        f"{'LAST CREATED':<30}"
    )
    print("-" * 140)

    for row in rows:
        print(
            f"{value_or_null(row['source']):<28}"
            f"{value_or_null(row['engine_version']):<36}"
            f"{row['count']:>12,}"
            f"{value_or_null(row['first_created']):<30}"
            f"{value_or_null(row['last_created']):<30}"
        )


# =============================================================================
# TIMESTAMP INTERVAL ANALYSIS
# =============================================================================

def calculate_intervals(conn, symbol, lineage_filter):
    if lineage_filter == "NULL":
        query = f"""
            SELECT timestamp
            FROM {TABLE_NAME}
            WHERE symbol = ?
              AND (source IS NULL OR engine_version IS NULL)
            ORDER BY timestamp
        """
        rows = conn.execute(query, (symbol,)).fetchall()

    elif lineage_filter == "IDENTIFIED":
        query = f"""
            SELECT timestamp
            FROM {TABLE_NAME}
            WHERE symbol = ?
              AND source IS NOT NULL
              AND engine_version IS NOT NULL
            ORDER BY timestamp
        """
        rows = conn.execute(query, (symbol,)).fetchall()

    else:
        raise ValueError("Unknown lineage filter.")

    timestamps = [
        parse_timestamp(row["timestamp"])
        for row in rows
    ]

    timestamps = [ts for ts in timestamps if ts is not None]

    intervals = []

    for previous, current in zip(timestamps, timestamps[1:]):
        delta = (current - previous).total_seconds()

        if delta >= 0:
            intervals.append(delta)

    return intervals


def print_interval_summary(conn, symbol, lineage_filter):
    intervals = calculate_intervals(
        conn,
        symbol,
        lineage_filter,
    )

    if not intervals:
        return None

    counter = Counter(
        round(value, 3)
        for value in intervals
    )

    most_common = counter.most_common(5)

    return {
        "count": len(intervals),
        "min": min(intervals),
        "max": max(intervals),
        "avg": sum(intervals) / len(intervals),
        "most_common": most_common,
    }


def print_contaminated_asset_intervals(conn):
    section("TIMESTAMP INTERVAL ANALYSIS — CONTAMINATED ASSETS")

    print(
        f"{'ASSET':<10}"
        f"{'LINEAGE':<14}"
        f"{'N':>10}"
        f"{'MIN':>12}"
        f"{'AVG':>12}"
        f"{'MAX':>12}"
        f"{'COMMON INTERVALS'}"
    )
    print("-" * 120)

    for symbol in sorted(CONTAMINATED_ASSETS):

        for lineage in ("NULL", "IDENTIFIED"):

            summary = print_interval_summary(
                conn,
                symbol,
                lineage,
            )

            if summary is None:
                continue

            common = ", ".join(
                f"{value}s x{count}"
                for value, count
                in summary["most_common"]
            )

            print(
                f"{symbol:<10}"
                f"{lineage:<14}"
                f"{summary['count']:>10,}"
                f"{format_seconds(summary['min']):>12}"
                f"{format_seconds(summary['avg']):>12}"
                f"{format_seconds(summary['max']):>12}"
                f"  {common}"
            )


# =============================================================================
# PRICE STREAM ANALYSIS
# =============================================================================

def get_price_statistics(conn, symbol, lineage_filter):
    if lineage_filter == "NULL":
        query = f"""
            SELECT
                MIN(price) AS min_price,
                MAX(price) AS max_price,
                AVG(price) AS avg_price,
                COUNT(*) AS count
            FROM {TABLE_NAME}
            WHERE symbol = ?
              AND (source IS NULL OR engine_version IS NULL)
        """
    else:
        query = f"""
            SELECT
                MIN(price) AS min_price,
                MAX(price) AS max_price,
                AVG(price) AS avg_price,
                COUNT(*) AS count
            FROM {TABLE_NAME}
            WHERE symbol = ?
              AND source IS NOT NULL
              AND engine_version IS NOT NULL
        """

    return conn.execute(query, (symbol,)).fetchone()


def print_price_stream_analysis(conn):
    section("PRICE STREAM ANALYSIS — CONTAMINATED ASSETS")

    print(
        f"{'ASSET':<10}"
        f"{'LINEAGE':<14}"
        f"{'ROWS':>12}"
        f"{'MIN PRICE':>20}"
        f"{'MAX PRICE':>20}"
        f"{'AVG PRICE':>20}"
    )
    print("-" * 100)

    for symbol in sorted(CONTAMINATED_ASSETS):

        for lineage in ("NULL", "IDENTIFIED"):

            row = get_price_statistics(
                conn,
                symbol,
                lineage,
            )

            if row["count"] == 0:
                continue

            print(
                f"{symbol:<10}"
                f"{lineage:<14}"
                f"{row['count']:>12,}"
                f"{value_or_null(row['min_price']):>20}"
                f"{value_or_null(row['max_price']):>20}"
                f"{value_or_null(row['avg_price']):>20}"
            )


# =============================================================================
# DUPLICATE OVERLAP ANALYSIS
# =============================================================================

def print_duplicate_overlap_analysis(conn):
    section("NULL-LINEAGE OVERLAP ANALYSIS")

    # Find timestamps where the same symbol exists multiple times.
    # We intentionally do not modify anything.
    rows = conn.execute(
        f"""
        SELECT
            symbol,
            timestamp,
            COUNT(*) AS count
        FROM {TABLE_NAME}
        WHERE source IS NULL
          AND engine_version IS NULL
        GROUP BY symbol, timestamp
        HAVING COUNT(*) > 1
        ORDER BY count DESC, symbol, timestamp
        LIMIT 50
        """
    ).fetchall()

    if not rows:
        print("No NULL-lineage duplicate timestamp groups found.")
        return

    print(
        f"{'SYMBOL':<12}"
        f"{'TIMESTAMP':<35}"
        f"{'ROWS':>10}"
    )
    print("-" * 60)

    for row in rows:
        print(
            f"{row['symbol']:<12}"
            f"{row['timestamp']:<35}"
            f"{row['count']:>10}"
        )


# =============================================================================
# ALL ASSET LINEAGE PATTERN
# =============================================================================

def print_lineage_asset_coverage(conn):
    section("LINEAGE ASSET COVERAGE")

    rows = conn.execute(
        f"""
        SELECT
            CASE
                WHEN source IS NULL
                  OR engine_version IS NULL
                    THEN 'NULL_LINEAGE'
                ELSE 'IDENTIFIED_LINEAGE'
            END AS lineage_status,
            COUNT(DISTINCT symbol) AS assets,
            COUNT(*) AS rows
        FROM {TABLE_NAME}
        GROUP BY lineage_status
        ORDER BY lineage_status
        """
    ).fetchall()

    print(
        f"{'LINEAGE STATUS':<25}"
        f"{'ASSETS':>12}"
        f"{'ROWS':>15}"
    )
    print("-" * 55)

    for row in rows:
        print(
            f"{row['lineage_status']:<25}"
            f"{row['assets']:>12,}"
            f"{row['rows']:>15,}"
        )


# =============================================================================
# POTENTIAL ROOT CAUSE SUMMARY
# =============================================================================

def print_root_cause_indicators(conn):
    section("ROOT CAUSE INDICATORS")

    total = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM {TABLE_NAME}
        """
    ).fetchone()[0]

    null_lineage = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM {TABLE_NAME}
        WHERE source IS NULL
           OR engine_version IS NULL
        """
    ).fetchone()[0]

    identified = total - null_lineage

    contaminated_count = conn.execute(
        f"""
        SELECT COUNT(DISTINCT symbol)
        FROM {TABLE_NAME}
        WHERE symbol IN ({",".join("?" for _ in CONTAMINATED_ASSETS)})
          AND source IS NULL
          AND engine_version IS NULL
        """,
        tuple(CONTAMINATED_ASSETS),
    ).fetchone()[0]

    print(
        f"Total rows                       : {total:,}"
    )
    print(
        f"NULL-lineage rows                : {null_lineage:,}"
    )
    print(
        f"Identified-lineage rows          : {identified:,}"
    )
    print(
        f"Target contaminated assets       : {contaminated_count:,}"
    )

    if total:
        ratio = null_lineage / total * 100
        print(
            f"NULL-lineage ratio               : {ratio:.2f}%"
        )

    print()
    print("Interpretation:")
    print(
        "  This audit does NOT decide which records are valid."
    )
    print(
        "  It only identifies lineage/origin patterns."
    )
    print(
        "  No contaminated record is deleted or rewritten."
    )


# =============================================================================
# MAIN
# =============================================================================

def main():

    line()
    print("ARUNDA TRADER — HISTORY LINEAGE ORIGIN AUDIT v0.1")
    line()

    print("MODE                 : READ ONLY")
    print(f"DATABASE             : {DB_PATH}")
    print("WRITE OPERATIONS     : NONE")
    print("SCHEMA CHANGES       : NONE")
    print("DELETE OPERATIONS    : NONE")
    print("INSERT OPERATIONS    : NONE")
    print("UPDATE OPERATIONS    : NONE")
    print("")

    conn = None

    try:

        conn = get_connection()

        print("READ-ONLY CONNECTION  : ESTABLISHED")

        validate_table(conn)

        columns = get_columns(conn)

        required_columns = {
            "timestamp",
            "symbol",
            "price",
            "source",
            "source_timestamp",
            "engine_version",
            "created_at",
        }

        missing = required_columns - set(columns)

        if missing:
            raise RuntimeError(
                "Required columns missing: "
                + ", ".join(sorted(missing))
            )

        print(
            f"TABLE                 : {TABLE_NAME}"
        )

        print_database_overview(conn)

        print_global_lineage_distribution(conn)

        print_null_lineage_origin(conn)

        print_lineage_windows(conn)

        print_lineage_asset_coverage(conn)

        print_contaminated_assets()

        print_asset_lineage_details(conn)

        print_source_timestamp_audit(conn)

        print_created_at_audit(conn)

        print_contaminated_asset_intervals(conn)

        print_price_stream_analysis(conn)

        print_duplicate_overlap_analysis(conn)

        print_root_cause_indicators(conn)

        line()

        print("ARUNDA HISTORY LINEAGE ORIGIN AUDIT COMPLETE")

        print()
        print("Database was opened in READ-ONLY mode.")
        print(
            "No INSERT / UPDATE / DELETE / ALTER / CREATE operation was executed."
        )

    except Exception as exc:

        print()
        line("=")
        print("AUDIT FAILED")
        line("=")

        print(type(exc).__name__)
        print(str(exc))

        sys.exit(1)

    finally:

        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()