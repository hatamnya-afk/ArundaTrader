import sqlite3

c = sqlite3.connect("arunda.db")

rows = c.execute("""
SELECT
    id,
    timestamp,
    market,
    final_score,
    status,
    signal,
    entry_price,
    engine_version,
    snapshot_id
FROM hunter_signals
ORDER BY id DESC
LIMIT 10
""").fetchall()

for r in rows:
    print(r)

c.close()