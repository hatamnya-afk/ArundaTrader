import pandas as pd
import numpy as np

FILE = "hunter_records.csv"

INTERVAL_SECONDS = 15

print()
print("==============================================")
print("        ARUNDA PATTERN ENGINE v0.2")
print("==============================================")

# ------------------------------------------------
# LOAD DATA
# ------------------------------------------------

df = pd.read_csv(FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

df = df.sort_values(
    ["market", "timestamp"]
).reset_index(drop=True)

print(f"Records : {len(df)}")
print(f"Markets : {df['market'].nunique()}")
print()

# ------------------------------------------------
# FUTURE RETURN FUNCTION
# ------------------------------------------------

def add_future_return(data, minutes):

    steps = int(
        minutes * 60 / INTERVAL_SECONDS
    )

    future_price = (
        data.groupby("market")["price"]
        .shift(-steps)
    )

    data[f"future_{minutes}m"] = (
        (future_price / data["price"]) - 1
    ) * 100

    return data


# ------------------------------------------------
# FUTURE RETURNS
# ------------------------------------------------

for minutes in [5, 15, 30]:

    df = add_future_return(
        df,
        minutes
    )

# ------------------------------------------------
# PRESSURE CHANGE
# ------------------------------------------------

df["pressure_change"] = (
    df.groupby("market")["pressure"]
    .diff()
)

# ------------------------------------------------
# PRICE MOMENTUM
# ------------------------------------------------

df["price_change"] = (
    df.groupby("market")["price"]
    .pct_change()
    * 100
)

# ------------------------------------------------
# VOLUME CHANGE
# ------------------------------------------------

df["volume_change"] = (
    df.groupby("market")["volume_24h"]
    .pct_change()
    * 100
)

# ------------------------------------------------
# FEATURES
# ------------------------------------------------

features = [
    "pressure",
    "pressure_change",
    "price_change",
    "volume_change",
    "spread_pct",
]

print("FEATURES")
print("----------------------------------------------")

print(
    df[features].describe()
)

# ------------------------------------------------
# FUTURE RETURNS
# ------------------------------------------------

targets = [
    "future_5m",
    "future_15m",
    "future_30m",
]

print()
print("FUTURE RETURNS")
print("----------------------------------------------")

print(
    df[targets].describe()
)

# ------------------------------------------------
# CORRELATIONS
# ------------------------------------------------

print()
print("FEATURE → FUTURE RETURN CORRELATION")
print("----------------------------------------------")

for target in targets:

    print()
    print(target)

    for feature in features:

        valid = df[
            [feature, target]
        ].dropna()

        if len(valid) < 20:
            continue

        correlation = valid[feature].corr(
            valid[target]
        )

        print(
            f"{feature:<20} : "
            f"{correlation:>8.4f}"
        )

# ------------------------------------------------
# PRESSURE BUCKET ANALYSIS
# ------------------------------------------------

print()
print("PRESSURE ANALYSIS")
print("----------------------------------------------")

df["pressure_bucket"] = pd.cut(
    df["pressure"],
    bins=[
        0,
        40,
        50,
        60,
        70,
        80,
        100
    ],
    labels=[
        "<40",
        "40-50",
        "50-60",
        "60-70",
        "70-80",
        "80+"
    ]
)

for target in targets:

    print()
    print(f"{target}")

    result = (
        df.groupby(
            "pressure_bucket",
            observed=False
        )[target]
        .agg(
            ["count", "mean", "median"]
        )
    )

    print(result)

print()
print("==============================================")
print("        ANALYSIS COMPLETE")
print("==============================================")