import sqlite3

DB_PATH = "arunda.db"
ENGINE_VERSION = "v0.1"

MAX_GROUPS = 50


def connect_read_only():
    return sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )


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
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return {
        row[1]: {
            "type": row[2],
            "notnull": row[3],
            "default": row[4],
            "pk": row[5],
        }
        for row in rows
    }


def count_rows(conn):
    return conn.execute(
        "SELECT COUNT(*) FROM market_history"
    ).fetchone()[0]


def count_distinct(conn, expression):
    """
    Safe COUNT(DISTINCT expression).

    The expression is generated internally by this diagnostic
    and is not user supplied.
    """
    sql = f"""
        SELECT COUNT(*)
        FROM (
            SELECT DISTINCT {expression}
            FROM market_history
        )
    """

    return conn.execute(sql).fetchone()[0]


def count_collision_groups(conn, expression):
    """
    Counts identity values appearing more than once.
    """
    sql = f"""
        SELECT COUNT(*)
        FROM (
            SELECT {expression}
            FROM market_history
            GROUP BY {expression}
            HAVING COUNT(*) > 1
        )
    """

    return conn.execute(sql).fetchone()[0]


def count_duplicate_rows(conn, expression):
    """
    Number of rows beyond the first row in each identity group.
    Example:
        360 rows -> 359 duplicate rows.
    """
    sql = f"""
        SELECT COALESCE(
            SUM(group_count - 1),
            0
        )
        FROM (
            SELECT
                {expression},
                COUNT(*) AS group_count
            FROM market_history
            GROUP BY {expression}
            HAVING COUNT(*) > 1
        )
    """

    return conn.execute(sql).fetchone()[0]


def print_identity_test(
    conn,
    label,
    expression,
    total_rows,
    show_groups=True,
):
    distinct_count = count_distinct(
        conn,
        expression,
    )

    collision_groups = count_collision_groups(
        conn,
        expression,
    )

    duplicate_rows = count_duplicate_rows(
        conn,
        expression,
    )

    unique = distinct_count == total_rows

    print()
    print(label)
    print("-" * 100)
    print(f"Expression              : {expression}")
    print(f"Total Rows              : {total_rows}")
    print(f"Distinct Values         : {distinct_count}")
    print(f"Collision Groups        : {collision_groups}")
    print(f"Duplicate Rows          : {duplicate_rows}")
    print(
        f"Unique Across Rows      : "
        f"{'YES' if unique else 'NO'}"
    )

    if show_groups and collision_groups > 0:
        print()
        print(f"{label} COLLISION GROUPS")
        print("-" * 100)
        print(f"Expression : {expression}")

        sql = f"""
            SELECT
                {expression} AS identity_value,
                COUNT(*) AS rows
            FROM market_history
            GROUP BY {expression}
            HAVING COUNT(*) > 1
            ORDER BY rows DESC, identity_value
            LIMIT ?
        """

        rows = conn.execute(
            sql,
            (MAX_GROUPS,),
        ).fetchall()

        for row in rows:
            print(
                f"  {str(row[0]):<70}"
                f" rows={row[1]}"
            )


def print_database_header(conn, available_columns):
    print("=" * 100)
    print("DATABASE")
    print("=" * 100)

    print("Database        : CONNECTED")

    if table_exists(conn, "market_history"):
        print("History Table   : market_history")
    else:
        print("History Table   : NOT FOUND")
        return False

    print(
        f"Columns         : "
        f"{len(available_columns)}"
    )

    return True


def print_identity_field_availability(
    available_columns,
):
    print()
    print("=" * 100)
    print("IDENTITY FIELD AVAILABILITY")
    print("=" * 100)

    identity_fields = [
        "symbol",
        "name",
        "source",
        "source_timestamp",
        "engine_version",
        "timestamp",
        "created_at",
    ]

    for field in identity_fields:
        status = (
            "PRESENT"
            if field in available_columns
            else "MISSING"
        )

        print(
            f"{field:<22}: {status}"
        )


def print_identity_schema(
    available_columns,
):
    print()
    print("=" * 100)
    print("MARKET_HISTORY IDENTITY FIELD SCHEMA")
    print("=" * 100)

    fields = [
        "timestamp",
        "symbol",
        "name",
        "source",
        "source_timestamp",
        "engine_version",
        "created_at",
    ]

    for field in fields:

        if field not in available_columns:
            print(
                f"{field:<22}: MISSING"
            )
            continue

        info = available_columns[field]

        print(
            f"{field:<22} "
            f"type={str(info['type']):<12} "
            f"notnull={info['notnull']} "
            f"default={info['default']}"
        )


def print_symbol_name_analysis(
    conn,
    total_rows,
):
    print()
    print("=" * 100)
    print("SYMBOL + NAME IDENTITY ANALYSIS")
    print("=" * 100)

    expression = """
        symbol || '|' || COALESCE(name, '<NULL>')
    """

    sql = f"""
        SELECT
            symbol,
            COALESCE(name, '<NULL>') AS name,
            COUNT(*) AS rows
        FROM market_history
        GROUP BY
            symbol,
            COALESCE(name, '<NULL>')
        ORDER BY
            symbol,
            name
    """

    rows = conn.execute(sql).fetchall()

    for row in rows[:MAX_GROUPS]:
        print(
            f"{str(row[0]):<12} "
            f"{str(row[1]):<45} "
            f"rows={row[2]}"
        )

    if len(rows) > MAX_GROUPS:
        print()
        print(
            f"... {len(rows) - MAX_GROUPS} "
            f"additional identity groups omitted."
        )


def print_source_identity_analysis(
    conn,
    available_columns,
    total_rows,
):
    print()
    print("=" * 100)
    print("SOURCE-AWARE IDENTITY ANALYSIS")
    print("=" * 100)

    if "source" not in available_columns:
        print("Source field unavailable.")
        return

    expressions = [
        (
            "SOURCE + SYMBOL",
            """
            COALESCE(source, '<NULL>') || '|' || symbol
            """,
        ),
        (
            "SOURCE + SYMBOL + NAME",
            """
            COALESCE(source, '<NULL>')
            || '|'
            || symbol
            || '|'
            || COALESCE(name, '<NULL>')
            """,
        ),
    ]

    for label, expression in expressions:
        print_identity_test(
            conn,
            label,
            expression,
            total_rows,
            show_groups=True,
        )


def print_source_distribution(
    conn,
    available_columns,
):
    print()
    print("=" * 100)
    print("SOURCE DISTRIBUTION")
    print("=" * 100)

    if "source" not in available_columns:
        print("Source field unavailable.")
        return

    rows = conn.execute(
        """
        SELECT
            COALESCE(source, '<NULL>') AS source,
            COUNT(*) AS rows,
            COUNT(DISTINCT symbol) AS symbols,
            COUNT(DISTINCT COALESCE(name, '<NULL>')) AS names
        FROM market_history
        GROUP BY source
        ORDER BY rows DESC
        """
    ).fetchall()

    print(
        f"{'SOURCE':<35}"
        f"{'ROWS':>12}"
        f"{'SYMBOLS':>12}"
        f"{'NAMES':>12}"
    )

    print("-" * 100)

    for row in rows:
        print(
            f"{str(row[0]):<35}"
            f"{row[1]:>12}"
            f"{row[2]:>12}"
            f"{row[3]:>12}"
        )


def print_temporal_identity_analysis(
    conn,
    available_columns,
):
    print()
    print("=" * 100)
    print("TEMPORAL IDENTITY ANALYSIS")
    print("=" * 100)

    required = {
        "symbol",
        "name",
        "timestamp",
        "created_at",
    }

    missing = required - set(available_columns)

    if missing:
        print(
            "Missing fields: "
            + ", ".join(sorted(missing))
        )
        return

    sql = """
        SELECT
            symbol,
            COALESCE(name, '<NULL>') AS name,
            COUNT(*) AS rows,
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp,
            MIN(created_at) AS first_created_at,
            MAX(created_at) AS last_created_at
        FROM market_history
        GROUP BY
            symbol,
            COALESCE(name, '<NULL>')
        HAVING COUNT(*) > 1
        ORDER BY
            rows DESC,
            symbol,
            name
        LIMIT ?
    """

    rows = conn.execute(
        sql,
        (MAX_GROUPS,),
    ).fetchall()

    for row in rows:

        print()
        print(
            f"{row[0]} | {row[1]}"
        )

        print(
            f"  rows={row[2]}"
        )

        print(
            f"  first_timestamp="
            f"{row[3]}"
        )

        print(
            f"  last_timestamp="
            f"{row[4]}"
        )

        print(
            f"  first_created_at="
            f"{row[5]}"
        )

        print(
            f"  last_created_at="
            f"{row[6]}"
        )


def print_identity_summary(
    conn,
    available_columns,
    total_rows,
):
    print()
    print("=" * 100)
    print("IDENTITY CONTRACT SUMMARY")
    print("=" * 100)

    symbol_distinct = count_distinct(
        conn,
        "symbol",
    )

    symbol_name_distinct = count_distinct(
        conn,
        """
        symbol || '|' || COALESCE(name, '<NULL>')
        """,
    )

    source_symbol_distinct = None

    if "source" in available_columns:
        source_symbol_distinct = count_distinct(
            conn,
            """
            COALESCE(source, '<NULL>') || '|' || symbol
            """,
        )

    source_symbol_name_distinct = None

    if "source" in available_columns:
        source_symbol_name_distinct = count_distinct(
            conn,
            """
            COALESCE(source, '<NULL>')
            || '|'
            || symbol
            || '|'
            || COALESCE(name, '<NULL>')
            """,
        )

    print(
        f"Total Rows                    : "
        f"{total_rows}"
    )

    print(
        f"Distinct Symbols              : "
        f"{symbol_distinct}"
    )

    print(
        f"Distinct Symbol + Name        : "
        f"{symbol_name_distinct}"
    )

    if source_symbol_distinct is not None:
        print(
            f"Distinct Source + Symbol     : "
            f"{source_symbol_distinct}"
        )

    if source_symbol_name_distinct is not None:
        print(
            f"Distinct Source + Symbol + Name"
            f" : {source_symbol_name_distinct}"
        )

    print()

    print(
        "Identity Interpretation:"
    )

    if symbol_distinct != total_rows:
        print(
            "- SYMBOL alone is NOT a unique asset identity."
        )
    else:
        print(
            "- SYMBOL alone is unique in current history."
        )

    if symbol_name_distinct != total_rows:
        print(
            "- SYMBOL + NAME is NOT row-unique."
        )
    else:
        print(
            "- SYMBOL + NAME is row-unique."
        )

    if source_symbol_name_distinct is not None:

        if source_symbol_name_distinct != total_rows:
            print(
                "- SOURCE + SYMBOL + NAME is NOT row-unique."
            )
        else:
            print(
                "- SOURCE + SYMBOL + NAME is row-unique."
            )


def main():

    print("=" * 100)
    print(
        "ARUNDA MARKET HISTORY ASSET IDENTITY "
        "CONTRACT DIAGNOSTIC v0.1"
    )
    print(
        "READ-ONLY / IDENTITY CONTRACT ANALYSIS"
    )
    print("=" * 100)

    print(
        f"Database        : {DB_PATH}"
    )

    print(
        "Mode            : READ ONLY"
    )

    print(
        "Database Write  : DISABLED"
    )

    print(
        f"Engine Version  : {ENGINE_VERSION}"
    )

    print("=" * 100)

    conn = connect_read_only()

    try:

        available_columns = get_columns(
            conn,
            "market_history",
        )

        if not print_database_header(
            conn,
            available_columns,
        ):
            return

        total_rows = count_rows(conn)

        print_identity_field_availability(
            available_columns,
        )

        print_identity_schema(
            available_columns,
        )

        print()
        print("=" * 100)
        print("IDENTITY UNIQUENESS TESTS")
        print("=" * 100)

        print_identity_test(
            conn,
            "SYMBOL ONLY",
            "symbol",
            total_rows,
            show_groups=True,
        )

        print_identity_test(
            conn,
            "NAME ONLY",
            "COALESCE(name, '<NULL>')",
            total_rows,
            show_groups=True,
        )

        print_identity_test(
            conn,
            "SYMBOL + NAME",
            """
            symbol || '|' || COALESCE(name, '<NULL>')
            """,
            total_rows,
            show_groups=True,
        )

        if "source" in available_columns:

            print_identity_test(
                conn,
                "SOURCE + SYMBOL",
                """
                COALESCE(source, '<NULL>') || '|' || symbol
                """,
                total_rows,
                show_groups=True,
            )

            print_identity_test(
                conn,
                "SOURCE + SYMBOL + NAME",
                """
                COALESCE(source, '<NULL>')
                || '|'
                || symbol
                || '|'
                || COALESCE(name, '<NULL>')
                """,
                total_rows,
                show_groups=True,
            )

        print_symbol_name_analysis(
            conn,
            total_rows,
        )

        print_source_identity_analysis(
            conn,
            available_columns,
            total_rows,
        )

        print_source_distribution(
            conn,
            available_columns,
        )

        print_temporal_identity_analysis(
            conn,
            available_columns,
        )

        print_identity_summary(
            conn,
            available_columns,
            total_rows,
        )

        print()
        print("=" * 100)
        print("DIAGNOSTIC CONCLUSION")
        print("=" * 100)

        print(
            "Analysis Mode              : READ ONLY"
        )

        print(
            "Database Modification      : NONE"
        )

        print(
            "Engine Modification        : NONE"
        )

        print(
            "Identity Repair            : NONE"
        )

        print()

        print(
            "NO DATABASE OR ENGINE "
            "MODIFICATIONS WERE PERFORMED."
        )

        print("=" * 100)

        print(
            "ARUNDA MARKET HISTORY ASSET IDENTITY "
            f"CONTRACT DIAGNOSTIC {ENGINE_VERSION} COMPLETE"
        )

        print("=" * 100)

    finally:
        conn.close()


if __name__ == "__main__":
    main()