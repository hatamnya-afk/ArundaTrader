from pathlib import Path
import sqlite3
from datetime import datetime, timezone

FABRIC_DB = Path(
    r"C:\Users\ASUS\ArundaTrader\public_market_data_fabric\canonical_store_v0.1.sqlite"
)

LAUNCH_TS = int(
    datetime.fromisoformat(
        "2026-08-31T00:00:00+00:00"
    ).timestamp()
)

TIMEFRAME = "1h"

ASSETS = [
    "BTC","ETH","SOL","XRP","ADA",
    "DOGE","SHIB","LINK","AVAX","DOT",
    "LTC","UNI","AAVE","SUI","NEAR"
]

# Exact requirements implied by market_data_engine.py
REQUIREMENTS = {
    "EMA20": 20,
    "EMA50": 50,
    "RSI14": 15,       # 14 deltas require 15 closes
    "MACD": 35,        # engine explicitly requires >=35
    "BB20": 20,
    "VOLUME20": 20,
}

MARKET_SCORE_COMPONENTS = [
    "EMA20",
    "EMA50",
    "RSI14",
    "MACD",
    "BB20",
    "VOLUME20",
]

def ts(x):
    if isinstance(x, int):
        return x
    return int(float(x))

def load_market_rows(conn, asset):
    return conn.execute(
        """
        SELECT
            asset,
            symbol,
            source_id,
            timestamp,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            source_type,
            source_timestamp
        FROM canonical_ohlcv
        WHERE UPPER(asset)=?
          AND timeframe=?
          AND timestamp>=?
        ORDER BY timestamp ASC
        """,
        (asset, TIMEFRAME, LAUNCH_TS)
    ).fetchall()

def contiguous_runs(rows):
    if not rows:
        return []

    rows = sorted(rows, key=lambda r: ts(r["timestamp"]))

    runs = []
    current = [rows[0]]

    for row in rows[1:]:
        prev = ts(current[-1]["timestamp"])
        now = ts(row["timestamp"])

        if now - prev == 3600:
            current.append(row)
        else:
            runs.append(current)
            current = [row]

    runs.append(current)
    return runs

print("=" * 100)
print("ARUNDA MARKET ARM HISTORY REQUIREMENT v0.1")
print("=" * 100)

print()
print("FABRIC_DB=", FABRIC_DB)
print("LAUNCH_BOUNDARY=2026-08-31T00:00:00+00:00")
print("TIMEFRAME=1h")
print("DB_MODE=READ_ONLY")
print()

conn = sqlite3.connect(
    f"file:{FABRIC_DB}?mode=ro",
    uri=True
)
conn.row_factory = sqlite3.Row

global_pass = True

for asset in ASSETS:

    rows = load_market_rows(conn, asset)
    runs = contiguous_runs(rows)

    if not runs:
        print(
            f"{asset} | NO_DATA"
        )
        global_pass = False
        continue

    current = max(
        runs,
        key=lambda x: ts(x[-1]["timestamp"])
    )

    points = len(current)

    print()
    print("-" * 100)
    print(f"ASSET={asset}")
    print(f"TOTAL_PRODUCTION_ROWS={len(rows)}")
    print(f"CONTIGUOUS_RUN={points}")

    for component, required in REQUIREMENTS.items():

        ready = points >= required

        print(
            f"{component:<10} "
            f"REQUIRED={required:<3} "
            f"AVAILABLE={points:<3} "
            f"READY={ready}"
        )

        if not ready:
            global_pass = False

    # Determine what can actually contribute to technical_score
    available_components = [
        name
        for name, required in REQUIREMENTS.items()
        if points >= required
    ]

    print(
        "AVAILABLE_COMPONENTS=",
        ",".join(available_components)
        if available_components else "NONE"
    )

    print(
        "MARKET_SCORE_FULL_INPUT_READY=",
        points >= max(REQUIREMENTS.values())
    )

    print(
        "OLDEST_CURRENT_RUN=",
        datetime.fromtimestamp(
            ts(current[0]["timestamp"]),
            timezone.utc
        ).isoformat()
    )

    print(
        "LATEST_CURRENT_RUN=",
        datetime.fromtimestamp(
            ts(current[-1]["timestamp"]),
            timezone.utc
        ).isoformat()
    )

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)

print(
    "MAX_REQUIRED_HISTORY=",
    max(REQUIREMENTS.values())
)
print(
    "CURRENT_RUN_EXPECTED=21"
)
print(
    "MARKET_SCORE_REQUIRES_FULL_COMPONENT_SET=",
    max(REQUIREMENTS.values())
)
print(
    "MARKET_ARM_READY=",
    global_pass
)
print(
    "FABRIC_MODIFIED=FALSE"
)
print(
    "PRODUCTION_DB_TOUCHED=FALSE"
)
print(
    "DB_WRITES=0"
)
print(
    "PRODUCER_EXECUTED=FALSE"
)
print(
    "FUSION_EXECUTED=FALSE"
)
print(
    "SCORE=OFF"
)
print(
    "DECISION=OFF"
)
print(
    "ORDER_INTENTS=0"
)
print(
    "EXECUTION=OFF"
)
print("=" * 100)

conn.close()
