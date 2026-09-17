import sqlite3
from collections import Counter

DB = "arunda.db"

conn = sqlite3.connect(DB)

print()
print("=" * 80)
print("             ARUNDA FEATURE INTEGRITY AUDIT v0.1")
print("=" * 80)


# ------------------------------------------------------------
# HUNTER SIGNALS
# ------------------------------------------------------------

rows = conn.execute("""
    SELECT
        hunter_score,
        book_score,
        momentum_score,
        social_score,
        volume_score,
        catalyst_score,
        global_score,
        final_score
    FROM hunter_signals
""").fetchall()

print()
print("DATABASE")
print("-" * 80)
print("Signals :", len(rows))


# ------------------------------------------------------------
# FEATURE ANALYSIS
# ------------------------------------------------------------

features = {
    "HUNTER": 0,
    "BOOK": 1,
    "MOM": 2,
    "SOC": 3,
    "VOL": 4,
    "CAT": 5,
    "GLOBAL": 6,
    "FINAL": 7
}

print()
print("FEATURE DISTRIBUTION")
print("-" * 80)

for name, index in features.items():

    values = [
        r[index]
        for r in rows
        if r[index] is not None
    ]

    if not values:
        print(f"{name.ljust(8)} | NO DATA")
        continue

    unique = len(set(values))
    minimum = min(values)
    maximum = max(values)
    average = sum(values) / len(values)

    counter = Counter(values)
    most_common = counter.most_common(3)

    print(
        f"{name.ljust(8)} | "
        f"N {len(values):3d} | "
        f"Unique {unique:3d} | "
        f"Min {minimum:6.2f} | "
        f"Max {maximum:6.2f} | "
        f"Avg {average:6.2f}"
    )

    if unique <= 3:
        print(
            f"         | Values: {most_common}"
        )


# ------------------------------------------------------------
# FALLBACK 50 DETECTION
# ------------------------------------------------------------

print()
print("FALLBACK / CONSTANT DETECTION")
print("-" * 80)

for name, index in features.items():

    values = [
        r[index]
        for r in rows
        if r[index] is not None
    ]

    if not values:
        continue

    count_50 = sum(
        1 for x in values
        if x == 50
    )

    pct_50 = count_50 / len(values) * 100

    unique = len(set(values))

    if unique == 1:
        status = "DEAD / CONSTANT"

    elif pct_50 >= 90:
        status = "CRITICAL FALLBACK"

    elif pct_50 >= 50:
        status = "HIGH FALLBACK"

    elif pct_50 > 0:
        status = "PARTIAL FALLBACK"

    else:
        status = "OK"

    print(
        f"{name.ljust(8)} | "
        f"50-count {count_50:3d}/{len(values):3d} | "
        f"{pct_50:6.2f}% | "
        f"{status}"
    )


# ------------------------------------------------------------
# SCORE SANITY
# ------------------------------------------------------------

print()
print("SCORE SANITY")
print("-" * 80)

checks = [
    ("HUNTER", 0),
    ("BOOK", 1),
    ("MOM", 2),
    ("SOC", 3),
    ("VOL", 4),
    ("CAT", 5),
    ("GLOBAL", 6),
    ("FINAL", 7)
]

for name, index in checks:

    bad = 0

    for r in rows:

        value = r[index]

        if value is None:
            continue

        if value < 0 or value > 100:
            bad += 1

    if bad:
        print(
            f"{name.ljust(8)} | OUT OF RANGE : {bad}"
        )
    else:
        print(
            f"{name.ljust(8)} | RANGE OK"
        )


# ------------------------------------------------------------
# VERDICT
# ------------------------------------------------------------

print()
print("=" * 80)
print("FEATURE INTEGRITY VERDICT")
print("=" * 80)

issues = []

for name, index in features.items():

    values = [
        r[index]
        for r in rows
        if r[index] is not None
    ]

    if not values:
        issues.append(name + ":NO_DATA")
        continue

    unique = len(set(values))
    pct_50 = sum(
        1 for x in values
        if x == 50
    ) / len(values) * 100

    if unique == 1:
        issues.append(name + ":CONSTANT")

    elif pct_50 >= 90:
        issues.append(name + ":FALLBACK")


if issues:

    print("STATUS : FEATURE INTEGRITY PROBLEM")
    print()
    print("Issues:")

    for issue in issues:
        print("- " + issue)

else:

    print("STATUS : FEATURES LOOK HEALTHY")
    print("No major constant/fallback feature detected.")


print()
print("Database modified : NO")
print("=" * 80)
print("FEATURE AUDIT COMPLETE")
print("=" * 80)

conn.close()