import sqlite3

DB = "arunda.db"

conn = sqlite3.connect(DB)

print("=" * 100)
print("ARUNDA DATABASE REAL AUDIT")
print("=" * 100)

tables = conn.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""").fetchall()

print()
print("TABLES")
print("-" * 100)

for (table,) in tables:

    count = conn.execute(
        f'SELECT COUNT(*) FROM "{table}"'
    ).fetchone()[0]

    print(f"{table:<35} {count:>12}")

print()
print("=" * 100)
print("TABLE SCHEMAS")
print("=" * 100)

for (table,) in tables:

    print()
    print(f"[{table}]")
    print("-" * 100)

    columns = conn.execute(
        f'PRAGMA table_info("{table}")'
    ).fetchall()

    for column in columns:

        cid, name, dtype, notnull, default, pk = column

        print(
            f"{cid:<4}"
            f"{name:<30}"
            f"{dtype:<12}"
            f"NOT_NULL={notnull} "
            f"PK={pk} "
            f"DEFAULT={default}"
        )

print()
print("=" * 100)
print("SQLITE INTEGRITY")
print("=" * 100)

integrity = conn.execute(
    "PRAGMA integrity_check"
).fetchone()[0]

print("Integrity :", integrity)

print()
print("=" * 100)
print("AUDIT COMPLETE")
print("=" * 100)

conn.close()