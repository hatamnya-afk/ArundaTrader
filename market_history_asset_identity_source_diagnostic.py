import sqlite3

DB_PATH = "arunda.db"
ENGINE_VERSION = "v0.1"

COLLISION_SYMBOLS = (
    "AI", "AVA", "BOB", "EDGE", "FRAX", "GUSD", "LIGHT",
    "LUSD", "U", "UP", "USDF", "VELO", "XAI"
)


def main():
    print("=" * 100)
    print("ARUNDA MARKET HISTORY ASSET IDENTITY SOURCE DIAGNOSTIC v0.1")
    print("READ-ONLY / COLLISION SOURCE ANALYSIS")
    print("=" * 100)
    print(f"Database        : {DB_PATH}")
    print("Mode            : READ ONLY")
    print("Database Write  : DISABLED")
    print(f"Engine Version  : {ENGINE_VERSION}")
    print("=" * 100)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row

    try:
        print()
        print("=" * 100)
        print("DATABASE")
        print("=" * 100)

        print("Database        : CONNECTED")

        table_exists = conn.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type='table'
              AND name='market_history'
            """
        ).fetchone()

        if not table_exists:
            print("History Table   : NOT FOUND")
            return

        print("History Table   : market_history")

        columns = conn.execute(
            "PRAGMA table_info(market_history)"
        ).fetchall()

        print(f"Columns         : {len(columns)}")

        print()
        print("=" * 100)
        print("IDENTITY SOURCE FIELD INSPECTION")
        print("=" * 100)

        available_columns = {row["name"] for row in columns}

        source_fields = [
            "symbol",
            "name",
            "rank",
            "source",
            "source_timestamp",
            "engine_version",
            "created_at",
            "timestamp",
        ]

        print("Available identity/source fields:")
        for field in source_fields:
            status = "PRESENT" if field in available_columns else "MISSING"
            print(f"{field:<22}: {status}")

        print()
        print("=" * 100)
        print("COLLISION SOURCE ANALYSIS")
        print("=" * 100)

        for symbol in COLLISION_SYMBOLS:

            print()
            print("-" * 100)
            print(f"SYMBOL : {symbol}")
            print("-" * 100)

            rows = conn.execute(
                """
                SELECT
                    name,
                    COUNT(*) AS row_count,
                    MIN(timestamp) AS first_timestamp,
                    MAX(timestamp) AS last_timestamp,
                    MIN(created_at) AS first_created_at,
                    MAX(created_at) AS last_created_at
                FROM market_history
                WHERE symbol = ?
                GROUP BY name
                ORDER BY first_timestamp
                """,
                (symbol,),
            ).fetchall()

            for row in rows:

                print()
                print(f"NAME                : {row['name']}")
                print(f"Rows                : {row['row_count']}")
                print(f"First Timestamp     : {row['first_timestamp']}")
                print(f"Last Timestamp      : {row['last_timestamp']}")
                print(f"First Created At    : {row['first_created_at']}")
                print(f"Last Created At     : {row['last_created_at']}")

                if "source" in available_columns:
                    source_rows = conn.execute(
                        """
                        SELECT
                            COALESCE(source, '<NULL>') AS source,
                            COUNT(*) AS count
                        FROM market_history
                        WHERE symbol = ?
                          AND name = ?
                        GROUP BY source
                        ORDER BY count DESC
                        """,
                        (symbol, row["name"]),
                    ).fetchall()

                    print("Sources:")
                    for source_row in source_rows:
                        print(
                            f"  {source_row['source']:<30}"
                            f" {source_row['count']:>6}"
                        )

                if "engine_version" in available_columns:
                    version_rows = conn.execute(
                        """
                        SELECT
                            COALESCE(engine_version, '<NULL>') AS version,
                            COUNT(*) AS count
                        FROM market_history
                        WHERE symbol = ?
                          AND name = ?
                        GROUP BY engine_version
                        ORDER BY count DESC
                        """,
                        (symbol, row["name"]),
                    ).fetchall()

                    print("Engine Versions:")
                    for version_row in version_rows:
                        print(
                            f"  {version_row['version']:<30}"
                            f" {version_row['count']:>6}"
                        )

                if "rank" in available_columns:
                    rank_rows = conn.execute(
                        """
                        SELECT
                            COUNT(*) AS count
                        FROM market_history
                        WHERE symbol = ?
                          AND name = ?
                          AND rank IS NOT NULL
                        """,
                        (symbol, row["name"]),
                    ).fetchone()

                    print(
                        f"Non-NULL Rank Rows  : "
                        f"{rank_rows['count']}"
                    )

        print()
        print("=" * 100)
        print("TIMESTAMP INTRODUCTION ANALYSIS")
        print("=" * 100)

        for symbol in COLLISION_SYMBOLS:

            rows = conn.execute(
                """
                SELECT
                    name,
                    MIN(timestamp) AS first_timestamp,
                    MIN(created_at) AS first_created_at,
                    COUNT(*) AS rows
                FROM market_history
                WHERE symbol = ?
                GROUP BY name
                ORDER BY first_timestamp
                """,
                (symbol,),
            ).fetchall()

            print()
            print(f"{symbol}")

            for row in rows:
                print(
                    f"  {row['name']:<30}"
                    f" rows={row['rows']:>4}"
                    f" first_timestamp={row['first_timestamp']}"
                    f" first_created_at={row['first_created_at']}"
                )

        print()
        print("=" * 100)
        print("SOURCE CONSISTENCY CHECK")
        print("=" * 100)

        if "source" in available_columns:

            source_collision_rows = conn.execute(
                """
                SELECT
                    symbol,
                    COUNT(DISTINCT COALESCE(source, '<NULL>')) AS source_count
                FROM market_history
                WHERE symbol IN (
                    'AI','AVA','BOB','EDGE','FRAX','GUSD','LIGHT',
                    'LUSD','U','UP','USDF','VELO','XAI'
                )
                GROUP BY symbol
                HAVING COUNT(DISTINCT COALESCE(source, '<NULL>')) > 1
                ORDER BY symbol
                """
            ).fetchall()

            print(
                f"Symbols With Multiple Sources : "
                f"{len(source_collision_rows)}"
            )

            for row in source_collision_rows:
                print(
                    f"{row['symbol']:<12}"
                    f" sources={row['source_count']}"
                )

        else:
            print("Source column unavailable.")

        print()
        print("=" * 100)
        print("DIAGNOSTIC CONCLUSION")
        print("=" * 100)

        print("Collision Symbols          : 13")
        print("Analysis Mode              : READ ONLY")
        print("Database Modification      : NONE")
        print()
        print("NO DATABASE MODIFICATIONS WERE PERFORMED.")
        print("=" * 100)
        print(
            "ARUNDA MARKET HISTORY ASSET IDENTITY SOURCE "
            f"DIAGNOSTIC {ENGINE_VERSION} COMPLETE"
        )
        print("=" * 100)

    finally:
        conn.close()


if __name__ == "__main__":
    main()
