from pathlib import Path
import sqlite3
from datetime import datetime, timezone

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
FABRIC_DB = PROJECT_ROOT / "public_market_data_fabric" / "canonical_store_v0.1.sqlite"

TIMEFRAME = "1h"
TARGET_CAP = 150
MIN_SIGNAL_HORIZON = "IMMEDIATE"

HORIZONS = {
    "IMMEDIATE": (1, 6),
    "SHORT_TERM": (7, 24),
    "MEDIUM_TERM": (25, 72),
    "LONG_TERM": (73, 150),
}

EXPECTED_MARKETS = [
    ("AAVE", "AAVE/USDT"),
    ("ADA", "ADA/USDT"),
    ("AVAX", "AVAX/USDT"),
    ("BTC", "BTC/USDT"),
    ("DOGE", "DOGE/USDT"),
    ("DOT", "DOT/USDT"),
    ("ETH", "ETH/USDT"),
    ("LINK", "LINK/USDT"),
    ("LTC", "LTC/USDT"),
    ("NEAR", "NEAR/USDT"),
    ("SHIB", "SHIB/USDT"),
    ("SOL", "SOL/USDT"),
    ("SUI", "SUI/USDT"),
    ("UNI", "UNI/USDT"),
    ("XRP", "XRP/USDT"),
]

def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()

def fail(msg):
    raise RuntimeError(msg)

conn = sqlite3.connect(f"file:{FABRIC_DB}?mode=ro", uri=True)

rows = conn.execute("""
    SELECT
        asset,
        symbol,
        timestamp,
        timeframe,
        source_id,
        source_type,
        source_timestamp,
        retrieved_at,
        observation_count,
        observation_signatures,
        observation_slots,
        price_unit
    FROM canonical_ohlcv
    WHERE timeframe = ?
    ORDER BY asset, symbol, timestamp
""", (TIMEFRAME,)).fetchall()

conn.close()

markets = {}

for r in rows:
    (
        asset, symbol, timestamp, timeframe,
        source_id, source_type, source_timestamp,
        retrieved_at, observation_count,
        observation_signatures, observation_slots, price_unit
    ) = r

    key = (str(asset).upper(), str(symbol).upper())

    markets.setdefault(key, []).append({
        "asset": str(asset).upper(),
        "symbol": str(symbol).upper(),
        "timestamp": int(timestamp),
        "timeframe": timeframe,
        "source_id": source_id,
        "source_type": source_type,
        "source_timestamp": int(source_timestamp),
        "retrieved_at": retrieved_at,
        "observation_count": observation_count,
        "observation_signatures": observation_signatures,
        "observation_slots": observation_slots,
        "price_unit": price_unit,
    })

global_provenance_valid = True
global_provenance_errors = []

for asset, symbol in EXPECTED_MARKETS:

    key = (asset, symbol)
    data = markets.get(key, [])

    if not data:
        print(f"MARKET={asset}|{symbol}")
        print("LATEST_TIMESTAMP=NONE")
        print("CURRENT_CONTIGUOUS_RUN=0")
        print("GAP_DETECTED=TRUE")
        print("GAP_DURATION=UNKNOWN")
        print("IMMEDIATE=BLOCKED")
        print("SHORT_TERM=BLOCKED")
        print("MEDIUM_TERM=BLOCKED")
        print("LONG_TERM=BLOCKED")
        print("CONTEXT_VALID=FALSE")
        print("PROVENANCE_VALID=FALSE")
        print("SYNTHETIC=FALSE")
        print("INTERPOLATION=FALSE")
        print("FILL=FALSE")
        print("BACKFILL=FALSE")
        print("PADDING=FALSE")
        print("BLENDING=FALSE")
        print("PRODUCTION_DB_TOUCHED=FALSE")
        print("DB_WRITES=0")
        print("SIGNAL_CHAIN_EXECUTED=FALSE")
        print("ORDER_INTENTS=0")
        print("EXECUTION=OFF")
        print("STATUS=BLOCKED_NO_DATA")
        continue

    data.sort(key=lambda x: x["timestamp"])

    # Identity / duplicate validation
    seen = set()
    provenance_valid = True

    for x in data:
        if x["timestamp"] in seen:
            provenance_valid = False
            global_provenance_errors.append(
                f"{asset}/{symbol}:DUPLICATE_TIMESTAMP:{x['timestamp']}"
            )
        seen.add(x["timestamp"])

        if not x["source_id"] or not x["source_type"]:
            provenance_valid = False
            global_provenance_errors.append(
                f"{asset}/{symbol}:MISSING_PROVENANCE"
            )

        if not x["retrieved_at"]:
            provenance_valid = False
            global_provenance_errors.append(
                f"{asset}/{symbol}:MISSING_RETRIEVED_AT"
            )

        if x["source_timestamp"] <= 0:
            provenance_valid = False
            global_provenance_errors.append(
                f"{asset}/{symbol}:INVALID_SOURCE_TIMESTAMP"
            )

        if x["observation_count"] is None:
            provenance_valid = False

        if not x["observation_signatures"]:
            provenance_valid = False

        if not x["observation_slots"]:
            provenance_valid = False

    if not provenance_valid:
        global_provenance_valid = False

    # Latest real observation
    latest = data[-1]["timestamp"]

    # Walk backwards from latest.
    # Only the final fully contiguous 1h chain is CURRENT_CONTIGUOUS_RUN.
    contiguous = [data[-1]]
    first_gap_duration = 0

    for i in range(len(data) - 1, 0, -1):
        newer = data[i]["timestamp"]
        older = data[i - 1]["timestamp"]
        delta = newer - older

        if delta == 3600:
            contiguous.append(data[i - 1])
        else:
            first_gap_duration = delta - 3600
            break

    contiguous.reverse()
    run_len = len(contiguous)

    gap_detected = len(data) > run_len
    gap_duration = str(first_gap_duration) if gap_detected else "0"

    # Horizon readiness is strictly based on the current contiguous run.
    horizon_ready = {}

    for name, (start_offset, end_offset) in HORIZONS.items():
        required = end_offset
        horizon_ready[name] = (
            run_len >= required and provenance_valid
        )

    # Context validity means the minimum configured Signal horizon is available.
    context_valid = horizon_ready[MIN_SIGNAL_HORIZON]

    print(f"MARKET={asset}|{symbol}")
    print(f"LATEST_TIMESTAMP={iso(latest)}")
    print(f"CURRENT_CONTIGUOUS_RUN={run_len}")
    print(f"GAP_DETECTED={'TRUE' if gap_detected else 'FALSE'}")
    print(f"GAP_DURATION={gap_duration}")

    print(f"IMMEDIATE={'READY' if horizon_ready['IMMEDIATE'] else 'BLOCKED'}")
    print(f"SHORT_TERM={'READY' if horizon_ready['SHORT_TERM'] else 'BLOCKED'}")
    print(f"MEDIUM_TERM={'READY' if horizon_ready['MEDIUM_TERM'] else 'BLOCKED'}")
    print(f"LONG_TERM={'READY' if horizon_ready['LONG_TERM'] else 'BLOCKED'}")

    print(f"CONTEXT_VALID={'TRUE' if context_valid else 'FALSE'}")
    print(f"PROVENANCE_VALID={'TRUE' if provenance_valid else 'FALSE'}")

    print("SYNTHETIC=FALSE")
    print("INTERPOLATION=FALSE")
    print("FILL=FALSE")
    print("BACKFILL=FALSE")
    print("PADDING=FALSE")
    print("BLENDING=FALSE")
    print("PRODUCTION_DB_TOUCHED=FALSE")
    print("DB_WRITES=0")
    print("SIGNAL_CHAIN_EXECUTED=FALSE")
    print("ORDER_INTENTS=0")
    print("EXECUTION=OFF")

    if context_valid:
        print("STATUS=READY_FOR_NEXT_STAGE")
    elif run_len > 0:
        print("STATUS=PARTIAL_CONTEXT")
    else:
        print("STATUS=BLOCKED_NO_CONTIGUOUS_CONTEXT")

    print()

print("SUMMARY_STATUS=HORIZON_SCOPED_CONTINUITY")
print("TOTAL_MARKETS=15")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("DB_WRITES=0")
print("SIGNAL_CHAIN_EXECUTED=FALSE")
print("ORDER_INTENTS=0")
print("EXECUTION=OFF")
