import pandas as pd

FILE = "market_data.csv"

df = pd.read_csv(FILE)

df["timestamp"] = pd.to_datetime(df["timestamp"])

print("\n========== ARUNDA MARKET ANALYZER ==========\n")

print(f"Records       : {len(df):,}")
print(f"Start         : {df['timestamp'].min()}")
print(f"End           : {df['timestamp'].max()}")

print("\n--- PRICE ---")

print(f"Start Price   : {df['mid_price'].iloc[0]:,.0f}")
print(f"End Price     : {df['mid_price'].iloc[-1]:,.0f}")

price_change = (
    (df["mid_price"].iloc[-1] /
     df["mid_price"].iloc[0]) - 1
) * 100

print(f"Total Change  : {price_change:.4f}%")

print("\n--- ORDER BOOK ---")

print(f"Avg P0.1      : {df['pressure_01'].mean():.2f}%")
print(f"Avg P0.25     : {df['pressure_025'].mean():.2f}%")
print(f"Avg P0.5      : {df['pressure_05'].mean():.2f}%")
print(f"Avg P1        : {df['pressure_1'].mean():.2f}%")
print(f"Avg P2        : {df['pressure_2'].mean():.2f}%")

print("\n--- SPREAD ---")

print(f"Avg Spread    : {df['spread_percent'].mean():.4f}%")
print(f"Max Spread    : {df['spread_percent'].max():.4f}%")

print("\n--- PRESSURE EXTREMES ---")

print(
    f"P0.5 Min      : "
    f"{df['pressure_05'].min():.2f}%"
)

print(
    f"P0.5 Max      : "
    f"{df['pressure_05'].max():.2f}%"
)

print("\n============================================")