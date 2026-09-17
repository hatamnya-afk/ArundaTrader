import sqlite3

DB = "arunda.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=" * 60)
print("       ARUNDA SIGNAL DB FIX v0.1")
print("=" * 60)

columns = cur.execute("""
    PRAGMA table_info(hunter_signals)
""").fetchall()

existing = {row[1] for row in columns}

print("\nExisting columns:")
for name in existing:
    print(" -", name)

if "entry_price" not in existing:
    cur.execute("""
        ALTER TABLE hunter_signals
        ADD COLUMN entry_price REAL
    """)
    print("\n+ Added: entry_price")
else:
    print("\nentry_price already exists")

conn.commit()

print("\nFinal schema:")
columns = cur.execute("""
    PRAGMA table_info(hunter_signals)
""").fetchall()

for row in columns:
    print(row)

conn.close()

print("\nDATABASE FIX COMPLETE")