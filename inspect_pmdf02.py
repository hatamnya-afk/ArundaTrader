import sqlite3

p = r"public_market_data_fabric\canonical_store_v0.1.sqlite"

conn = sqlite3.connect(p)
conn.row_factory = sqlite3.Row

rows = conn.execute("""
SELECT
    id,
    asset,
    symbol,
    timestamp,
    source_id,
    source_type,
    observation_count,
    pool,
    raydium_instruction
FROM canonical_ohlcv
WHERE source_id LIKE 'KUCOIN_SPOT:%'
ORDER BY id
""").fetchall()

for row in rows:
    print(dict(row))

conn.close()