import sqlite3

DB = "arunda.db"

REQUIRED_COLUMNS = {
    "open_interest": "REAL",
    "open_interest_change_pct": "REAL",
    "funding_rate": "REAL",
    "long_short_ratio": "REAL",
    "long_pct": "REAL",
    "short_pct": "REAL",
    "liquidation_long": "REAL",
    "liquidation_short": "REAL",
    "liquidation_total": "REAL",
    "positioning_score": "REAL",
    "source": "TEXT",
    "data_quality": "TEXT",
    "latency_ms": "REAL",
    "engine_version": "TEXT",
}


def main():

    print("=" * 80)
    print("       ARUNDA POSITIONING DATABASE MIGRATION")
    print("=" * 80)

    conn = sqlite3.connect(DB)

    # --------------------------------------------------------
    # CREATE TABLE IF NOT EXISTS
    # --------------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS positioning_data (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT NOT NULL,
            market TEXT NOT NULL,

            open_interest REAL,
            open_interest_change_pct REAL,

            funding_rate REAL,

            long_short_ratio REAL,
            long_pct REAL,
            short_pct REAL,

            liquidation_long REAL,
            liquidation_short REAL,
            liquidation_total REAL,

            positioning_score REAL,

            source TEXT,
            data_quality TEXT,

            latency_ms REAL,

            engine_version TEXT,

            UNIQUE(market, timestamp)
        )
    """)

    # --------------------------------------------------------
    # CHECK EXISTING COLUMNS
    # --------------------------------------------------------

    rows = conn.execute(
        "PRAGMA table_info(positioning_data)"
    ).fetchall()

    existing = {
        row[1]
        for row in rows
    }

    print()
    print("Existing columns:")
    print("-" * 80)

    for column in sorted(existing):
        print(f"  {column}")

    # --------------------------------------------------------
    # ADD MISSING COLUMNS
    # --------------------------------------------------------

    print()
    print("Checking schema...")
    print("-" * 80)

    added = 0

    for column, column_type in REQUIRED_COLUMNS.items():

        if column not in existing:

            print(
                f"ADDING  : {column} "
                f"({column_type})"
            )

            conn.execute(
                f"""
                ALTER TABLE positioning_data
                ADD COLUMN {column} {column_type}
                """
            )

            added += 1

        else:

            print(
                f"EXISTS  : {column}"
            )

    conn.commit()

    # --------------------------------------------------------
    # FINAL SCHEMA
    # --------------------------------------------------------

    rows = conn.execute(
        "PRAGMA table_info(positioning_data)"
    ).fetchall()

    print()
    print("=" * 80)
    print("FINAL POSITIONING_DATA SCHEMA")
    print("=" * 80)

    for row in rows:
        print(
            f"{row[0]:2} | "
            f"{row[1]:30} | "
            f"{row[2]}"
        )

    conn.close()

    print()
    print("=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)

    print(
        f"Columns added : {added}"
    )

    print(
        "Database      : arunda.db"
    )

    print(
        "Table         : positioning_data"
    )

    print("=" * 80)


if __name__ == "__main__":
    main()