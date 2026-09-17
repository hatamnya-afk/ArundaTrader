import sqlite3
import csv
import os
from datetime import datetime

DB_FILE = "arunda.db"
CSV_FILE = "hunter_records.csv"

# ==========================================
# DATABASE
# ==========================================

def create_database():

    conn = sqlite3.connect(DB_FILE)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS market_records (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            timestamp TEXT NOT NULL,

            market TEXT NOT NULL,

            asset TEXT,

            price REAL,

            change_24h REAL,

            volume_24h REAL,

            best_bid REAL,

            best_ask REAL,

            mid REAL,

            spread_pct REAL,

            bid_volume REAL,

            ask_volume REAL,

            pressure REAL,

            hunter_score REAL

        )
    """)

    # Indexes
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_market
        ON market_records(market)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_timestamp
        ON market_records(timestamp)
    """)

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_market_timestamp
        ON market_records(market, timestamp)
    """)

    conn.commit()

    return conn


# ==========================================
# IMPORT OLD CSV
# ==========================================

def import_csv(conn):

    if not os.path.exists(CSV_FILE):

        print()
        print("No CSV file found.")
        print("Nothing to import.")

        return

    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM market_records"
    )

    existing = cursor.fetchone()[0]

    if existing > 0:

        print()
        print(
            f"Database already contains "
            f"{existing} records."
        )

        print(
            "CSV import skipped."
        )

        return

    print()
    print("Importing CSV...")
    print("------------------------------------------")

    with open(
        CSV_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        reader = csv.DictReader(f)

        rows = []

        for row in reader:

            rows.append((
                row["timestamp"],
                row["market"],
                row["asset"],
                float(row["price"]),
                float(row["change_24h"]),
                float(row["volume_24h"]),
                float(row["best_bid"]),
                float(row["best_ask"]),
                float(row["mid"]),
                float(row["spread_pct"]),
                float(row["bid_volume"]),
                float(row["ask_volume"]),
                float(row["pressure"]),
                float(row["hunter_score"]),
            ))

    cursor.executemany("""
        INSERT INTO market_records (

            timestamp,
            market,
            asset,
            price,
            change_24h,
            volume_24h,
            best_bid,
            best_ask,
            mid,
            spread_pct,
            bid_volume,
            ask_volume,
            pressure,
            hunter_score

        )

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)

    """, rows)

    conn.commit()

    print(
        f"Imported : {len(rows)} records"
    )


# ==========================================
# DATABASE TEST
# ==========================================

def test_database(conn):

    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM market_records"
    )

    total = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT market)
        FROM market_records
    """)

    markets = cursor.fetchone()[0]

    cursor.execute("""
        SELECT MIN(timestamp),
               MAX(timestamp)
        FROM market_records
    """)

    first, last = cursor.fetchone()

    print()
    print("DATABASE STATUS")
    print("------------------------------------------")

    print(
        f"Records : {total}"
    )

    print(
        f"Markets : {markets}"
    )

    print(
        f"Start   : {first}"
    )

    print(
        f"End     : {last}"
    )


# ==========================================
# MAIN
# ==========================================

def main():

    print()
    print("==========================================")
    print("       ARUNDA SQLITE RECORDER v0.1")
    print("==========================================")

    conn = create_database()

    import_csv(conn)

    test_database(conn)

    conn.close()

    print()
    print("==========================================")
    print("DATABASE READY")
    print(f"File: {DB_FILE}")
    print("==========================================")


if __name__ == "__main__":
    main()