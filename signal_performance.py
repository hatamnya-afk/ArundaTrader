import sqlite3

DB = "arunda.db"

conn = sqlite3.connect(DB)

print("=" * 80)
print("              ARUNDA SIGNAL PERFORMANCE v0.1")
print("=" * 80)

# ------------------------------------------------------------
# LOAD COMPLETED SIGNALS
# ------------------------------------------------------------

rows = conn.execute("""
    SELECT
        h.market,
        h.final_score,
        h.book_score,
        h.momentum_score,
        h.social_score,
        h.volume_score,
        h.catalyst_score,
        h.global_score,
        h.status,
        o.return_5m,
        o.return_15m,
        o.return_30m,
        o.return_60m,
        o.outcome
    FROM hunter_signals h
    JOIN signal_outcomes o
        ON h.id = o.signal_id
""").fetchall()

print()
print("DATA")
print("-" * 80)
print("Completed signals :", len(rows))

if not rows:
    print("No completed outcomes.")
    conn.close()
    raise SystemExit

# ------------------------------------------------------------
# OVERALL PERFORMANCE
# ------------------------------------------------------------

def avg(values):
    values = [x for x in values if x is not None]
    return sum(values) / len(values) if values else 0


def win_rate(values):
    values = [x for x in values if x is not None]
    return (
        sum(1 for x in values if x > 0)
        / len(values)
        * 100
        if values else 0
    )


print()
print("TIMEFRAME PERFORMANCE")
print("-" * 80)

for name, index in [
    ("5m", 9),
    ("15m", 10),
    ("30m", 11),
    ("60m", 12),
]:
    values = [r[index] for r in rows]

    print(
        f"{name:5} | "
        f"Avg Return : {avg(values):8.3f}% | "
        f"Positive : {win_rate(values):6.2f}%"
    )

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
    ("60+", 60, 101),
]

for name, low, high in bands:

    selected = [
        r for r in rows
        if r[1] is not None and low <= r[1] < high
    ]

    if not selected:
        continue

    returns = [r[12] for r in selected]

    print(
        f"{name:7} | "
        f"N {len(selected):3} | "
        f"Avg60m {avg(returns):8.3f}% | "
        f"Positive {win_rate(returns):6.2f}%"
    )

# ------------------------------------------------------------
# COMPONENT PERFORMANCE
# ------------------------------------------------------------

print()
print("COMPONENT CORRELATION")
print("-" * 80)

components = [
    ("FINAL", 1),
    ("BOOK", 2),
    ("MOM", 3),
    ("SOC", 4),
    ("VOL", 5),
    ("CAT", 6),
    ("GLOBAL", 7),
]

returns = [r[12] for r in rows]

def correlation(xs, ys):

    pairs = [
        (x, y)
        for x, y in zip(xs, ys)
        if x is not None and y is not None
    ]

    if len(pairs) < 2:
        return 0

    x = [p[0] for p in pairs]
    y = [p[1] for p in pairs]

    mx = sum(x) / len(x)
    my = sum(y) / len(y)

    numerator = sum(
        (a - mx) * (b - my)
        for a, b in zip(x, y)
    )

    den_x = sum((a - mx) ** 2 for a in x)
    den_y = sum((b - my) ** 2 for b in y)

    denominator = (den_x * den_y) ** 0.5

    return numerator / denominator if denominator else 0


for name, index in components:

    values = [r[index] for r in rows]

    corr = correlation(values, returns)

    print(
        f"{name:7} | "
        f"Correlation with 60m return : {corr:7.3f}"
    )

# ------------------------------------------------------------
# STATUS PERFORMANCE
# ------------------------------------------------------------

print()
print("STATUS PERFORMANCE")
print("-" * 80)

statuses = sorted(set(r[8] for r in rows))

for status in statuses:

    selected = [
        r for r in rows
        if r[8] == status
    ]

    values = [r[12] for r in selected]

    print(
        f"{status:8} | "
        f"N {len(selected):3} | "
        f"Avg60m {avg(values):8.3f}% | "
        f"Positive {win_rate(values):6.2f}%"
    )

# ------------------------------------------------------------
# BEST / WORST
# ------------------------------------------------------------

print()
print("BEST / WORST")
print("-" * 80)

best = max(rows, key=lambda r: r[12])
worst = min(rows, key=lambda r: r[12])

print(
    f"Best  : {best[0]:12} "
    f"{best[12]:+.3f}%"
)

print(
    f"Worst : {worst[0]:12} "
    f"{worst[12]:+.3f}%"
)

print()
print("=" * 80)
print("PERFORMANCE ANALYSIS COMPLETE")
print("=" * 80)

conn.close()