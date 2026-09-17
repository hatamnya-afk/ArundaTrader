import sqlite3
from collections import Counter

DB_PATH = "arunda.db"
ENGINE_VERSION = "v0.1"


def main():
    print("=" * 90)
    print(f"ARUNDA MARKET HISTORY DUPLICATE DIAGNOSTIC {ENGINE_VERSION}")
    print("DUPLICATE TIMESTAMP / DATA INTEGRITY ANALYSIS")
    print("=" * 90)
    print(f"Database        : {DB_PATH}")
    print("Mode            : READ ONLY")
    print("Database Write  : DISABLED")
    print(f"Engine Version  : {ENGINE_VERSION}")
    print("=" * 90)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)

    try:
        cursor = conn.cursor()

        print()
        print("DATABASE")
        print("=" * 90)

        cursor.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'market_history'
        """)

        if cursor.fetchone() is None:
            print("ERROR: market_history table not found")
            return

        print("Database        : CONNECTED")
        print("History Table   : market_history")

        # ---------------------------------------------------------
        # GLOBAL DUPLICATE GROUPS
        # ---------------------------------------------------------

        print()
        print("=" * 90)
        print("GLOBAL DUPLICATE TIMESTAMP ANALYSIS")
        print("=" * 90)

        cursor.execute("""
            SELECT
                COUNT(*) AS duplicate_groups,
                COALESCE(SUM(cnt - 1), 0) AS duplicate_rows,
                COALESCE(MAX(cnt), 0) AS max_repetitions
            FROM (
                SELECT symbol, timestamp, COUNT(*) AS cnt
                FROM market_history
                WHERE timestamp IS NOT NULL
                GROUP BY symbol, timestamp
                HAVING COUNT(*) > 1
            )
        """)

        duplicate_groups, duplicate_rows, max_repetitions = cursor.fetchone()

        print(f"Duplicate Groups          : {duplicate_groups}")
        print(f"Duplicate Excess Rows     : {duplicate_rows}")
        print(f"Maximum Repetitions       : {max_repetitions}")

        # ---------------------------------------------------------
        # ASSETS AFFECTED
        # ---------------------------------------------------------

        cursor.execute("""
            SELECT COUNT(*)
            FROM (
                SELECT symbol, timestamp
                FROM market_history
                WHERE timestamp IS NOT NULL
                GROUP BY symbol, timestamp
                HAVING COUNT(*) > 1
            )
        """)

        affected_groups = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(DISTINCT symbol)
            FROM market_history
            WHERE timestamp IS NOT NULL
              AND (symbol, timestamp) IN (
                    SELECT symbol, timestamp
                    FROM market_history
                    WHERE timestamp IS NOT NULL
                    GROUP BY symbol, timestamp
                    HAVING COUNT(*) > 1
              )
        """)

        affected_assets = cursor.fetchone()[0]

        print()
        print("AFFECTED ASSETS")
        print("=" * 90)
        print(f"Assets With Duplicates    : {affected_assets}")
        print(f"Duplicate Groups Checked  : {affected_groups}")

        # ---------------------------------------------------------
        # DUPLICATE DISTRIBUTION
        # ---------------------------------------------------------

        print()
        print("DUPLICATE REPETITION DISTRIBUTION")
        print("=" * 90)

        cursor.execute("""
            SELECT cnt, COUNT(*)
            FROM (
                SELECT symbol, timestamp, COUNT(*) AS cnt
                FROM market_history
                WHERE timestamp IS NOT NULL
                GROUP BY symbol, timestamp
                HAVING COUNT(*) > 1
            )
            GROUP BY cnt
            ORDER BY cnt
        """)

        distribution = cursor.fetchall()

        for repetitions, groups in distribution:
            print(
                f"{repetitions:>3} occurrences : "
                f"{groups:>6} timestamp groups"
            )

        # ---------------------------------------------------------
        # TOP ASSETS
        # ---------------------------------------------------------

        print()
        print("TOP ASSETS BY DUPLICATE GROUPS")
        print("=" * 90)

        cursor.execute("""
            SELECT
                symbol,
                COUNT(*) AS duplicate_groups,
                SUM(cnt - 1) AS excess_rows,
                MAX(cnt) AS max_repetitions
            FROM (
                SELECT
                    symbol,
                    timestamp,
                    COUNT(*) AS cnt
                FROM market_history
                WHERE timestamp IS NOT NULL
                GROUP BY symbol, timestamp
                HAVING COUNT(*) > 1
            )
            GROUP BY symbol
            ORDER BY duplicate_groups DESC, excess_rows DESC
            LIMIT 25
        """)

        print(
            f"{'SYMBOL':<18}"
            f"{'GROUPS':>10}"
            f"{'EXCESS':>10}"
            f"{'MAX REP':>10}"
        )
        print("-" * 90)

        for symbol, groups, excess, maximum in cursor.fetchall():
            print(
                f"{str(symbol):<18}"
                f"{groups:>10}"
                f"{excess:>10}"
                f"{maximum:>10}"
            )

        # ---------------------------------------------------------
        # PRICE CONSISTENCY
        # ---------------------------------------------------------

        print()
        print("DUPLICATE PRICE CONSISTENCY")
        print("=" * 90)

        cursor.execute("""
            SELECT
                SUM(
                    CASE
                        WHEN distinct_prices = 1 THEN 1
                        ELSE 0
                    END
                ),
                SUM(
                    CASE
                        WHEN distinct_prices > 1 THEN 1
                        ELSE 0
                    END
                )
            FROM (
                SELECT
                    symbol,
                    timestamp,
                    COUNT(DISTINCT price) AS distinct_prices
                FROM market_history
                WHERE timestamp IS NOT NULL
                GROUP BY symbol, timestamp
                HAVING COUNT(*) > 1
            )
        """)

        identical_price_groups, conflicting_price_groups = cursor.fetchone()

        identical_price_groups = identical_price_groups or 0
        conflicting_price_groups = conflicting_price_groups or 0

        print(
            f"Same Price In Duplicate   : "
            f"{identical_price_groups}"
        )
        print(
            f"Different Prices           : "
            f"{conflicting_price_groups}"
        )

        total_price_groups = (
            identical_price_groups +
            conflicting_price_groups
        )

        if total_price_groups:
            identical_pct = (
                identical_price_groups /
                total_price_groups *
                100.0
            )
            conflicting_pct = (
                conflicting_price_groups /
                total_price_groups *
                100.0
            )
        else:
            identical_pct = 0.0
            conflicting_pct = 0.0

        print(
            f"Identical Price %          : "
            f"{identical_pct:.2f}%"
        )
        print(
            f"Conflicting Price %       : "
            f"{conflicting_pct:.2f}%"
        )

        # ---------------------------------------------------------
        # SAMPLE CONFLICTING DUPLICATES
        # ---------------------------------------------------------

        print()
        print("SAMPLE DUPLICATES WITH DIFFERENT PRICES")
        print("=" * 90)

        cursor.execute("""
            SELECT
                symbol,
                timestamp,
                COUNT(*) AS occurrences,
                MIN(price) AS min_price,
                MAX(price) AS max_price
            FROM market_history
            WHERE timestamp IS NOT NULL
            GROUP BY symbol, timestamp
            HAVING COUNT(*) > 1
               AND COUNT(DISTINCT price) > 1
            ORDER BY symbol, timestamp
            LIMIT 20
        """)

        rows = cursor.fetchall()

        if rows:
            print(
                f"{'SYMBOL':<18}"
                f"{'OCC':>6}"
                f"{'MIN PRICE':>20}"
                f"{'MAX PRICE':>20}"
                f"  TIMESTAMP"
            )
            print("-" * 90)

            for symbol, timestamp, occurrences, min_price, max_price in rows:
                print(
                    f"{str(symbol):<18}"
                    f"{occurrences:>6}"
                    f"{str(min_price):>20}"
                    f"{str(max_price):>20}"
                    f"  {timestamp}"
                )
        else:
            print("No conflicting-price duplicate samples found.")

        # ---------------------------------------------------------
        # SAMPLE IDENTICAL DUPLICATES
        # ---------------------------------------------------------

        print()
        print("SAMPLE DUPLICATES WITH IDENTICAL PRICES")
        print("=" * 90)

        cursor.execute("""
            SELECT
                symbol,
                timestamp,
                COUNT(*) AS occurrences,
                MIN(price) AS price
            FROM market_history
            WHERE timestamp IS NOT NULL
            GROUP BY symbol, timestamp
            HAVING COUNT(*) > 1
               AND COUNT(DISTINCT price) = 1
            ORDER BY symbol, timestamp
            LIMIT 20
        """)

        rows = cursor.fetchall()

        if rows:
            print(
                f"{'SYMBOL':<18}"
                f"{'OCC':>6}"
                f"{'PRICE':>20}"
                f"  TIMESTAMP"
            )
            print("-" * 90)

            for symbol, timestamp, occurrences, price in rows:
                print(
                    f"{str(symbol):<18}"
                    f"{occurrences:>6}"
                    f"{str(price):>20}"
                    f"  {timestamp}"
                )
        else:
            print("No identical-price duplicate samples found.")

        # ---------------------------------------------------------
        # CONCLUSION
        # ---------------------------------------------------------

        print()
        print("=" * 90)
        print("DIAGNOSTIC CONCLUSION")
        print("=" * 90)

        if duplicate_groups == 0:
            status = "NO_DUPLICATES"
        elif conflicting_price_groups == 0:
            status = "DUPLICATES_WITH_IDENTICAL_PRICES"
        else:
            status = "DUPLICATES_REQUIRE_REVIEW"

        print(f"Duplicate Status            : {status}")
        print(f"Duplicate Groups            : {duplicate_groups}")
        print(f"Duplicate Excess Rows       : {duplicate_rows}")
        print(f"Affected Assets             : {affected_assets}")
        print(f"Conflicting Price Groups    : {conflicting_price_groups}")

        print()
        print("NO DATABASE MODIFICATIONS WERE PERFORMED.")
        print("=" * 90)
        print(
            "ARUNDA MARKET HISTORY DUPLICATE "
            f"DIAGNOSTIC {ENGINE_VERSION} COMPLETE"
        )
        print("=" * 90)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
