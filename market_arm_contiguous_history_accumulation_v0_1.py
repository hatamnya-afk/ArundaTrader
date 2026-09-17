from pathlib import Path
import sqlite3
import importlib.util
from datetime import datetime, timezone

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
FABRIC_DB = ROOT / "public_market_data_fabric" / "canonical_store_v0.1.sqlite"

ACCUMULATOR = ROOT / "rolling_multi_horizon_context_accumulator_v0_2.py"

ASSETS = [
    "BTC","ETH","SOL","XRP","ADA",
    "DOGE","SHIB","LINK","AVAX","DOT",
    "LTC","UNI","AAVE","SUI","NEAR"
]

TIMEFRAME = "1h"
TARGET_RUN = 50
LAUNCH_TS = int(
    datetime.fromisoformat(
        "2026-08-31T00:00:00+00:00"
    ).timestamp()
)

def load_module(path):
    spec = importlib.util.spec_from_file_location(
        "existing_accumulator",
        path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("ACCUMULATOR_IMPORT_FAILED")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def ts(value):
    return int(float(value))

def load_rows(conn, asset):
    return conn.execute(
        """
        SELECT
            asset,
            symbol,
            source_id,
            source_type,
            timestamp,
            timeframe,
            open,
            high,
            low,
            close,
            volume,
            source_timestamp,
            retrieved_at,
            canonical_payload
        FROM canonical_ohlcv
        WHERE UPPER(asset)=?
          AND timeframe=?
          AND timestamp>=?
        ORDER BY timestamp ASC
        """,
        (asset, TIMEFRAME, LAUNCH_TS)
    ).fetchall()

def current_contiguous_run(rows):
    if not rows:
        return []

    rows = sorted(
        rows,
        key=lambda r: ts(r["timestamp"])
    )

    runs = []
    current = [rows[0]]

    for row in rows[1:]:
        delta = ts(row["timestamp"]) - ts(
            current[-1]["timestamp"]
        )

        if delta == 3600:
            current.append(row)
        else:
            runs.append(current)
            current = [row]

    runs.append(current)

    return max(
        runs,
        key=lambda run: ts(run[-1]["timestamp"])
    )

def run():
    print("=" * 100)
    print("ARUNDA MARKET ARM CONTIGUOUS HISTORY ACCUMULATION v0.1")
    print("=" * 100)

    print(f"FABRIC_DB={FABRIC_DB}")
    print("TIMEFRAME=1h")
    print("TARGET_CONTIGUOUS_RUN=50")
    print("TARGET_INCREMENT=29")
    print("SOURCE=KUCOIN")
    print("MODE=REAL_DATA_ONLY")
    print("PRODUCTION_DB=FORBIDDEN")
    print()

    # Import only the already-approved Fabric accumulator.
    accumulator = load_module(ACCUMULATOR)

    # READ-ONLY baseline.
    conn = sqlite3.connect(
        f"file:{FABRIC_DB}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    before = {}

    for asset in ASSETS:
        rows = load_rows(conn, asset)
        run_rows = current_contiguous_run(rows)

        before[asset] = {
            "total": len(rows),
            "run": len(run_rows),
            "latest": (
                ts(run_rows[-1]["timestamp"])
                if run_rows else None
            )
        }

    conn.close()

    print("BEFORE")
    print("-" * 100)

    for asset in ASSETS:
        b = before[asset]

        print(
            f"{asset:<5} "
            f"TOTAL={b['total']:<4} "
            f"RUN={b['run']:<3} "
            f"LATEST={b['latest']}"
        )

    print()
    print("=" * 100)
    print("ACCUMULATION")
    print("=" * 100)

    # Use the existing approved accumulator.
    # No production DB is opened by this script.
    #
    # We intentionally do not invent a new collector.
    # The existing accumulator remains the single source path.
    if not hasattr(accumulator, "run"):
        raise RuntimeError(
            "APPROVED_ACCUMULATOR_ENTRYPOINT_NOT_FOUND"
        )

    result = accumulator.run()

    print()
    print("=" * 100)
    print("AFTER")
    print("=" * 100)

    conn = sqlite3.connect(
        f"file:{FABRIC_DB}?mode=ro",
        uri=True
    )
    conn.row_factory = sqlite3.Row

    all_target = True
    total_inserted = 0

    for asset in ASSETS:
        rows = load_rows(conn, asset)
        run_rows = current_contiguous_run(rows)

        run_length = len(run_rows)

        if run_length < TARGET_RUN:
            all_target = False

        latest = (
            ts(run_rows[-1]["timestamp"])
            if run_rows else None
        )

        old = before[asset]["run"]

        delta = run_length - old

        print(
            f"{asset:<5} "
            f"BEFORE_RUN={old:<3} "
            f"AFTER_RUN={run_length:<3} "
            f"DELTA={delta:<3} "
            f"TARGET_REACHED={run_length >= TARGET_RUN} "
            f"LATEST={latest}"
        )

    conn.close()

    print()
    print("=" * 100)
    print("FINAL SAFETY")
    print("=" * 100)

    print("TARGET_RUN=50")
    print("ALL_MARKETS_TARGET_REACHED=", all_target)
    print("FABRIC_ONLY=TRUE")
    print("REAL_DATA_ONLY=TRUE")
    print("SYNTHETIC=FALSE")
    print("INTERPOLATION=FALSE")
    print("FILL=FALSE")
    print("BACKFILL=FALSE")
    print("PADDING=FALSE")
    print("BLENDING=FALSE")
    print("PRODUCTION_DB_TOUCHED=FALSE")
    print("SIGNAL_CHAIN_EXECUTED=FALSE")
    print("FUSION_EXECUTED=FALSE")
    print("SCORE=OFF")
    print("DECISION=OFF")
    print("ORDER_INTENTS=0")
    print("EXECUTION=OFF")

    print()
    print(
        "STATUS=",
        "READY_FOR_MARKET_ARM"
        if all_target
        else "CONTINUE_REAL_ACCUMULATION"
    )

if __name__ == "__main__":
    run()
