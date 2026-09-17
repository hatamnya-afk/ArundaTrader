import sqlite3

conn = sqlite3.connect("arunda.db")
conn.row_factory = sqlite3.Row

print("=" * 90)
print("MARKET SNAPSHOT HISTORY DEPTH AUDIT")
print("=" * 90)

rows = conn.execute("""
    SELECT
        symbol,
        COUNT(*) AS snapshot_count,
        MIN(source_timestamp) AS first_source_timestamp,
        MAX(source_timestamp) AS last_source_timestamp
    FROM market_data
    WHERE
        source = 'COINMARKETCAP'
        AND timeframe = 'SNAPSHOT'
        AND close IS NOT NULL
    GROUP BY symbol
    ORDER BY symbol
""").fetchall()

for row in rows:
    status = (
        "READY"
        if row["snapshot_count"] >= 60
        else "INSUFFICIENT"
    )

    print(
        f"{row['symbol']:<6}"
        f" | COUNT={row['snapshot_count']:<4}"
        f" | STATUS={status:<11}"
        f" | FIRST={row['first_source_timestamp']}"
        f" | LAST={row['last_source_timestamp']}"
    )

print()
print("=" * 90)
print("REQUIRED HISTORY : 60 SNAPSHOTS / ASSET")
print("=" * 90)

conn.close()
