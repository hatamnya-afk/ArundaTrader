import sqlite3

DB = "arunda.db"

conn = sqlite3.connect(DB)
cur = conn.cursor()

print("=" * 80)
print("ARUNDA DATABASE INSPECTOR")
print("=" * 80)

tables = cur.execute("""
SELECT name
FROM sqlite_master
WHERE type='table'
ORDER BY name
""").fetchall()

print("\nTABLES:")
for row in tables:
    print(" -", row[0])

print("\n" + "=" * 80)

for (table,) in tables:
    print(f"\n--- {table} ---")

    columns = cur.execute(
        f"PRAGMA table_info('{table}')"
    ).fetchall()

    for col in columns:
        print(
            f"{col[0]:2} | "
            f"{col[1]:30} | "
            f"{col[2]}"
        )

print("\n" + "=" * 80)
print("RECENT DATA")
print("=" * 80)

for table in [
    "market_data",
    "market_signals",
    "positioning_data",
    "news_data",
    "news_signals",
    "fusion_signals"
]:

    exists = cur.execute(
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name=?",
        (table,)
    ).fetchone()

    if not exists:
        continue

    print(f"\n### {table}")

    try:
        rows = cur.execute(
            f"SELECT * FROM '{table}' "
            f"ORDER BY id DESC LIMIT 3"
        ).fetchall()

        for row in rows:
            print(row)

    except Exception as e:
        print("ERROR:", repr(e))

conn.close()

print("\n" + "=" * 80)
print("INSPECTION COMPLETE")
print("=" * 80)