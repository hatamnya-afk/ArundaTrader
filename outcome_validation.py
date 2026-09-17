import sqlite3
from datetime import datetime

DB = "arunda.db"

conn = sqlite3.connect(DB)

print("=" * 80)
print("              ARUNDA OUTCOME VALIDATION v0.1")
print("=" * 80)

# ------------------------------------------------------------
# 1. SIGNAL / OUTCOME COUNTS
# ------------------------------------------------------------

signals = conn.execute("""
    SELECT COUNT(*)
    FROM hunter_signals
""").fetchone()[0]

outcomes = conn.execute("""
    SELECT COUNT(*)
    FROM signal_outcomes
""").fetchone()[0]

print()
print("DATABASE")
print("-" * 80)
print(f"Hunter signals : {signals}")
print(f"Outcomes       : {outcomes}")

# ------------------------------------------------------------
# 2. SIGNAL STATUS DISTRIBUTION
# ------------------------------------------------------------

print()
print("SIGNAL STATUS")
print("-" * 80)

rows = conn.execute("""
    SELECT
        COALESCE(status, 'NULL'),
        COUNT(*)
    FROM hunter_signals
    GROUP BY status
    ORDER BY COUNT(*) DESC
""").fetchall()

for status, count in rows:
    print(f"{status:10} : {count}")

# ------------------------------------------------------------
# 3. SIGNAL -> OUTCOME MATCH
# ------------------------------------------------------------

print()
print("SIGNAL / OUTCOME MATCH")
print("-" * 80)

matched = conn.execute("""
    SELECT COUNT(*)
    FROM hunter_signals h
    JOIN signal_outcomes o
      ON h.id = o.signal_id
""").fetchone()[0]

unmatched = signals - matched

print(f"Matched   : {matched}")
print(f"Unmatched : {unmatched}")

# ------------------------------------------------------------
# 4. OUTCOME STATUS
# ------------------------------------------------------------

print()
print("OUTCOME STATUS")
print("-" * 80)

rows = conn.execute("""
    SELECT
        COALESCE(outcome, 'NULL'),
        COUNT(*)
    FROM signal_outcomes
    GROUP BY outcome
    ORDER BY COUNT(*) DESC
""").fetchall()

for outcome, count in rows:
    print(f"{outcome:10} : {count}")

# ------------------------------------------------------------
# 5. TIMEFRAME DATA COMPLETENESS
# ------------------------------------------------------------

print()
print("TIMEFRAME COMPLETENESS")
print("-" * 80)

columns = [
    ("5m", "return_5m"),
    ("15m", "return_15m"),
    ("30m", "return_30m"),
    ("60m", "return_60m"),
]

for label, column in columns:

    total = conn.execute(f"""
        SELECT COUNT(*)
        FROM signal_outcomes
        WHERE {column} IS NOT NULL
    """).fetchone()[0]

    print(f"{label:5} : {total}/{outcomes}")

# ------------------------------------------------------------
# 6. SIGNAL STATUS -> OUTCOME
# ------------------------------------------------------------

print()
print("STATUS → OUTCOME")
print("-" * 80)

rows = conn.execute("""
    SELECT
        h.status,
        COUNT(*) AS total,
        SUM(CASE WHEN o.outcome = 'WIN' THEN 1 ELSE 0 END),
        SUM(CASE WHEN o.outcome = 'LOSS' THEN 1 ELSE 0 END),
        SUM(CASE WHEN o.outcome = 'FLAT' THEN 1 ELSE 0 END)
    FROM hunter_signals h
    JOIN signal_outcomes o
      ON h.id = o.signal_id
    GROUP BY h.status
    ORDER BY h.status
""").fetchall()

for status, total, wins, losses, flats in rows:

    rate = (
        wins / total * 100
        if total
        else 0
    )

    print(
        f"{status:8} | "
        f"Total {total:3} | "
        f"W {wins:3} | "
        f"L {losses:3} | "
        f"F {flats:3} | "
        f"WinRate {rate:6.2f}%"
    )

# ------------------------------------------------------------
# 7. ENGINE / SNAPSHOT CONSISTENCY
# ------------------------------------------------------------

print()
print("ENGINE CONSISTENCY")
print("-" * 80)

rows = conn.execute("""
    SELECT
        COALESCE(engine_version, 'NULL'),
        COUNT(*)
    FROM hunter_signals
    GROUP BY engine_version
""").fetchall()

for version, count in rows:
    print(f"{version:15} : {count}")

print()
print("SNAPSHOTS")
print("-" * 80)

rows = conn.execute("""
    SELECT
        COALESCE(snapshot_id, 'NULL'),
        COUNT(*)
    FROM hunter_signals
    GROUP BY snapshot_id
    ORDER BY MIN(id)
""").fetchall()

for snapshot, count in rows:
    print(f"{snapshot} : {count}")

# ------------------------------------------------------------
# 8. ORPHAN OUTCOMES
# ------------------------------------------------------------

print()
print("ORPHAN OUTCOMES")
print("-" * 80)

orphans = conn.execute("""
    SELECT COUNT(*)
    FROM signal_outcomes o
    LEFT JOIN hunter_signals h
      ON h.id = o.signal_id
    WHERE h.id IS NULL
""").fetchone()[0]

print(f"Orphan outcomes : {orphans}")

# ------------------------------------------------------------
# 9. DUPLICATE OUTCOMES
# ------------------------------------------------------------

print()
print("DUPLICATE OUTCOMES")
print("-" * 80)

duplicates = conn.execute("""
    SELECT
        signal_id,
        COUNT(*)
    FROM signal_outcomes
    GROUP BY signal_id
    HAVING COUNT(*) > 1
""").fetchall()

if duplicates:
    for signal_id, count in duplicates:
        print(
            f"Signal {signal_id} : {count} outcomes"
        )
else:
    print("None")

# ------------------------------------------------------------
# 10. FINAL VERDICT
# ------------------------------------------------------------

print()
print("=" * 80)
print("VALIDATION VERDICT")
print("=" * 80)

issues = []

if unmatched > 0:
    issues.append("UNMATCHED_SIGNALS")

if orphans > 0:
    issues.append("ORPHAN_OUTCOMES")

if duplicates:
    issues.append("DUPLICATE_OUTCOMES")

for label, column in columns:

    total = conn.execute(f"""
        SELECT COUNT(*)
        FROM signal_outcomes
        WHERE {column} IS NOT NULL
    """).fetchone()[0]

    if total < outcomes:
        issues.append(f"MISSING_{label}")

if issues:
    print("STATUS : NEEDS REVIEW")
    print()
    print("Issues detected:")
    for issue in issues:
        print(f"- {issue}")
else:
    print("STATUS : VALID")
    print()
    print("Signal → Outcome chain appears structurally consistent.")

conn.close()

print()
print("=" * 80)
print("VALIDATION COMPLETE")
print("=" * 80)