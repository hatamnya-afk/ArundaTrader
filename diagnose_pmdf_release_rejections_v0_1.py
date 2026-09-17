from pathlib import Path
import sqlite3
import json
import math

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
FABRIC_DB = ROOT / "public_market_data_fabric" / "canonical_store_v0.1.sqlite"

LAUNCH_TS = 1788134400
TIMEFRAME = "1h"


def finite(v):
    try:
        return math.isfinite(float(v))
    except Exception:
        return False


def jlist(v):
    try:
        x = json.loads(v)
        return x if isinstance(x, list) else None
    except Exception:
        return None


def main():

    con = sqlite3.connect(
        f"file:{FABRIC_DB.as_posix()}?mode=ro",
        uri=True
    )
    con.row_factory = sqlite3.Row

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

        print(f"ROWS={len(rows)}")

        for i, r in enumerate(rows, 1):

            failures = []

            try:
                ts = int(r["timestamp"])
            except Exception:
                ts = None
                failures.append("INVALID_TIMESTAMP")

            if ts is not None and ts < LAUNCH_TS:
                failures.append("PRE_LAUNCH")

            source_type = str(r["source_type"] or "")
            source_id = str(r["source_id"] or "")

            if source_type == "DEX_ONCHAIN":
                failures.append("LEGACY_DEX")

            elif not (
                source_type == "CEX_PUBLIC_API"
                and source_id.startswith("KUCOIN_SPOT:")
            ):
                failures.append("INVALID_CEX_SOURCE")

            if str(r["timeframe"]) != TIMEFRAME:
                failures.append("INVALID_TIMEFRAME")

            signatures = jlist(r["observation_signatures"])
            slots = jlist(r["observation_slots"])

            try:
                observation_count = int(r["observation_count"])
            except Exception:
                observation_count = -1

            try:
                source_timestamp = int(r["source_timestamp"])
            except Exception:
                source_timestamp = None

            if not bool(str(r["retrieved_at"] or "").strip()):
                failures.append("MISSING_RETRIEVED_AT")

            if source_timestamp != ts:
                failures.append("SOURCE_TIMESTAMP_MISMATCH")

            if observation_count != 1:
                failures.append("INVALID_OBSERVATION_COUNT")

            if signatures is None:
                failures.append("INVALID_SIGNATURES_JSON")
            elif len(signatures) != 1:
                failures.append("INVALID_SIGNATURE_COUNT")
            elif not bool(str(signatures[0]).strip()):
                failures.append("EMPTY_SIGNATURE")

            if slots is None:
                failures.append("INVALID_SLOTS_JSON")
            elif len(slots) != 1:
                failures.append("INVALID_SLOT_COUNT")
            elif ts is not None:
                try:
                    if int(slots[0]) != ts:
                        failures.append("SLOT_TIMESTAMP_MISMATCH")
                except Exception:
                    failures.append("INVALID_SLOT_VALUE")

            if not bool(str(r["canonical_payload"] or "").strip()):
                failures.append("MISSING_CANONICAL_PAYLOAD")

            if source_type == "CEX_PUBLIC_API":
                if r["pool"] is not None:
                    failures.append("CEX_HAS_POOL")

                if r["raydium_instruction"] is not None:
                    failures.append("CEX_HAS_RAYDIUM_INSTRUCTION")

            values = [
                r["open"],
                r["high"],
                r["low"],
                r["close"],
                r["volume"],
            ]

            if not all(finite(v) for v in values):
                failures.append("NON_FINITE_OHLCV")
            else:
                o = float(r["open"])
                h = float(r["high"])
                l = float(r["low"])
                c = float(r["close"])
                v = float(r["volume"])

                if o <= 0:
                    failures.append("OPEN_NON_POSITIVE")
                if h <= 0:
                    failures.append("HIGH_NON_POSITIVE")
                if l <= 0:
                    failures.append("LOW_NON_POSITIVE")
                if c <= 0:
                    failures.append("CLOSE_NON_POSITIVE")
                if v < 0:
                    failures.append("VOLUME_NEGATIVE")

                if h < max(o, c, l):
                    failures.append("HIGH_INVALID_RELATION")

                if l > min(o, c, h):
                    failures.append("LOW_INVALID_RELATION")

            print()
            print(f"===== ROW_{i} =====")
            print(f"asset={r['asset']}")
            print(f"symbol={r['symbol']}")
            print(f"timestamp={r['timestamp']}")
            print(f"timeframe={r['timeframe']}")
            print(f"source_id={r['source_id']}")
            print(f"source_type={r['source_type']}")
            print(f"open={r['open']}")
            print(f"high={r['high']}")
            print(f"low={r['low']}")
            print(f"close={r['close']}")
            print(f"volume={r['volume']}")
            print(f"source_timestamp={r['source_timestamp']}")
            print(f"retrieved_at={r['retrieved_at']}")
            print(f"observation_count={r['observation_count']}")
            print(f"observation_signatures={r['observation_signatures']}")
            print(f"observation_slots={r['observation_slots']}")
            print(f"pool={r['pool']}")
            print(f"raydium_instruction={r['raydium_instruction']}")
            print(
                "RESULT="
                + ("VALID" if not failures else "BLOCKED")
            )
            print(
                "FAILURES="
                + (
                    "NONE"
                    if not failures
                    else ",".join(failures)
                )
            )

    finally:
        con.close()

    print()
    print("READ_ONLY=True")
    print("DB_WRITES=0")


if __name__ == "__main__":
    main()