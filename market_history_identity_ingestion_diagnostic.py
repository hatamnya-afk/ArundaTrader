import sqlite3

DB_PATH = "arunda.db"
ENGINE_VERSION = "v0.1"

COLLISION_SYMBOLS = (
    "AI", "AVA", "BOB", "EDGE", "FRAX", "GUSD", "LIGHT",
    "LUSD", "U", "UP", "USDF", "VELO", "XAI"
)


def main():
    print("=" * 100)
    print("ARUNDA MARKET HISTORY IDENTITY INGESTION DIAGNOSTIC v0.1")
    print("READ-ONLY / INGESTION PATH ANALYSIS")
    print("=" * 100)
    print(f"Database        : {DB_PATH}")
    print("Mode            : READ ONLY")
    print("Database Write  : DISABLED")
    print(f"Engine Version  : {ENGINE_VERSION}")
    print("=" * 100)

    conn = sqlite3.connect(
        f"file:{DB_PATH}?mode=ro",
        uri=True,
    )
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

        available_columns = {row["name"] for row in columns}

        print(f"Columns         : {len(columns)}")

        print()
        print("=" * 100)
        print("INGESTION FIELD INSPECTION")
        print("=" * 100)

        ingestion_fields = [
            "timestamp",
            "created_at",
            "source",
            "source_timestamp",
            "engine_version",
            "symbol",
            "name",
        ]

        for field in ingestion_fields:
            status = (
                "PRESENT"
                if field in available_columns
                else "MISSING"
            )
            print(f"{field:<22}: {status}")

        print()
        print("=" * 100)
        print("INGESTION PATH SUMMARY")
        print("=" * 100)

        if "source" in available_columns:

            source_rows = conn.execute(
                """
                SELECT
                    COALESCE(source, '<NULL>') AS source,
                    COUNT(*) AS rows,
                    COUNT(DISTINCT symbol) AS symbols,
                    COUNT(DISTINCT name) AS names
                FROM market_history
                GROUP BY source
                ORDER BY rows DESC
                """
            ).fetchall()

            print(
                f"{'SOURCE':<30}"
                f"{'ROWS':>10}"
                f"{'SYMBOLS':>12}"
                f"{'NAMES':>10}"
            )
            print("-" * 100)

            for row in source_rows:
                print(
                    f"{row['source']:<30}"
                    f"{row['rows']:>10}"
                    f"{row['symbols']:>12}"
                    f"{row['names']:>10}"
                )

        else:
            print("Source column unavailable.")

        print()
        print("=" * 100)
        print("ENGINE VERSION INGESTION SUMMARY")
        print("=" * 100)

        if "engine_version" in available_columns:

            version_rows = conn.execute(
                """
                SELECT
                    COALESCE(engine_version, '<NULL>') AS version,
                    COUNT(*) AS rows,
                    COUNT(DISTINCT symbol) AS symbols,
                    COUNT(DISTINCT name) AS names
                FROM market_history
                GROUP BY engine_version
                ORDER BY rows DESC
                """
            ).fetchall()

            print(
                f"{'ENGINE VERSION':<35}"
                f"{'ROWS':>10}"
                f"{'SYMBOLS':>12}"
                f"{'NAMES':>10}"
            )
            print("-" * 100)

            for row in version_rows:
                print(
                    f"{row['version']:<35}"
                    f"{row['rows']:>10}"
                    f"{row['symbols']:>12}"
                    f"{row['names']:>10}"
                )

        else:
            print("Engine version column unavailable.")

        print()
        print("=" * 100)
        print("TIMESTAMP / CREATED_AT RELATIONSHIP")
        print("=" * 100)

        if "timestamp" in available_columns and "created_at" in available_columns:

            relationship_rows = conn.execute(
                """
                SELECT
                    CASE
                        WHEN created_at IS NULL
                            THEN 'CREATED_AT NULL'
                        WHEN timestamp IS NULL
                            THEN 'TIMESTAMP NULL'
                        WHEN timestamp = created_at
                            THEN 'EQUAL'
                        WHEN timestamp < created_at
                            THEN 'TIMESTAMP BEFORE CREATED_AT'
                        WHEN timestamp > created_at
                            THEN 'TIMESTAMP AFTER CREATED_AT'
                        ELSE 'OTHER'
                    END AS relationship,
                    COUNT(*) AS rows
                FROM market_history
                GROUP BY relationship
                ORDER BY rows DESC
                """
            ).fetchall()

            print(
                f"{'RELATIONSHIP':<35}"
                f"{'ROWS':>12}"
            )
            print("-" * 100)

            for row in relationship_rows:
                print(
                    f"{row['relationship']:<35}"
                    f"{row['rows']:>12}"
                )

        print()
        print("=" * 100)
        print("SOURCE TIMESTAMP INSPECTION")
        print("=" * 100)

        if "source_timestamp" in available_columns:

            source_timestamp_rows = conn.execute(
                """
                SELECT
                    COALESCE(source, '<NULL>') AS source,
                    COUNT(*) AS total_rows,
                    SUM(
                        CASE
                            WHEN source_timestamp IS NULL
                            THEN 1 ELSE 0
                        END
                    ) AS null_source_timestamp,
                    SUM(
                        CASE
                            WHEN source_timestamp IS NOT NULL
                            THEN 1 ELSE 0
                        END
                    ) AS non_null_source_timestamp
                FROM market_history
                GROUP BY source
                ORDER BY total_rows DESC
                """
            ).fetchall()

            print(
                f"{'SOURCE':<30}"
                f"{'ROWS':>10}"
                f"{'NULL TS':>12}"
                f"{'NON-NULL TS':>15}"
            )
            print("-" * 100)

            for row in source_timestamp_rows:
                print(
                    f"{row['source']:<30}"
                    f"{row['total_rows']:>10}"
                    f"{row['null_source_timestamp']:>12}"
                    f"{row['non_null_source_timestamp']:>15}"
                )

        else:
            print("Source timestamp column unavailable.")

        print()
        print("=" * 100)
        print("COLLISION INGESTION INSPECTION")
        print("=" * 100)

        for symbol in COLLISION_SYMBOLS:

            print()
            print(f"SYMBOL : {symbol}")
            print("-" * 100)

            if "source" in available_columns and "engine_version" in available_columns:

                rows = conn.execute(
                    """
                    SELECT
                        name,
                        COALESCE(source, '<NULL>') AS source,
                        COALESCE(engine_version, '<NULL>') AS engine_version,
                        COUNT(*) AS rows,
                        MIN(timestamp) AS first_timestamp,
                        MAX(timestamp) AS last_timestamp,
                        MIN(created_at) AS first_created_at,
                        MAX(created_at) AS last_created_at
                    FROM market_history
                    WHERE symbol = ?
                    GROUP BY
                        name,
                        source,
                        engine_version
                    ORDER BY
                        first_created_at,
                        name
                    """,
                    (symbol,),
                ).fetchall()

                print(
                    f"{'NAME':<30}"
                    f"{'SOURCE':<25}"
                    f"{'ENGINE':<28}"
                    f"{'ROWS':>8}"
                )
                print("-" * 100)

                for row in rows:
                    print(
                        f"{str(row['name']):<30}"
                        f"{row['source']:<25}"
                        f"{row['engine_version']:<28}"
                        f"{row['rows']:>8}"
                    )

                    print(
                        f"    first_timestamp : "
                        f"{row['first_timestamp']}"
                    )
                    print(
                        f"    last_timestamp  : "
                        f"{row['last_timestamp']}"
                    )
                    print(
                        f"    first_created   : "
                        f"{row['first_created_at']}"
                    )
                    print(
                        f"    last_created    : "
                        f"{row['last_created_at']}"
                    )

        print()
        print("=" * 100)
        print("COLLISION INTRODUCTION CHECK")
        print("=" * 100)

        for symbol in COLLISION_SYMBOLS:

            rows = conn.execute(
                """
                SELECT
                    name,
                    MIN(created_at) AS first_created_at,
                    MIN(timestamp) AS first_timestamp,
                    COUNT(*) AS rows
                FROM market_history
                WHERE symbol = ?
                GROUP BY name
                ORDER BY first_created_at, name
                """,
                (symbol,),
            ).fetchall()

            print()
            print(symbol)

            for row in rows:
                print(
                    f"  {row['name']:<30}"
                    f" rows={row['rows']:>4}"
                    f" first_created={row['first_created_at']}"
                    f" first_timestamp={row['first_timestamp']}"
                )

        print()
        print("=" * 100)
        print("CMC INGESTION ISOLATION CHECK")
        print("=" * 100)

        if (
            "source" in available_columns
            and "engine_version" in available_columns
        ):

            cmc_rows = conn.execute(
                """
                SELECT
                    COUNT(*) AS rows,
                    COUNT(DISTINCT symbol) AS symbols,
                    COUNT(DISTINCT name) AS names
                FROM market_history
                WHERE source = 'COINMARKETCAP'
                   OR engine_version = 'MARKET_HISTORY_CMC_v0.1'
                """
            ).fetchone()

            print(
                f"CMC Rows                  : "
                f"{cmc_rows['rows']}"
            )
            print(
                f"CMC Distinct Symbols      : "
                f"{cmc_rows['symbols']}"
            )
            print(
                f"CMC Distinct Names        : "
                f"{cmc_rows['names']}"
            )

        print()
        print("=" * 100)
        print("DIAGNOSTIC CONCLUSION")
        print("=" * 100)

        print("Analysis Mode              : READ ONLY")
        print("Database Modification      : NONE")
        print()
        print(
            "No ingestion path was modified."
        )
        print(
            "NO DATABASE MODIFICATIONS WERE PERFORMED."
        )
        print("=" * 100)
        print(
            "ARUNDA MARKET HISTORY IDENTITY INGESTION "
            f"DIAGNOSTIC {ENGINE_VERSION} COMPLETE"
        )
        print("=" * 100)

    finally:
        conn.close()


if __name__ == "__main__":
    main()