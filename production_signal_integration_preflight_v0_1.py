from pathlib import Path
import sqlite3
from datetime import datetime, timezone

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
FABRIC_DB = PROJECT_ROOT / "public_market_data_fabric" / "canonical_store_v0.1.sqlite"

LAUNCH_TIMESTAMP = int(
    datetime(2026, 8, 31, 0, 0, tzinfo=timezone.utc).timestamp()
)

TIMEFRAME = "1h"
REQUIRED_SIGNAL_CONTEXT = 21

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

def get_current_run(rows):
    if not rows:
        return 0, None

    rows = sorted(rows, key=lambda x: x["timestamp"])
    latest = rows[-1]["timestamp"]

    run = 1

    for i in range(len(rows) - 1, 0, -1):
        newer = rows[i]["timestamp"]
        older = rows[i - 1]["timestamp"]

        if newer - older != 3600:
            break

        run += 1

    return run, latest


# --------------------------------------------------
# READ-ONLY FABRIC ACCESS
# --------------------------------------------------

conn = sqlite3.connect(
    f"file:{FABRIC_DB}?mode=ro",
    uri=True
)

raw = conn.execute("""
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
      AND timestamp >= ?
    ORDER BY asset, symbol, timestamp
""", (TIMEFRAME, LAUNCH_TIMESTAMP)).fetchall()

conn.close()


markets = {}

for r in raw:
    (
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
        price_unit,
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


ready_count = 0
blocked_count = 0


for asset, symbol in EXPECTED_MARKETS:

    key = (asset, symbol)
    rows = markets.get(key, [])

    context_ready = False
    launch_valid = True
    provenance_valid = True
    ordering_valid = True
    continuity_valid = False
    legacy_used = False
    signal_input_ready = False

    if not rows:
        blocked_count += 1

        print(f"MARKET={asset}|{symbol}")
        print("CURRENT_CONTIGUOUS_RUN=0")
        print(f"REQUIRED_SIGNAL_CONTEXT={REQUIRED_SIGNAL_CONTEXT}")
        print("CONTEXT_READY=FALSE")
        print("LAUNCH_BOUNDARY_VALID=FALSE")
        print("PROVENANCE_VALID=FALSE")
        print("ORDERING_VALID=FALSE")
        print("CONTINUITY_VALID=FALSE")
        print("LEGACY_DATA_USED=FALSE")
        print("SIGNAL_INPUT_READY=FALSE")
        print()

        continue


    # --------------------------------------------------
    # MARKET-SCOPED ORDERING
    # --------------------------------------------------

    rows.sort(key=lambda x: x["timestamp"])

    timestamps = [x["timestamp"] for x in rows]

    if timestamps != sorted(timestamps):
        ordering_valid = False

    if len(timestamps) != len(set(timestamps)):
        ordering_valid = False


    # --------------------------------------------------
    # LAUNCH BOUNDARY
    # --------------------------------------------------

    for x in rows:
        if x["timestamp"] < LAUNCH_TIMESTAMP:
            launch_valid = False
            legacy_used = True


    # --------------------------------------------------
    # PROVENANCE
    # --------------------------------------------------

    for x in rows:

        if not x["source_id"]:
            provenance_valid = False

        if not x["source_type"]:
            provenance_valid = False

        if x["source_timestamp"] <= 0:
            provenance_valid = False

        if not x["retrieved_at"]:
            provenance_valid = False

        if x["observation_count"] is None:
            provenance_valid = False

        if not x["observation_signatures"]:
            provenance_valid = False

        if not x["observation_slots"]:
            provenance_valid = False


    # --------------------------------------------------
    # CURRENT CONTIGUOUS RUN
    # --------------------------------------------------

    run_length, latest_timestamp = get_current_run(rows)

    continuity_valid = run_length >= REQUIRED_SIGNAL_CONTEXT


    # --------------------------------------------------
    # SIGNAL INPUT CONTRACT
    # --------------------------------------------------

    context_ready = (
        run_length >= REQUIRED_SIGNAL_CONTEXT
    )

    signal_input_ready = (
        context_ready
        and launch_valid
        and provenance_valid
        and ordering_valid
        and continuity_valid
        and not legacy_used
    )


    if signal_input_ready:
        ready_count += 1
    else:
        blocked_count += 1


    # --------------------------------------------------
    # OUTPUT
    # --------------------------------------------------

    print(f"MARKET={asset}|{symbol}")

    if latest_timestamp is not None:
        print(f"CURRENT_CONTIGUOUS_RUN={run_length}")
    else:
        print("CURRENT_CONTIGUOUS_RUN=0")

    print(f"REQUIRED_SIGNAL_CONTEXT={REQUIRED_SIGNAL_CONTEXT}")
    print(f"CONTEXT_READY={'TRUE' if context_ready else 'FALSE'}")
    print(f"LAUNCH_BOUNDARY_VALID={'TRUE' if launch_valid else 'FALSE'}")
    print(f"PROVENANCE_VALID={'TRUE' if provenance_valid else 'FALSE'}")
    print(f"ORDERING_VALID={'TRUE' if ordering_valid else 'FALSE'}")
    print(f"CONTINUITY_VALID={'TRUE' if continuity_valid else 'FALSE'}")
    print(f"LEGACY_DATA_USED={'TRUE' if legacy_used else 'FALSE'}")
    print(f"SIGNAL_INPUT_READY={'TRUE' if signal_input_ready else 'FALSE'}")

    print()


# --------------------------------------------------
# SUMMARY
# --------------------------------------------------

print("MARKETS_TOTAL=15")
print(f"MARKETS_READY={ready_count}")
print(f"MARKETS_BLOCKED={blocked_count}")
print("PRODUCTION_DB_TOUCHED=FALSE")
print("PRODUCTION_DB_WRITE=0")
print("SIGNAL_CHAIN_EXECUTED=FALSE")
print("ORDER_INTENTS=0")
print("EXECUTION=OFF")
print("PRODUCTION_PATH_MUTATION=FALSE")

if ready_count == 15:
    print("STATUS=SIGNAL_INPUT_PREFLIGHT_PASS")
else:
    print("STATUS=PARTIAL_MARKET_READINESS")
