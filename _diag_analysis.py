import sqlite3

c = sqlite3.connect("arunda.db")
rows = c.execute("""
SELECT id, symbol, source, timeframe, technical_score, timestamp
FROM market_data
WHERE source = 'CMC_SNAPSHOT_ANALYSIS_v0.2'
ORDER BY id DESC
""").fetchall()

for r in rows:
    print(r)

c.close()
