from pathlib import Path
import sqlite3
import importlib.util
import requests
import math
import time
from datetime import datetime, timezone


# ============================================================
# ARUNDA MARKET ARM
# CONTIGUOUS HISTORY ACCUMULATION v0.8
#
# PURPOSE:
#   Build 50 REAL CLOSED contiguous candles BACKWARD
#   from the latest CLOSED candle.
#
# OPEN CURRENT CANDLE:
#   NEVER COUNTED
#   NEVER NORMALIZED
#   NEVER INSERTED
#
# NO:
#   synthetic
#   interpolation
#   fill
#   backfill
#   padding
#   blending
#   gap crossing
#
# PRODUCTION DB:
#   NEVER OPENED
#
# SIGNAL / FUSION / SCORE / DECISION:
#   OFF
# ============================================================


ROOT = Path(__file__).resolve().parent


FABRIC_DB = (
    ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)


STORE_MODULE = (
    ROOT
    / "local_canonical_store_v0.1.py"
)


KUCOIN_MODULE = (
    ROOT
    / "public_market_data_kucoin.py"
)


KUCOIN_URL = (
    "https://api.kucoin.com/api/v1/market/candles"
)


TIMEFRAME = "1h"
TIMEFRAME_SECONDS = 3600

TARGET_RUN = 50

# How much historical time to request around the target.
# This is only a real-data retrieval window.
HISTORY_BUFFER_CANDLES = 8


LAUNCH_TS = int(
    datetime(
        2026,
        8,
        31,
        tzinfo=timezone.utc
    ).timestamp()
)


ASSETS = [
    "BTC",
    "ETH",
    "SOL",
    "XRP",
    "ADA",
    "DOGE",
    "SHIB",
    "LINK",
    "AVAX",
    "DOT",
    "LTC",
    "UNI",
    "AAVE",
    "SUI",
    "NEAR",
]


TIMEOUT = 20


# ============================================================
# MODULE LOADER
# ============================================================

def load_module(path, name):

    spec = importlib.util.spec_from_file_location(
        name,
        path
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED:{path}"
        )

    module = importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module


# ============================================================
# TIME
# ============================================================

def now_ts():

    return int(
        time.time()
    )


def utc_iso(timestamp):

    return datetime.fromtimestamp(
        int(timestamp),
        timezone.utc
    ).isoformat()


# ============================================================
# NUMERIC
# ============================================================

def finite(value):

    try:

        return math.isfinite(
            float(value)
        )

    except Exception:

        return False


# ============================================================
# CLOSED CANDLE
#
# A candle is CLOSED only when:
#
# timestamp + 3600 <= current_time
#
# Therefore the currently forming candle is ALWAYS excluded.
# ============================================================

def is_closed_candle(
    timestamp,
    current_time
):

    return (
        int(timestamp)
        + TIMEFRAME_SECONDS
        <= int(current_time)
    )


# ============================================================
# FABRIC READ
# ============================================================

def load_rows(conn, asset):

    symbol = f"{asset}/USDT"

    source_id = (
        f"KUCOIN_SPOT:{asset}-USDT"
    )

    return conn.execute(
        """
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
            price_unit,
            canonical_payload
        FROM canonical_ohlcv
        WHERE UPPER(asset)=?
          AND symbol=?
          AND source_id=?
          AND source_type='CEX_PUBLIC_API'
          AND timeframe=?
          AND timestamp>=?
        ORDER BY timestamp ASC
        """,
        (
            asset.upper(),
            symbol,
            source_id,
            TIMEFRAME,
            LAUNCH_TS,
        ),
    ).fetchall()


# ============================================================
# CURRENT CLOSED CONTIGUOUS RUN
#
# CRITICAL:
# Current OPEN candle is filtered OUT before timestamps
# are considered.
# ============================================================

def current_contiguous_run(
    rows,
    current_time
):

    if not rows:

        return 0, None, None


    timestamps = [
        int(row[2])
        for row in rows
        if is_closed_candle(
            int(row[2]),
            current_time
        )
    ]


    if not timestamps:

        return 0, None, None


    if len(timestamps) != len(
        set(timestamps)
    ):

        raise RuntimeError(
            "DUPLICATE_TIMESTAMP_IN_MARKET"
        )


    run = 1


    for index in range(
        len(timestamps) - 1,
        0,
        -1
    ):

        delta = (
            timestamps[index]
            - timestamps[index - 1]
        )


        if delta == TIMEFRAME_SECONDS:

            run += 1

        else:

            break


    return (
        run,
        timestamps[-run],
        timestamps[-1]
    )


# ============================================================
# KUCOIN HISTORICAL FETCH
#
# IMPORTANT:
# We retain RAW KuCoin rows.
#
# Canonicalization is delegated to the EXISTING:
# public_market_data_kucoin.normalize()
# public_market_data_kucoin.validate_candle()
#
# Current OPEN candle is rejected HERE as well.
# ============================================================

def fetch_kucoin_history(
    asset,
    start_ts,
    end_ts,
    current_time
):

    symbol = f"{asset}-USDT"


    response = requests.get(
        KUCOIN_URL,
        params={
            "symbol": symbol,
            "type": "1hour",
            "startAt": int(start_ts),
            "endAt": int(end_ts),
        },
        timeout=TIMEOUT,
    )


    response.raise_for_status()


    payload = response.json()


    if not isinstance(
        payload,
        dict
    ):

        raise RuntimeError(
            f"KUCOIN_RESPONSE_INVALID:{asset}"
        )


    if payload.get("code") != "200000":

        raise RuntimeError(
            f"KUCOIN_API_ERROR:{asset}:"
            f"{payload.get('msg')}"
        )


    data = payload.get("data")


    if not isinstance(
        data,
        list
    ):

        raise RuntimeError(
            f"KUCOIN_DATA_INVALID:{asset}"
        )


    result = []


    for raw in data:

        if not isinstance(
            raw,
            list
        ):

            continue


        if len(raw) < 6:

            continue


        try:

            timestamp = int(
                float(raw[0])
            )

            open_price = float(raw[1])
            close_price = float(raw[2])
            high_price = float(raw[3])
            low_price = float(raw[4])
            volume = float(raw[5])

        except Exception:

            continue


        # ----------------------------------------------------
        # HARD OPEN-CANDLE EXCLUSION
        #
        # This is deliberately BEFORE normalization/storage.
        # ----------------------------------------------------

        if not is_closed_candle(
            timestamp,
            current_time
        ):

            continue


        if timestamp < LAUNCH_TS:

            continue


        if timestamp < start_ts:

            continue


        if timestamp > end_ts:

            continue


        if (
            timestamp
            % TIMEFRAME_SECONDS
            != 0
        ):

            continue


        if not all(
            finite(x)
            for x in [
                open_price,
                close_price,
                high_price,
                low_price,
                volume,
            ]
        ):

            continue


        if open_price <= 0:
            continue

        if close_price <= 0:
            continue

        if high_price <= 0:
            continue

        if low_price <= 0:
            continue

        if volume < 0:
            continue


        if high_price < max(
            open_price,
            close_price
        ):

            continue


        if low_price > min(
            open_price,
            close_price
        ):

            continue


        result.append(raw)


    # API-response duplicate protection.
    unique = {}


    for raw in result:

        timestamp = int(
            float(raw[0])
        )


        if timestamp not in unique:

            unique[timestamp] = raw


    return [
        unique[timestamp]
        for timestamp in sorted(unique)
    ]


# ============================================================
# BACKWARD CONTIGUOUS SEQUENCE
#
# Target:
#
#       latest CLOSED
#            ↓
#          -1h
#          -1h
#          -1h
#           ...
#          50 candles
#
# GAP:
#   STOP.
#
# We NEVER jump over a missing timestamp.
# ============================================================

def build_backward_sequence(
    existing_timestamps,
    candidates,
    latest_closed,
    target_run,
    current_time
):

    by_timestamp = {}


    # Existing Fabric observations.
    for timestamp in existing_timestamps:

        ts = int(timestamp)

        if not is_closed_candle(
            ts,
            current_time
        ):

            continue

        if ts < LAUNCH_TS:

            continue

        by_timestamp[ts] = None


    # New real KuCoin observations.
    for raw in candidates:

        timestamp = int(
            float(raw[0])
        )


        if not is_closed_candle(
            timestamp,
            current_time
        ):

            continue


        if timestamp < LAUNCH_TS:

            continue


        by_timestamp[timestamp] = raw


    # --------------------------------------------------------
    # Walk BACKWARD from latest CLOSED.
    # --------------------------------------------------------

    selected = []

    missing = []

    timestamp = int(latest_closed)


    while len(selected) < target_run:

        if timestamp not in by_timestamp:

            missing.append(timestamp)

            break


        selected.append(
            (
                timestamp,
                by_timestamp[timestamp]
            )
        )


        timestamp -= TIMEFRAME_SECONDS


    return selected, missing


# ============================================================
# HARD IDENTITY
# ============================================================

def validate_identity(
    normalized,
    asset
):

    expected_asset = (
        asset.upper()
    )

    expected_symbol = (
        f"{asset}/USDT"
    )

    expected_source = (
        f"KUCOIN_SPOT:{asset}-USDT"
    )


    if normalized.get(
        "asset",
        ""
    ).upper() != expected_asset:

        raise RuntimeError(
            f"IDENTITY_ASSET_MISMATCH:{asset}"
        )


    if normalized.get(
        "symbol"
    ) != expected_symbol:

        raise RuntimeError(
            f"IDENTITY_SYMBOL_MISMATCH:{asset}"
        )


    if normalized.get(
        "source_id"
    ) != expected_source:

        raise RuntimeError(
            f"IDENTITY_SOURCE_MISMATCH:{asset}"
        )


    if normalized.get(
        "source_type"
    ) != "CEX_PUBLIC_API":

        raise RuntimeError(
            f"SOURCE_TYPE_MISMATCH:{asset}"
        )


    if normalized.get(
        "timeframe"
    ) != TIMEFRAME:

        raise RuntimeError(
            f"TIMEFRAME_MISMATCH:{asset}"
        )


    timestamp = int(
        normalized["timestamp"]
    )


    if timestamp < LAUNCH_TS:

        raise RuntimeError(
            f"LAUNCH_BOUNDARY_VIOLATION:{asset}"
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 100)

    print(
        "ARUNDA MARKET ARM CONTIGUOUS "
        "HISTORY ACCUMULATION v0.8"
    )

    print("=" * 100)

    print(
        "MODE=BACKWARD_HISTORICAL_ACCUMULATION"
    )

    print(
        "SOURCE=KUCOIN"
    )

    print(
        "TIMEFRAME=1h"
    )

    print(
        "TARGET_RUN=50"
    )

    print(
        "DIRECTION=BACKWARD"
    )

    print(
        "KUCOIN_CANONICAL_ADAPTER_BINDING=True"
    )

    print(
        "CANONICAL_STORE_STORAGE_ONLY=True"
    )

    print(
        "REAL_DATA_ONLY=True"
    )

    print(
        "SYNTHETIC=False"
    )

    print(
        "INTERPOLATION=False"
    )

    print(
        "FILL=False"
    )

    print(
        "BACKFILL=False"
    )

    print(
        "PADDING=False"
    )

    print(
        "BLENDING=False"
    )

    print(
        "OPEN_LAST_CANDLE_EXCLUDED=True"
    )

    print(
        "CLOSED_ONLY=True"
    )

    print(
        "START_FROM_LATEST_CLOSED=True"
    )

    print(
        "GAP_CROSSING=False"
    )

    print(
        "PRODUCTION_DB_TOUCHED=False"
    )

    print(
        "SIGNAL_CHAIN_EXECUTED=False"
    )

    print(
        "FUSION_EXECUTED=False"
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


    # ========================================================
    # FILE CHECKS
    # ========================================================

    if not FABRIC_DB.exists():

        raise RuntimeError(
            "FABRIC_DB_NOT_FOUND"
        )


    if not STORE_MODULE.exists():

        raise RuntimeError(
            "STORE_MODULE_NOT_FOUND"
        )


    if not KUCOIN_MODULE.exists():

        raise RuntimeError(
            "KUCOIN_ADAPTER_NOT_FOUND"
        )


    # ========================================================
    # LOAD EXISTING APPROVED MODULES
    # ========================================================

    store = load_module(
        STORE_MODULE,
        "canonical_store_v0_8"
    )


    kucoin = load_module(
        KUCOIN_MODULE,
        "public_market_data_kucoin_v0_8"
    )


    # ========================================================
    # API CONTRACT CHECK
    # ========================================================

    if not hasattr(
        store,
        "insert_candle"
    ):

        raise RuntimeError(
            "STORE_API_INSERT_CANDLE_MISSING"
        )


    if not hasattr(
        kucoin,
        "normalize"
    ):

        raise RuntimeError(
            "KUCOIN_API_NORMALIZE_MISSING"
        )


    if not hasattr(
        kucoin,
        "validate_candle"
    ):

        raise RuntimeError(
            "KUCOIN_API_VALIDATE_CANDLE_MISSING"
        )


    print(
        "KUCOIN_BINDING=PASS"
    )


    # ========================================================
    # FABRIC ONLY
    # ========================================================

    conn = sqlite3.connect(
        str(FABRIC_DB)
    )


    summary = []


    try:

        for asset in ASSETS:

            current_time = now_ts()


            # ------------------------------------------------
            # READ CURRENT FABRIC STATE
            # ------------------------------------------------

            rows = load_rows(
                conn,
                asset
            )


            existing_timestamps = {
                int(row[2])
                for row in rows
                if is_closed_candle(
                    int(row[2]),
                    current_time
                )
            }


            run, run_start, latest_closed = (
                current_contiguous_run(
                    rows,
                    current_time
                )
            )


            # ------------------------------------------------
            # TARGET ALREADY REACHED
            # ------------------------------------------------

            if run >= TARGET_RUN:

                print(
                    f"{asset}: "
                    f"RUN={run} "
                    f"TARGET_REACHED=True"
                )


                summary.append(
                    (
                        asset,
                        run,
                        0
                    )
                )


                continue


            if latest_closed is None:

                raise RuntimeError(
                    f"NO_CLOSED_CONTEXT:{asset}"
                )


            needed = (
                TARGET_RUN - run
            )


            # ------------------------------------------------
            # BACKWARD REQUEST
            #
            # Example:
            #
            # latest = 22:00
            # run    = 24
            # needed = 26
            #
            # request:
            # 22:00 backward ~34 candles
            #
            # Current 23:00 OPEN candle is NOT requested
            # as part of the target sequence.
            # ------------------------------------------------

            request_end = (
                latest_closed
                - TIMEFRAME_SECONDS
            )


            request_start = (
                latest_closed
                - (
                    needed
                    + HISTORY_BUFFER_CANDLES
                )
                * TIMEFRAME_SECONDS
            )


            if request_start < LAUNCH_TS:

                request_start = LAUNCH_TS


            print()

            print(
                f"{asset}: "
                f"RUN={run} "
                f"NEEDED={needed} "
                f"LATEST_CLOSED={latest_closed} "
                f"LATEST_CLOSED_UTC={utc_iso(latest_closed)}"
            )

            print(
                f"{asset}: "
                f"BACKWARD_REQUEST="
                f"{utc_iso(request_start)}"
                f" -> "
                f"{utc_iso(request_end)}"
            )


            # ------------------------------------------------
            # REAL KUCOIN HISTORY
            # ------------------------------------------------

            candidates = fetch_kucoin_history(
                asset,
                request_start,
                request_end,
                current_time
            )


            # ------------------------------------------------
            # BACKWARD TARGET
            # ------------------------------------------------

            selected, missing = (
                build_backward_sequence(
                    existing_timestamps,
                    candidates,
                    latest_closed,
                    TARGET_RUN,
                    current_time
                )
            )


            # ------------------------------------------------
            # FAIL CLOSED ON GAP
            # ------------------------------------------------

            if len(selected) < TARGET_RUN:

                if missing:

                    missing_ts = missing[0]

                    print(
                        f"{asset}: "
                        f"GAP_OR_UNAVAILABLE="
                        f"{missing_ts} "
                        f"{utc_iso(missing_ts)}"
                    )

                else:

                    print(
                        f"{asset}: "
                        f"INSUFFICIENT_CLOSED_HISTORY"
                    )


                summary.append(
                    (
                        asset,
                        run,
                        0
                    )
                )


                continue


            # ------------------------------------------------
            # HARD VERIFY BACKWARD CONTINUITY
            # ------------------------------------------------

            expected = latest_closed


            for timestamp, raw in selected:

                if timestamp != expected:

                    raise RuntimeError(
                        f"BACKWARD_CONTINUITY_FAILURE:"
                        f"{asset}:"
                        f"expected={expected}:"
                        f"actual={timestamp}"
                    )


                if not is_closed_candle(
                    timestamp,
                    current_time
                ):

                    raise RuntimeError(
                        f"OPEN_OR_FUTURE_CANDLE:"
                        f"{asset}:"
                        f"timestamp={timestamp}"
                    )


                if timestamp < LAUNCH_TS:

                    raise RuntimeError(
                        f"LAUNCH_BOUNDARY_VIOLATION:"
                        f"{asset}:"
                        f"timestamp={timestamp}"
                    )


                expected -= TIMEFRAME_SECONDS


            # ------------------------------------------------
            # ONLY NEW CANDLES NEED INSERTION
            #
            # Existing Fabric candles are NOT rewritten.
            # ------------------------------------------------

            new_sequence = [
                (timestamp, raw)
                for timestamp, raw in selected
                if raw is not None
            ]


            inserted = 0


            # ------------------------------------------------
            # CANONICALIZATION
            #
            # Existing KUCOIN adapter owns:
            #   normalize()
            #   validate_candle()
            #
            # Store owns only:
            #   insert_candle()
            # ------------------------------------------------

            for timestamp, raw in reversed(
                new_sequence
            ):

                # Absolute safety:
                # never canonicalize an OPEN candle.

                if not is_closed_candle(
                    timestamp,
                    now_ts()
                ):

                    raise RuntimeError(
                        f"OPEN_CANDLE_REJECTED:"
                        f"{asset}:"
                        f"timestamp={timestamp}"
                    )


                normalized = kucoin.normalize(
                    asset,
                    f"{asset}-USDT",
                    raw,
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )


                validation_result = (
                    kucoin.validate_candle(
                        normalized
                    )
                )


                if validation_result is False:

                    raise RuntimeError(
                        f"KUCOIN_CANONICAL_VALIDATION_FAILED:"
                        f"{asset}:"
                        f"timestamp={timestamp}"
                    )


                validate_identity(
                    normalized,
                    asset
                )


                # Final timestamp consistency.
                if int(
                    normalized["timestamp"]
                ) != timestamp:

                    raise RuntimeError(
                        f"CANONICAL_TIMESTAMP_MISMATCH:"
                        f"{asset}:"
                        f"expected={timestamp}:"
                        f"actual={normalized['timestamp']}"
                    )


                ok = store.insert_candle(
                    conn,
                    normalized
                )


                if ok:

                    inserted += 1


                    print(
                        f"  INSERTED={asset} "
                        f"TIMESTAMP={timestamp} "
                        f"UTC={utc_iso(timestamp)}"
                    )


            # ------------------------------------------------
            # POST-INSERT VERIFICATION
            # ------------------------------------------------

            verify_time = now_ts()


            verify_rows = load_rows(
                conn,
                asset
            )


            verify_run, verify_start, verify_latest = (
                current_contiguous_run(
                    verify_rows,
                    verify_time
                )
            )


            print(
                f"  RESULT={asset} "
                f"RUN={verify_run} "
                f"INSERTED={inserted} "
                f"LATEST_CLOSED={verify_latest}"
            )


            if verify_run < run:

                raise RuntimeError(
                    f"RUN_REGRESSION:{asset}"
                )


            summary.append(
                (
                    asset,
                    verify_run,
                    inserted
                )
            )


        # ====================================================
        # FINAL VALIDATION
        # ====================================================

        print()

        print("=" * 100)

        print(
            "FINAL VALIDATION"
        )

        print("=" * 100)


        all_ready = True


        for asset, run, inserted in summary:

            if run >= TARGET_RUN:

                status = "READY"

            else:

                status = "PARTIAL"

                all_ready = False


            print(
                f"{asset}: "
                f"RUN={run} "
                f"INSERTED={inserted} "
                f"STATUS={status}"
            )


        print("=" * 100)


        if all_ready:

            print(
                "MARKET_ARM_READY=True"
            )

            print(
                "CONTIGUOUS_50_READY=15/15"
            )

            print(
                "STATUS=READY_FOR_PRODUCTION_FUSION_BINDING"
            )

        else:

            print(
                "MARKET_ARM_READY=False"
            )

            print(
                "STATUS=BACKWARD_ACCUMULATION_CONTINUES"
            )


        print(
            "PRODUCTION_DB_TOUCHED=False"
        )

        print(
            "SIGNAL_CHAIN_EXECUTED=False"
        )

        print(
            "FUSION_EXECUTED=False"
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

        print(
            "SYNTHETIC=False"
        )

        print(
            "INTERPOLATION=False"
        )

        print(
            "FILL=False"
        )

        print(
            "BACKFILL=False"
        )

        print(
            "PADDING=False"
        )

        print(
            "BLENDING=False"
        )

        print(
            "OPEN_LAST_CANDLE_EXCLUDED=True"
        )

        print(
            "FAIL_CLOSED=True"
        )


    finally:

        conn.close()


if __name__ == "__main__":

    main()