from __future__ import annotations

import importlib.util
import math
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

KUCOIN_MODULE_PATH = (
    PROJECT_ROOT / "public_market_data_kucoin.py"
)

STORE_MODULE_PATH = (
    PROJECT_ROOT / "local_canonical_store_v0.1.py"
)

FABRIC_DB = (
    PROJECT_ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)


# ============================================================
# CONTRACT
# ============================================================

ENGINE = "HISTORICAL_FABRIC_ACCUMULATOR"
VERSION = "v0.1"

TIMEFRAME = "1h"
MIN_REAL_BARS = 21

EXECUTION = False
ORDER_INTENTS_CREATED = 0

NO_SYNTHETIC = True
NO_INTERPOLATION = True
NO_FILL = True
NO_BACKFILL = True
NO_PADDING = True
NO_BLENDING = True

PROVIDER = "KUCOIN"
SOURCE_TYPE = "CEX_PUBLIC_API"

EXPECTED_ASSETS = (
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
)

ASSET_SYMBOLS = {
    "BTC": "BTC-USDT",
    "ETH": "ETH-USDT",
    "SOL": "SOL-USDT",
    "XRP": "XRP-USDT",
    "ADA": "ADA-USDT",
    "DOGE": "DOGE-USDT",
    "SHIB": "SHIB-USDT",
    "LINK": "LINK-USDT",
    "AVAX": "AVAX-USDT",
    "DOT": "DOT-USDT",
    "LTC": "LTC-USDT",
    "UNI": "UNI-USDT",
    "AAVE": "AAVE-USDT",
    "SUI": "SUI-USDT",
    "NEAR": "NEAR-USDT",
}

TIMEFRAME_SECONDS = 3600

# Fetch enough history to obtain >=21 closed candles.
# We deliberately request a bounded real historical window.
FETCH_HOURS = 36

REQUEST_TIMEOUT = 15


# ============================================================
# MODULE LOADER
# ============================================================

def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(
        name,
        path,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"MODULE_LOAD_FAILED:{path.name}"
        )

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ============================================================
# TIME
# ============================================================

def utc_now_epoch() -> int:
    return int(
        datetime.now(timezone.utc).timestamp()
    )


def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# FABRIC READ
# ============================================================

def read_existing_counts(
    conn: sqlite3.Connection,
) -> dict[str, int]:
    """
    Read existing CEX KuCoin /USDT candle counts.

    No mutation.
    """

    rows = conn.execute(
        """
        SELECT
            asset,
            symbol,
            timeframe,
            source_id,
            COUNT(*)
        FROM canonical_ohlcv
        WHERE timeframe = ?
          AND source_id LIKE 'KUCOIN_SPOT:%'
        GROUP BY
            asset,
            symbol,
            timeframe,
            source_id
        ORDER BY asset
        """,
        (TIMEFRAME,),
    ).fetchall()

    counts = {}

    for asset, symbol, timeframe, source_id, count in rows:

        key = (
            str(asset).upper(),
            str(symbol),
            str(source_id),
            str(timeframe),
        )

        counts[key] = int(count)

    return counts


def existing_timestamps(
    conn: sqlite3.Connection,
    asset: str,
    symbol: str,
    source_id: str,
) -> set[int]:
    """
    Return existing timestamps for one explicit market.

    Market identity is:
        asset + symbol + source_id + timeframe
    """

    rows = conn.execute(
        """
        SELECT timestamp
        FROM canonical_ohlcv
        WHERE asset = ?
          AND symbol = ?
          AND source_id = ?
          AND timeframe = ?
        """,
        (
            asset,
            symbol,
            source_id,
            TIMEFRAME,
        ),
    ).fetchall()

    return {
        int(row[0])
        for row in rows
    }


# ============================================================
# KUCOIN HISTORICAL FETCH
# ============================================================

def fetch_closed_bars(
    kucoin_module,
    symbol: str,
    required_new: int,
) -> list[list]:
    """
    Fetch real historical KuCoin 1h candles.

    No synthetic data.
    No fill.
    No interpolation.
    No blending.

    Current/open candle is excluded.
    """

    if required_new <= 0:
        return []

    now = utc_now_epoch()

    start_at = (
        now
        - FETCH_HOURS * TIMEFRAME_SECONDS
    )

    end_at = now

    response = kucoin_module.requests.get(
        kucoin_module.API_URL,
        params={
            "symbol": symbol,
            "type": "1hour",
            "startAt": start_at,
            "endAt": end_at,
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    payload = response.json()

    if payload.get("code") != "200000":
        raise RuntimeError(
            f"KUCOIN_API_ERROR:{payload.get('code')}"
        )

    rows = payload.get("data")

    if not isinstance(rows, list):
        raise RuntimeError(
            f"{symbol}:INVALID_KUCOIN_DATA"
        )

    now = utc_now_epoch()
    current_hour = (
        now - (now % TIMEFRAME_SECONDS)
    )

    closed = []

    for row in rows:

        if not isinstance(row, list):
            continue

        if len(row) < 6:
            continue

        try:
            timestamp = int(row[0])
        except (TypeError, ValueError):
            continue

        if timestamp <= 0:
            continue

        if timestamp % TIMEFRAME_SECONDS != 0:
            continue

        # Never consume current/open candle.
        if timestamp >= current_hour:
            continue

        closed.append(row)

    # Strict timestamp uniqueness.
    timestamps = [
        int(row[0])
        for row in closed
    ]

    if len(timestamps) != len(set(timestamps)):
        raise RuntimeError(
            f"{symbol}:DUPLICATE_RAW_TIMESTAMPS"
        )

    # Old -> new.
    closed.sort(
        key=lambda row: int(row[0])
    )

    # Only real historical rows.
    return closed


# ============================================================
# GAP REPORT
# ============================================================

def detect_gaps(
    timestamps: list[int],
) -> list[tuple[int, int, int]]:
    """
    Report missing hourly intervals.

    Gaps are never filled.
    """

    gaps = []

    if len(timestamps) < 2:
        return gaps

    for previous, current in zip(
        timestamps,
        timestamps[1:],
    ):
        delta = current - previous

        if delta > TIMEFRAME_SECONDS:

            missing = (
                delta // TIMEFRAME_SECONDS
            ) - 1

            if missing > 0:
                gaps.append(
                    (
                        previous,
                        current,
                        missing,
                    )
                )

    return gaps


# ============================================================
# MAIN ACCUMULATION
# ============================================================

def main() -> int:

    print()
    print("=" * 90)
    print(
        "ARUNDA TRADER — HISTORICAL FABRIC ACCUMULATOR v0.1"
    )
    print("=" * 90)

    if not KUCOIN_MODULE_PATH.exists():
        print("STATUS=FAIL")
        print("ERROR=KUCOIN_MODULE_NOT_FOUND")
        return 1

    if not STORE_MODULE_PATH.exists():
        print("STATUS=FAIL")
        print("ERROR=STORE_MODULE_NOT_FOUND")
        return 1

    if not FABRIC_DB.exists():
        print("STATUS=FAIL")
        print("ERROR=FABRIC_DB_NOT_FOUND")
        return 1

    # Load existing verified modules.
    kucoin = load_module(
        KUCOIN_MODULE_PATH,
        "arunda_public_market_data_kucoin_v01",
    )

    store = load_module(
        STORE_MODULE_PATH,
        "local_canonical_store_v01",
    )

    insert_candle = store.insert_candle

    conn = sqlite3.connect(
        str(FABRIC_DB)
    )

    try:

        before_total = conn.execute(
            "SELECT COUNT(*) FROM canonical_ohlcv"
        ).fetchone()[0]

        before_counts = read_existing_counts(
            conn
        )

        total_inserted = 0
        total_duplicates = 0
        total_valid = 0
        total_raw = 0

        failed_assets = []
        ready_assets = []
        insufficient_assets = []

        retrieved_at = utc_now_iso()

        for asset in EXPECTED_ASSETS:

            symbol = ASSET_SYMBOLS[asset]
            canonical_symbol = symbol.replace(
                "-",
                "/",
            )

            source_id = (
                f"KUCOIN_SPOT:{symbol}"
            )

            key = (
                asset,
                canonical_symbol,
                source_id,
                TIMEFRAME,
            )

            existing = before_counts.get(
                key,
                0,
            )

            required_new = max(
                0,
                MIN_REAL_BARS - existing,
            )

            print()
            print(
                f"MARKET={asset}|"
                f"{canonical_symbol}|"
                f"{source_id}|"
                f"EXISTING={existing}|"
                f"REQUIRED_NEW={required_new}"
            )

            if required_new == 0:
                ready_assets.append(asset)
                print(
                    "ACTION=NONE_ALREADY_READY"
                )
                continue

            try:

                existing_ts = existing_timestamps(
                    conn,
                    asset,
                    canonical_symbol,
                    source_id,
                )

                raw_rows = fetch_closed_bars(
                    kucoin,
                    symbol,
                    required_new,
                )

                total_raw += len(raw_rows)

                if not raw_rows:
                    raise RuntimeError(
                        "NO_CLOSED_HISTORICAL_BARS"
                    )

                # Only timestamps not already present.
                new_rows = [
                    row
                    for row in raw_rows
                    if int(row[0])
                    not in existing_ts
                ]

                # Old -> new.
                new_rows.sort(
                    key=lambda row: int(row[0])
                )

                # We need enough new REAL candles.
                if len(new_rows) < required_new:
                    raise RuntimeError(
                        f"INSUFFICIENT_NEW_REAL_BARS:"
                        f"{len(new_rows)}/"
                        f"{required_new}"
                    )

                # Use newest required real bars.
                new_rows = new_rows[
                    -required_new:
                ]

                raw_timestamps = [
                    int(row[0])
                    for row in new_rows
                ]

                gaps = detect_gaps(
                    raw_timestamps
                )

                if gaps:
                    print(
                        f"GAPS_REPORTED={len(gaps)}"
                    )

                inserted_asset = 0
                duplicate_asset = 0
                valid_asset = 0

                for raw_bar in new_rows:

                    candle = kucoin.normalize(
                        asset,
                        symbol,
                        raw_bar,
                        retrieved_at,
                    )

                    kucoin.validate_candle(
                        candle
                    )

                    # Strong identity assertions.
                    if candle["asset"] != asset:
                        raise RuntimeError(
                            "ASSET_IDENTITY_MISMATCH"
                        )

                    if candle["symbol"] != canonical_symbol:
                        raise RuntimeError(
                            "SYMBOL_IDENTITY_MISMATCH"
                        )

                    if candle["source_id"] != source_id:
                        raise RuntimeError(
                            "SOURCE_IDENTITY_MISMATCH"
                        )

                    if candle["timeframe"] != TIMEFRAME:
                        raise RuntimeError(
                            "TIMEFRAME_MISMATCH"
                        )

                    timestamp = int(
                        candle["timestamp"]
                    )

                    if timestamp in existing_ts:
                        duplicate_asset += 1
                        total_duplicates += 1
                        continue

                    # Existing verified writer.
                    inserted = insert_candle(
                        conn,
                        candle,
                    )

                    if inserted:
                        inserted_asset += 1
                        total_inserted += 1
                        existing_ts.add(timestamp)
                    else:
                        duplicate_asset += 1
                        total_duplicates += 1

                    valid_asset += 1
                    total_valid += 1

                final_count = conn.execute(
                    """
                    SELECT COUNT(*)
                    FROM canonical_ohlcv
                    WHERE asset = ?
                      AND symbol = ?
                      AND source_id = ?
                      AND timeframe = ?
                    """,
                    (
                        asset,
                        canonical_symbol,
                        source_id,
                        TIMEFRAME,
                    ),
                ).fetchone()[0]

                print(
                    f"RAW={len(raw_rows)}|"
                    f"NEW={len(new_rows)}|"
                    f"VALID={valid_asset}|"
                    f"INSERTED={inserted_asset}|"
                    f"DUPLICATES={duplicate_asset}|"
                    f"FINAL={final_count}"
                )

                if final_count >= MIN_REAL_BARS:
                    ready_assets.append(asset)
                else:
                    insufficient_assets.append(
                        asset
                    )

            except Exception as exc:

                failed_assets.append(
                    (
                        asset,
                        str(exc),
                    )
                )

                print(
                    f"MARKET_STATUS=FAIL|"
                    f"ERROR={type(exc).__name__}:"
                    f"{exc}"
                )

        after_total = conn.execute(
            "SELECT COUNT(*) FROM canonical_ohlcv"
        ).fetchone()[0]

        db_delta = after_total - before_total

        expected_delta = total_inserted

        validation = (
            len(failed_assets) == 0
            and db_delta == expected_delta
            and len(ready_assets)
            + len(insufficient_assets)
            + len(failed_assets)
            == len(EXPECTED_ASSETS)
            and len(ready_assets)
            == len(EXPECTED_ASSETS)
            and total_duplicates == 0
        )

        print()
        print("=" * 90)
        print("===== ACCUMULATION RESULT =====")
        print("=" * 90)

        print(f"ENGINE={ENGINE}")
        print(f"VERSION={VERSION}")
        print(f"PROVIDER={PROVIDER}")
        print(f"SOURCE_TYPE={SOURCE_TYPE}")
        print(f"TIMEFRAME={TIMEFRAME}")

        print(
            f"ASSETS_REQUESTED={len(EXPECTED_ASSETS)}"
        )

        print(
            f"ASSETS_READY={len(ready_assets)}"
        )

        print(
            f"ASSETS_FAILED={len(failed_assets)}"
        )

        print(
            f"ASSETS_INSUFFICIENT={len(insufficient_assets)}"
        )

        print(f"RAW_BARS={total_raw}")
        print(f"VALID_BARS={total_valid}")
        print(
            f"CANONICAL_BARS_INSERTED={total_inserted}"
        )
        print(
            f"DUPLICATES={total_duplicates}"
        )

        print(
            f"FABRIC_ROWS_BEFORE={before_total}"
        )

        print(
            f"FABRIC_ROWS_AFTER={after_total}"
        )

        print(
            f"FABRIC_ROW_DELTA={db_delta}"
        )

        print(
            f"EXPECTED_DB_DELTA={expected_delta}"
        )

        print(
            f"REAL_DATA={True}"
        )

        print(
            f"SYNTHETIC={False}"
        )

        print(
            f"INTERPOLATION={False}"
        )

        print(
            f"FILL={False}"
        )

        print(
            f"BACKFILL={False}"
        )

        print(
            f"PADDING={False}"
        )

        print(
            f"BLENDING={False}"
        )

        print(
            f"PRODUCTION_DB_TOUCHED={False}"
        )

        print(
            f"PRODUCTION_DB_WRITES=0"
        )

        print(
            f"EXECUTION={EXECUTION}"
        )

        print(
            f"ORDER_INTENTS_CREATED="
            f"{ORDER_INTENTS_CREATED}"
        )

        print(
            f"FAIL_CLOSED={not validation}"
        )

        print(
            f"VALIDATION="
            f"{'PASS' if validation else 'FAIL'}"
        )

        print(
            f"STATUS="
            f"{'READY_FOR_ROLLING_CONTEXT' if validation else 'ACCUMULATION_INCOMPLETE'}"
        )

        if failed_assets:
            print()
            print("FAILED_MARKETS=")
            for asset, reason in failed_assets:
                print(
                    f"  {asset}: {reason}"
                )

        if insufficient_assets:
            print()
            print("INSUFFICIENT_MARKETS=")
            for asset in insufficient_assets:
                print(
                    f"  {asset}"
                )

        return 0 if validation else 1

    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())