# market_arm_contiguous_history_accumulation_v0_4.py

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
TARGET_RUN = 50
LAUNCH_TS = int(datetime(2026, 8, 31, tzinfo=timezone.utc).timestamp())

ASSETS = [
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "DOGE", "SHIB", "LINK", "AVAX", "DOT",
    "LTC", "UNI", "AAVE", "SUI", "NEAR"
]

TIMEFRAME_SECONDS = 3600
TIMEOUT = 20


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"MODULE_LOAD_FAILED:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def utc_iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def is_finite(value):
    try:
        return math.isfinite(float(value))
    except Exception:
        return False


def load_rows(conn, asset):
    symbol = f"{asset}/USDT"
    source_id = f"KUCOIN_SPOT:{asset}-USDT"

    rows = conn.execute(
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

    return rows


def current_contiguous_run(rows):
    if not rows:
        return 0, None, None

    timestamps = [int(r[2]) for r in rows]

    # Duplicate timestamps = hard failure
    if len(timestamps) != len(set(timestamps)):
        raise RuntimeError("DUPLICATE_TIMESTAMP_IN_MARKET")

    run = 1

    for i in range(len(timestamps) - 1, 0, -1):
        if timestamps[i] - timestamps[i - 1] == TIMEFRAME_SECONDS:
            run += 1
        else:
            break

    return run, timestamps[-run], timestamps[-1]


def fetch_kucoin_history(asset, start_ts, end_ts):
    """
    Fetch REAL historical 1h candles from KuCoin.

    The requested interval is bounded.
    No synthetic data.
    No interpolation.
    No fill.
    """

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
        raise RuntimeError(f"KUCOIN_RESPONSE_INVALID:{asset}")

    if payload.get("code") != "200000":
        raise RuntimeError(
            f"KUCOIN_API_ERROR:{asset}:{payload.get('msg')}"
        )

    data = payload.get("data")

    if not isinstance(data, list):
        raise RuntimeError(f"KUCOIN_DATA_INVALID:{asset}")

    result = []

    for raw in data:
        if not isinstance(raw, list):
            continue

        if len(raw) < 6:
            continue

        try:
            ts = int(float(raw[0]))
            op = float(raw[1])
            close = float(raw[2])
            high = float(raw[3])
            low = float(raw[4])
            volume = float(raw[5])
        except Exception:
            continue

        if not all(
            is_finite(x)
            for x in [ts, op, close, high, low, volume]
        ):
            continue

        if ts < LAUNCH_TS:
            continue

        if ts % TIMEFRAME_SECONDS != 0:
            continue

        if ts < start_ts or ts > end_ts:
            continue

        if op <= 0 or close <= 0 or high <= 0 or low <= 0:
            continue

        if volume < 0:
            continue

        if high < max(op, close):
            continue

        if low > min(op, close):
            continue

        result.append(raw)

    result.sort(key=lambda x: int(float(x[0])))

    # Deduplicate API response
    unique = {}
    for raw in result:
        ts = int(float(raw[0]))
        unique[ts] = raw

    return [unique[k] for k in sorted(unique)]


def build_forward_sequence(rows, candidates, next_expected):
    """
    Accept ONLY candles forming a continuous sequence
    immediately after the current latest candle.

    The first missing timestamp must equal next_expected.
    """

    by_ts = {}

    for raw in candidates:
        ts = int(float(raw[0]))

        if ts not in by_ts:
            by_ts[ts] = raw

    sequence = []

    expected = next_expected

    while expected in by_ts:
        sequence.append(by_ts[expected])
        expected += TIMEFRAME_SECONDS

    return sequence


def main():
    print("=" * 100)
    print("ARUNDA MARKET ARM CONTIGUOUS HISTORY ACCUMULATION v0.4")
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
        raise RuntimeError("FABRIC_DB_NOT_FOUND")

    store = load_module(
        STORE_MODULE,
        "canonical_store_v0_4"
    )

    conn = sqlite3.connect(str(FABRIC_DB))

    try:
        summary = []

        for asset in ASSETS:
            rows = load_rows(conn, asset)

            run, run_start, latest = current_contiguous_run(rows)

            if run >= TARGET_RUN:
                print(
                    f"{asset}: RUN={run} TARGET_REACHED=TRUE"
                )
                summary.append((asset, run, 0))
                continue

            needed = TARGET_RUN - run
            next_expected = latest + TIMEFRAME_SECONDS

            print()
            print(
                f"{asset}: "
                f"RUN={run} "
                f"NEEDED={needed} "
                f"START={next_expected} "
                f"START_UTC={utc_iso(next_expected)}"
            )

            # Request enough future historical range to cover target.
            # End is bounded by current UTC time minus one full candle.
            now_ts = int(datetime.now(timezone.utc).timestamp())

            closed_end = (
                now_ts // TIMEFRAME_SECONDS
            ) * TIMEFRAME_SECONDS - TIMEFRAME_SECONDS

            if closed_end < next_expected:
                raise RuntimeError(
                    f"NO_CLOSED_CANDLE_AVAILABLE:{asset}"
                )

            requested_end = min(
                next_expected + (
                    needed + 2
                ) * TIMEFRAME_SECONDS,
                closed_end
            )

            candidates = fetch_kucoin_history(
                asset,
                next_expected,
                requested_end
            )

            sequence = build_forward_sequence(
                rows,
                candidates,
                next_expected
            )

            if not sequence:
                raise RuntimeError(
                    f"FORWARD_HISTORY_NOT_AVAILABLE:{asset}:"
                    f"expected={next_expected}"
                )

            inserted = 0

            for raw in sequence[:needed]:
                ts = int(float(raw[0]))

                # Never accept a candle that is not closed.
                now_check = int(
                    datetime.now(timezone.utc).timestamp()
                )

                if ts + TIMEFRAME_SECONDS > now_check:
                    raise RuntimeError(
                        f"OPEN_OR_FUTURE_CANDLE:{asset}:"
                        f"timestamp={ts}"
                    )

                normalized = store.normalize(
                    asset,
                    f"{asset}-USDT",
                    raw,
                    datetime.now(timezone.utc).isoformat()
                )

                if not store.validate_candle(normalized):
                    raise RuntimeError(
                        f"CANONICAL_VALIDATION_FAILED:{asset}:"
                        f"timestamp={ts}"
                    )

                # Hard identity validation.
                if normalized["asset"].upper() != asset.upper():
                    raise RuntimeError(
                        f"IDENTITY_ASSET_MISMATCH:{asset}"
                    )

                if normalized["symbol"] != f"{asset}/USDT":
                    raise RuntimeError(
                        f"IDENTITY_SYMBOL_MISMATCH:{asset}"
                    )

                if normalized["source_id"] != (
                    f"KUCOIN_SPOT:{asset}-USDT"
                ):
                    raise RuntimeError(
                        f"IDENTITY_SOURCE_MISMATCH:{asset}"
                    )

                if normalized["timeframe"] != TIMEFRAME:
                    raise RuntimeError(
                        f"TIMEFRAME_MISMATCH:{asset}"
                    )

                ok = store.insert_candle(
                    conn,
                    normalized
                )

                if ok:
                    inserted += 1
                    print(
                        f"  INSERTED={asset} "
                        f"TIMESTAMP={ts} "
                        f"UTC={utc_iso(ts)}"
                    )

            # Re-read and verify the resulting contiguous run.
            verify_rows = load_rows(conn, asset)

            verify_run, verify_start, verify_latest = (
                current_contiguous_run(verify_rows)
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
                (asset, verify_run, inserted)
            )

        print()
        print("=" * 100)
        print("FINAL VALIDATION")
        print("=" * 100)

        all_target = True

        for asset, run, inserted in summary:
            status = "READY" if run >= TARGET_RUN else "PARTIAL"
            if run < TARGET_RUN:
                all_target = False

            print(
                f"{asset}: "
                f"RUN={run} "
                f"INSERTED={inserted} "
                f"STATUS={status}"
            )

        print("=" * 100)

        if all_target:
            print("MARKET_ARM_READY=True")
            print("CONTIGUOUS_50_READY=15/15")
            print("STATUS=READY_FOR_MARKET_SCORE")
        else:
            print("MARKET_ARM_READY=False")
            print("STATUS=FORWARD_ACCUMULATION_CONTINUES")

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