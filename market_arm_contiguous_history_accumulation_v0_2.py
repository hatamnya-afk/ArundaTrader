from pathlib import Path

import importlib.util
import sqlite3
import time
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parent
FABRIC_DB = ROOT / "public_market_data_fabric" / "canonical_store_v0.1.sqlite"

KUCOIN_MODULE = ROOT / "public_market_data_kucoin.py"

ASSETS = [
    "BTC", "ETH", "SOL", "XRP", "ADA",
    "DOGE", "SHIB", "LINK", "AVAX", "DOT",
    "LTC", "UNI", "AAVE", "SUI", "NEAR",
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
        "kucoin_public_module",
        path
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("KUCOIN_MODULE_IMPORT_FAILED")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def ts(value):
    return int(float(value))


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


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
            observation_count,
            observation_signatures,
            observation_slots,
            price_unit,
            canonical_payload
        FROM canonical_ohlcv
        WHERE UPPER(asset)=?
          AND symbol=?
          AND source_id=?
          AND source_type=?
          AND timeframe=?
          AND timestamp>=?
        ORDER BY timestamp ASC
        """,
        (
            asset,
            asset + "/USDT",
            "KUCOIN_SPOT:" + asset + "-USDT",
            "CEX_PUBLIC_API",
            TIMEFRAME,
            LAUNCH_TS,
        )
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
        delta = (
            ts(row["timestamp"])
            - ts(current[-1]["timestamp"])
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


def assert_no_duplicate_timestamps(rows, asset):
    timestamps = [ts(r["timestamp"]) for r in rows]

    if len(timestamps) != len(set(timestamps)):
        raise RuntimeError(
            f"DUPLICATE_TIMESTAMP:{asset}"
        )


def assert_market_identity(rows, asset):
    for row in rows:
        if str(row["asset"]).upper() != asset:
            raise RuntimeError(
                f"ASSET_IDENTITY_VIOLATION:{asset}"
            )

        if row["timeframe"] != TIMEFRAME:
            raise RuntimeError(
                f"TIMEFRAME_VIOLATION:{asset}"
            )

        if not str(row["source_id"]).startswith(
            "KUCOIN_SPOT:"
        ):
            raise RuntimeError(
                f"SOURCE_ID_VIOLATION:{asset}"
            )

        if row["source_type"] != "CEX_PUBLIC_API":
            raise RuntimeError(
                f"SOURCE_TYPE_VIOLATION:{asset}"
            )

        if ts(row["timestamp"]) < LAUNCH_TS:
            raise RuntimeError(
                f"LAUNCH_BOUNDARY_VIOLATION:{asset}"
            )


def validate_new_candle(
    candle,
    asset,
    expected_timestamp,
    kucoin_module
):
    required = {
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    }

    if not required.issubset(candle):
        raise RuntimeError(
            f"CANDLE_FIELDS_INVALID:{asset}"
        )

    actual_ts = ts(candle["timestamp"])

    if actual_ts != expected_timestamp:
        raise RuntimeError(
            f"NON_CONTIGUOUS_FETCH:{asset}:"
            f"expected={expected_timestamp}:"
            f"actual={actual_ts}"
        )

    if actual_ts % 3600 != 0:
        raise RuntimeError(
            f"TIMESTAMP_ALIGNMENT_INVALID:{asset}"
        )

    now = int(time.time())

    if actual_ts + 3600 > now:
        raise RuntimeError(
            f"OPEN_OR_FUTURE_CANDLE:{asset}"
        )

    normalized = kucoin_module.normalize(
        asset=asset,
        symbol=asset + "-USDT",
        bar=[
            actual_ts,
            candle["open"],
            candle["close"],
            candle["high"],
            candle["low"],
            candle["volume"],
        ],
        retrieved_at=utc_now_iso(),
    )

    kucoin_module.validate_candle(normalized)

    if normalized["timestamp"] != expected_timestamp:
        raise RuntimeError(
            f"NORMALIZED_TIMESTAMP_MISMATCH:{asset}"
        )

    if normalized["symbol"] != asset + "/USDT":
        raise RuntimeError(
            f"MARKET_IDENTITY_INVALID:{asset}"
        )

    return normalized


def run():
    print("=" * 100)
    print("ARUNDA MARKET ARM CONTIGUOUS HISTORY ACCUMULATION v0.2")
    print("=" * 100)
    print(f"FABRIC_DB={FABRIC_DB}")
    print(f"TIMEFRAME={TIMEFRAME}")
    print(f"TARGET_CONTIGUOUS_RUN={TARGET_RUN}")
    print("DIRECTION=FORWARD_ONLY")
    print("SOURCE=KUCOIN_SPOT")
    print("MODE=REAL_DATA_ONLY")
    print("PRODUCTION_DB=FORBIDDEN")
    print()

    kucoin = load_module(KUCOIN_MODULE)

    if not hasattr(kucoin, "fetch_kucoin"):
        raise RuntimeError(
            "KUCOIN_FETCH_API_NOT_FOUND"
        )

    if not hasattr(kucoin, "normalize"):
        raise RuntimeError(
            "KUCOIN_NORMALIZE_API_NOT_FOUND"
        )

    if not hasattr(kucoin, "validate_candle"):
        raise RuntimeError(
            "KUCOIN_VALIDATE_API_NOT_FOUND"
        )

    fabric_path = str(FABRIC_DB)

    conn = sqlite3.connect(fabric_path)
    conn.row_factory = sqlite3.Row

    before = {}

    try:
        for asset in ASSETS:
            rows = load_rows(conn, asset)

            assert_no_duplicate_timestamps(
                rows,
                asset
            )

            assert_market_identity(
                rows,
                asset
            )

            run_rows = current_contiguous_run(rows)

            latest = (
                ts(run_rows[-1]["timestamp"])
                if run_rows
                else None
            )

            before[asset] = {
                "total": len(rows),
                "run": len(run_rows),
                "latest": latest,
            }

        print("=" * 100)
        print("BEFORE")
        print("=" * 100)

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
        print("FORWARD ACCUMULATION")
        print("=" * 100)

        inserted = 0

        for asset in ASSETS:
            if before[asset]["run"] >= TARGET_RUN:
                continue

            current_run = before[asset]["run"]
            latest = before[asset]["latest"]

            if latest is None:
                raise RuntimeError(
                    f"NO_CONTIGUOUS_BASELINE:{asset}"
                )

            needed = TARGET_RUN - current_run

            print(
                f"{asset}: "
                f"RUN={current_run} "
                f"NEEDED={needed} "
                f"START={latest + 3600}"
            )

            expected = latest + 3600

            for _ in range(needed):
                raw_rows = kucoin.fetch_kucoin(
                    asset + "-USDT"
                )

                if not isinstance(raw_rows, list):
                    raise RuntimeError(
                        f"KUCOIN_INVALID_ROWS:{asset}"
                    )

                candidates = []

                for raw in raw_rows:
                    if not isinstance(raw, list):
                        continue

                    if len(raw) < 6:
                        continue

                    try:
                        raw_ts = ts(raw[0])
                    except Exception:
                        continue

                    if raw_ts == expected:
                        candidates.append(raw)

                if len(candidates) != 1:
                    raise RuntimeError(
                        f"EXPECTED_SINGLE_CANDLE_NOT_FOUND:"
                        f"{asset}:timestamp={expected}:"
                        f"candidates={len(candidates)}"
                    )

                raw = candidates[0]

                normalized = validate_new_candle(
                    {
                        "timestamp": raw[0],
                        "open": raw[1],
                        "close": raw[2],
                        "high": raw[3],
                        "low": raw[4],
                        "volume": raw[5],
                    },
                    asset,
                    expected,
                    kucoin
                )

                exists = conn.execute(
                    """
                    SELECT 1
                    FROM canonical_ohlcv
                    WHERE asset=?
                      AND symbol=?
                      AND timestamp=?
                      AND timeframe=?
                    """,
                    (
                        normalized["asset"],
                        normalized["symbol"],
                        normalized["timestamp"],
                        normalized["timeframe"],
                    )
                ).fetchone()

                if exists:
                    raise RuntimeError(
                        f"EXPECTED_NEW_CANDLE_ALREADY_EXISTS:"
                        f"{asset}:{expected}"
                    )

                from local_canonical_store_v0_1 import insert_candle

                ok = insert_candle(
                    conn,
                    normalized
                )

                if not ok:
                    raise RuntimeError(
                        f"FABRIC_INSERT_FAILED:{asset}:{expected}"
                    )

                inserted += 1
                expected += 3600

        print()
        print("=" * 100)
        print("AFTER")
        print("=" * 100)

        all_target = True

        for asset in ASSETS:
            rows = load_rows(conn, asset)

            assert_no_duplicate_timestamps(
                rows,
                asset
            )

            assert_market_identity(
                rows,
                asset
            )

            run_rows = current_contiguous_run(rows)

            run_length = len(run_rows)

            if run_length < TARGET_RUN:
                all_target = False

            latest = (
                ts(run_rows[-1]["timestamp"])
                if run_rows
                else None
            )

            old = before[asset]["run"]
            delta = run_length - old

            print(
                f"{asset:<5} "
                f"BEFORE_RUN={old:<3} "
                f"AFTER_RUN={run_length:<3} "
                f"DELTA={delta:<3} "
                f"TARGET_REACHED="
                f"{run_length >= TARGET_RUN} "
                f"LATEST={latest}"
            )

        print()
        print("=" * 100)
        print("FINAL INTEGRITY")
        print("=" * 100)

        print(f"CANONICAL_BARS_INSERTED={inserted}")
        print(f"TARGET_RUN={TARGET_RUN}")
        print(f"ALL_MARKETS_TARGET_REACHED={all_target}")
        print("FORWARD_ONLY=TRUE")
        print("REAL_DATA_ONLY=TRUE")
        print("SYNTHETIC=FALSE")
        print("INTERPOLATION=FALSE")
        print("FILL=FALSE")
        print("BACKFILL=FALSE")
        print("PADDING=FALSE")
        print("BLENDING=FALSE")
        print("PRE_GAP_DATA_USED=FALSE")
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
            "MARKET_ARM_READY"
            if all_target
            else "CONTINUE_REAL_ACCUMULATION"
        )

    finally:
        conn.close()


if __name__ == "__main__":
    run()
