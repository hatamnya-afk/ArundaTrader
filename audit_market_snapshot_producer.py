import sqlite3

conn = sqlite3.connect("arunda.db")
conn.row_factory = sqlite3.Row

print("=" * 90)
print("MARKET SNAPSHOT PRODUCER HEALTH AUDIT")
print("=" * 90)

print()
print("--- SNAPSHOT COUNTS BY ENGINE VERSION ---")

rows = conn.execute("""
    SELECT
        engine_version,
        COUNT(*) AS rows_count,
        COUNT(DISTINCT symbol) AS symbols,
        MIN(timestamp) AS first_timestamp,
        MAX(timestamp) AS last_timestamp
    FROM market_data
    WHERE
        source = 'COINMARKETCAP'
        AND timeframe = 'SNAPSHOT'
    GROUP BY engine_version
    ORDER BY last_timestamp DESC
""").fetchall()

for row in rows:
    print(dict(row))

print()
print("--- SNAPSHOT COUNTS BY TIMESTAMP ---")

rows = conn.execute("""
    SELECT
        timestamp,
        COUNT(*) AS rows_count,
        COUNT(DISTINCT symbol) AS symbols
    FROM market_data
    WHERE
        source = 'COINMARKETCAP'
        AND timeframe = 'SNAPSHOT'
    GROUP BY timestamp
    ORDER BY timestamp DESC
    LIMIT 20
""").fetchall()

for row in rows:
    print(dict(row))

print()
print("--- LATEST SNAPSHOT PER ASSET ---")

rows = conn.execute("""
    SELECT
        symbol,
        timestamp,
        source_timestamp,
        engine_version
    FROM market_data
    WHERE
        source = 'COINMARKETCAP'
        AND timeframe = 'SNAPSHOT'
    ORDER BY id DESC
""").fetchall()

seen = set()

for row in rows:

    symbol = row["symbol"]

    if symbol in seen:
        continue

    seen.add(symbol)

    print(dict(row))

print()
print("--- TOTALS ---")

row = conn.execute("""
    SELECT
        COUNT(*) AS total_rows,
        COUNT(DISTINCT symbol) AS distinct_symbols
    FROM market_data
    WHERE
        source = 'COINMARKETCAP'
        AND timeframe = 'SNAPSHOT'
""").fetchone()

print(dict(row))

conn.close()

print()
print("=" * 90)
print("READ-ONLY PRODUCER AUDIT COMPLETE")
print("=" * 90)
