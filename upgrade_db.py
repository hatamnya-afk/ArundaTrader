import sqlite3

DB = "arunda.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=" * 60)
print("       ARUNDA DATABASE UPGRADE v0.1")
print("=" * 60)

# ---------------------------------------------------------
# 1. LunarCrush data
# ---------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS social_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    asset TEXT NOT NULL,

    galaxy_score REAL,
    alt_rank REAL,

    social_volume REAL,
    social_engagement REAL,
    social_contributors REAL,
    social_mentions REAL,

    percent_change_24h REAL,
    percent_change_7d REAL,
    percent_change_30d REAL,

    source TEXT DEFAULT 'lunarcrush'
)
""")

# ---------------------------------------------------------
# 2. Fusion / Hunter snapshots
# ---------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS hunter_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    market TEXT NOT NULL,
    asset TEXT,

    hunter_score REAL,
    book_score REAL,
    galaxy_score REAL,
    momentum_score REAL,
    social_score REAL,
    volume_score REAL,
    catalyst_score REAL,
    global_score REAL,

    final_score REAL,

    status TEXT,
    signal TEXT
)
""")

# ---------------------------------------------------------
# 3. Future outcome tracking
# ---------------------------------------------------------

cur.execute("""
CREATE TABLE IF NOT EXISTS signal_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    signal_id INTEGER NOT NULL,
    timestamp TEXT NOT NULL,

    market TEXT NOT NULL,
    entry_price REAL,

    price_5m REAL,
    price_15m REAL,
    price_30m REAL,
    price_60m REAL,

    return_5m REAL,
    return_15m REAL,
    return_30m REAL,
    return_60m REAL,

    max_gain REAL,
    max_drawdown REAL,

    outcome TEXT,

    FOREIGN KEY(signal_id)
        REFERENCES hunter_signals(id)
)
""")

# ---------------------------------------------------------
# 4. Indexes
# ---------------------------------------------------------

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_market_records_market_time
ON market_records(market, timestamp)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_social_asset_time
ON social_metrics(asset, timestamp)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_signals_market_time
ON hunter_signals(market, timestamp)
""")

cur.execute("""
CREATE INDEX IF NOT EXISTS idx_outcomes_market_time
ON signal_outcomes(market, timestamp)
""")

conn.commit()

# ---------------------------------------------------------
# 5. Show schema
# ---------------------------------------------------------

tables = cur.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name
""").fetchall()

print("\nTABLES")
print("-" * 60)

for table in tables:
    print(table[0])

print("\nDATABASE UPGRADE COMPLETE")
print("=" * 60)

conn.close()