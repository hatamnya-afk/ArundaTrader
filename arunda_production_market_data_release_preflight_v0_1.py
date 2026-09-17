from pathlib import Path
import sqlite3
import json
import math

ENGINE = "ARUNDA_PRODUCTION_MARKET_DATA_RELEASE_PREFLIGHT"
VERSION = "v0.1"

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
FABRIC_DB = ROOT / "public_market_data_fabric" / "canonical_store_v0.1.sqlite"
PRODUCTION_DB = ROOT / "arunda.db"

LAUNCH_BOUNDARY = "2026-08-31T00:00:00+00:00"
LAUNCH_TS = 1788134400

TIMEFRAME = "1h"
PRIMARY_PROVIDER = "KUCOIN"
FAILOVER_POLICY = "FAILOVER, NOT BLENDING"


def finite(v):
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def json_list(v):
    try:
        x = json.loads(v)
        return x if isinstance(x, list) else None
    except Exception:
        return None


def is_nullish(v):
    return v is None or str(v).strip().lower() in ("", "null", "none")


def main():

    if not FABRIC_DB.exists():
        print(f"ENGINE={ENGINE}")
        print(f"VERSION={VERSION}")
        print("FABRIC_INPUT=False")
        print(f"LAUNCH_BOUNDARY={LAUNCH_BOUNDARY}")
        print("CANONICAL_BARS=0")
        print("VALID_BARS=0")
        print("LEGACY_BLOCKED=0")
        print("PRE_LAUNCH_BLOCKED=0")
        print("INVALID_SOURCE_BLOCKED=0")
        print("MISSING_PROVENANCE_BLOCKED=0")
        print("DUPLICATE_BLOCKED=0")
        print(f"PRIMARY_PROVIDER={PRIMARY_PROVIDER}")
        print(f"FAILOVER_POLICY={FAILOVER_POLICY}")
        print("BLENDING=False")
        print("PRODUCTION_ENABLE_REQUESTED=False")
        print("PRODUCTION_DB_TOUCHED=False")
        print("DB_WRITES=0")
        print("ORDER_INTENTS_CREATED=0")
        print("EXECUTION=DISABLED")
        print("VALIDATION=FAIL")
        print("STATUS=RELEASE_PREFLIGHT_FAIL")
        return

    production_before = (
        PRODUCTION_DB.stat().st_mtime_ns
        if PRODUCTION_DB.exists()
        else None
    )

    con = sqlite3.connect(
        f"file:{FABRIC_DB.as_posix()}?mode=ro",
        uri=True
    )
    con.row_factory = sqlite3.Row

    canonical_bars = 0
    valid = []

    legacy_blocked = 0
    pre_launch_blocked = 0
    invalid_source_blocked = 0
    missing_provenance_blocked = 0
    duplicate_blocked = 0

    seen = set()

    try:

        rows = con.execute("""
            SELECT
                asset,
                symbol,
                timestamp,
                timeframe,
                open,
                high,
                low,
                close,
                volume,
                source_id,
                source_type,
                source_timestamp,
                retrieved_at,
                observation_count,
                observation_signatures,
                observation_slots,
                pool,
                raydium_instruction,
                canonical_payload
            FROM canonical_ohlcv
            ORDER BY timestamp, asset, symbol
        """).fetchall()

        canonical_bars = len(rows)

        for row in rows:

            try:
                timestamp = int(row["timestamp"])
            except Exception:
                invalid_source_blocked += 1
                continue

            if timestamp < LAUNCH_TS:
                pre_launch_blocked += 1
                continue

            source_type = str(row["source_type"] or "")
            source_id = str(row["source_id"] or "")

            # DEX is legacy/non-production for this CEX release.
            if source_type == "DEX_ONCHAIN":
                legacy_blocked += 1
                continue

            # Current canonical production provider.
            if not (
                source_type == "CEX_PUBLIC_API"
                and source_id.startswith("KUCOIN_SPOT:")
            ):
                invalid_source_blocked += 1
                continue

            if str(row["timeframe"]) != TIMEFRAME:
                invalid_source_blocked += 1
                continue

            signatures = json_list(
                row["observation_signatures"]
            )

            slots = json_list(
                row["observation_slots"]
            )

            try:
                observation_count = int(
                    row["observation_count"]
                )
            except Exception:
                observation_count = -1

            try:
                source_timestamp = int(
                    row["source_timestamp"]
                )
            except Exception:
                source_timestamp = None

            provenance_valid = (
                bool(str(row["retrieved_at"] or "").strip())
                and source_timestamp == timestamp
                and observation_count == 1
                and signatures is not None
                and len(signatures) == 1
                and bool(str(signatures[0]).strip())
                and slots is not None
                and len(slots) == 1
                and int(slots[0]) == timestamp
                and bool(
                    str(row["canonical_payload"] or "").strip()
                )
            )

            if not provenance_valid:
                missing_provenance_blocked += 1
                continue

            # CEX must not contain actual DEX provenance.
            # SQLite may contain the literal string "null".
            if not is_nullish(row["pool"]):
                invalid_source_blocked += 1
                continue

            if not is_nullish(row["raydium_instruction"]):
                invalid_source_blocked += 1
                continue

            values = [
                row["open"],
                row["high"],
                row["low"],
                row["close"],
                row["volume"],
            ]

            if not all(finite(v) for v in values):
                invalid_source_blocked += 1
                continue

            o = float(row["open"])
            h = float(row["high"])
            l = float(row["low"])
            c = float(row["close"])
            v = float(row["volume"])

            if (
                o <= 0
                or h <= 0
                or l <= 0
                or c <= 0
                or v < 0
                or h < max(o, c, l)
                or l > min(o, c, h)
            ):
                invalid_source_blocked += 1
                continue

            key = (
                str(row["asset"]),
                str(row["symbol"]),
                timestamp,
                str(row["timeframe"]),
            )

            if key in seen:
                duplicate_blocked += 1
                continue

            seen.add(key)
            valid.append(row)

    finally:
        con.close()

    production_after = (
        PRODUCTION_DB.stat().st_mtime_ns
        if PRODUCTION_DB.exists()
        else None
    )

    production_db_touched = (
        production_before != production_after
    )

    validation = (
        canonical_bars > 0
        and len(valid) > 0
        and not production_db_touched
    )

    print(f"ENGINE={ENGINE}")
    print(f"VERSION={VERSION}")
    print("FABRIC_INPUT=True")
    print(f"LAUNCH_BOUNDARY={LAUNCH_BOUNDARY}")
    print(f"CANONICAL_BARS={canonical_bars}")
    print(f"VALID_BARS={len(valid)}")
    print(f"LEGACY_BLOCKED={legacy_blocked}")
    print(f"PRE_LAUNCH_BLOCKED={pre_launch_blocked}")
    print(f"INVALID_SOURCE_BLOCKED={invalid_source_blocked}")
    print(f"MISSING_PROVENANCE_BLOCKED={missing_provenance_blocked}")
    print(f"DUPLICATE_BLOCKED={duplicate_blocked}")
    print(f"PRIMARY_PROVIDER={PRIMARY_PROVIDER}")
    print(f"FAILOVER_POLICY={FAILOVER_POLICY}")
    print("BLENDING=False")
    print("PRODUCTION_ENABLE_REQUESTED=False")
    print(f"PRODUCTION_DB_TOUCHED={production_db_touched}")
    print("DB_WRITES=0")
    print("ORDER_INTENTS_CREATED=0")
    print("EXECUTION=DISABLED")
    print(f"VALIDATION={'PASS' if validation else 'FAIL'}")
    print(
        "STATUS="
        + (
            "RELEASE_PREFLIGHT_READY"
            if validation
            else "RELEASE_PREFLIGHT_FAIL"
        )
    )


if __name__ == "__main__":
    main()