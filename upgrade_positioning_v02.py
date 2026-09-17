import sqlite3

DB = "arunda.db"


def main():

    print("=" * 80)
    print("       ARUNDA POSITIONING DB v0.2 MIGRATION")
    print("=" * 80)

    conn = sqlite3.connect(DB)

    # --------------------------------------------------
    # EXISTING SCHEMA
    # --------------------------------------------------

    rows = conn.execute(
        "PRAGMA table_info(positioning_data)"
    ).fetchall()

    existing = {row[1] for row in rows}

    print()
    print("Current columns:")
    for column in existing:
        print("  ", column)

    # --------------------------------------------------
    # NEW v0.2 COLUMNS
    # --------------------------------------------------

    new_columns = {
        "open_interest_change_pct": "REAL",
        "long_pct": "REAL",
        "short_pct": "REAL",
        "latency_ms": "REAL",
        "symbol": "TEXT",
        "interval": "TEXT",
    }

    print()
    print("Applying v0.2 schema...")
    print("-" * 80)

    added = 0

    for column, datatype in new_columns.items():

        if column not in existing:

            conn.execute(
                f"""
                ALTER TABLE positioning_data
                ADD COLUMN {column} {datatype}
                """
            )

            print(
                f"ADDED   : {column}"
            )

            added += 1

        else:

            print(
                f"EXISTS  : {column}"
            )

    conn.commit()

    # --------------------------------------------------
    # VERIFY
    # --------------------------------------------------

    rows = conn.execute(
        "PRAGMA table_info(positioning_data)"
    ).fetchall()

    print()
    print("=" * 80)
    print("FINAL SCHEMA")
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