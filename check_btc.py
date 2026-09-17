import sqlite3

c = sqlite3.connect("arunda.db")

rows = c.execute(
    """
    SELECT asset, timestamp
    FROM market_records
    WHERE asset = 'BTC'
    ORDER BY timestamp ASC
    LIMIT 10
    """
).fetchall()

for row in rows:
    print(row)

c.close()