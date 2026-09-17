import sqlite3
from datetime import datetime, timezone

DB = "arunda.db"

def main():
    print("=" * 90)
    print("        ARUNDA TECHNICAL / HISTORY DIAGNOSTIC v0.1")
    print("=" * 90)
    print("Mode        : READ ONLY")
    print("Database    : arunda.db")
    print("Writes      : NONE")
    print("=" * 90)

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    # ------------------------------------------------------------
    # DATABASE CHECK
    # ------------------------------------------------------------
    tables = {
        r["name"]
        for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }

    print("\nDatabase Tables:")
    for table in sorted(tables):
        print(f"  - {table}")

    if "market_history" not in tables:
        print("\nERROR: market_history table not found.")
        conn.close()
        return

    # ------------------------------------------------------------
    # HISTORY SCHEMA
    # ------------------------------------------------------------
    columns = [
        r["name"]
        for r in conn.execute(
            "PRAGMA table_info(market_history)"
        ).fetchall()
    ]

    print("\n" + "-" * 90)
    print("MARKET HISTORY SCHEMA")
    print("-" * 90)

    for c in columns:
        print(f"  {c}")

    required = ["symbol", "timestamp", "price"]

    missing = [c for c in required if c not in columns]

    if missing:
        print("\nERROR: Missing required columns:")
        for c in missing:
            print(f"  - {c}")
        conn.close()
        return

    # ------------------------------------------------------------
    # GLOBAL COUNTS
    # ------------------------------------------------------------
    total_rows = conn.execute(
        "SELECT COUNT(*) FROM market_history"
    ).fetchone()[0]

    total_assets = conn.execute(
        """
        SELECT COUNT(DISTINCT symbol)
        FROM market_history
        WHERE symbol IS NOT NULL
        """
    ).fetchone()[0]

    print("\n" + "=" * 90)
    print("GLOBAL HISTORY")
    print("=" * 90)

    print(f"Total Historical Rows : {total_rows}")
    print(f"Unique Assets         : {total_assets}")

    if total_assets:
        print(
            f"Average Rows / Asset  : "
            f"{total_rows / total_assets:.2f}"
        )

    # ------------------------------------------------------------
    # TIME RANGE
    # ------------------------------------------------------------
    time_range = conn.execute(
        """
        SELECT
            MIN(timestamp) AS first_ts,
            MAX(timestamp) AS last_ts
        FROM market_history
        """
    ).fetchone()

    print("\n" + "-" * 90)
    print("GLOBAL TIME RANGE")
    print("-" * 90)

    print(f"First Timestamp : {time_range['first_ts']}")
    print(f"Last Timestamp  : {time_range['last_ts']}")

    # ------------------------------------------------------------
    # DISTINCT TIMESTAMPS
    # ------------------------------------------------------------
    timestamp_count = conn.execute(
        """
        SELECT COUNT(DISTINCT timestamp)
        FROM market_history
        """
    ).fetchone()[0]

    print(f"Distinct Timestamps : {timestamp_count}")

    # ------------------------------------------------------------
    # TIMESTAMP DISTRIBUTION
    # ------------------------------------------------------------
    print("\n" + "-" * 90)
    print("TIMESTAMP DISTRIBUTION")
    print("-" * 90)

    rows = conn.execute(
        """
        SELECT
            timestamp,
            COUNT(*) AS asset_count
        FROM market_history
        GROUP BY timestamp
        ORDER BY timestamp
        """
    ).fetchall()

    for r in rows[:20]:
        print(
            f"{str(r['timestamp']):35} "
            f"Assets={r['asset_count']}"
        )

    if len(rows) > 20:
        print(f"... {len(rows) - 20} more timestamps")

    # ------------------------------------------------------------
    # ASSET HISTORY DEPTH
    # ------------------------------------------------------------
    print("\n" + "=" * 90)
    print("ASSET HISTORY DEPTH")
    print("=" * 90)

    depth_rows = conn.execute(
        """
        SELECT
            symbol,
            COUNT(*) AS rows_count,
            COUNT(DISTINCT timestamp) AS timestamp_count,
            MIN(timestamp) AS first_ts,
            MAX(timestamp) AS last_ts
        FROM market_history
        WHERE symbol IS NOT NULL
        GROUP BY symbol
        ORDER BY rows_count DESC, symbol
        """
    ).fetchall()

    distribution = {}

    for r in depth_rows:
        n = r["rows_count"]
        distribution[n] = distribution.get(n, 0) + 1

    print("\nHistory Depth Distribution:")

    for depth in sorted(distribution):
        print(
            f"  {depth:4} rows : "
            f"{distribution[depth]:4} assets"
        )

    # ------------------------------------------------------------
    # TOP DEPTH ASSETS
    # ------------------------------------------------------------
    print("\n" + "-" * 90)
    print("DEEPEST HISTORIES")
    print("-" * 90)

    for r in depth_rows[:20]:
        print(
            f"{str(r['symbol']):15} "
            f"Rows={r['rows_count']:4} "
            f"Timestamps={r['timestamp_count']:4} "
            f"First={r['first_ts']} "
            f"Last={r['last_ts']}"
        )

    # ------------------------------------------------------------
    # SHALLOW HISTORIES
    # ------------------------------------------------------------
    print("\n" + "-" * 90)
    print("SHALLOW HISTORIES")
    print("-" * 90)

    shallow = sorted(
        depth_rows,
        key=lambda x: (x["rows_count"], x["symbol"])
    )

    for r in shallow[:30]:
        print(
            f"{str(r['symbol']):15} "
            f"Rows={r['rows_count']:4} "
            f"Timestamps={r['timestamp_count']:4} "
            f"First={r['first_ts']} "
            f"Last={r['last_ts']}"
        )

    # ------------------------------------------------------------
    # PRICE QUALITY
    # ------------------------------------------------------------
    print("\n" + "=" * 90)
    print("PRICE DATA QUALITY")
    print("=" * 90)

    null_price = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE price IS NULL
        """
    ).fetchone()[0]

    zero_price = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE price = 0
        """
    ).fetchone()[0]

    negative_price = conn.execute(
        """
        SELECT COUNT(*)
        FROM market_history
        WHERE price < 0
        """
    ).fetchone()[0]

    print(f"NULL Prices     : {null_price}")
    print(f"Zero Prices     : {zero_price}")
    print(f"Negative Prices : {negative_price}")

    # ------------------------------------------------------------
    # DUPLICATES
    # ------------------------------------------------------------
    print("\n" + "=" * 90)
    print("DUPLICATE CHECK")
    print("=" * 90)

    duplicate_groups = conn.execute(
        """
        SELECT
            symbol,
            timestamp,
            COUNT(*) AS cnt
        FROM market_history
        GROUP BY symbol, timestamp
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC
        """
    ).fetchall()

    duplicate_rows = sum(
        r["cnt"] - 1 for r in duplicate_groups
    )

    print(f"Duplicate Groups : {len(duplicate_groups)}")
    print(f"Duplicate Rows   : {duplicate_rows}")

    for r in duplicate_groups[:20]:
        print(
            f"{r['symbol']:15} "
            f"{r['timestamp']} "
            f"Count={r['cnt']}"
        )

    # ------------------------------------------------------------
    # INTERVAL ANALYSIS
    # ------------------------------------------------------------
    print("\n" + "=" * 90)
    print("TIMESTAMP INTERVAL ANALYSIS")
    print("=" * 90)

    timestamps = [
        r["timestamp"]
        for r in conn.execute(
            """
            SELECT DISTINCT timestamp
            FROM market_history
            ORDER BY timestamp
            """
        ).fetchall()
    ]

    parsed = []

    for ts in timestamps:
        try:
            value = ts.replace("Z", "+00:00")

            dt = datetime.fromisoformat(value)

            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

            parsed.append(dt)
        except Exception:
            pass

    intervals = []

    for i in range(1, len(parsed)):
        seconds = (
            parsed[i] - parsed[i - 1]
        ).total_seconds()

        intervals.append(seconds)

    if intervals:
        intervals_sorted = sorted(intervals)

        def percentile(values, p):
            if not values:
                return None

            index = int(
                round(
                    (len(values) - 1) * p
                )
            )

            return values[index]

        print(
            f"Minimum Interval : "
            f"{min(intervals):.2f} sec"
        )

        print(
            f"Median Interval  : "
            f"{percentile(intervals_sorted, 0.50):.2f} sec"
        )

        print(
            f"P90 Interval     : "
            f"{percentile(intervals_sorted, 0.90):.2f} sec"
        )

        print(
            f"Maximum Interval : "
            f"{max(intervals):.2f} sec"
        )

    else:
        print("Not enough timestamps.")

    # ------------------------------------------------------------
    # TECHNICAL REQUIREMENT CHECK
    # ------------------------------------------------------------
    print("\n" + "=" * 90)
    print("TECHNICAL FEATURE REQUIREMENT CHECK")
    print("=" * 90)

    requirements = [
        ("return_1", 2),
        ("return_3", 4),
        ("return_5", 6),
        ("return_10", 11),
        ("return_20", 21),
        ("SMA_20", 20),
        ("EMA_20", 20),
        ("RSI_14", 15),
        ("VOLATILITY_20", 21),
    ]

    print(
        f"{'Feature':20} "
        f"{'Required Rows':15} "
        f"{'Assets Capable':15} "
        f"{'Status'}"
    )

    print("-" * 75)

    for feature, required_rows in requirements:

        capable = conn.execute(
            """
            SELECT COUNT(*)
            FROM (
                SELECT symbol
                FROM market_history
                WHERE symbol IS NOT NULL
                GROUP BY symbol
                HAVING COUNT(*) >= ?
            )
            """,
            (required_rows,),
        ).fetchone()[0]

        status = (
            "AVAILABLE"
            if capable > 0
            else "INSUFFICIENT_HISTORY"
        )

        print(
            f"{feature:20} "
            f"{required_rows:<15} "
            f"{capable:<15} "
            f"{status}"
        )

    # ------------------------------------------------------------
    # MARKET STATE RELATION
    # ------------------------------------------------------------
    print("\n" + "=" * 90)
    print("CURRENT MARKET STATE RELATION")
    print("=" * 90)

    if "market_state" in tables:

        state_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_state
            """
        ).fetchone()[0]

        state_assets = conn.execute(
            """
            SELECT COUNT(DISTINCT symbol)
            FROM market_state
            WHERE symbol IS NOT NULL
            """
        ).fetchone()[0]

        print(f"Market State Rows   : {state_rows}")
        print(f"Market State Assets : {state_assets}")

    else:
        print("market_state table not found.")

    # ------------------------------------------------------------
    # TECHNICAL RELATION
    # ------------------------------------------------------------
    print("\n" + "=" * 90)
    print("CURRENT TECHNICAL RELATION")
    print("=" * 90)

    if "market_technical" in tables:

        tech_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM market_technical
            """
        ).fetchone()[0]

        tech_assets = conn.execute(
            """
            SELECT COUNT(DISTINCT symbol)
            FROM market_technical
            WHERE symbol IS NOT NULL
            """
        ).fetchone()[0]

        print(f"Technical Rows   : {tech_rows}")
        print(f"Technical Assets : {tech_assets}")

    else:
        print("market_technical table not found.")

    # ------------------------------------------------------------
    # FINAL DIAGNOSIS
    # ------------------------------------------------------------
    print("\n" + "=" * 90)
    print("DIAGNOSTIC CONCLUSION")
    print("=" * 90)

    if total_rows == 0:
        conclusion = "NO_HISTORY"
    elif total_assets == 0:
        conclusion = "NO_ASSETS"
    elif timestamp_count <= 1:
        conclusion = "SINGLE_SNAPSHOT"
    elif total_rows / max(total_assets, 1) < 5:
        conclusion = "VERY_SHALLOW_HISTORY"
    elif total_rows / max(total_assets, 1) < 20:
        conclusion = "LIMITED_HISTORY"
    else:
        conclusion = "TECHNICAL_HISTORY_USABLE"

    print(f"History Diagnosis : {conclusion}")

    print("\nNo database modifications were performed.")

    print("=" * 90)
    print("       ARUNDA TECHNICAL / HISTORY DIAGNOSTIC v0.1 COMPLETE")
    print("=" * 90)

    conn.close()


if __name__ == "__main__":
    main()
