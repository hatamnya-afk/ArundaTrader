import sqlite3

c = sqlite3.connect("arunda.db")

rows = c.execute(
    "PRAGMA table_info(market_records)"
).fetchall()

for row in rows:
    print(row)

c.close()