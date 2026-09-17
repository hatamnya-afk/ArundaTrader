import sqlite3
import math

DB = "arunda.db"


def correlation(x, y):
    pairs = []

    for a, b in zip(x, y):
        if a is None or b is None:
            continue

        try:
            a = float(a)
            b = float(b)

            if math.isfinite(a) and math.isfinite(b):
                pairs.append((a, b))
        except:
            pass

    if len(pairs) < 3:
        return None

    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]

    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)

    numerator = sum(
        (a - mx) * (b - my)
        for a, b in pairs
    )

    dx = sum(
        (a - mx) ** 2
        for a in xs
    )

    dy = sum(
        (b - my) ** 2
        for b in ys
    )

    if dx == 0 or dy == 0:
        return 0

    return numerator / math.sqrt(dx * dy)


conn = sqlite3.connect(DB)

print()
print("=" * 80)
print("             ARUNDA CALIBRATION DIAGNOSTIC v0.1")
print("=" * 80)


# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------

signals = conn.execute(
    "SELECT COUNT(*) FROM hunter_signals"
).fetchone()[0]

outcomes = conn.execute(
    "SELECT COUNT(*) FROM signal_outcomes"
).fetchone()[0]

print()
print("DATABASE")
print("-" * 80)
print("Hunter signals :", signals)
print("Outcomes       :", outcomes)


# ------------------------------------------------------------
# COMPLETED SIGNALS
# ------------------------------------------------------------

rows = conn.execute("""
    SELECT
        h.id,
        h.market,
        h.final_score,
        h.book_score,
        h.momentum_score,
        h.social_score,
        h.volume_score,
        h.catalyst_score,
        h.global_score,
        h.status,
        o.return_60m
    FROM hunter_signals h
    JOIN signal_outcomes o
        ON o.signal_id = h.id
    WHERE o.return_60m IS NOT NULL
    ORDER BY h.id
""").fetchall()

print()
print("COMPLETED SAMPLE")
print("-" * 80)
print("Completed      :", len(rows))


if not rows:
    print()
    print("No completed outcomes.")
    conn.close()
    raise SystemExit


# ------------------------------------------------------------
# SCORE DISTRIBUTION
# ------------------------------------------------------------

scores = [
    r[2]
    for r in rows
    if r[2] is not None
]

print()
print("FINAL SCORE")
print("-" * 80)
print("Minimum        :", round(min(scores), 2))
print("Maximum        :", round(max(scores), 2))
print("Average        :", round(sum(scores) / len(scores), 2))


# ------------------------------------------------------------
# SCORE BANDS
# ------------------------------------------------------------

print()
print("FINAL SCORE BANDS")
print("-" * 80)

bands = [
    ("<40", 0, 40),
    ("40-45", 40, 45),
    ("45-50", 45, 50),
    ("50-55", 50, 55),
    ("55-60", 55, 60),
    ("60+", 60, 999)
]

for name, low, high in bands:

    selected = []

    for r in rows:

        score = r[2]

        if score is None:
            continue

        if low <= score < high:
            selected.append(r)

    if not selected:
        continue

    returns = [
        float(r[10])
        for r in selected
    ]

    positive = sum(
        1 for x in returns
        if x > 0
    )

    avg = sum(returns) / len(returns)

    print(
        f"{name.ljust(7)} | "
        f"N {len(selected):3d} | "
        f"Avg60m {avg:+.3f}% | "
        f"Positive {positive / len(selected) * 100:6.2f}%"
    )


# ------------------------------------------------------------
# COMPONENT CORRELATION
# ------------------------------------------------------------

print()
print("COMPONENT CORRELATION")
print("-" * 80)

returns = [
    r[10]
    for r in rows
]

components = {
    "FINAL": 2,
    "BOOK": 3,
    "MOM": 4,
    "SOC": 5,
    "VOL": 6,
    "CAT": 7,
    "GLOBAL": 8
}

for name, index in components.items():

    values = [
        r[index]
        for r in rows
    ]

    corr = correlation(
        values,
        returns
    )

    if corr is None:
        print(
            f"{name.ljust(7)} | insufficient data"
        )
    else:
        print(
            f"{name.ljust(7)} | "
            f"60m correlation {corr:+.3f}"
        )


# ------------------------------------------------------------
# STATUS PERFORMANCE
# ------------------------------------------------------------

print()
print("STATUS PERFORMANCE")
print("-" * 80)

status_rows = conn.execute("""
    SELECT
        h.status,
        COUNT(*),
        SUM(
            CASE
                WHEN o.return_60m > 0 THEN 1
                ELSE 0
            END
        ),
        AVG(o.return_60m)
    FROM hunter_signals h
    JOIN signal_outcomes o
        ON o.signal_id = h.id
    WHERE o.return_60m IS NOT NULL
    GROUP BY h.status
    ORDER BY h.status
""").fetchall()

for status, total, positive, avg in status_rows:

    positive = positive or 0

    print(
        f"{status.ljust(8)} | "
        f"N {total:3d} | "
        f"Positive {positive / total * 100:6.2f}% | "
        f"Avg60m {avg:+.3f}%"
    )


# ------------------------------------------------------------
# TIMEFRAME
# ------------------------------------------------------------

print()
print("TIMEFRAME")
print("-" * 80)

tf_rows = conn.execute("""
    SELECT
        return_5m,
        return_15m,
        return_30m,
        return_60m
    FROM signal_outcomes
    WHERE return_60m IS NOT NULL
""").fetchall()

timeframes = [
    ("5m", 0),
    ("15m", 1),
    ("30m", 2),
    ("60m", 3)
]

for name, index in timeframes:

    values = [
        r[index]
        for r in tf_rows
        if r[index] is not None
    ]

    if not values:
        continue

    avg = sum(values) / len(values)

    positive = sum(
        1 for x in values
        if x > 0
    )

    print(
        f"{name.ljust(5)} | "
        f"Avg {avg:+.3f}% | "
        f"Positive {positive / len(values) * 100:6.2f}%"
    )


# ------------------------------------------------------------
# VERDICT
# ------------------------------------------------------------

print()
print("=" * 80)
print("CALIBRATION DIAGNOSTIC VERDICT")
print("=" * 80)

final_corr = correlation(
    [r[2] for r in rows],
    returns
)

print()

if len(rows) < 100:

    print("STATUS : INSUFFICIENT SAMPLE")
    print("ACTION : COLLECT MORE OUTCOMES")

elif final_corr is None:

    print("STATUS : INSUFFICIENT DATA")

elif final_corr < 0:

    print("STATUS : SIGNAL DIRECTION PROBLEM")
    print("ACTION : INVESTIGATE SCORE COMPONENTS")

elif final_corr < 0.10:

    print("STATUS : LOW SIGNAL POWER")
    print("ACTION : DO NOT CALIBRATE YET")

else:

    print("STATUS : CALIBRATION CANDIDATE")
    print("ACTION : WEIGHT CALIBRATION MAY BEGIN")


print()
print("Database modified : NO")
print("=" * 80)
print("DIAGNOSTIC COMPLETE")
print("=" * 80)

conn.close()