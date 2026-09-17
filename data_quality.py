import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime


# ============================================================
# ARUNDA DATA QUALITY GATE v0.2
# ============================================================
#
# Purpose:
#   Validate hunter_records.csv before analytical engines
#   consume the data.
#
# Input:
#   hunter_records.csv
#
# Mode:
#   ANALYSIS / VALIDATION ONLY
#
# Result:
#   PASS
#   WARNING
#   FAIL
#
# This engine does NOT modify the source CSV.
# ============================================================


FILE = "hunter_records.csv"
ENGINE_VERSION = "DATA_QUALITY_GATE_v0.2"


# ============================================================
# REQUIRED SCHEMA
# ============================================================

REQUIRED_COLUMNS = [
    "timestamp",
    "market",
    "asset",
    "price",
    "change_24h",
    "volume_24h",
    "best_bid",
    "best_ask",
    "mid",
    "spread_pct",
    "bid_volume",
    "ask_volume",
    "pressure",
    "hunter_score",
]


# ============================================================
# HEADER
# ============================================================

print()
print("=" * 78)
print("                 ARUNDA DATA QUALITY GATE v0.2")
print("=" * 78)
print(f"File            : {FILE}")
print(f"Engine          : {ENGINE_VERSION}")
print("Mode            : VALIDATION ONLY")
print("Source mutation : DISABLED")
print("=" * 78)
print()


# ============================================================
# FILE CHECK
# ============================================================

if not os.path.exists(FILE):

    print("=" * 78)
    print("DATA QUALITY GATE ERROR")
    print("=" * 78)
    print(f"File not found : {FILE}")
    print("=" * 78)

    sys.exit(1)


# ============================================================
# LOAD DATA
# ============================================================

try:

    df = pd.read_csv(FILE)

except Exception as e:

    print("=" * 78)
    print("DATA QUALITY GATE ERROR")
    print("=" * 78)
    print(f"CSV READ ERROR : {e}")
    print("=" * 78)

    sys.exit(1)


print("DATASET")
print("-" * 78)
print(f"Records        : {len(df)}")
print(f"Columns        : {len(df.columns)}")
print(f"Markets        : {df['market'].nunique() if 'market' in df.columns else 'N/A'}")
print(f"Assets         : {df['asset'].nunique() if 'asset' in df.columns else 'N/A'}")
print()


# ============================================================
# GATE STATE
# ============================================================

warnings = []
failures = []


# ============================================================
# 1. SCHEMA VALIDATION
# ============================================================

print("1. SCHEMA VALIDATION")
print("-" * 78)

missing_columns = [
    column
    for column in REQUIRED_COLUMNS
    if column not in df.columns
]

extra_columns = [
    column
    for column in df.columns
    if column not in REQUIRED_COLUMNS
]

if missing_columns:

    print("STATUS         : FAIL")

    print(
        "Missing columns:",
        ", ".join(missing_columns)
    )

    failures.append(
        f"Missing required columns: {', '.join(missing_columns)}"
    )

else:

    print("STATUS         : PASS")
    print("Required schema: OK")


if extra_columns:

    print(
        "Extra columns  :",
        ", ".join(extra_columns)
    )

else:

    print("Extra columns  : NONE")

print()


# ============================================================
# STOP IF SCHEMA IS BROKEN
# ============================================================

if failures:

    print("=" * 78)
    print("                 DATA QUALITY GATE")
    print("=" * 78)
    print("STATUS : FAIL")
    print("ACTION : Fix schema before analytical processing.")
    print("=" * 78)

    sys.exit(2)


# ============================================================
# NUMERIC CONVERSION
# ============================================================

NUMERIC_COLUMNS = [
    "price",
    "change_24h",
    "volume_24h",
    "best_bid",
    "best_ask",
    "mid",
    "spread_pct",
    "bid_volume",
    "ask_volume",
    "pressure",
    "hunter_score",
]


for column in NUMERIC_COLUMNS:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce"
    )


# ============================================================
# 2. MISSING VALUES
# ============================================================

print("2. MISSING VALUE VALIDATION")
print("-" * 78)

missing_counts = df[REQUIRED_COLUMNS].isna().sum()

missing_total = int(
    missing_counts.sum()
)

if missing_total == 0:

    print("STATUS         : PASS")
    print("Missing values : 0")

else:

    print("STATUS         : WARNING")
    print(
        f"Missing values : {missing_total}"
    )

    for column, count in missing_counts.items():

        if count > 0:

            print(
                f"  {column:<16}: {count}"
            )

    warnings.append(
        f"{missing_total} missing values detected"
    )

print()


# ============================================================
# 3. DUPLICATE VALIDATION
# ============================================================

print("3. DUPLICATE VALIDATION")
print("-" * 78)

duplicates = int(
    df.duplicated(
        subset=["timestamp", "market"]
    ).sum()
)

if duplicates == 0:

    print("STATUS         : PASS")

else:

    print("STATUS         : WARNING")

    warnings.append(
        f"{duplicates} duplicate timestamp/market records"
    )

print(
    f"Duplicate rows : {duplicates}"
)

print()


# ============================================================
# 4. PRICE VALIDATION
# ============================================================

print("4. PRICE VALIDATION")
print("-" * 78)

bad_price = (
    df["price"].isna()
    |
    (df["price"] <= 0)
    |
    (~np.isfinite(df["price"]))
)

bad_price_count = int(
    bad_price.sum()
)

if bad_price_count == 0:

    print("STATUS         : PASS")

else:

    print("STATUS         : FAIL")

    failures.append(
        f"{bad_price_count} invalid prices"
    )

print(
    f"Invalid prices : {bad_price_count}"
)

print()


# ============================================================
# 5. ORDER BOOK VALIDATION
# ============================================================

print("5. ORDER BOOK VALIDATION")
print("-" * 78)

bad_bid = (
    df["best_bid"].isna()
    |
    (df["best_bid"] <= 0)
    |
    (~np.isfinite(df["best_bid"]))
)

bad_ask = (
    df["best_ask"].isna()
    |
    (df["best_ask"] <= 0)
    |
    (~np.isfinite(df["best_ask"]))
)

bad_bid_count = int(
    bad_bid.sum()
)

bad_ask_count = int(
    bad_ask.sum()
)

bad_order = (
    (~bad_bid)
    &
    (~bad_ask)
    &
    (df["best_ask"] <= df["best_bid"])
)

bad_order_count = int(
    bad_order.sum()
)

print(
    f"Invalid bids       : {bad_bid_count}"
)

print(
    f"Invalid asks       : {bad_ask_count}"
)

print(
    f"Invalid bid/ask    : {bad_order_count}"
)

if (
    bad_bid_count == 0
    and
    bad_ask_count == 0
    and
    bad_order_count == 0
):

    print("STATUS             : PASS")

else:

    print("STATUS             : FAIL")

    failures.append(
        "Order book validation failure"
    )

print()


# ============================================================
# 6. MID PRICE VALIDATION
# ============================================================

print("6. MID PRICE VALIDATION")
print("-" * 78)

expected_mid = (
    df["best_bid"] +
    df["best_ask"]
) / 2

mid_difference = (
    df["mid"] -
    expected_mid
).abs()

bad_mid = (
    df["mid"].isna()
    |
    (df["mid"] <= 0)
    |
    (~np.isfinite(df["mid"]))
    |
    (mid_difference > expected_mid.abs() * 0.001)
)

bad_mid_count = int(
    bad_mid.sum()
)

print(
    f"Invalid mid prices : {bad_mid_count}"
)

if bad_mid_count == 0:

    print("STATUS             : PASS")

else:

    print("STATUS             : WARNING")

    warnings.append(
        f"{bad_mid_count} suspicious mid prices"
    )

print()


# ============================================================
# 7. SPREAD VALIDATION
# ============================================================

print("7. SPREAD VALIDATION")
print("-" * 78)

calculated_spread = (
    (
        df["best_ask"] -
        df["best_bid"]
    )
    /
    (
        (
            df["best_ask"] +
            df["best_bid"]
        ) / 2
    )
) * 100

spread_difference = (
    df["spread_pct"] -
    calculated_spread
).abs()

bad_spread_value = (
    df["spread_pct"].isna()
    |
    (~np.isfinite(df["spread_pct"]))
    |
    (df["spread_pct"] < 0)
    |
    (df["spread_pct"] > 20)
)

bad_spread_consistency = (
    spread_difference > 0.05
)

bad_spread_count = int(
    bad_spread_value.sum()
)

inconsistent_spread_count = int(
    bad_spread_consistency.sum()
)

print(
    f"Invalid spread     : {bad_spread_count}"
)

print(
    f"Inconsistent spread: {inconsistent_spread_count}"
)

if (
    bad_spread_count == 0
    and
    inconsistent_spread_count == 0
):

    print("STATUS             : PASS")

else:

    print("STATUS             : WARNING")

    warnings.append(
        "Spread validation produced anomalies"
    )

print()


# ============================================================
# 8. VOLUME VALIDATION
# ============================================================

print("8. VOLUME VALIDATION")
print("-" * 78)

volume_columns = [
    "volume_24h",
    "bid_volume",
    "ask_volume",
]

volume_errors = 0

for column in volume_columns:

    invalid = (
        df[column].isna()
        |
        (df[column] < 0)
        |
        (~np.isfinite(df[column]))
    )

    count = int(
        invalid.sum()
    )

    volume_errors += count

    print(
        f"{column:<16}: {count} invalid"
    )


if volume_errors == 0:

    print("STATUS             : PASS")

else:

    print("STATUS             : FAIL")

    failures.append(
        f"{volume_errors} invalid volume values"
    )

print()


# ============================================================
# 9. PRESSURE VALIDATION
# ============================================================

print("9. PRESSURE VALIDATION")
print("-" * 78)

bad_pressure = (
    df["pressure"].isna()
    |
    (~np.isfinite(df["pressure"]))
    |
    (df["pressure"] < 0)
    |
    (df["pressure"] > 100)
)

bad_pressure_count = int(
    bad_pressure.sum()
)

print(
    f"Invalid pressure : {bad_pressure_count}"
)

if bad_pressure_count == 0:

    print("STATUS           : PASS")

else:

    print("STATUS           : FAIL")

    failures.append(
        f"{bad_pressure_count} invalid pressure values"
    )

print()


# ============================================================
# 10. HUNTER SCORE VALIDATION
# ============================================================

print("10. HUNTER SCORE VALIDATION")
print("-" * 78)

bad_hunter = (
    df["hunter_score"].isna()
    |
    (~np.isfinite(df["hunter_score"]))
)

bad_hunter_count = int(
    bad_hunter.sum()
)

print(
    f"Invalid scores : {bad_hunter_count}"
)

if bad_hunter_count == 0:

    print("STATUS         : PASS")

else:

    print("STATUS         : FAIL")

    failures.append(
        f"{bad_hunter_count} invalid hunter scores"
    )

print()


# ============================================================
# 11. TIMESTAMP VALIDATION
# ============================================================

print("11. TIMESTAMP VALIDATION")
print("-" * 78)

parsed_timestamp = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

bad_timestamp = (
    parsed_timestamp.isna()
)

bad_timestamp_count = int(
    bad_timestamp.sum()
)

print(
    f"Invalid timestamps : {bad_timestamp_count}"
)

if bad_timestamp_count == 0:

    print("STATUS             : PASS")

else:

    print("STATUS             : FAIL")

    failures.append(
        f"{bad_timestamp_count} invalid timestamps"
    )

print()


# ============================================================
# 12. MARKET COVERAGE
# ============================================================

print("12. MARKET COVERAGE")
print("-" * 78)

coverage = (
    df.groupby("market")
    .agg(
        records=("market", "size"),
        first=("timestamp", "min"),
        last=("timestamp", "max"),
    )
    .sort_values(
        "records",
        ascending=False
    )
)

print(
    coverage.to_string()
)

print()


# ============================================================
# 13. ASSET COVERAGE
# ============================================================

print("13. ASSET COVERAGE")
print("-" * 78)

asset_coverage = (
    df.groupby("asset")
    .size()
    .sort_values(
        ascending=False
    )
)

print(
    asset_coverage.to_string()
)

print()


# ============================================================
# 14. TIME INTERVAL ANALYSIS
# ============================================================

print("14. TIME INTERVAL ANALYSIS")
print("-" * 78)

working_df = df.copy()

working_df["timestamp"] = parsed_timestamp

working_df = working_df.sort_values(
    ["market", "timestamp"]
)

working_df["interval_seconds"] = (
    working_df
    .groupby("market")["timestamp"]
    .diff()
    .dt.total_seconds()
)

intervals = (
    working_df["interval_seconds"]
    .dropna()
)

if len(intervals) == 0:

    print(
        "No interval data available."
    )

else:

    print(
        f"Intervals       : {len(intervals)}"
    )

    print(
        f"Minimum         : {intervals.min():.2f} sec"
    )

    print(
        f"Median          : {intervals.median():.2f} sec"
    )

    print(
        f"Maximum         : {intervals.max():.2f} sec"
    )

print()


# ============================================================
# 15. DATASET TIME RANGE
# ============================================================

print("15. DATASET TIME RANGE")
print("-" * 78)

valid_times = parsed_timestamp.dropna()

if len(valid_times) > 0:

    first_timestamp = valid_times.min()
    last_timestamp = valid_times.max()

    duration = (
        last_timestamp -
        first_timestamp
    )

    print(
        f"First record    : {first_timestamp}"
    )

    print(
        f"Last record     : {last_timestamp}"
    )

    print(
        f"Coverage        : {duration}"
    )

else:

    print(
        "No valid timestamps available."
    )

print()


# ============================================================
# 16. MARKET CONSISTENCY
# ============================================================

print("16. MARKET CONSISTENCY")
print("-" * 78)

market_asset_pairs = (
    df[
        ["market", "asset"]
    ]
    .drop_duplicates()
)

print(
    f"Market/asset pairs : "
    f"{len(market_asset_pairs)}"
)

print(
    market_asset_pairs
    .sort_values(["market", "asset"])
    .to_string(index=False)
)

print()


# ============================================================
# FINAL QUALITY CALCULATION
# ============================================================

total_records = max(
    len(df),
    1
)

critical_problem_count = (
    bad_price_count
    +
    bad_bid_count
    +
    bad_ask_count
    +
    bad_order_count
    +
    volume_errors
    +
    bad_pressure_count
    +
    bad_hunter_count
    +
    bad_timestamp_count
)

warning_problem_count = (
    duplicates
    +
    bad_mid_count
    +
    bad_spread_count
    +
    inconsistent_spread_count
    +
    missing_total
)


quality_penalty = (
    critical_problem_count * 100
    /
    total_records
)

warning_penalty = (
    warning_problem_count * 25
    /
    total_records
)

quality_score = max(
    0,
    100 -
    quality_penalty -
    warning_penalty
)


# ============================================================
# FINAL GATE
# ============================================================

if len(failures) > 0:

    final_status = "FAIL"

elif len(warnings) > 0:

    final_status = "WARNING"

else:

    final_status = "PASS"


# ============================================================
# FINAL REPORT
# ============================================================

print("=" * 78)
print("                    DATA QUALITY GATE")
print("=" * 78)

print(
    f"Records             : {len(df)}"
)

print(
    f"Markets             : {df['market'].nunique()}"
)

print(
    f"Assets              : {df['asset'].nunique()}"
)

print(
    f"Quality Score       : {quality_score:.2f}%"
)

print(
    f"Critical Problems   : {critical_problem_count}"
)

print(
    f"Warnings            : {len(warnings)}"
)

print(
    f"Failures            : {len(failures)}"
)

print(
    f"Final Status        : {final_status}"
)

print("=" * 78)


# ============================================================
# FAILURE DETAILS
# ============================================================

if failures:

    print()
    print("FAILURE DETAILS")
    print("-" * 78)

    for item in failures:

        print(
            f"- {item}"
        )


# ============================================================
# WARNING DETAILS
# ============================================================

if warnings:

    print()
    print("WARNING DETAILS")
    print("-" * 78)

    for item in warnings:

        print(
            f"- {item}"
        )


# ============================================================
# GATE DECISION
# ============================================================

print()
print("=" * 78)

if final_status == "PASS":

    print(
        "DATA QUALITY GATE : PASS"
    )

    print(
        "ACTION             : Data is acceptable for next stage."
    )

elif final_status == "WARNING":

    print(
        "DATA QUALITY GATE : WARNING"
    )

    print(
        "ACTION             : Data may proceed with caution."
    )

else:

    print(
        "DATA QUALITY GATE : FAIL"
    )

    print(
        "ACTION             : Block downstream analytical processing."
    )

print("=" * 78)
print()


# ============================================================
# EXIT CODE
# ============================================================

if final_status == "PASS":

    sys.exit(0)

elif final_status == "WARNING":

    sys.exit(0)

else:

    sys.exit(2)