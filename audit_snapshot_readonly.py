import sqlite3
import statistics
from datetime import datetime

DB = "arunda.db"

con = sqlite3.connect(DB)
cur = con.cursor()

print("=" * 78)
print("ARUNDA MARKET SNAPSHOT FORENSIC AUDIT v0.1")
print("=" * 78)
print("MODE          : READ ONLY")
print("DATABASE      : arunda.db")
print("WRITE         : NONE")
print("=" * 78)

rows = cur.execute("""
    SELECT timestamp,
           COUNT(*),
           COUNT(DISTINCT symbol)
    FROM market_data
    WHERE source = 'COINMARKETCAP'
      AND timeframe = 'SNAPSHOT'
    GROUP BY timestamp
    ORDER BY timestamp
""").fetchall()

print(f"SNAPSHOTS     : {len(rows)}")
print(f"TOTAL ROWS    : {sum(r[1] for r in rows)}")
print(f"MIN ROWS      : {min(r[1] for r in rows) if rows else 0}")
print(f"MAX ROWS      : {max(r[1] for r in rows) if rows else 0}")
print(f"MIN DISTINCT  : {min(r[2] for r in rows) if rows else 0}")
print(f"MAX DISTINCT  : {max(r[2] for r in rows) if rows else 0}")

timestamps = [datetime.fromisoformat(r[0]) for r in rows]

gaps = [
    (timestamps[i] - timestamps[i-1]).total_seconds()
    for i in range(1, len(timestamps))
]

print()
print("TIMELINE")
print("-" * 78)
print(f"FIRST         : {rows[0][0] if rows else 'NONE'}")
print(f"LAST          : {rows[-1][0] if rows else 'NONE'}")
print(f"GAP MIN       : {min(gaps) if gaps else 0:.2f} sec")
print(f"GAP MAX       : {max(gaps) if gaps else 0:.2f} sec")
print(f"GAP MEDIAN    : {statistics.median(gaps) if gaps else 0:.2f} sec")

print()
print("ASSET COUNTS")
print("-" * 78)

assets = cur.execute("""
    SELECT symbol, COUNT(*)
    FROM market_data
    WHERE source = 'COINMARKETCAP'
      AND timeframe = 'SNAPSHOT'
    GROUP BY symbol
    ORDER BY symbol
""").fetchall()

for symbol, count in assets:
    print(f"{symbol:<10} : {count}")

print()
print("SOURCE / TIMEFRAME")
print("-" * 78)

for row in cur.execute("""
    SELECT source, timeframe, COUNT(*)
    FROM market_data
    GROUP BY source, timeframe
    ORDER BY source, timeframe
"""):
    print(row)

print()
print("LATEST 10 SNAPSHOT TIMESTAMPS")
print("-" * 78)

for row in cur.execute("""
    SELECT timestamp
    FROM market_data
    WHERE source = 'COINMARKETCAP'
      AND timeframe = 'SNAPSHOT'
    GROUP BY timestamp
    ORDER BY timestamp DESC
    LIMIT 10
"""):
    print(row[0])

print()
print("=" * 78)
print("AUDIT COMPLETE")
print("=" * 78)

con.close()
