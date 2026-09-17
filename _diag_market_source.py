import sqlite3

c = sqlite3.connect("arunda.db")

rows = c.execute("""
SELECT source, timeframe, COUNT(*)
FROM market_data
WHERE symbol = 'BTC'
GROUP BY source, timeframe
ORDER BY COUNT(*) DESC
""").fetchall()

for row in rows:
    print(row)

c.close()
