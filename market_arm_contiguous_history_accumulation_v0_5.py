
from pathlib import Path
import sqlite3
import importlib.util
import requests
import math
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent

FABRIC_DB = ROOT / "public_market_data_fabric" / "canonical_store_v0.1.sqlite"
STORE_MODULE = ROOT / "local_canonical_store_v0.1.py"

KUCOIN_URL = "https://api.kucoin.com/api/v1/market/candles"

TIMEFRAME = "1h"
TIMEFRAME_SECONDS = 3600
TARGET_RUN = 50

LAUNCH_TS = int(
    datetime(
        2026, 8, 31,
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


def utc_iso(ts):
    return datetime.fromtimestamp(
        int(ts),
        timezone.utc
    ).isoformat()


def finite(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def load_rows(conn, asset):

    symbol = f"{asset}/USDT"
    source_id = f"KUCOIN_SPOT:{asset}-USDT"

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


def current_contiguous_run(rows):

    if not rows:
        return 0, None, None

    timestamps = [
        int(row[2])
        for row in rows
    ]

    if len(timestamps) != len(set(timestamps)):
        raise RuntimeError(
            "DUPLICATE_TIMESTAMP_IN_MARKET"
        )

    run = 1

    for i in range(
        len(timestamps) - 1,
        0,
        -1
    ):

        delta = (
            timestamps[i]
            - timestamps[i - 1]
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


def fetch_kucoin_history(
    asset,
    start_ts,
    end_ts
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

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"KUCOIN_RESPONSE_INVALID:{asset}"
        )

    if payload.get("code") != "200000":
        raise RuntimeError(
            f"KUCOIN_API_ERROR:{asset}:"
            f"{payload.get('msg')}"
        )

    data = payload.get("data")

    if not isinstance(data, list):
        raise RuntimeError(
            f"KUCOIN_DATA_INVALID:{asset}"
        )

    result = []

    for raw in data:

        if not isinstance(raw, list):
            continue

        if len(raw) < 6:
            continue

        try:
            timestamp = int(float(raw[0]))
            open_price = float(raw[1])
            close_price = float(raw[2])
            high_price = float(raw[3])
            low_price = float(raw[4])
            volume = float(raw[5])
        except Exception:
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

        if timestamp < LAUNCH_TS:
            continue

        if timestamp % TIMEFRAME_SECONDS != 0:
            continue

        if timestamp < start_ts:
            continue

        if timestamp > end_ts:
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

    result.sort(
        key=lambda x: int(float(x[0]))
    )

    unique = {}

    for raw in result:

        timestamp = int(float(raw[0]))

        if timestamp not in unique:
            unique[timestamp] = raw

    return [
        unique[t]
        for t in sorted(unique)
    ]


def build_contiguous_sequence(
    candidates,
    expected,
    needed
):

    by_timestamp = {}

    for raw in candidates:

        timestamp = int(
            float(raw[0])
        )

        by_timestamp[timestamp] = raw

    sequence = []

    current = expected

    while (
        current in by_timestamp
        and len(sequence) < needed
    ):

        sequence.append(
            by_timestamp[current]
        )

        current += TIMEFRAME_SECONDS

    return sequence


def main():

    print("=" * 100)
    print(
        "ARUNDA MARKET ARM CONTIGUOUS "
        "HISTORY ACCUMULATION v0.5"
    )
    print("=" * 100)

    print("MODE=FORWARD_HISTORICAL_CATCH_UP")
    print("SOURCE=KUCOIN")
    print("TIMEFRAME=1h")
    print("TARGET_RUN=50")

    print("REAL_DATA_ONLY=True")
    print("SYNTHETIC=False")
    print("INTERPOLATION=False")
    print("FILL=False")
    print("BACKFILL=False")
    print("PADDING=False")
    print("BLENDING=False")

    print("EXECUTION=OFF")
    print("ORDER_INTENTS=0")
    print("=" * 100)

    if not FABRIC_DB.exists():
        raise RuntimeError(
            "FABRIC_DB_NOT_FOUND"
        )

    store = load_module(
        STORE_MODULE,
        "canonical_store_v0_5"
    )

    conn = sqlite3.connect(
        str(FABRIC_DB)
    )

    try:

        summary = []

        for asset in ASSETS:

            rows = load_rows(
                conn,
                asset
            )

            run, run_start, latest = (
                current_contiguous_run(rows)
            )

            if run >= TARGET_RUN:

                print(
                    f"{asset}: "
                    f"RUN={run} "
                    f"TARGET_REACHED=True"
                )

                summary.append(
                    (asset, run, 0)
                )

                continue

            needed = TARGET_RUN - run

            expected = (
                latest
                + TIMEFRAME_SECONDS
            )

            print()
            print(
                f"{asset}: "
                f"RUN={run} "
                f"NEEDED={needed} "
                f"START={expected} "
                f"START_UTC={utc_iso(expected)}"
            )

            # --------------------------------------------------
            # IMPORTANT:
            # Do NOT calculate candle closure from local clock.
            #
            # Request a bounded historical window extending
            # beyond the required target. KuCoin returns the
            # actual historical observations.
            # --------------------------------------------------

            request_end = (
                expected
                + (
                    needed + 3
                ) * TIMEFRAME_SECONDS
            )

            candidates = fetch_kucoin_history(
                asset,
                expected,
                request_end
            )

            if not candidates:

                raise RuntimeError(
                    f"FORWARD_HISTORY_NOT_AVAILABLE:"
                    f"{asset}:"
                    f"expected={expected}"
                )

            # --------------------------------------------------
            # API-CLOSURE RULE
            #
            # The newest returned candle is treated as the
            # potentially active/current candle.
            #
            # Therefore it is NEVER inserted automatically.
            #
            # Historical candles strictly before that newest
            # observation are eligible.
            # --------------------------------------------------

            newest_api_timestamp = max(
                int(float(raw[0]))
                for raw in candidates
            )

            closed_candidates = [
                raw
                for raw in candidates
                if int(float(raw[0]))
                < newest_api_timestamp
            ]

            if not closed_candidates:

                raise RuntimeError(
                    f"NO_CLOSED_HISTORICAL_CANDLE:"
                    f"{asset}:"
                    f"expected={expected}"
                )

            sequence = build_contiguous_sequence(
                closed_candidates,
                expected,
                needed
            )

            if not sequence:

                raise RuntimeError(
                    f"CONTIGUOUS_FORWARD_SEQUENCE_NOT_FOUND:"
                    f"{asset}:"
                    f"expected={expected}"
                )

            # --------------------------------------------------
            # HARD CONTIGUITY CHECK
            # --------------------------------------------------

            previous = expected

            for raw in sequence:

                timestamp = int(
                    float(raw[0])
                )

                if timestamp != previous:

                    raise RuntimeError(
                        f"CONTINUITY_FAILURE:"
                        f"{asset}:"
                        f"expected={previous}:"
                        f"actual={timestamp}"
                    )

                previous += TIMEFRAME_SECONDS

            inserted = 0

            for raw in sequence:

                timestamp = int(
                    float(raw[0])
                )

                normalized = store.normalize(
                    asset,
                    f"{asset}-USDT",
                    raw,
                    datetime.now(
                        timezone.utc
                    ).isoformat()
                )

                if not store.validate_candle(
                    normalized
                ):
                    raise RuntimeError(
                        f"CANONICAL_VALIDATION_FAILED:"
                        f"{asset}:"
                        f"timestamp={timestamp}"
                    )

                # --------------------------------------------------
                # HARD IDENTITY
                # --------------------------------------------------

                if (
                    normalized["asset"].upper()
                    != asset.upper()
                ):
                    raise RuntimeError(
                        f"IDENTITY_ASSET_MISMATCH:"
                        f"{asset}"
                    )

                if normalized["symbol"] != (
                    f"{asset}/USDT"
                ):
                    raise RuntimeError(
                        f"IDENTITY_SYMBOL_MISMATCH:"
                        f"{asset}"
                    )

                if normalized["source_id"] != (
                    f"KUCOIN_SPOT:{asset}-USDT"
                ):
                    raise RuntimeError(
                        f"IDENTITY_SOURCE_MISMATCH:"
                        f"{asset}"
                    )

                if normalized["source_type"] != (
                    "CEX_PUBLIC_API"
                ):
                    raise RuntimeError(
                        f"SOURCE_TYPE_MISMATCH:"
                        f"{asset}"
                    )

                if normalized["timeframe"] != (
                    TIMEFRAME
                ):
                    raise RuntimeError(
                        f"TIMEFRAME_MISMATCH:"
                        f"{asset}"
                    )

                if timestamp < LAUNCH_TS:
                    raise RuntimeError(
                        f"LAUNCH_BOUNDARY_VIOLATION:"
                        f"{asset}"
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

            # --------------------------------------------------
            # POST-INSERT VERIFICATION
            # --------------------------------------------------

            verify_rows = load_rows(
                conn,
                asset
            )

            verify_run, verify_start, verify_latest = (
                current_contiguous_run(
                    verify_rows
                )
            )

            print(
                f"  RESULT={asset} "
                f"RUN={verify_run} "
                f"INSERTED={inserted} "
                f"LATEST={verify_latest}"
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

        print()
        print("=" * 100)
        print("FINAL VALIDATION")
        print("=" * 100)

        all_ready = True

        for asset, run, inserted in summary:

            status = (
                "READY"
                if run >= TARGET_RUN
                else "PARTIAL"
            )

            if run < TARGET_RUN:
                all_ready = False

            print(
                f"{asset}: "
                f"RUN={run} "
                f"INSERTED={inserted} "
                f"STATUS={status}"
            )

        print("=" * 100)

        print(
            f"MARKET_ARM_READY="
            f"{'True' if all_ready else 'False'}"
        )

        if all_ready:

            print(
                "CONTIGUOUS_50_READY=15/15"
            )

            print(
                "STATUS=READY_FOR_MARKET_SCORE"
            )

        else:

            print(
                "STATUS=FORWARD_ACCUMULATION_CONTINUES"
            )

        print("PRODUCTION_DB_TOUCHED=False")
        print("SIGNAL_CHAIN_EXECUTED=False")
        print("FUSION_EXECUTED=False")
        print("SCORE=OFF")
        print("DECISION=OFF")
        print("ORDER_INTENTS=0")
        print("EXECUTION=OFF")

        print("SYNTHETIC=False")
        print("INTERPOLATION=False")
        print("FILL=False")
        print("BACKFILL=False")
        print("PADDING=False")
        print("BLENDING=False")

        print("FAIL_CLOSED=True")

    finally:

        conn.close()


if __name__ == "__main__":
    main()