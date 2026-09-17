import pandas as pd
import numpy as np
import os
import sys


# ============================================================
# ARUNDA DATA QUALITY DIAGNOSTIC v0.1
# ============================================================
#
# Purpose:
#   Investigate invalid Order Book / Spread records.
#
# Input:
#   hunter_records.csv
#
# Mode:
#   READ ONLY
#
# IMPORTANT:
#   This script NEVER modifies the source CSV.
# ============================================================


FILE = "hunter_records.csv"


# ============================================================
# HEADER
# ============================================================

print()
print("=" * 78)
print("              ARUNDA DATA QUALITY DIAGNOSTIC v0.1")
print("=" * 78)
print(f"File : {FILE}")
print("Mode : READ ONLY")
print("=" * 78)
print()


# ============================================================
# FILE CHECK
# ============================================================

if not os.path.exists(FILE):

    print("ERROR")
    print("-" * 78)
    print(f"File not found: {FILE}")
    sys.exit(1)


# ============================================================
# LOAD
# ============================================================

try:

    df = pd.read_csv(FILE)

except Exception as e:

    print("ERROR")
    print("-" * 78)
    print(f"CSV READ ERROR: {e}")
    sys.exit(1)


# ============================================================
# TIMESTAMP
# ============================================================

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)


# ============================================================
# NUMERIC COLUMNS
# ============================================================

numeric_columns = [
    "price",
    "best_bid",
    "best_ask",
    "mid",
    "spread_pct",
    "bid_volume",
    "ask_volume",
    "pressure",
    "hunter_score",
]

for column in numeric_columns:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ============================================================
# CALCULATIONS
# ============================================================

df["calculated_mid"] = (
    df["best_bid"] +
    df["best_ask"]
) / 2


df["calculated_spread"] = (
    (
        df["best_ask"] -
        df["best_bid"]
    )
    /
    df["calculated_mid"]
) * 100


df["bid_ask_invalid"] = (
    df["best_ask"] <= df["best_bid"]
)


df["spread_invalid"] = (
    (df["spread_pct"] < 0)
    |
    (df["spread_pct"] > 20)
)


df["mid_difference"] = (
    df["mid"] -
    df["calculated_mid"]
).abs()


df["spread_difference"] = (
    df["spread_pct"] -
    df["calculated_spread"]
).abs()


# ============================================================
# 1. BASIC COUNTS
# ============================================================

print("1. BASIC DIAGNOSTIC")
print("-" * 78)

print(
    f"Total records              : {len(df)}"
)

print(
    f"Invalid bid/ask records    : "
    f"{int(df['bid_ask_invalid'].sum())}"
)

print(
    f"Invalid spread records     : "
    f"{int(df['spread_invalid'].sum())}"
)

print()


# ============================================================
# 2. INVALID ORDER BOOK RECORDS
# ============================================================

bad_order = df[
    df["bid_ask_invalid"]
].copy()


print("2. INVALID ORDER BOOK RECORDS")
print("-" * 78)

if len(bad_order) == 0:

    print("No invalid Order Book records.")

else:

    print(
        f"Records found : {len(bad_order)}"
    )

    print()

    display_columns = [
        "timestamp",
        "market",
        "asset",
        "price",
        "best_bid",
        "best_ask",
        "mid",
        "spread_pct",
        "calculated_mid",
        "calculated_spread",
        "bid_volume",
        "ask_volume",
        "pressure",
        "hunter_score",
    ]

    print(
        bad_order[
            display_columns
        ].to_string(
            index=False
        )
    )

print()


# ============================================================
# 3. INVALID SPREAD RECORDS
# ============================================================

bad_spread = df[
    df["spread_invalid"]
].copy()


print("3. INVALID SPREAD RECORDS")
print("-" * 78)

if len(bad_spread) == 0:

    print("No invalid spread records.")

else:

    print(
        f"Records found : {len(bad_spread)}"
    )

    print()

    display_columns = [
        "timestamp",
        "market",
        "asset",
        "price",
        "best_bid",
        "best_ask",
        "mid",
        "spread_pct",
        "calculated_spread",
    ]

    print(
        bad_spread[
            display_columns
        ].to_string(
            index=False
        )
    )

print()


# ============================================================
# 4. OVERLAP ANALYSIS
# ============================================================

print("4. OVERLAP ANALYSIS")
print("-" * 78)

both = df[
    df["bid_ask_invalid"]
    &
    df["spread_invalid"]
]

order_only = df[
    df["bid_ask_invalid"]
    &
    ~df["spread_invalid"]
]

spread_only = df[
    ~df["bid_ask_invalid"]
    &
    df["spread_invalid"]
]

print(
    f"Both Order Book + Spread : {len(both)}"
)

print(
    f"Order Book only          : {len(order_only)}"
)

print(
    f"Spread only              : {len(spread_only)}"
)

print()


# ============================================================
# 5. MARKET DISTRIBUTION
# ============================================================

print("5. INVALID RECORDS BY MARKET")
print("-" * 78)

if len(bad_order) > 0:

    market_distribution = (
        bad_order
        .groupby(
            ["market", "asset"]
        )
        .size()
        .sort_values(
            ascending=False
        )
    )

    print(
        market_distribution.to_string()
    )

else:

    print("NONE")

print()


# ============================================================
# 6. SPREAD DISTRIBUTION
# ============================================================

print("6. SPREAD DISTRIBUTION")
print("-" * 78)

print(
    df["spread_pct"]
    .describe()
    .to_string()
)

print()


# ============================================================
# 7. INVALID SPREAD VALUES
# ============================================================

print("7. EXTREME SPREAD VALUES")
print("-" * 78)

extreme_spreads = (
    df[
        df["spread_invalid"]
    ]
    [
        [
            "timestamp",
            "market",
            "asset",
            "spread_pct",
            "calculated_spread",
            "best_bid",
            "best_ask",
        ]
    ]
    .sort_values(
        "spread_pct",
        ascending=False
    )
)


if len(extreme_spreads) > 0:

    print(
        extreme_spreads
        .to_string(
            index=False
        )
    )

else:

    print("NONE")

print()


# ============================================================
# 8. MID PRICE CONSISTENCY
# ============================================================

print("8. MID PRICE CONSISTENCY")
print("-" * 78)

mid_problem = df[
    df["mid_difference"]
    >
    (
        df["calculated_mid"].abs()
        * 0.001
    )
]

print(
    f"Mid inconsistencies : {len(mid_problem)}"
)

if len(mid_problem) > 0:

    print()

    print(
        mid_problem[
            [
                "timestamp",
                "market",
                "asset",
                "best_bid",
                "best_ask",
                "mid",
                "calculated_mid",
                "mid_difference",
            ]
        ]
        .to_string(
            index=False
        )
    )

print()


# ============================================================
# 9. SOURCE PRICE RELATIONSHIP
# ============================================================

print("9. PRICE / ORDER BOOK RELATIONSHIP")
print("-" * 78)

price_below_bid = df[
    df["price"] < df["best_bid"]
]

price_above_ask = df[
    df["price"] > df["best_ask"]
]

print(
    f"Price below best_bid : "
    f"{len(price_below_bid)}"
)

print(
    f"Price above best_ask : "
    f"{len(price_above_ask)}"
)

print()


# ============================================================
# 10. INVALID RECORD TIMING
# ============================================================

print("10. INVALID RECORD TIMING")
print("-" * 78)

if len(bad_order) > 0:

    timing = (
        bad_order
        .groupby("market")
        .agg(
            count=("market", "size"),
            first=("timestamp", "min"),
            last=("timestamp", "max"),
        )
        .sort_values(
            "count",
            ascending=False
        )
    )

    print(
        timing.to_string()
    )

else:

    print("NONE")

print()


# ============================================================
# 11. FIRST / LAST INVALID RECORDS
# ============================================================

print("11. INVALID RECORD TIME RANGE")
print("-" * 78)

if len(bad_order) > 0:

    print(
        f"First invalid : "
        f"{bad_order['timestamp'].min()}"
    )

    print(
        f"Last invalid  : "
        f"{bad_order['timestamp'].max()}"
    )

else:

    print("NONE")

print()


# ============================================================
# 12. FINAL DIAGNOSTIC
# ============================================================

print("=" * 78)
print("                 DIAGNOSTIC SUMMARY")
print("=" * 78)

print(
    f"Total records          : {len(df)}"
)

print(
    f"Invalid Order Book     : {len(bad_order)}"
)

print(
    f"Invalid Spread         : {len(bad_spread)}"
)

print(
    f"Both problems          : {len(both)}"
)

print(
    f"Order Book only        : {len(order_only)}"
)

print(
    f"Spread only            : {len(spread_only)}"
)

print(
    f"Mid inconsistencies    : {len(mid_problem)}"
)

print(
    f"Price below bid        : {len(price_below_bid)}"
)

print(
    f"Price above ask        : {len(price_above_ask)}"
)

print("=" * 78)

print()
print("DIAGNOSTIC STATUS : COMPLETE")
print("SOURCE MUTATION   : NONE")
print()