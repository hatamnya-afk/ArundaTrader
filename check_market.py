import sqlite3

c = sqlite3.connect("arunda.db")

rows = c.execute(
    """
    SELECT
        id,
        timestamp,
        symbol,
        timeframe,
        open,
        high,
        low,
        close,
        volume,
        source
    FROM market_data
    ORDER BY id DESC
    LIMIT 12
    """
).fetchall()

for row in rows:
    print(row)

c.close()