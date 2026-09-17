from pathlib import Path
import sqlite3
import json
import math
import os

ENGINE = "ARUNDA_CONTROLLED_PRODUCTION_MARKET_DATA_RELEASE"
VERSION = "v0.1"

ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
FABRIC_DB = ROOT / "public_market_data_fabric" / "canonical_store_v0.1.sqlite"
PRODUCTION_DB = ROOT / "arunda.db"

LAUNCH_TIMESTAMP = "2026-08-31T00:00:00+00:00"
LAUNCH_TS = 1788134400

TIMEFRAME = "1h"

PRIMARY_PROVIDER = "KUCOIN"
FAILOVER_PROVIDER = "BITGET"
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
    return v is None or str(v).strip().lower() in (
        "",
        "null",
        "none",
    )


def emit(
    release_mode,
    fabric_input,
    selected_provider,
    failover_triggered,
    canonical_bars,
    valid_bars,
    provenance_valid,
    legacy_blocked,
    pre_launch_blocked,
    invalid_source_blocked,
    missing_provenance_blocked,
    duplicate_blocked,
    production_consumption_enabled,
    production_candles_consumed,
    production_db_touched,
    db_writes,
    production_path_mutation,
    validation,
    status,
):
    print(f"ENGINE={ENGINE}")
    print(f"VERSION={VERSION}")
    print(f"RELEASE_MODE={release_mode}")
    print(f"FABRIC_INPUT={fabric_input}")
    print(f"PRIMARY_PROVIDER={PRIMARY_PROVIDER}")
    print(f"SELECTED_PROVIDER={selected_provider}")
    print(f"FAILOVER_TRIGGERED={failover_triggered}")
    print(f"CANONICAL_BARS={canonical_bars}")
    print(f"VALID_BARS={valid_bars}")
    print(f"PROVENANCE_VALID={provenance_valid}")
    print(f"LEGACY_BLOCKED={legacy_blocked}")
    print(f"PRE_LAUNCH_BLOCKED={pre_launch_blocked}")
    print(f"INVALID_SOURCE_BLOCKED={invalid_source_blocked}")
    print(f"MISSING_PROVENANCE_BLOCKED={missing_provenance_blocked}")
    print(f"DUPLICATE_BLOCKED={duplicate_blocked}")
    print("BLENDING=False")
    print(
        f"PRODUCTION_CONSUMPTION_ENABLED="
        f"{production_consumption_enabled}"
    )
    print(
        f"PRODUCTION_CANDLES_CONSUMED="
        f"{production_candles_consumed}"
    )
    print(f"PRODUCTION_DB_TOUCHED={production_db_touched}")
    print(f"DB_WRITES={db_writes}")
    print(f"PRODUCTION_PATH_MUTATION={production_path_mutation}")
    print("ORDER_INTENTS_CREATED=0")
    print("TRADING_ENABLED=False")
    print("EXECUTION=DISABLED")
    print(f"VALIDATION={'PASS' if validation else 'FAIL'}")
    print(f"STATUS={status}")


def fail_closed(
    fabric_input=False,
    canonical_bars=0,
    legacy_blocked=0,
    pre_launch_blocked=0,
    invalid_source_blocked=0,
    missing_provenance_blocked=0,
    duplicate_blocked=0,
    production_db_touched=False,
    production_path_mutation=False,
):
    emit(
        release_mode="CONTROLLED_PRODUCTION",
        fabric_input=fabric_input,
        selected_provider="NONE",
        failover_triggered=False,
        canonical_bars=canonical_bars,
        valid_bars=0,
        provenance_valid=False,
        legacy_blocked=legacy_blocked,
        pre_launch_blocked=pre_launch_blocked,
        invalid_source_blocked=invalid_source_blocked,
        missing_provenance_blocked=missing_provenance_blocked,
        duplicate_blocked=duplicate_blocked,
        production_consumption_enabled=False,
        production_candles_consumed=0,
        production_db_touched=production_db_touched,
        db_writes=0,
        production_path_mutation=production_path_mutation,
        validation=False,
        status="CONTROLLED_RELEASE_FAIL_CLOSED",
    )


def main():

    # ---------------------------------------------------------
    # HARD SAFETY: required Fabric must exist
    # ---------------------------------------------------------

    if not FABRIC_DB.exists():
        fail_closed()
        return

    # ---------------------------------------------------------
    # HARD SAFETY: production DB is OBSERVED only
    # ---------------------------------------------------------

    production_before = (
        PRODUCTION_DB.stat().st_mtime_ns
        if PRODUCTION_DB.exists()
        else None
    )

    # ---------------------------------------------------------
    # Fabric READ ONLY
    # ---------------------------------------------------------

    try:
        con = sqlite3.connect(
            f"file:{FABRIC_DB.as_posix()}?mode=ro",
            uri=True,
        )
        con.row_factory = sqlite3.Row
    except Exception:
        fail_closed()
        return

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

            # -------------------------------------------------
            # Timestamp
            # -------------------------------------------------

            try:
                timestamp = int(row["timestamp"])
            except Exception:
                invalid_source_blocked += 1
                continue

            if timestamp < LAUNCH_TS:
                pre_launch_blocked += 1
                continue

            # -------------------------------------------------
            # Source
            # -------------------------------------------------

            source_type = str(row["source_type"] or "")
            source_id = str(row["source_id"] or "")

            # Existing DEX data is NON-PRODUCTION for this
            # CEX production release path.
            if source_type == "DEX_ONCHAIN":
                legacy_blocked += 1
                continue

            if not (
                source_type == "CEX_PUBLIC_API"
                and source_id.startswith("KUCOIN_SPOT:")
            ):
                invalid_source_blocked += 1
                continue

            # -------------------------------------------------
            # Timeframe
            # -------------------------------------------------

            if str(row["timeframe"]) != TIMEFRAME:
                invalid_source_blocked += 1
                continue

            # -------------------------------------------------
            # Provenance
            # -------------------------------------------------

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

            provenance_ok = (
                bool(
                    str(
                        row["retrieved_at"] or ""
                    ).strip()
                )
                and source_timestamp == timestamp
                and observation_count == 1
                and signatures is not None
                and len(signatures) == 1
                and bool(
                    str(signatures[0]).strip()
                )
                and slots is not None
                and len(slots) == 1
                and int(slots[0]) == timestamp
                and bool(
                    str(
                        row["canonical_payload"] or ""
                    ).strip()
                )
            )

            if not provenance_ok:
                missing_provenance_blocked += 1
                continue

            # -------------------------------------------------
            # CEX must not contain DEX metadata
            # -------------------------------------------------

            if not is_nullish(row["pool"]):
                invalid_source_blocked += 1
                continue

            if not is_nullish(
                row["raydium_instruction"]
            ):
                invalid_source_blocked += 1
                continue

            # -------------------------------------------------
            # OHLCV
            # -------------------------------------------------

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

            # -------------------------------------------------
            # One candle = one source
            # -------------------------------------------------

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

    except Exception:
        con.close()

        production_after = (
            PRODUCTION_DB.stat().st_mtime_ns
            if PRODUCTION_DB.exists()
            else None
        )

        touched = production_before != production_after

        fail_closed(
            fabric_input=True,
            canonical_bars=canonical_bars,
            legacy_blocked=legacy_blocked,
            pre_launch_blocked=pre_launch_blocked,
            invalid_source_blocked=invalid_source_blocked,
            missing_provenance_blocked=missing_provenance_blocked,
            duplicate_blocked=duplicate_blocked,
            production_db_touched=touched,
            production_path_mutation=False,
        )
        return

    finally:
        try:
            con.close()
        except Exception:
            pass

    # ---------------------------------------------------------
    # Contract gate
    # ---------------------------------------------------------

    provenance_valid = (
        len(valid) > 0
        and missing_provenance_blocked == 0
    )

    contract_valid = (
        canonical_bars > 0
        and len(valid) > 0
        and provenance_valid
        and invalid_source_blocked == 0
        and duplicate_blocked == 0
        and production_before
        is not None
    )

    # ---------------------------------------------------------
    # IMPORTANT:
    # Production consumption is ONLY an in-memory controlled
    # handoff. No production DB write. No trading mutation.
    # ---------------------------------------------------------

    production_consumed = []

    if contract_valid:

        production_consumed = list(valid)

        production_consumption_enabled = True
        production_candles_consumed = len(
            production_consumed
        )

    else:

        production_consumed = []

        production_consumption_enabled = False
        production_candles_consumed = 0

    # ---------------------------------------------------------
    # Production DB integrity check
    # ---------------------------------------------------------

    production_after = (
        PRODUCTION_DB.stat().st_mtime_ns
        if PRODUCTION_DB.exists()
        else None
    )

    production_db_touched = (
        production_before != production_after
    )

    # ---------------------------------------------------------
    # Production path mutation:
    # this controlled release performs no filesystem mutation
    # on production path.
    # ---------------------------------------------------------

    production_path_mutation = False

    # ---------------------------------------------------------
    # Final fail-closed enforcement
    # ---------------------------------------------------------

    if production_db_touched:
        production_consumption_enabled = False
        production_candles_consumed = 0
        production_consumed = []

    validation = (
        contract_valid
        and production_consumption_enabled
        and production_candles_consumed == len(valid)
        and not production_db_touched
        and not production_path_mutation
    )

    if validation:
        status = "CONTROLLED_PRODUCTION_RELEASE_PASS"
        selected_provider = PRIMARY_PROVIDER
        failover_triggered = False
    else:
        status = "CONTROLLED_RELEASE_FAIL_CLOSED"
        selected_provider = "NONE"
        failover_triggered = False
        production_consumption_enabled = False
        production_candles_consumed = 0
        production_consumed = []

    # ---------------------------------------------------------
    # Compact Runtime Evidence
    # ---------------------------------------------------------

    emit(
        release_mode="CONTROLLED_PRODUCTION",
        fabric_input=True,
        selected_provider=selected_provider,
        failover_triggered=failover_triggered,
        canonical_bars=canonical_bars,
        valid_bars=len(valid),
        provenance_valid=provenance_valid,
        legacy_blocked=legacy_blocked,
        pre_launch_blocked=pre_launch_blocked,
        invalid_source_blocked=invalid_source_blocked,
        missing_provenance_blocked=missing_provenance_blocked,
        duplicate_blocked=duplicate_blocked,
        production_consumption_enabled=(
            production_consumption_enabled
        ),
        production_candles_consumed=(
            production_candles_consumed
        ),
        production_db_touched=production_db_touched,
        db_writes=0,
        production_path_mutation=(
            production_path_mutation
        ),
        validation=validation,
        status=status,
    )


if __name__ == "__main__":
    main()