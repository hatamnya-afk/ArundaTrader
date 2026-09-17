import sqlite3

DB_PATH = "arunda.db"
ENGINE_VERSION = "v0.1"

SAMPLES = 10


def main():
    print("=" * 100)
    print(f"ARUNDA MARKET HISTORY DUPLICATE PAIR INSPECTION {ENGINE_VERSION}")
    print("READ-ONLY SAMPLE INSPECTION")
    print("=" * 100)
    print(f"Database        : {DB_PATH}")
    print("Mode            : READ ONLY")
    print("Database Write  : DISABLED")
    print(f"Samples         : {SAMPLES}")
    print("=" * 100)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    try:
        cursor = conn.cursor()

        # ---------------------------------------------------------
        # TABLE STRUCTURE
        # ---------------------------------------------------------

        cursor.execute("PRAGMA table_info(market_history)")
        columns = cursor.fetchall()

        if not columns:
            print("ERROR: market_history table not found")
            return

        column_names = [column[1] for column in columns]

        print()
        print("TABLE COLUMNS")
        print("=" * 100)

        for index, name in enumerate(column_names, start=1):
            print(f"{index:>2}. {name}")

        # ---------------------------------------------------------
        # DUPLICATE SAMPLE PAIRS
        # ---------------------------------------------------------

        print()
        print("=" * 100)
        print("DUPLICATE PAIR SAMPLES")
        print("=" * 100)

        cursor.execute("""
            SELECT
                symbol,
                timestamp
            FROM market_history
            WHERE timestamp IS NOT NULL
            GROUP BY symbol, timestamp
            HAVING COUNT(*) > 1
            ORDER BY symbol, timestamp
            LIMIT ?
        """, (SAMPLES,))

        duplicate_keys = cursor.fetchall()

        if not duplicate_keys:
            print("No duplicate pairs found.")
            return

        placeholders = ", ".join(["?"] * len(column_names))
        select_columns = ", ".join(
            f'"{name}"' for name in column_names
        )

        for sample_number, (symbol, timestamp) in enumerate(
            duplicate_keys,
            start=1
        ):
            print()
            print("-" * 100)
            print(f"DUPLICATE SAMPLE #{sample_number}")
            print(f"Symbol          : {symbol}")
            print(f"Timestamp       : {timestamp}")
            print("-" * 100)

            cursor.execute(
                f"""
                SELECT {select_columns}
                FROM market_history
                WHERE symbol = ?
                  AND timestamp = ?
                ORDER BY rowid
                """,
                (symbol, timestamp)
            )

            rows = cursor.fetchall()

            for row_number, row in enumerate(rows, start=1):
                print()
                print(f"--- RECORD {row_number} ---")

                for column_name, value in zip(column_names, row):
                    print(
                        f"{column_name:<24}: {value}"
                    )

        # ---------------------------------------------------------
        # PAIR DIFFERENCE SUMMARY
        # ---------------------------------------------------------

        print()
        print("=" * 100)
        print("PAIR DIFFERENCE SUMMARY")
        print("=" * 100)

        differing_columns = set()

        for symbol, timestamp in duplicate_keys:
            cursor.execute(
                f"""
                SELECT {select_columns}
                FROM market_history
                WHERE symbol = ?
                  AND timestamp = ?
                ORDER BY rowid
                """,
                (symbol, timestamp)
            )

            rows = cursor.fetchall()

            if len(rows) >= 2:
                first = rows[0]
                second = rows[1]

                for column_name, value_a, value_b in zip(
                    column_names,
                    first,
                    second
                ):
                    if value_a != value_b:
                        differing_columns.add(column_name)

        if differing_columns:
            print("Columns differing between duplicate pairs:")

            for column_name in column_names:
                if column_name in differing_columns:
                    print(f" - {column_name}")
        else:
            print("No differing columns detected.")

        print()
        print("=" * 100)
        print("DIAGNOSTIC CONCLUSION")
        print("=" * 100)
        print(f"Duplicate Samples Inspected : {len(duplicate_keys)}")
        print(
            "Database Modification       : NONE"
        )
        print()
        print("NO DATABASE MODIFICATIONS WERE PERFORMED.")
        print("=" * 100)
        print(
            "ARUNDA MARKET HISTORY DUPLICATE "
            f"PAIR INSPECTION {ENGINE_VERSION} COMPLETE"
        )
        print("=" * 100)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
