import sqlite3
from statistics import mean

DB = "arunda.db"

TIMEFRAMES = [
    ("5m", "return_5m"),
    ("15m", "return_15m"),
    ("30m", "return_30m"),
    ("60m", "return_60m"),
]


def pct(value):
    if value is None:
        return None
    return float(value)


def fmt(value):
    if value is None:
        return "N/A"
    return f"{value:+.3f}%"


def win_rate(wins, total):
    if total == 0:
        return 0.0
    return wins / total * 100


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print()
print("=" * 80)
print("                 ARUNDA PRECISION AUDIT v0.2")
print("=" * 80)

# ------------------------------------------------------------
# SIGNAL / OUTCOME DATA
# ------------------------------------------------------------

rows = conn.execute("""
    SELECT
        h.id,
        h.market,
        h.status,
        h.final_score,
        o.return_5m,
        o.return_15m,
        o.return_30m,
        o.return_60m,
        o.outcome
    FROM hunter_signals h
    LEFT JOIN signal_outcomes o
        ON h.id = o.signal_id
    ORDER BY h.id ASC
""").fetchall()

total = len(rows)
completed = sum(
    1 for r in rows
    if r["outcome"] is not None
)

waiting = total - completed

print()
print("SIGNALS")
print("-" * 80)
print(f"Total signals       : {total}")
print(f"Completed           : {completed}")
print(f"Waiting             : {waiting}")

# ------------------------------------------------------------
# OUTCOMES
# ------------------------------------------------------------

wins = sum(
    1 for r in rows
    if r["outcome"] == "WIN"
)

losses = sum(
    1 for r in rows
    if r["outcome"] == "LOSS"
)

flats = sum(
    1 for r in rows
    if r["outcome"] == "FLAT"
)

print()
print("OUTCOMES")
print("-" * 80)
print(f"WIN                 : {wins}")
print(f"LOSS                : {losses}")
print(f"FLAT                : {flats}")
print(f"Win Rate            : {win_rate(wins, completed):.2f}%")

# ------------------------------------------------------------
# TIMEFRAME PERFORMANCE
# ------------------------------------------------------------

print()
print("TIMEFRAME PERFORMANCE")
print("-" * 80)

for label, column in TIMEFRAMES:

    values = [
        pct(r[column])
        for r in rows
        if r[column] is not None
    ]

    if not values:
        print(
            f"{label:<5} | "
            f"Avg Return : N/A | "
            f"Win Rate : N/A"
        )
        continue

    avg_return = mean(values)
    tf_wins = sum(1 for v in values if v > 0)

    print(
        f"{label:<5} | "
        f"Avg Return : {fmt(avg_return):>9} | "
        f"Win Rate : {win_rate(tf_wins, len(values)):6.2f}%"
    )

# ------------------------------------------------------------
# SIGNAL CLASS PERFORMANCE
# ------------------------------------------------------------

print()
print("BY SIGNAL")
print("-" * 80)

statuses = ["PRIME", "WATCH", "IGNORE"]

for status in statuses:

    subset = [
        r for r in rows
        if r["status"] == status
    ]

    completed_subset = [
        r for r in subset
        if r["outcome"] is not None
    ]

    swins = sum(
        1 for r in completed_subset
        if r["outcome"] == "WIN"
    )

    slosses = sum(
        1 for r in completed_subset
        if r["outcome"] == "LOSS"
    )

    print(
        f"{status:<6} | "
        f"Signals : {len(subset):3d} | "
        f"Wins : {swins:2d} | "
        f"Losses : {slosses:2d} | "
        f"Win Rate : {win_rate(swins, len(completed_subset)):6.2f}%"
    )

# ------------------------------------------------------------
# BEST / WORST
# ------------------------------------------------------------

best = None
worst = None
best_return = None
worst_return = None

for r in rows:

    value = r["return_60m"]

    if value is None:
        continue

    value = float(value)

    if best_return is None or value > best_return:
        best_return = value
        best = r

    if worst_return is None or value < worst_return:
        worst_return = value
        worst = r

print()
print("TOP / BOTTOM")
print("-" * 80)

if best:
    print(
        f"Best  : {best['market']:<10} "
        f"{fmt(best_return)}"
    )
else:
    print("Best  : N/A")

if worst:
    print(
        f"Worst : {worst['market']:<10} "
        f"{fmt(worst_return)}"
    )
else:
    print("Worst : N/A")

# ------------------------------------------------------------
# PRECISION VERDICT
# ------------------------------------------------------------

print()
print("=" * 80)
print("PRECISION VERDICT")
print("=" * 80)

if completed < 30:
    precision = "INSUFFICIENT DATA"
    calibration = "WAIT"
elif win_rate(wins, completed) < 20:
    precision = "LOW"
    calibration = "REQUIRED"
elif win_rate(wins, completed) < 40:
    precision = "MEDIUM"
    calibration = "CONSIDER"
else:
    precision = "PROMISING"
    calibration = "DEFER"

print(f"Current precision          : {precision}")
print(f"Hunter calibration         : {calibration}")
print(f"Sample size                : {completed}")

if completed < 100:
    print("More samples required     : YES")
else:
    print("More samples required     : NO")

print("=" * 80)
print("AUDIT COMPLETE")
print("=" * 80)

conn.close()