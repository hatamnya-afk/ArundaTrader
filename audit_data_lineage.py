import sqlite3
from pathlib import Path
from collections import defaultdict


DB_PATH = Path("arunda.db")


TABLES = [
    "market_universe",
    "market_history",
    "market_data",
    "market_technical",
    "market_microstructure",
    "market_state",
    "market_opportunity",
    "market_news",
    "market_news_intelligence",
    "news_data",
    "news_signals",
    "positioning_data",
    "social_metrics",
    "market_whale",
    "hunter_signals",
    "fusion_signals",
    "opportunity_signals",
    "trade_decisions",
    "trade_gate_decisions",
    "risk_decisions",
    "signal_outcomes",
]


def print_header(title):
    print("\n" + "=" * 100)
    print(title)
    print("=" * 100)


def table_exists(cursor, table):
    cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    )
    return cursor.fetchone() is not None


def get_columns(cursor, table):
    cursor.execute(f'PRAGMA table_info("{table}")')
    return [row[1] for row in cursor.fetchall()]


def get_count(cursor, table):
    cursor.execute(f'SELECT COUNT(*) FROM "{table}"')
    return cursor.fetchone()[0]


def get_min_max(cursor, table, column):
    cursor.execute(
        f'''
        SELECT MIN("{column}"), MAX("{column}")
        FROM "{table}"
        WHERE "{column}" IS NOT NULL
        '''
    )
    return cursor.fetchone()


def get_latest_row(cursor, table, time_column):
    cursor.execute(
        f'''
        SELECT *
        FROM "{table}"
        WHERE "{time_column}" IS NOT NULL
        ORDER BY "{time_column}" DESC
        LIMIT 1
        '''
    )
    return cursor.fetchone()


def get_distinct_count(cursor, table, column):
    cursor.execute(
        f'''
        SELECT COUNT(DISTINCT "{column}")
        FROM "{table}"
        WHERE "{column}" IS NOT NULL
        '''
    )
    return cursor.fetchone()[0]


def get_latest_values(cursor, table, time_column, columns):
    result = {}

    latest = get_latest_row(cursor, table, time_column)

    if latest is None:
        return result

    cursor.execute(f'PRAGMA table_info("{table}")')
    schema = cursor.fetchall()

    names = [row[1] for row in schema]

    row_dict = dict(zip(names, latest))

    for column in columns:
        if column in row_dict:
            result[column] = row_dict[column]

    return result


def get_null_stats(cursor, table, columns):
    stats = {}

    total = get_count(cursor, table)

    if total == 0:
        return stats

    for column in columns:
        cursor.execute(
            f'''
            SELECT COUNT(*)
            FROM "{table}"
            WHERE "{column}" IS NULL
            '''
        )

        null_count = cursor.fetchone()[0]

        stats[column] = {
            "null": null_count,
            "filled": total - null_count,
            "null_pct": (null_count / total) * 100,
        }

    return stats


def get_duplicate_stats(cursor, table):
    """
    Generic duplicate audit.

    We intentionally do not assume a primary business key.
    We only inspect duplicate timestamps/symbol combinations
    when those columns exist.
    """

    columns = get_columns(cursor, table)

    if "timestamp" in columns and "symbol" in columns:

        cursor.execute(
            f'''
            SELECT COUNT(*)
            FROM (
                SELECT timestamp, symbol
                FROM "{table}"
                GROUP BY timestamp, symbol
                HAVING COUNT(*) > 1
            )
            '''
        )

        duplicate_groups = cursor.fetchone()[0]

        return {
            "key": "timestamp + symbol",
            "duplicate_groups": duplicate_groups,
        }

    if "timestamp" in columns and "asset" in columns:

        cursor.execute(
            f'''
            SELECT COUNT(*)
            FROM (
                SELECT timestamp, asset
                FROM "{table}"
                GROUP BY timestamp, asset
                HAVING COUNT(*) > 1
            )
            '''
        )

        duplicate_groups = cursor.fetchone()[0]

        return {
            "key": "timestamp + asset",
            "duplicate_groups": duplicate_groups,
        }

    return {
        "key": "N/A",
        "duplicate_groups": None,
    }


def audit_table(cursor, table):

    if not table_exists(cursor, table):
        print(f"\n{table:<35} NOT FOUND")
        return

    columns = get_columns(cursor, table)

    count = get_count(cursor, table)

    time_column = None

    for candidate in [
        "timestamp",
        "created_at",
        "updated_at",
        "published_at",
        "released_at",
        "run_timestamp",
        "entry_timestamp",
    ]:
        if candidate in columns:
            time_column = candidate
            break

    print("\n" + "-" * 100)
    print(f"TABLE : {table}")
    print("-" * 100)

    print(f"Records              : {count}")
    print(f"Time column          : {time_column or 'NONE'}")

    if time_column:
        first, last = get_min_max(cursor, table, time_column)

        print(f"First timestamp      : {first}")
        print(f"Last timestamp       : {last}")

    identity_columns = []

    for candidate in [
        "symbol",
        "asset",
        "market",
        "source",
        "engine_version",
        "state_version",
        "technical_version",
        "opportunity_version",
    ]:
        if candidate in columns:
            identity_columns.append(candidate)

    for column in identity_columns:

        if column in ["symbol", "asset", "market", "source"]:

            distinct = get_distinct_count(cursor, table, column)

            print(
                f"Distinct {column:<12}: {distinct}"
            )

    latest_values = get_latest_values(
        cursor,
        table,
        time_column,
        [
            "symbol",
            "asset",
            "market",
            "source",
            "engine_version",
            "state_version",
            "technical_version",
            "opportunity_version",
            "status",
            "data_status",
            "decision",
            "direction",
            "signal_strength",
        ],
    )

    if latest_values:

        print("\nLatest record metadata:")

        for key, value in latest_values.items():

            if value is not None:
                print(f"  {key:<24}: {value}")

    duplicate_stats = get_duplicate_stats(cursor, table)

    print("\nDuplicate audit:")

    print(
        f"  Key                  : {duplicate_stats['key']}"
    )

    if duplicate_stats["duplicate_groups"] is not None:

        print(
            f"  Duplicate groups     : "
            f"{duplicate_stats['duplicate_groups']}"
        )

    else:

        print("  Duplicate groups     : N/A")

    null_stats = get_null_stats(
        cursor,
        table,
        [
            c
            for c in [
                "timestamp",
                "symbol",
                "asset",
                "market",
                "price",
                "source",
                "engine_version",
            ]
            if c in columns
        ],
    )

    if null_stats:

        print("\nCritical NULL audit:")

        for column, stats in null_stats.items():

            print(
                f"  {column:<20}: "
                f"{stats['null']} NULL "
                f"({stats['null_pct']:.2f}%)"
            )


def main():

    print_header(
        "ARUNDA TRADER — DATA LINEAGE AUDIT v0.1"
    )

    print(
        "MODE                 : READ ONLY"
    )

    print(
        "DATABASE             : "
        f"{DB_PATH.resolve()}"
    )

    print(
        "WRITE OPERATIONS     : NONE"
    )

    print(
        "SCHEMA CHANGES       : NONE"
    )

    print(
        "DELETE OPERATIONS    : NONE"
    )

    if not DB_PATH.exists():

        print("\nERROR: arunda.db not found.")

        return

    connection = sqlite3.connect(
        f"file:{DB_PATH.resolve()}?mode=ro",
        uri=True,
    )

    cursor = connection.cursor()

    try:

        print_header("DATABASE OVERVIEW")

        cursor.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
            ORDER BY name
            """
        )

        all_tables = [
            row[0]
            for row in cursor.fetchall()
        ]

        print(
            f"Total SQLite tables : {len(all_tables)}"
        )

        print("\nAudited tables:")

        for table in TABLES:

            if table in all_tables:
                print(f"  [OK] {table}")

            else:
                print(f"  [--] {table}")

        print_header(
            "TABLE-BY-TABLE DATA LINEAGE AUDIT"
        )

        for table in TABLES:

            audit_table(
                cursor,
                table,
            )

        print_header(
            "PIPELINE TIMELINE COMPARISON"
        )

        timeline_tables = [
            "market_history",
            "market_technical",
            "market_microstructure",
            "market_state",
            "market_opportunity",
            "fusion_signals",
            "opportunity_signals",
            "trade_decisions",
            "trade_gate_decisions",
            "risk_decisions",
            "signal_outcomes",
        ]

        print(
            f"{'TABLE':<32}"
            f"{'COUNT':>10}"
            f"{'FIRST':>32}"
            f"{'LAST':>32}"
        )

        print("-" * 106)

        for table in timeline_tables:

            if not table_exists(cursor, table):
                continue

            columns = get_columns(
                cursor,
                table,
            )

            time_column = None

            for candidate in [
                "timestamp",
                "created_at",
                "entry_timestamp",
                "run_timestamp",
            ]:

                if candidate in columns:

                    time_column = candidate

                    break

            count = get_count(
                cursor,
                table,
            )

            first = "-"
            last = "-"

            if time_column:

                first, last = get_min_max(
                    cursor,
                    table,
                    time_column,
                )

            print(
                f"{table:<32}"
                f"{count:>10}"
                f"{str(first):>32}"
                f"{str(last):>32}"
            )

        print_header(
            "ENGINE VERSION AUDIT"
        )

        version_tables = [
            "market_history",
            "market_data",
            "market_technical",
            "market_microstructure",
            "market_state",
            "market_opportunity",
            "market_news",
            "market_news_intelligence",
            "hunter_signals",
            "fusion_signals",
            "opportunity_signals",
            "trade_decisions",
            "trade_gate_decisions",
            "risk_decisions",
            "signal_outcomes",
        ]

        for table in version_tables:

            if not table_exists(cursor, table):
                continue

            columns = get_columns(
                cursor,
                table,
            )

            version_column = None

            for candidate in [
                "engine_version",
                "state_version",
                "technical_version",
                "opportunity_version",
            ]:

                if candidate in columns:

                    version_column = candidate

                    break

            if not version_column:
                print(
                    f"{table:<32} VERSION COLUMN: NONE"
                )
                continue

            cursor.execute(
                f'''
                SELECT "{version_column}", COUNT(*)
                FROM "{table}"
                GROUP BY "{version_column}"
                ORDER BY COUNT(*) DESC
                '''
            )

            rows = cursor.fetchall()

            print(f"\n{table}")

            for version, count in rows:

                print(
                    f"  {version!r:<25} "
                    f"{count:>10}"
                )

        print_header(
            "DATA SOURCE AUDIT"
        )

        source_tables = [
            "market_history",
            "market_data",
            "market_microstructure",
            "market_news",
            "market_news_intelligence",
            "news_data",
            "positioning_data",
            "market_whale",
            "social_metrics",
        ]

        for table in source_tables:

            if not table_exists(cursor, table):
                continue

            columns = get_columns(
                cursor,
                table,
            )

            if "source" not in columns:

                if "data_source" in columns:
                    source_column = "data_source"

                else:
                    print(
                        f"{table:<32} SOURCE COLUMN: NONE"
                    )
                    continue

            else:
                source_column = "source"

            cursor.execute(
                f'''
                SELECT "{source_column}", COUNT(*)
                FROM "{table}"
                GROUP BY "{source_column}"
                ORDER BY COUNT(*) DESC
                '''
            )

            rows = cursor.fetchall()

            print(f"\n{table}")

            for source, count in rows:

                print(
                    f"  {str(source):<30}"
                    f"{count:>10}"
                )

        print_header(
            "LINEAGE AUDIT COMPLETE"
        )

        print(
            "Database was opened in READ-ONLY mode."
        )

        print(
            "No INSERT / UPDATE / DELETE / ALTER / CREATE "
            "operation was executed."
        )

    finally:

        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()