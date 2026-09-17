import sqlite3
from pathlib import Path


DB_PATH = Path("arunda.db")


def get_tables(conn):
    return conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()


def get_columns(conn, table):
    return conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()


def get_row_count(conn, table):
    return conn.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()[0]


def get_sample(conn, table, limit=3):
    return conn.execute(
        f'SELECT * FROM "{table}" LIMIT ?',
        (limit,)
    ).fetchall()


def get_indexes(conn, table):
    return conn.execute(
        f'PRAGMA index_list("{table}")'
    ).fetchall()


def print_separator(char="=", size=100):
    print(char * size)


def main():

    print_separator()
    print("              ARUNDA DATABASE AUDIT v0.1")
    print_separator()

    print(f"Database : {DB_PATH.resolve()}")
    print(f"Exists   : {DB_PATH.exists()}")

    if not DB_PATH.exists():
        print()
        print("ERROR: arunda.db not found.")
        return 1

    print(f"Size     : {DB_PATH.stat().st_size:,} bytes")

    conn = sqlite3.connect(DB_PATH)

    try:

        tables = get_tables(conn)

        print()
        print_separator()
        print("DATABASE TABLES")
        print_separator()

        if not tables:
            print("NO TABLES FOUND")
            return 0

        print(f"Table Count : {len(tables)}")
        print()

        for (table,) in tables:

            print_separator("-")
            print(f"TABLE : {table}")
            print_separator("-")

            columns = get_columns(conn, table)
            row_count = get_row_count(conn, table)
            indexes = get_indexes(conn, table)

            print(f"Rows    : {row_count:,}")
            print(f"Columns : {len(columns)}")
            print()

            print("SCHEMA")
            print(
                f"{'CID':<6}"
                f"{'NAME':<28}"
                f"{'TYPE':<15}"
                f"{'NOTNULL':<10}"
                f"{'DEFAULT':<20}"
                f"{'PK'}"
            )

            print("-" * 100)

            for cid, name, dtype, notnull, default, pk in columns:

                print(
                    f"{cid:<6}"
                    f"{name:<28}"
                    f"{dtype:<15}"
                    f"{notnull:<10}"
                    f"{str(default):<20}"
                    f"{pk}"
                )

            print()

            print("INDEXES")

            if indexes:

                for index in indexes:
                    print(index)

            else:

                print("NONE")

            print()

            print("SAMPLE ROWS")

            sample = get_sample(conn, table)

            if not sample:

                print("NO ROWS")

            else:

                column_names = [
                    column[1]
                    for column in columns
                ]

                for row_number, row in enumerate(sample, 1):

                    print()
                    print(f"ROW #{row_number}")

                    for name, value in zip(
                        column_names,
                        row
                    ):

                        print(
                            f"  {name:<28}: {value}"
                        )

            print()

        # ====================================================
        # SPECIAL MARKET DATA AUDIT
        # ====================================================

        print_separator()
        print("ARUNDA MARKET DATA STRUCTURE AUDIT")
        print_separator()

        market_tables = [
            "market_universe",
            "market_state",
            "market_history",
            "market_data",
        ]

        for table in market_tables:

            if not any(
                table == row[0]
                for row in tables
            ):
                print()
                print(f"{table:<20}: NOT FOUND")
                continue

            count = get_row_count(
                conn,
                table
            )

            print()
            print(f"{table:<20}: {count:,} rows")

            columns = [
                row[1]
                for row in get_columns(
                    conn,
                    table
                )
            ]

            print(
                "Columns              : "
                + ", ".join(columns)
            )

            # -----------------------------------------------
            # Symbol coverage
            # -----------------------------------------------

            if "symbol" in columns:

                symbol_count = conn.execute(
                    f'''
                    SELECT COUNT(DISTINCT symbol)
                    FROM "{table}"
                    WHERE symbol IS NOT NULL
                    '''
                ).fetchone()[0]

                print(
                    f"Unique Symbols       : {symbol_count:,}"
                )

                top_symbols = conn.execute(
                    f'''
                    SELECT symbol, COUNT(*) AS cnt
                    FROM "{table}"
                    WHERE symbol IS NOT NULL
                    GROUP BY symbol
                    ORDER BY cnt DESC
                    LIMIT 10
                    '''
                ).fetchall()

                if top_symbols:

                    print("Top Symbols:")

                    for symbol, cnt in top_symbols:

                        print(
                            f"  {symbol:<15} {cnt:,}"
                        )

            # -----------------------------------------------
            # Timestamp coverage
            # -----------------------------------------------

            timestamp_column = None

            for candidate in [
                "timestamp",
                "source_timestamp",
                "created_at",
            ]:

                if candidate in columns:

                    timestamp_column = candidate
                    break

            if timestamp_column:

                result = conn.execute(
                    f'''
                    SELECT
                        MIN("{timestamp_column}"),
                        MAX("{timestamp_column}")
                    FROM "{table}"
                    '''
                ).fetchone()

                print(
                    f"Time Range           : "
                    f"{result[0]} → {result[1]}"
                )

        # ====================================================
        # MARKET HISTORY DEPTH
        # ====================================================

        if any(
            table == "market_history"
            for table in [row[0] for row in tables]
        ):

            print()
            print_separator()
            print("MARKET HISTORY DEPTH AUDIT")
            print_separator()

            rows = conn.execute("""
                SELECT
                    symbol,
                    COUNT(*) AS records,
                    MIN(timestamp),
                    MAX(timestamp)
                FROM market_history
                GROUP BY symbol
                ORDER BY records DESC, symbol
                LIMIT 30
            """).fetchall()

            print(
                f"{'SYMBOL':<15}"
                f"{'RECORDS':<12}"
                f"{'FIRST':<30}"
                f"{'LAST':<30}"
            )

            print("-" * 100)

            for symbol, records, first_seen, last_seen in rows:

                print(
                    f"{str(symbol):<15}"
                    f"{records:<12}"
                    f"{str(first_seen):<30}"
                    f"{str(last_seen):<30}"
                )

        # ====================================================
        # MARKET DATA SOURCE AUDIT
        # ====================================================

        if any(
            table == "market_data"
            for table in [row[0] for row in tables]
        ):

            print()
            print_separator()
            print("MARKET DATA SOURCE AUDIT")
            print_separator()

            columns = [
                row[1]
                for row in get_columns(
                    conn,
                    "market_data"
                )
            ]

            if "source" in columns:

                rows = conn.execute("""
                    SELECT
                        source,
                        COUNT(*) AS records
                    FROM market_data
                    GROUP BY source
                    ORDER BY records DESC
                """).fetchall()

                print(
                    f"{'SOURCE':<45}"
                    f"{'RECORDS'}"
                )

                print("-" * 70)

                for source, records in rows:

                    print(
                        f"{str(source):<45}"
                        f"{records:,}"
                    )

            if "timeframe" in columns:

                print()

                rows = conn.execute("""
                    SELECT
                        timeframe,
                        COUNT(*) AS records
                    FROM market_data
                    GROUP BY timeframe
                    ORDER BY records DESC
                """).fetchall()

                print(
                    f"{'TIMEFRAME':<20}"
                    f"{'RECORDS'}"
                )

                print("-" * 40)

                for timeframe, records in rows:

                    print(
                        f"{str(timeframe):<20}"
                        f"{records:,}"
                    )

        # ====================================================
        # INTEGRITY CHECK
        # ====================================================

        print()
        print_separator()
        print("SQLITE INTEGRITY CHECK")
        print_separator()

        integrity = conn.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        print(
            f"Integrity : {integrity}"
        )

        print()
        print_separator()
        print("AUDIT COMPLETE")
        print_separator()

        return 0

    finally:

        conn.close()


if __name__ == "__main__":
    raise SystemExit(
        main()
    )