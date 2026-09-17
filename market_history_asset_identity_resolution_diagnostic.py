# -*- coding: utf-8 -*-

"""
ARUNDA MARKET HISTORY ASSET IDENTITY RESOLUTION DIAGNOSTIC v0.1

READ-ONLY / IDENTITY RESOLUTION ANALYSIS

Purpose:
    Analyze whether market_history contains enough stable evidence
    to resolve a persistent asset identity.

Rules:
    - Database is READ ONLY.
    - No INSERT.
    - No UPDATE.
    - No DELETE.
    - No ALTER.
    - No CREATE.
    - No schema modification.
    - No engine modification.
    - No identity repair.
    - No asset_id creation.

This diagnostic analyzes:
    1. symbol reuse
    2. name variation
    3. source variation
    4. source_timestamp behavior
    5. engine_version behavior
    6. timestamp behavior
    7. source-aware identity candidates
    8. possible stable identity evidence
    9. unresolved identity groups
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from collections import defaultdict


DB_PATH = Path(__file__).resolve().parent / "arunda.db"

VERSION = "v0.1"
ENGINE_VERSION = "v0.1"

HISTORY_TABLE = "market_history"

IDENTITY_FIELDS = (
    "symbol",
    "name",
    "source",
    "source_timestamp",
    "engine_version",
    "timestamp",
    "created_at",
)


# =============================================================================
# OUTPUT HELPERS
# =============================================================================

def line(char="=", length=100):
    print(char * length)


def title(text):
    line("=")
    print(text)
    line("=")


def section(text):
    print()
    line("=")
    print(text)
    line("=")


def subsection(text):
    print()
    line("-")
    print(text)
    line("-")


def fmt(value):
    if value is None:
        return "<NULL>"
    return str(value)


# =============================================================================
# DATABASE
# =============================================================================

def connect_read_only(db_path: Path):
    """
    Open SQLite database strictly in READ ONLY mode.
    """

    uri = f"file:{db_path.as_posix()}?mode=ro"

    return sqlite3.connect(
        uri,
        uri=True,
        timeout=5,
    )


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
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row[1] for row in rows]


def get_total_rows(conn):
    row = conn.execute(
        f"SELECT COUNT(*) FROM {HISTORY_TABLE}"
    ).fetchone()

    return int(row[0])


# =============================================================================
# BASIC STATISTICS
# =============================================================================

def count_distinct(conn, expression):
    """
    Count DISTINCT values.

    expression is generated internally by this diagnostic.
    It is never populated by user input.
    """

    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT {expression}
            FROM {HISTORY_TABLE}
            GROUP BY {expression}
        )
        """
    ).fetchone()

    return int(row[0])


def count_collision_groups(conn, expression):
    """
    Number of identity groups containing more than one row.
    """

    row = conn.execute(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT {expression}
            FROM {HISTORY_TABLE}
            GROUP BY {expression}
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()

    return int(row[0])


def count_duplicate_rows(conn, expression):
    """
    Number of rows beyond the first row in each duplicate group.
    """

    row = conn.execute(
        f"""
        SELECT COALESCE(
            SUM(group_count - 1),
            0
        )
        FROM (
            SELECT COUNT(*) AS group_count
            FROM {HISTORY_TABLE}
            GROUP BY {expression}
            HAVING COUNT(*) > 1
        )
        """
    ).fetchone()

    return int(row[0] or 0)


def print_identity_test(
    conn,
    label,
    expression,
):
    total_rows = get_total_rows(conn)
    distinct_count = count_distinct(conn, expression)
    collision_groups = count_collision_groups(conn, expression)
    duplicate_rows = count_duplicate_rows(conn, expression)

    print()
    print(label)
    print("-" * 100)
    print(f"Expression              : {expression}")
    print(f"Total Rows              : {total_rows}")
    print(f"Distinct Values         : {distinct_count}")
    print(f"Collision Groups        : {collision_groups}")
    print(f"Duplicate Rows          : {duplicate_rows}")
    print(
        "Unique Across Rows      : "
        + ("YES" if distinct_count == total_rows else "NO")
    )


# =============================================================================
# FIELD PRESENCE
# =============================================================================

def print_field_availability(columns):
    section("IDENTITY FIELD AVAILABILITY")

    for field in IDENTITY_FIELDS:
        status = "PRESENT" if field in columns else "MISSING"
        print(f"{field:<24}: {status}")


# =============================================================================
# FIELD NULLABILITY / CONTENT
# =============================================================================

def field_content_statistics(conn, field):
    row = conn.execute(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            SUM(
                CASE
                    WHEN {field} IS NULL THEN 1
                    ELSE 0
                END
            ) AS null_rows,
            COUNT(DISTINCT {field}) AS distinct_values
        FROM {HISTORY_TABLE}
        """
    ).fetchone()

    return (
        int(row[0]),
        int(row[1] or 0),
        int(row[2]),
    )


def print_field_content_analysis(conn, columns):
    section("IDENTITY FIELD CONTENT ANALYSIS")

    for field in IDENTITY_FIELDS:
        if field not in columns:
            continue

        total, null_rows, distinct_values = field_content_statistics(
            conn,
            field,
        )

        non_null = total - null_rows

        print(f"{field:<24}")
        print(f"  total rows             : {total}")
        print(f"  NULL rows              : {null_rows}")
        print(f"  NON-NULL rows          : {non_null}")
        print(f"  distinct values        : {distinct_values}")


# =============================================================================
# SYMBOL ANALYSIS
# =============================================================================

def print_symbol_resolution_analysis(conn):
    section("SYMBOL RESOLUTION ANALYSIS")

    rows = conn.execute(
        f"""
        SELECT
            symbol,
            COUNT(*) AS rows,
            COUNT(DISTINCT COALESCE(name, '<NULL>')) AS names,
            COUNT(DISTINCT COALESCE(source, '<NULL>')) AS sources,
            COUNT(DISTINCT COALESCE(engine_version, '<NULL>'))
                AS engine_versions,
            COUNT(DISTINCT COALESCE(source_timestamp, '<NULL>'))
                AS source_timestamps,
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp
        FROM {HISTORY_TABLE}
        WHERE symbol IS NOT NULL
        GROUP BY symbol
        HAVING
            COUNT(DISTINCT COALESCE(name, '<NULL>')) > 1
            OR COUNT(DISTINCT COALESCE(source, '<NULL>')) > 1
            OR COUNT(DISTINCT COALESCE(engine_version, '<NULL>')) > 1
        ORDER BY rows DESC, symbol
        """
    ).fetchall()

    print(f"Resolution Groups      : {len(rows)}")

    if not rows:
        print("No symbol resolution conflicts detected.")
        return

    print()
    print(
        f"{'SYMBOL':<18}"
        f"{'ROWS':>8}"
        f"{'NAMES':>8}"
        f"{'SOURCES':>10}"
        f"{'ENGINES':>10}"
        f"{'SRC_TS':>10}"
    )

    print("-" * 100)

    for row in rows[:100]:
        (
            symbol,
            records,
            names,
            sources,
            engines,
            source_timestamps,
            first_timestamp,
            last_timestamp,
        ) = row

        print(
            f"{str(symbol):<18}"
            f"{records:>8}"
            f"{names:>8}"
            f"{sources:>10}"
            f"{engines:>10}"
            f"{source_timestamps:>10}"
        )


# =============================================================================
# SYMBOL + NAME VARIATION
# =============================================================================

def print_symbol_name_variations(conn):
    section("SYMBOL + NAME VARIATION ANALYSIS")

    rows = conn.execute(
        f"""
        SELECT
            symbol,
            COUNT(*) AS rows,
            COUNT(DISTINCT COALESCE(name, '<NULL>')) AS name_count
        FROM {HISTORY_TABLE}
        WHERE symbol IS NOT NULL
        GROUP BY symbol
        HAVING COUNT(DISTINCT COALESCE(name, '<NULL>')) > 1
        ORDER BY rows DESC, symbol
        """
    ).fetchall()

    print(f"Symbols With Name Variation : {len(rows)}")

    if not rows:
        print("No symbol/name variation detected.")
        return

    print()
    print(
        f"{'SYMBOL':<20}"
        f"{'ROWS':>10}"
        f"{'NAME COUNT':>14}"
    )

    print("-" * 100)

    for symbol, records, name_count in rows[:100]:
        print(
            f"{str(symbol):<20}"
            f"{records:>10}"
            f"{name_count:>14}"
        )


# =============================================================================
# SOURCE VARIATION
# =============================================================================

def print_source_variation(conn):
    section("SOURCE VARIATION ANALYSIS")

    rows = conn.execute(
        f"""
        SELECT
            symbol,
            COUNT(*) AS rows,
            COUNT(DISTINCT COALESCE(source, '<NULL>')) AS source_count
        FROM {HISTORY_TABLE}
        WHERE symbol IS NOT NULL
        GROUP BY symbol
        HAVING COUNT(DISTINCT COALESCE(source, '<NULL>')) > 1
        ORDER BY rows DESC, symbol
        """
    ).fetchall()

    print(f"Symbols With Source Variation : {len(rows)}")

    if not rows:
        print("No source variation detected.")
        return

    print()
    print(
        f"{'SYMBOL':<20}"
        f"{'ROWS':>10}"
        f"{'SOURCE COUNT':>16}"
    )

    print("-" * 100)

    for symbol, records, source_count in rows[:100]:
        print(
            f"{str(symbol):<20}"
            f"{records:>10}"
            f"{source_count:>16}"
        )


# =============================================================================
# SOURCE TIMESTAMP ANALYSIS
# =============================================================================

def print_source_timestamp_analysis(conn):
    section("SOURCE TIMESTAMP ANALYSIS")

    row = conn.execute(
        f"""
        SELECT
            COUNT(*) AS total_rows,
            SUM(
                CASE
                    WHEN source_timestamp IS NULL THEN 1
                    ELSE 0
                END
            ) AS null_rows,
            COUNT(DISTINCT source_timestamp) AS distinct_values
        FROM {HISTORY_TABLE}
        """
    ).fetchone()

    total_rows = int(row[0])
    null_rows = int(row[1] or 0)
    distinct_values = int(row[2])

    print(f"Total Rows              : {total_rows}")
    print(f"NULL Source Timestamp   : {null_rows}")
    print(f"NON-NULL Source TS      : {total_rows - null_rows}")
    print(f"Distinct Source TS      : {distinct_values}")

    print()

    rows = conn.execute(
        f"""
        SELECT
            COALESCE(source, '<NULL>') AS source,
            COUNT(*) AS rows,
            SUM(
                CASE
                    WHEN source_timestamp IS NULL THEN 1
                    ELSE 0
                END
            ) AS null_ts,
            COUNT(DISTINCT source_timestamp) AS distinct_ts
        FROM {HISTORY_TABLE}
        GROUP BY COALESCE(source, '<NULL>')
        ORDER BY rows DESC
        """
    ).fetchall()

    print(
        f"{'SOURCE':<28}"
        f"{'ROWS':>10}"
        f"{'NULL TS':>12}"
        f"{'DISTINCT TS':>16}"
    )

    print("-" * 100)

    for source, records, null_ts, distinct_ts in rows:
        print(
            f"{str(source):<28}"
            f"{records:>10}"
            f"{null_ts:>12}"
            f"{distinct_ts:>16}"
        )


# =============================================================================
# ENGINE VERSION ANALYSIS
# =============================================================================

def print_engine_version_analysis(conn):
    section("ENGINE VERSION ANALYSIS")

    rows = conn.execute(
        f"""
        SELECT
            COALESCE(engine_version, '<NULL>') AS engine,
            COUNT(*) AS rows,
            COUNT(DISTINCT symbol) AS symbols,
            COUNT(DISTINCT COALESCE(name, '<NULL>')) AS names,
            COUNT(DISTINCT COALESCE(source, '<NULL>')) AS sources
        FROM {HISTORY_TABLE}
        GROUP BY COALESCE(engine_version, '<NULL>')
        ORDER BY rows DESC
        """
    ).fetchall()

    print(
        f"{'ENGINE VERSION':<30}"
        f"{'ROWS':>10}"
        f"{'SYMBOLS':>12}"
        f"{'NAMES':>12}"
        f"{'SOURCES':>12}"
    )

    print("-" * 100)

    for engine, records, symbols, names, sources in rows:
        print(
            f"{str(engine):<30}"
            f"{records:>10}"
            f"{symbols:>12}"
            f"{names:>12}"
            f"{sources:>12}"
        )


# =============================================================================
# TEMPORAL RESOLUTION
# =============================================================================

def print_temporal_resolution(conn):
    section("TEMPORAL IDENTITY RESOLUTION")

    rows = conn.execute(
        f"""
        SELECT
            symbol,
            COUNT(*) AS rows,
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp,
            COUNT(DISTINCT DATE(timestamp)) AS active_days
        FROM {HISTORY_TABLE}
        WHERE symbol IS NOT NULL
        GROUP BY symbol
        ORDER BY rows DESC, symbol
        """
    ).fetchall()

    print(f"Symbols Analyzed        : {len(rows)}")

    if not rows:
        return

    print()
    print(
        f"{'SYMBOL':<18}"
        f"{'ROWS':>8}"
        f"{'DAYS':>8}"
        f"{'FIRST TIMESTAMP':<30}"
        f"{'LAST TIMESTAMP':<30}"
    )

    print("-" * 100)

    for symbol, records, first_ts, last_ts, active_days in rows[:100]:
        print(
            f"{str(symbol):<18}"
            f"{records:>8}"
            f"{active_days:>8}"
            f"{str(first_ts):<30}"
            f"{str(last_ts):<30}"
        )


# =============================================================================
# SOURCE + SYMBOL + NAME RESOLUTION
# =============================================================================

def print_source_identity_analysis(conn):
    section("SOURCE-AWARE IDENTITY RESOLUTION")

    tests = [
        (
            "SOURCE + SYMBOL",
            "COALESCE(source, '<NULL>') || '|' || symbol",
        ),
        (
            "SOURCE + SYMBOL + NAME",
            "COALESCE(source, '<NULL>') || '|' || symbol || '|' "
            "|| COALESCE(name, '<NULL>')",
        ),
        (
            "SOURCE + SYMBOL + NAME + ENGINE",
            "COALESCE(source, '<NULL>') || '|' || symbol || '|' "
            "|| COALESCE(name, '<NULL>') || '|' "
            "|| COALESCE(engine_version, '<NULL>')",
        ),
    ]

    for label, expression in tests:
        print_identity_test(
            conn,
            label,
            expression,
        )


# =============================================================================
# STABLE IDENTITY CANDIDATE ANALYSIS
# =============================================================================

def print_candidate_identity_analysis(conn):
    section("STABLE IDENTITY CANDIDATE ANALYSIS")

    candidates = [
        (
            "symbol",
            "symbol",
        ),
        (
            "symbol + name",
            "symbol || '|' || COALESCE(name, '<NULL>')",
        ),
        (
            "source + symbol",
            "COALESCE(source, '<NULL>') || '|' || symbol",
        ),
        (
            "source + symbol + name",
            "COALESCE(source, '<NULL>') || '|' || symbol || '|' "
            "|| COALESCE(name, '<NULL>')",
        ),
        (
            "source + symbol + name + engine",
            "COALESCE(source, '<NULL>') || '|' || symbol || '|' "
            "|| COALESCE(name, '<NULL>') || '|' "
            "|| COALESCE(engine_version, '<NULL>')",
        ),
    ]

    total_rows = get_total_rows(conn)

    print(
        f"{'CANDIDATE':<38}"
        f"{'DISTINCT':>12}"
        f"{'COLLISIONS':>14}"
        f"{'ROW UNIQUE':>14}"
    )

    print("-" * 100)

    for label, expression in candidates:
        distinct_count = count_distinct(
            conn,
            expression,
        )

        collision_groups = count_collision_groups(
            conn,
            expression,
        )

        unique = distinct_count == total_rows

        print(
            f"{label:<38}"
            f"{distinct_count:>12}"
            f"{collision_groups:>14}"
            f"{('YES' if unique else 'NO'):>14}"
        )


# =============================================================================
# IDENTITY CONFLICT EXAMPLES
# =============================================================================

def print_identity_conflict_examples(conn):
    section("IDENTITY CONFLICT EXAMPLES")

    rows = conn.execute(
        f"""
        SELECT
            symbol,
            COUNT(*) AS rows,
            COUNT(DISTINCT COALESCE(name, '<NULL>')) AS names,
            COUNT(DISTINCT COALESCE(source, '<NULL>')) AS sources
        FROM {HISTORY_TABLE}
        WHERE symbol IS NOT NULL
        GROUP BY symbol
        HAVING
            COUNT(DISTINCT COALESCE(name, '<NULL>')) > 1
            OR COUNT(DISTINCT COALESCE(source, '<NULL>')) > 1
        ORDER BY rows DESC, symbol
        LIMIT 20
        """
    ).fetchall()

    if not rows:
        print("No conflicts found.")
        return

    for symbol, records, names, sources in rows:
        print()
        print(f"SYMBOL : {symbol}")
        print(f"  rows              : {records}")
        print(f"  distinct names    : {names}")
        print(f"  distinct sources  : {sources}")

        names_rows = conn.execute(
            f"""
            SELECT
                COALESCE(name, '<NULL>') AS name,
                COUNT(*) AS rows
            FROM {HISTORY_TABLE}
            WHERE symbol = ?
            GROUP BY COALESCE(name, '<NULL>')
            ORDER BY rows DESC, name
            """,
            (symbol,),
        ).fetchall()

        print("  names:")

        for name, name_count in names_rows[:10]:
            print(
                f"    {str(name):<50}"
                f" rows={name_count}"
            )

        source_rows = conn.execute(
            f"""
            SELECT
                COALESCE(source, '<NULL>') AS source,
                COUNT(*) AS rows
            FROM {HISTORY_TABLE}
            WHERE symbol = ?
            GROUP BY COALESCE(source, '<NULL>')
            ORDER BY rows DESC, source
            """,
            (symbol,),
        ).fetchall()

        print("  sources:")

        for source, source_count in source_rows[:10]:
            print(
                f"    {str(source):<30}"
                f" rows={source_count}"
            )


# =============================================================================
# IDENTITY RESOLUTION DECISION
# =============================================================================

def resolve_contract_status(conn):
    total_rows = get_total_rows(conn)

    symbol_distinct = count_distinct(
        conn,
        "symbol",
    )

    symbol_name_distinct = count_distinct(
        conn,
        "symbol || '|' || COALESCE(name, '<NULL>')",
    )

    source_symbol_distinct = count_distinct(
        conn,
        "COALESCE(source, '<NULL>') || '|' || symbol",
    )

    source_symbol_name_distinct = count_distinct(
        conn,
        "COALESCE(source, '<NULL>') || '|' || symbol || '|' "
        "|| COALESCE(name, '<NULL>')",
    )

    source_symbol_name_engine_distinct = count_distinct(
        conn,
        "COALESCE(source, '<NULL>') || '|' || symbol || '|' "
        "|| COALESCE(name, '<NULL>') || '|' "
        "|| COALESCE(engine_version, '<NULL>')",
    )

    return {
        "total_rows": total_rows,
        "symbol_distinct": symbol_distinct,
        "symbol_name_distinct": symbol_name_distinct,
        "source_symbol_distinct": source_symbol_distinct,
        "source_symbol_name_distinct": source_symbol_name_distinct,
        "source_symbol_name_engine_distinct":
            source_symbol_name_engine_distinct,
    }


def print_contract_summary(stats):
    section("IDENTITY RESOLUTION CONTRACT SUMMARY")

    print(
        f"Total Rows                         : "
        f"{stats['total_rows']}"
    )

    print(
        f"Distinct Symbols                   : "
        f"{stats['symbol_distinct']}"
    )

    print(
        f"Distinct Symbol + Name             : "
        f"{stats['symbol_name_distinct']}"
    )

    print(
        f"Distinct Source + Symbol           : "
        f"{stats['source_symbol_distinct']}"
    )

    print(
        f"Distinct Source + Symbol + Name    : "
        f"{stats['source_symbol_name_distinct']}"
    )

    print(
        f"Distinct Source + Symbol + Name + "
        f"Engine                            : "
        f"{stats['source_symbol_name_engine_distinct']}"
    )

    print()
    print("Resolution Interpretation:")

    if stats["symbol_distinct"] == stats["total_rows"]:
        print("- SYMBOL may be row-unique.")
    else:
        print("- SYMBOL alone cannot resolve individual rows.")

    if stats["symbol_name_distinct"] == stats["total_rows"]:
        print("- SYMBOL + NAME is row-unique.")
    else:
        print("- SYMBOL + NAME cannot resolve individual rows.")

    if stats["source_symbol_distinct"] == stats["total_rows"]:
        print("- SOURCE + SYMBOL is row-unique.")
    else:
        print("- SOURCE + SYMBOL cannot resolve individual rows.")

    if stats["source_symbol_name_distinct"] == stats["total_rows"]:
        print("- SOURCE + SYMBOL + NAME is row-unique.")
    else:
        print(
            "- SOURCE + SYMBOL + NAME cannot resolve "
            "individual historical rows."
        )

    if (
        stats["source_symbol_name_engine_distinct"]
        == stats["total_rows"]
    ):
        print(
            "- SOURCE + SYMBOL + NAME + ENGINE "
            "is row-unique."
        )
    else:
        print(
            "- SOURCE + SYMBOL + NAME + ENGINE "
            "is NOT row-unique."
        )


# =============================================================================
# FINAL CONCLUSION
# =============================================================================

def print_final_conclusion(stats):
    section("DIAGNOSTIC CONCLUSION")

    total = stats["total_rows"]

    strongest = stats[
        "source_symbol_name_engine_distinct"
    ]

    print("Analysis Mode              : READ ONLY")
    print("Database Modification      : NONE")
    print("Engine Modification        : NONE")
    print("Identity Resolution        : ANALYSIS ONLY")
    print("Identity Repair            : NONE")
    print()

    if strongest == total:
        print(
            "RESULT                     : "
            "A row-unique composite identity candidate exists."
        )
        print()
        print(
            "IMPORTANT                  : "
            "This diagnostic does NOT create or persist that identity."
        )
    else:
        print(
            "RESULT                     : "
            "NO ROW-UNIQUE IDENTITY CANDIDATE FOUND "
            "FROM CURRENT FIELDS."
        )
        print()
        print(
            "IDENTITY STATUS            : "
            "UNRESOLVED"
        )
        print()
        print(
            "NEXT ARCHITECTURAL REQUIREMENT:"
        )
        print(
            "- Determine whether a stable external asset identity "
            "exists in the upstream source."
        )
        print(
            "- Do not infer permanent asset identity from symbol alone."
        )
        print(
            "- Do not merge collision groups automatically."
        )
        print(
            "- Do not repair historical rows at this stage."
        )

    print()
    print("NO DATABASE OR ENGINE MODIFICATIONS WERE PERFORMED.")


# =============================================================================
# MAIN
# =============================================================================

def main():
    title(
        "ARUNDA MARKET HISTORY ASSET IDENTITY RESOLUTION "
        f"DIAGNOSTIC {VERSION}"
    )

    print("READ-ONLY / IDENTITY RESOLUTION ANALYSIS")
    print("=" * 100)
    print(f"Database        : {DB_PATH.name}")
    print("Mode            : READ ONLY")
    print("Database Write  : DISABLED")
    print(f"Engine Version  : {ENGINE_VERSION}")

    print("=" * 100)

    if not DB_PATH.exists():
        print()
        print("ERROR")
        print(f"Database not found: {DB_PATH}")
        return

    conn = None

    try:
        conn = connect_read_only(DB_PATH)

        print()
        print("=" * 100)
        print("DATABASE")
        print("=" * 100)

        print(f"Database        : CONNECTED")

        if not table_exists(conn, HISTORY_TABLE):
            print(f"History Table   : {HISTORY_TABLE} NOT FOUND")
            return

        print(f"History Table   : {HISTORY_TABLE}")

        columns = get_columns(
            conn,
            HISTORY_TABLE,
        )

        print(f"Columns         : {len(columns)}")

        print_field_availability(columns)

        missing = [
            field
            for field in IDENTITY_FIELDS
            if field not in columns
        ]

        if missing:
            section("IDENTITY CONTRACT WARNING")

            print(
                "Missing identity fields:"
            )

            for field in missing:
                print(f"- {field}")

            print()
            print(
                "Resolution analysis is limited by "
                "missing database fields."
            )

        print_field_content_analysis(
            conn,
            columns,
        )

        print_symbol_resolution_analysis(
            conn,
        )

        print_symbol_name_variations(
            conn,
        )

        print_source_variation(
            conn,
        )

        print_source_timestamp_analysis(
            conn,
        )

        print_engine_version_analysis(
            conn,
        )

        print_temporal_resolution(
            conn,
        )

        print_source_identity_analysis(
            conn,
        )

        print_candidate_identity_analysis(
            conn,
        )

        print_identity_conflict_examples(
            conn,
        )

        stats = resolve_contract_status(
            conn,
        )

        print_contract_summary(
            stats,
        )

        print_final_conclusion(
            stats,
        )

        print()
        line("=")
        print(
            "ARUNDA MARKET HISTORY ASSET IDENTITY "
            f"RESOLUTION DIAGNOSTIC {VERSION} COMPLETE"
        )
        line("=")

    except sqlite3.Error as exc:
        print()
        print("=" * 100)
        print("SQLITE ERROR")
        print("=" * 100)
        print(type(exc).__name__)
        print(str(exc))

    except Exception as exc:
        print()
        print("=" * 100)
        print("UNEXPECTED ERROR")
        print("=" * 100)
        print(type(exc).__name__)
        print(str(exc))

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()