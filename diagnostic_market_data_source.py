import sqlite3

DB = "arunda.db"

conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

assets = ("BTC", "ETH", "SOL", "XRP")

print("=" * 90)
print("FUSION MARKET DATA SOURCE DIAGNOSTIC")
print("=" * 90)

print()
print("--- RAW SNAPSHOTS ---")

rows = conn.execute("""
    SELECT
        symbol,
        timeframe,
        source,
        technical_score,
        close,
        timestamp,
        source_timestamp,
        engine_version
    FROM market_data
    WHERE
        symbol IN ('BTC','ETH','SOL','XRP')
        AND source = 'COINMARKETCAP'
        AND timeframe = 'SNAPSHOT'
    ORDER BY id DESC
    LIMIT 12
""").fetchall()

for row in rows:
    print(dict(row))

print()
print("--- ANALYSIS ROWS ---")

rows = conn.execute("""
    SELECT
        symbol,
        timeframe,
        source,
        technical_score,
        close,
        timestamp,
        source_timestamp,
        engine_version
    FROM market_data
    WHERE
        symbol IN ('BTC','ETH','SOL','XRP')
        AND source = 'CMC_SNAPSHOT_ANALYSIS_v0.2'
        AND timeframe = 'SNAPSHOT'
    ORDER BY id DESC
    LIMIT 12
""").fetchall()

for row in rows:
    print(dict(row))

print()
print("--- LATEST ROW PER ASSET ---")

for asset in assets:

    row = conn.execute("""
        SELECT
            id,
            symbol,
            timeframe,
            source,
            technical_score,
            close,
            timestamp,
            source_timestamp,
            engine_version
        FROM market_data
        WHERE symbol = ?
        ORDER BY id DESC
        LIMIT 1
    """, (asset,)).fetchone()

    print(asset, "=>", dict(row) if row else None)

conn.close()

print()
print("=" * 90)
print("READ-ONLY DIAGNOSTIC COMPLETE")
print("=" * 90)
