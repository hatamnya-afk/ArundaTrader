# =============================================================================
# ARUNDA TRADER — MARKET HISTORY DUPLICATE AUDIT v0.1
# =============================================================================
#
# Purpose:
#   Read-only forensic audit of duplicate records in market_history.
#
# IMPORTANT:
#   - READ ONLY
#   - NO INSERT
#   - NO UPDATE
#   - NO DELETE
#   - NO CREATE
#   - NO ALTER
#   - NO schema modification
#
# Database:
#   C:\Users\ASUS\ArundaTrader\arunda.db
#
# =============================================================================

import sqlite3
from pathlib import Path
from collections import Counter


# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

TABLE_NAME = "market_history"

# Number of duplicate groups to show in detail
DETAIL_LIMIT = 50

# Number of rows from each duplicate group to inspect
GROUP_SAMPLE_LIMIT = 10


# =============================================================================
# READ-ONLY DATABASE CONNECTION
# =============================================================================

def get_connection():
    """
    Open SQLite database in STRICT READ-ONLY mode.

    IMPORTANT:
    sqlite3.connect() does NOT accept read_only=...
    SQLite read-only mode is enabled through URI:
        ?mode=ro
    """

    db_path = DB_PATH.resolve()

    if not db_path.exists():
        raise FileNotFoundError(
            f"Database not found:\n{db_path}"
        )

    uri = f"file:{db_path.as_posix()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=30,
    )


# =============================================================================
# HELPERS
# =============================================================================

def print_header(title):
    print()
    print("=" * 100)
    print(title)
    print("=" * 100)


def print_section(title):
    print()
    print("-" * 100)
    print(title)
    print("-" * 100)


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
    rows = conn.execute(
        f'PRAGMA table_info("{table_name}")'
    ).fetchall()

    return [row[1] for row in rows]


def format_value(value):
    if value is None:
        return "<NULL>"

    return str(value)


# =============================================================================
# DATABASE OVERVIEW
# =============================================================================

def audit_database_overview(conn):
    print_section("DATABASE / TABLE OVERVIEW")

    row = conn.execute(
        f'SELECT COUNT(*) FROM "{TABLE_NAME}"'
    ).fetchone()

    total_rows = row[0]

    print(f"Table                : {TABLE_NAME}")
    print(f"Total rows           : {total_rows:,}")

    columns = get_columns(conn, TABLE_NAME)

    print()
    print("Columns:")
    for column in columns:
        print(f"  - {column}")

    return total_rows, columns


# =============================================================================
# TIMESTAMP + SYMBOL DUPLICATE AUDIT
# =============================================================================

def audit_duplicate_groups(conn):
    print_section("DUPLICATE GROUP AUDIT")

    query = f"""
        SELECT
            symbol,
            timestamp,
            COUNT(*) AS duplicate_count
        FROM "{TABLE_NAME}"
        GROUP BY symbol, timestamp
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC, symbol, timestamp
    """

    rows = conn.execute(query).fetchall()

    duplicate_groups = len(rows)

    duplicate_rows = sum(
        count - 1
        for _, _, count in rows
    )

    total_rows_in_duplicate_groups = sum(
        count
        for _, _, count in rows
    )

    print(f"Duplicate Groups                 : {duplicate_groups:,}")
    print(f"Extra Duplicate Rows             : {duplicate_rows:,}")
    print(
        f"Rows Belonging To Duplicate Groups: "
        f"{total_rows_in_duplicate_groups:,}"
    )

    if duplicate_groups == 0:
        print()
        print("RESULT: No duplicate (symbol + timestamp) groups found.")
        return rows

    print()
    print("Worst duplicate groups:")

    for symbol, timestamp, count in rows[:DETAIL_LIMIT]:
        print(
            f"  {format_value(symbol):<15} "
            f"{format_value(timestamp):<32} "
            f"x{count}"
        )

    if duplicate_groups > DETAIL_LIMIT:
        print()
        print(
            f"... {duplicate_groups - DETAIL_LIMIT:,} "
            f"additional duplicate groups not displayed."
        )

    return rows


# =============================================================================
# DUPLICATE DISTRIBUTION BY ASSET
# =============================================================================

def audit_duplicate_distribution(conn):
    print_section("DUPLICATE DISTRIBUTION BY ASSET")

    query = f"""
        SELECT
            symbol,
            COUNT(*) AS duplicate_groups,
            SUM(group_count - 1) AS extra_rows
        FROM (
            SELECT
                symbol,
                timestamp,
                COUNT(*) AS group_count
            FROM "{TABLE_NAME}"
            GROUP BY symbol, timestamp
            HAVING COUNT(*) > 1
        )
        GROUP BY symbol
        ORDER BY extra_rows DESC, symbol
    """

    rows = conn.execute(query).fetchall()

    print(f"Assets with duplicates : {len(rows):,}")

    if not rows:
        print("No assets contain duplicate timestamp groups.")
        return rows

    print()
    print(
        f"{'ASSET':<15}"
        f"{'DUP GROUPS':>15}"
        f"{'EXTRA ROWS':>15}"
    )
    print("-" * 45)

    for symbol, groups, extra_rows in rows[:100]:
        print(
            f"{format_value(symbol):<15}"
            f"{groups:>15,}"
            f"{extra_rows:>15,}"
        )

    if len(rows) > 100:
        print()
        print(
            f"... {len(rows) - 100:,} additional assets not displayed."
        )

    return rows


# =============================================================================
# DUPLICATE PRICE CONSISTENCY
# =============================================================================

def audit_price_consistency(conn):
    print_section("DUPLICATE PRICE CONSISTENCY AUDIT")

    columns = get_columns(conn, TABLE_NAME)

    if "price" not in columns:
        print("PRICE column not available.")
        return

    query = f"""
        SELECT
            symbol,
            timestamp,
            COUNT(*) AS row_count,
            COUNT(DISTINCT price) AS distinct_prices
        FROM "{TABLE_NAME}"
        GROUP BY symbol, timestamp
        HAVING COUNT(*) > 1
    """

    rows = conn.execute(query).fetchall()

    if not rows:
        print("No duplicate groups to inspect.")
        return

    identical_price_groups = 0
    conflicting_price_groups = 0

    for symbol, timestamp, row_count, distinct_prices in rows:

        if distinct_prices <= 1:
            identical_price_groups += 1
        else:
            conflicting_price_groups += 1

    total = len(rows)

    print(
        f"Duplicate groups                     : {total:,}"
    )
    print(
        f"Same price within duplicate group    : "
        f"{identical_price_groups:,}"
    )
    print(
        f"Different prices within duplicate group: "
        f"{conflicting_price_groups:,}"
    )

    if total > 0:
        print(
            f"Identical price ratio                : "
            f"{identical_price_groups / total * 100:.2f}%"
        )
        print(
            f"Conflicting price ratio              : "
            f"{conflicting_price_groups / total * 100:.2f}%"
        )

    if conflicting_price_groups > 0:

        print()
        print("Examples of conflicting duplicate prices:")

        shown = 0

        for symbol, timestamp, _, distinct_prices in rows:

            if distinct_prices <= 1:
                continue

            detail_query = f"""
                SELECT
                    price,
                    source,
                    engine_version
                FROM "{TABLE_NAME}"
                WHERE symbol = ?
                  AND timestamp = ?
                LIMIT ?
            """

            detail_rows = conn.execute(
                detail_query,
                (symbol, timestamp, GROUP_SAMPLE_LIMIT),
            ).fetchall()

            print()
            print(
                f"  {symbol} | {timestamp}"
            )

            for price, source, engine in detail_rows:
                print(
                    f"      price={format_value(price)} "
                    f"source={format_value(source)} "
                    f"engine={format_value(engine)}"
                )

            shown += 1

            if shown >= DETAIL_LIMIT:
                break


# =============================================================================
# DUPLICATE LINEAGE CONSISTENCY
# =============================================================================

def audit_lineage_consistency(conn):
    print_section("DUPLICATE LINEAGE CONSISTENCY AUDIT")

    columns = get_columns(conn, TABLE_NAME)

    has_source = "source" in columns
    has_engine = "engine_version" in columns

    if not has_source and not has_engine:
        print("No source / engine_version columns available.")
        return

    query = f"""
        SELECT
            symbol,
            timestamp,
            COUNT(*) AS row_count,
            COUNT(DISTINCT source) AS distinct_sources,
            COUNT(DISTINCT engine_version) AS distinct_engines
        FROM "{TABLE_NAME}"
        GROUP BY symbol, timestamp
        HAVING COUNT(*) > 1
    """

    rows = conn.execute(query).fetchall()

    if not rows:
        print("No duplicate groups to inspect.")
        return

    same_lineage = 0
    mixed_lineage = 0

    for (
        symbol,
        timestamp,
        row_count,
        distinct_sources,
        distinct_engines,
    ) in rows:

        source_count = distinct_sources
        engine_count = distinct_engines

        if source_count <= 1 and engine_count <= 1:
            same_lineage += 1
        else:
            mixed_lineage += 1

    print(
        f"Duplicate groups                  : {len(rows):,}"
    )
    print(
        f"Same lineage                      : {same_lineage:,}"
    )
    print(
        f"Mixed lineage                     : {mixed_lineage:,}"
    )

    if rows:
        print()
        print("Examples of mixed-lineage groups:")

        shown = 0

        for (
            symbol,
            timestamp,
            row_count,
            distinct_sources,
            distinct_engines,
        ) in rows:

            if distinct_sources <= 1 and distinct_engines <= 1:
                continue

            detail_query = f"""
                SELECT
                    source,
                    engine_version,
                    price
                FROM "{TABLE_NAME}"
                WHERE symbol = ?
                  AND timestamp = ?
                LIMIT ?
            """

            detail_rows = conn.execute(
                detail_query,
                (symbol, timestamp, GROUP_SAMPLE_LIMIT),
            ).fetchall()

            print()
            print(
                f"  {symbol} | {timestamp} | rows={row_count}"
            )

            for source, engine, price in detail_rows:
                print(
                    f"      source={format_value(source):<25} "
                    f"engine={format_value(engine):<35} "
                    f"price={format_value(price)}"
                )

            shown += 1

            if shown >= DETAIL_LIMIT:
                break


# =============================================================================
# NULL / NON-NULL LINEAGE INSIDE DUPLICATES
# =============================================================================

def audit_null_lineage_duplicates(conn):
    print_section("DUPLICATE NULL-LINEAGE AUDIT")

    columns = get_columns(conn, TABLE_NAME)

    if "source" not in columns or "engine_version" not in columns:
        print("Required lineage columns are unavailable.")
        return

    query = f"""
        SELECT
            symbol,
            timestamp,
            COUNT(*) AS row_count,
            SUM(
                CASE
                    WHEN source IS NULL
                     AND engine_version IS NULL
                    THEN 1
                    ELSE 0
                END
            ) AS null_lineage_rows,
            SUM(
                CASE
                    WHEN source IS NOT NULL
                     OR engine_version IS NOT NULL
                    THEN 1
                    ELSE 0
                END
            ) AS identified_lineage_rows
        FROM "{TABLE_NAME}"
        GROUP BY symbol, timestamp
        HAVING COUNT(*) > 1
    """

    rows = conn.execute(query).fetchall()

    total_groups = len(rows)
    all_null_groups = 0
    mixed_null_groups = 0
    identified_groups = 0

    for (
        symbol,
        timestamp,
        row_count,
        null_rows,
        identified_rows,
    ) in rows:

        if null_rows == row_count:
            all_null_groups += 1

        elif null_rows > 0 and identified_rows > 0:
            mixed_null_groups += 1

        else:
            identified_groups += 1

    print(f"Duplicate groups                    : {total_groups:,}")
    print(f"All lineage NULL                    : {all_null_groups:,}")
    print(f"Mixed NULL / identified lineage     : {mixed_null_groups:,}")
    print(f"Fully identified lineage            : {identified_groups:,}")


# =============================================================================
# TEMPORAL CONCENTRATION
# =============================================================================

def audit_duplicate_time_range(conn):
    print_section("DUPLICATE TEMPORAL CONCENTRATION")

    query = f"""
        SELECT
            MIN(timestamp),
            MAX(timestamp)
        FROM "{TABLE_NAME}"
        WHERE (symbol, timestamp) IN (
            SELECT symbol, timestamp
            FROM "{TABLE_NAME}"
            GROUP BY symbol, timestamp
            HAVING COUNT(*) > 1
        )
    """

    row = conn.execute(query).fetchone()

    if not row or row[0] is None:
        print("No duplicate timestamps found.")
        return

    print(f"First duplicate timestamp : {row[0]}")
    print(f"Last duplicate timestamp  : {row[1]}")

    print()
    print("Duplicate groups by date:")

    query = f"""
        SELECT
            substr(timestamp, 1, 10) AS day,
            COUNT(*) AS groups
        FROM (
            SELECT
                symbol,
                timestamp
            FROM "{TABLE_NAME}"
            GROUP BY symbol, timestamp
            HAVING COUNT(*) > 1
        )
        GROUP BY day
        ORDER BY day
    """

    rows = conn.execute(query).fetchall()

    for day, groups in rows:
        print(
            f"  {format_value(day):<15} {groups:>10,}"
        )


# =============================================================================
# EXACT DUPLICATE ROW AUDIT
# =============================================================================

def audit_exact_row_duplicates(conn):
    print_section("EXACT ROW DUPLICATE AUDIT")

    columns = get_columns(conn, TABLE_NAME)

    # Only inspect columns that actually exist.
    preferred_columns = [
        "timestamp",
        "symbol",
        "price",
        "source",
        "engine_version",
    ]

    available = [
        column
        for column in preferred_columns
        if column in columns
    ]

    if not available:
        print("No suitable columns available.")
        return

    select_columns = ", ".join(
        f'"{column}"'
        for column in available
    )

    query = f"""
        SELECT
            {select_columns},
            COUNT(*) AS row_count
        FROM "{TABLE_NAME}"
        GROUP BY {select_columns}
        HAVING COUNT(*) > 1
        ORDER BY row_count DESC
    """

    rows = conn.execute(query).fetchall()

    exact_groups = len(rows)
    exact_extra_rows = sum(
        row[-1] - 1
        for row in rows
    )

    print(
        f"Exact duplicate groups : {exact_groups:,}"
    )
    print(
        f"Exact duplicate rows   : {exact_extra_rows:,}"
    )

    if rows:
        print()
        print("Worst exact duplicate rows:")

        for row in rows[:DETAIL_LIMIT]:

            values = row[:-1]
            count = row[-1]

            description = " | ".join(
                f"{column}={format_value(value)}"
                for column, value
                in zip(available, values)
            )

            print(
                f"  x{count} | {description}"
            )


# =============================================================================
# DUPLICATE TIMESTAMP FREQUENCY
# =============================================================================

def audit_duplicate_multiplicity(conn):
    print_section("DUPLICATE MULTIPLICITY DISTRIBUTION")

    query = f"""
        SELECT
            duplicate_count,
            COUNT(*) AS groups
        FROM (
            SELECT
                symbol,
                timestamp,
                COUNT(*) AS duplicate_count
            FROM "{TABLE_NAME}"
            GROUP BY symbol, timestamp
            HAVING COUNT(*) > 1
        )
        GROUP BY duplicate_count
        ORDER BY duplicate_count
    """

    rows = conn.execute(query).fetchall()

    if not rows:
        print("No duplicate groups found.")
        return

    print(
        f"{'ROWS PER GROUP':<20}"
        f"{'GROUPS':>15}"
    )
    print("-" * 35)

    for duplicate_count, groups in rows:
        print(
            f"{duplicate_count:<20}"
            f"{groups:>15,}"
        )


# =============================================================================
# FINAL VERDICT
# =============================================================================

def final_verdict(
    total_rows,
    duplicate_groups,
    duplicate_extra_rows,
):
    print_section("FINAL DUPLICATE AUDIT VERDICT")

    print(f"Total market_history rows : {total_rows:,}")
    print(f"Duplicate groups          : {duplicate_groups:,}")
    print(f"Extra duplicate rows      : {duplicate_extra_rows:,}")

    if duplicate_groups == 0:
        print()
        print("MARKET HISTORY DUPLICATE STATUS : CLEAN")

    else:
        print()
        print("MARKET HISTORY DUPLICATE STATUS : DUPLICATES DETECTED")

        print()
        print("IMPORTANT:")
        print(
            "Duplicate records were NOT deleted."
        )
        print(
            "No database modification was performed."
        )


# =============================================================================
# MAIN
# =============================================================================

def main():

    print_header(
        "ARUNDA TRADER — MARKET HISTORY DUPLICATE AUDIT v0.1"
    )

    print("MODE                 : READ ONLY")
    print(f"DATABASE             : {DB_PATH}")
    print("WRITE OPERATIONS     : NONE")
    print("SCHEMA CHANGES       : NONE")
    print("DELETE OPERATIONS    : NONE")
    print("INSERT OPERATIONS    : NONE")
    print("UPDATE OPERATIONS    : NONE")

    conn = None

    try:

        # ---------------------------------------------------------------------
        # CONNECT READ ONLY
        # ---------------------------------------------------------------------

        conn = get_connection()

        print()
        print("READ-ONLY CONNECTION  : ESTABLISHED")

        # ---------------------------------------------------------------------
        # VERIFY TABLE
        # ---------------------------------------------------------------------

        if not table_exists(conn, TABLE_NAME):
            raise RuntimeError(
                f"Required table does not exist: {TABLE_NAME}"
            )

        # ---------------------------------------------------------------------
        # DATABASE OVERVIEW
        # ---------------------------------------------------------------------

        total_rows, columns = audit_database_overview(conn)

        # ---------------------------------------------------------------------
        # DUPLICATE GROUP AUDIT
        # ---------------------------------------------------------------------

        duplicate_groups_data = audit_duplicate_groups(conn)

        duplicate_groups = len(
            duplicate_groups_data
        )

        duplicate_extra_rows = sum(
            count - 1
            for _, _, count in duplicate_groups_data
        )

        # ---------------------------------------------------------------------
        # DISTRIBUTION
        # ---------------------------------------------------------------------

        audit_duplicate_distribution(conn)

        # ---------------------------------------------------------------------
        # PRICE CONSISTENCY
        # ---------------------------------------------------------------------

        audit_price_consistency(conn)

        # ---------------------------------------------------------------------
        # LINEAGE CONSISTENCY
        # ---------------------------------------------------------------------

        audit_lineage_consistency(conn)

        # ---------------------------------------------------------------------
        # NULL LINEAGE
        # ---------------------------------------------------------------------

        audit_null_lineage_duplicates(conn)

        # ---------------------------------------------------------------------
        # TEMPORAL CONCENTRATION
        # ---------------------------------------------------------------------

        audit_duplicate_time_range(conn)

        # ---------------------------------------------------------------------
        # EXACT ROW DUPLICATES
        # ---------------------------------------------------------------------

        audit_exact_row_duplicates(conn)

        # ---------------------------------------------------------------------
        # MULTIPLICITY
        # ---------------------------------------------------------------------

        audit_duplicate_multiplicity(conn)

        # ---------------------------------------------------------------------
        # FINAL VERDICT
        # ---------------------------------------------------------------------

        final_verdict(
            total_rows,
            duplicate_groups,
            duplicate_extra_rows,
        )

        print()
        print("=" * 100)
        print("ARUNDA MARKET HISTORY DUPLICATE AUDIT COMPLETE")
        print("=" * 100)

        print()
        print("Database was opened in READ-ONLY mode.")
        print(
            "No INSERT / UPDATE / DELETE / ALTER / CREATE "
            "operation was executed."
        )

    except Exception as exc:

        print()
        print("=" * 100)
        print("AUDIT FAILED")
        print("=" * 100)

        print(type(exc).__name__)
        print(exc)

        raise

    finally:

        if conn is not None:
            conn.close()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()