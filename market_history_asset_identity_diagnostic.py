import sqlite3

DB_PATH = "arunda.db"
ENGINE_VERSION = "v0.1"


def main():
    print("=" * 100)
    print(f"ARUNDA MARKET HISTORY ASSET IDENTITY DIAGNOSTIC {ENGINE_VERSION}")
    print("SYMBOL / NAME IDENTITY COLLISION ANALYSIS")
    print("=" * 100)
    print(f"Database        : {DB_PATH}")
    print("Mode            : READ ONLY")
    print("Database Write  : DISABLED")
    print(f"Engine Version  : {ENGINE_VERSION}")
    print("=" * 100)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    try:
        cursor = conn.cursor()

        # ---------------------------------------------------------
        # TABLE CHECK
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'market_history'
        """)

        if cursor.fetchone() is None:
            print("ERROR: market_history table not found")
            return

        # ---------------------------------------------------------
        # GLOBAL IDENTITY SUMMARY
        # ---------------------------------------------------------

        print()
        print("GLOBAL ASSET IDENTITY")
        print("=" * 100)

        cursor.execute("""
            SELECT COUNT(DISTINCT symbol)
            FROM market_history
            WHERE symbol IS NOT NULL
        """)
        total_symbols = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT name)
            FROM market_history
            WHERE name IS NOT NULL
        """)
        total_names = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT symbol
                FROM market_history
                WHERE symbol IS NOT NULL
                GROUP BY symbol
                HAVING COUNT(DISTINCT name) > 1
            )
        """)
        collision_symbols = cursor.fetchone()[0]

        print(f"Distinct Symbols             : {total_symbols}")
        print(f"Distinct Names                : {total_names}")
        print(f"Symbols With Multiple Names   : {collision_symbols}")

        # ---------------------------------------------------------
        # COLLISION SUMMARY
        # ---------------------------------------------------------

        print()
        print("SYMBOL / NAME COLLISIONS")
        print("=" * 100)

        cursor.execute("""
            SELECT
                symbol,
                COUNT(DISTINCT name) AS name_count,
                COUNT(*) AS total_rows
            FROM market_history
            WHERE symbol IS NOT NULL
            GROUP BY symbol
            HAVING COUNT(DISTINCT name) > 1
            ORDER BY name_count DESC, symbol
        """)

        collisions = cursor.fetchall()

        if not collisions:
            print("No symbol/name collisions found.")
        else:
            print(
                f"{'SYMBOL':<18}"
                f"{'NAMES':>10}"
                f"{'ROWS':>12}"
            )
            print("-" * 100)

            for symbol, name_count, total_rows in collisions:
                print(
                    f"{str(symbol):<18}"
                    f"{name_count:>10}"
                    f"{total_rows:>12}"
                )

        # ---------------------------------------------------------
        # DETAILED COLLISION DATA
        # ---------------------------------------------------------

        print()
        print("DETAILED COLLISION DATA")
        print("=" * 100)

        for symbol, _, _ in collisions:

            print()
            print("-" * 100)
            print(f"SYMBOL : {symbol}")
            print("-" * 100)

            cursor.execute("""
                SELECT
                    name,
                    COUNT(*) AS rows,
                    MIN(price) AS min_price,
                    MAX(price) AS max_price,
                    MIN(market_cap) AS min_market_cap,
                    MAX(market_cap) AS max_market_cap,
                    MIN(volume_24h) AS min_volume,
                    MAX(volume_24h) AS max_volume,
                    MIN(timestamp) AS first_timestamp,
                    MAX(timestamp) AS last_timestamp
                FROM market_history
                WHERE symbol = ?
                GROUP BY name
                ORDER BY name
            """, (symbol,))

            rows = cursor.fetchall()

            print(
                f"{'NAME':<25}"
                f"{'ROWS':>8}"
                f"{'MIN PRICE':>16}"
                f"{'MAX PRICE':>16}"
            )
            print("-" * 100)

            for (
                name,
                row_count,
                min_price,
                max_price,
                min_market_cap,
                max_market_cap,
                min_volume,
                max_volume,
                first_timestamp,
                last_timestamp
            ) in rows:

                print(
                    f"{str(name):<25}"
                    f"{row_count:>8}"
                    f"{str(min_price):>16}"
                    f"{str(max_price):>16}"
                )

                print(
                    f"    Market Cap : "
                    f"{min_market_cap} → {max_market_cap}"
                )

                print(
                    f"    Volume     : "
                    f"{min_volume} → {max_volume}"
                )

                print(
                    f"    First      : "
                    f"{first_timestamp}"
                )

                print(
                    f"    Last       : "
                    f"{last_timestamp}"
                )

        # ---------------------------------------------------------
        # EXACT OVERLAP ANALYSIS
        # ---------------------------------------------------------

        print()
        print("=" * 100)
        print("TIMESTAMP OVERLAP ANALYSIS")
        print("=" * 100)

        for symbol, _, _ in collisions:

            cursor.execute("""
                SELECT
                    COUNT(*) AS overlapping_timestamps
                FROM (
                    SELECT timestamp
                    FROM market_history
                    WHERE symbol = ?
                    GROUP BY timestamp
                    HAVING COUNT(DISTINCT name) > 1
                )
            """, (symbol,))

            overlap = cursor.fetchone()[0]

            print(
                f"{str(symbol):<18}"
                f": {overlap:>6} timestamps contain multiple names"
            )

        # ---------------------------------------------------------
        # IDENTITY UNIQUENESS CHECK
        # ---------------------------------------------------------

        print()
        print("=" * 100)
        print("IDENTITY UNIQUENESS CHECK")
        print("=" * 100)

        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT symbol, name
                FROM market_history
                WHERE symbol IS NOT NULL
                  AND name IS NOT NULL
                GROUP BY symbol, name
            )
        """)

        symbol_name_pairs = cursor.fetchone()[0]

        print(
            f"Distinct Symbol/Name Pairs    : "
            f"{symbol_name_pairs}"
        )

        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT symbol, name
                FROM market_history
                WHERE symbol IS NOT NULL
                  AND name IS NOT NULL
                GROUP BY symbol, name
                HAVING COUNT(*) > 1
            )
        """)

        repeated_pairs = cursor.fetchone()[0]

        print(
            f"Repeated Symbol/Name Pairs    : "
            f"{repeated_pairs}"
        )

        # ---------------------------------------------------------
        # CONCLUSION
        # ---------------------------------------------------------

        print()
        print("=" * 100)
        print("DIAGNOSTIC CONCLUSION")
        print("=" * 100)

        if collision_symbols == 0:
            status = "NO_IDENTITY_COLLISIONS"
        else:
            status = "IDENTITY_COLLISIONS_PRESENT"

        print(f"Identity Status               : {status}")
        print(f"Collision Symbols             : {collision_symbols}")
        print(f"Distinct Symbols              : {total_symbols}")
        print(f"Distinct Names                : {total_names}")
        print(
            f"Distinct Symbol/Name Pairs    : "
            f"{symbol_name_pairs}"
        )

        print()
        print("NO DATABASE MODIFICATIONS WERE PERFORMED.")
        print("=" * 100)
        print(
            "ARUNDA MARKET HISTORY ASSET IDENTITY "
            f"DIAGNOSTIC {ENGINE_VERSION} COMPLETE"
        )
        print("=" * 100)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
