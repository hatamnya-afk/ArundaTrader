# -*- coding: utf-8 -*-

import importlib.util
import sqlite3
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json


# ============================================================
# ARUNDA TRADER
# ROLLING MULTI-HORIZON CONTEXT ACCUMULATOR v0.2
# ============================================================

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")

PRODUCTION_DB = PROJECT_ROOT / "arunda.db"

FABRIC_DB = (
    PROJECT_ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

KUCOIN_MODULE_PATH = (
    PROJECT_ROOT
    / "public_market_data_kucoin.py"
)

STORE_MODULE_PATH = (
    PROJECT_ROOT
    / "local_canonical_store_v0.1.py"
)

ENGINE = "ROLLING_MULTI_HORIZON_CONTEXT_ACCUMULATOR"
VERSION = "v0.2"

TIMEFRAME = "1h"
TARGET_DEPTH = 150
MIN_CONTEXT = 21

LAUNCH_TIMESTAMP = datetime(
    2026, 8, 31, 0, 0, 0, tzinfo=timezone.utc
)

LAUNCH_UNIX = int(LAUNCH_TIMESTAMP.timestamp())

KUCOIN_URL = (
    "https://api.kucoin.com/api/v1/market/candles"
)

BITGET_URL = (
    "https://api.bitget.com/api/v2/spot/market/history-candles"
)

MARKETS = [
    ("BTC", "BTC/USDT", "KUCOIN_SPOT:BTC-USDT", "BTC-USDT"),
    ("ETH", "ETH/USDT", "KUCOIN_SPOT:ETH-USDT", "ETH-USDT"),
    ("SOL", "SOL/USDT", "KUCOIN_SPOT:SOL-USDT", "SOL-USDT"),
    ("XRP", "XRP/USDT", "KUCOIN_SPOT:XRP-USDT", "XRP-USDT"),
    ("ADA", "ADA/USDT", "KUCOIN_SPOT:ADA-USDT", "ADA-USDT"),
    ("DOGE", "DOGE/USDT", "KUCOIN_SPOT:DOGE-USDT", "DOGE-USDT"),
    ("SHIB", "SHIB/USDT", "KUCOIN_SPOT:SHIB-USDT", "SHIB-USDT"),
    ("LINK", "LINK/USDT", "KUCOIN_SPOT:LINK-USDT", "LINK-USDT"),
    ("AVAX", "AVAX/USDT", "KUCOIN_SPOT:AVAX-USDT", "AVAX-USDT"),
    ("DOT", "DOT/USDT", "KUCOIN_SPOT:DOT-USDT", "DOT-USDT"),
    ("LTC", "LTC/USDT", "KUCOIN_SPOT:LTC-USDT", "LTC-USDT"),
    ("UNI", "UNI/USDT", "KUCOIN_SPOT:UNI-USDT", "UNI-USDT"),
    ("AAVE", "AAVE/USDT", "KUCOIN_SPOT:AAVE-USDT", "AAVE-USDT"),
    ("SUI", "SUI/USDT", "KUCOIN_SPOT:SUI-USDT", "SUI-USDT"),
    ("NEAR", "NEAR/USDT", "KUCOIN_SPOT:NEAR-USDT", "NEAR-USDT"),
]


# ============================================================
# FLAGS
# ============================================================

SYNTHETIC = False
INTERPOLATION = False
FILL = False
BACKFILL = False
PADDING = False
BLENDING = False

PRODUCTION_DB_TOUCHED = False
PRODUCTION_DB_WRITES = 0

SIGNAL_CHAIN_MODIFIED = False
ORDER_INTENTS = 0
EXECUTION = False


# ============================================================
# MODULE LOADER
# ============================================================

def load_module(path, name):

    if not path.exists():
        raise FileNotFoundError(
            f"MODULE_NOT_FOUND={path}"
        )

    spec = importlib.util.spec_from_file_location(
        name,
        str(path)
    )

    if spec is None or spec.loader is None:
        raise ImportError(
            f"MODULE_LOAD_FAILED={path}"
        )

    module = importlib.util.module_from_spec(spec)

    sys.modules[name] = module

    spec.loader.exec_module(module)

    return module


# ============================================================
# HTTP
# ============================================================

def http_get_json(url, params, timeout=20):

    query = urlencode(params)

    request = Request(
        f"{url}?{query}",
        headers={
            "User-Agent": "ArundaTrader/1.0"
        }
    )

    with urlopen(request, timeout=timeout) as response:

        raw = response.read()

        return json.loads(raw.decode("utf-8"))


# ============================================================
# TIME
# ============================================================

def utc_now():

    return datetime.now(timezone.utc).isoformat()


# ============================================================
# FETCH KUCOIN
# ============================================================

def fetch_kucoin(symbol, oldest_timestamp):

    end_at = oldest_timestamp - 1

    # Request a bounded window before the current oldest bar.
    # 36h gives enough room to obtain real closed 1h candles.
    start_at = max(
        LAUNCH_UNIX,
        end_at - (36 * 3600)
    )

    if end_at <= start_at:
        return []

    params = {
        "symbol": symbol,
        "type": "1hour",
        "startAt": start_at,
        "endAt": end_at,
    }

    data = http_get_json(
        KUCOIN_URL,
        params
    )

    if not isinstance(data, dict):
        raise RuntimeError(
            "KUCOIN_INVALID_RESPONSE"
        )

    if data.get("code") != "200000":
        raise RuntimeError(
            f"KUCOIN_API_ERROR={data}"
        )

    rows = data.get("data")

    if not isinstance(rows, list):
        raise RuntimeError(
            "KUCOIN_DATA_NOT_LIST"
        )

    result = []

    for row in rows:

        if not isinstance(row, list):
            continue

        if len(row) < 6:
            continue

        try:

            ts = int(row[0])

            # KuCoin format:
            # [timestamp, open, close, high, low, volume, turnover]

            candle = {
                "timestamp": ts,
                "open": float(row[1]),
                "close": float(row[2]),
                "high": float(row[3]),
                "low": float(row[4]),
                "volume": float(row[5]),
            }

        except Exception:
            continue

        result.append(candle)

    return result


# ============================================================
# FETCH BITGET FAILOVER
# ============================================================

def fetch_bitget(symbol, oldest_timestamp):

    end_ms = (oldest_timestamp - 1) * 1000

    start_ms = max(
        LAUNCH_UNIX * 1000,
        end_ms - (36 * 3600 * 1000)
    )

    if end_ms <= start_ms:
        return []

    params = {
        "symbol": symbol.replace("-", ""),
        "productType": "USDT-FUTURES",
        "granularity": "1h",
        "startTime": start_ms,
        "endTime": end_ms,
        "limit": "200",
    }

    data = http_get_json(
        BITGET_URL,
        params
    )

    if not isinstance(data, dict):
        raise RuntimeError(
            "BITGET_INVALID_RESPONSE"
        )

    if data.get("code") not in ("00000", 0, None):
        raise RuntimeError(
            f"BITGET_API_ERROR={data}"
        )

    rows = data.get("data")

    if not isinstance(rows, list):
        return []

    result = []

    for row in rows:

        if not isinstance(row, list):
            continue

        if len(row) < 6:
            continue

        try:

            ts_ms = int(row[0])
            ts = ts_ms // 1000

            candle = {
                "timestamp": ts,
                "open": float(row[1]),
                "high": float(row[2]),
                "low": float(row[3]),
                "close": float(row[4]),
                "volume": float(row[5]),
            }

        except Exception:
            continue

        result.append(candle)

    return result


# ============================================================
# CANDLE VALIDATION
# ============================================================

def validate_candle(candle):

    required = (
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )

    for key in required:

        if key not in candle:
            return False

    try:

        ts = int(candle["timestamp"])

        o = float(candle["open"])
        h = float(candle["high"])
        l = float(candle["low"])
        c = float(candle["close"])
        v = float(candle["volume"])

    except Exception:
        return False

    if ts < LAUNCH_UNIX:
        return False

    # Exact 1h alignment.
    if ts % 3600 != 0:
        return False

    # Never accept future/open candles.
    now = int(time.time())

    if ts + 3600 > now:
        return False

    if not all(
        value >= 0
        for value in (o, h, l, c, v)
    ):
        return False

    if h < max(o, c):
        return False

    if l > min(o, c):
        return False

    if h < l:
        return False

    return True


# ============================================================
# MARKET COUNTS
# ============================================================

def read_market_state(conn, asset, symbol, source_id):

    row = conn.execute(
        """
        SELECT
            COUNT(*) AS n,
            MIN(timestamp) AS oldest_ts,
            MAX(timestamp) AS newest_ts
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
        )
    ).fetchone()

    return (
        int(row["n"] or 0),
        row["oldest_ts"],
        row["newest_ts"],
    )


# ============================================================
# CANONICAL CANDLE
# ============================================================

def build_canonical_candle(
    asset,
    symbol,
    source_id,
    candle,
    source_type="CEX_PUBLIC_API",
):

    ts = int(candle["timestamp"])

    # Canonical provenance.
    #
    # IMPORTANT:
    # Current accumulator writes USDT_PER_ASSET.
    # Legacy rows may contain USDT_PER_<ASSET>.
    # Both are accepted by the final validator.

    return {
        "asset": asset,
        "symbol": symbol,
        "timestamp": ts,
        "timeframe": TIMEFRAME,

        "open": float(candle["open"]),
        "high": float(candle["high"]),
        "low": float(candle["low"]),
        "close": float(candle["close"]),
        "volume": float(candle["volume"]),

        "source_id": source_id,
        "source_type": source_type,

        "source_timestamp": ts,
        "retrieved_at": utc_now(),

        "observation_count": 1,

        "observation_signatures": (
            f"{source_id}:{symbol}:{ts}:{TIMEFRAME}"
        ),

        "observation_slots": (
            f"{ts}:{TIMEFRAME}"
        ),

        "pool": None,
        "raydium_instruction": None,

        "price_unit": "USDT_PER_ASSET",
    }


# ============================================================
# PROVENANCE VALIDATION
# ============================================================

def validate_provenance_row(
    row,
    asset,
    symbol,
    expected_source_id,
):

    expected_price_units = {
        "USDT_PER_ASSET",
        f"USDT_PER_{asset}",
    }

    if row["asset"] != asset:
        return False

    if row["symbol"] != symbol:
        return False

    if row["timeframe"] != TIMEFRAME:
        return False

    if row["source_id"] != expected_source_id:
        return False

    if row["source_type"] != "CEX_PUBLIC_API":
        return False

    if row["source_timestamp"] != row["timestamp"]:
        return False

    if not row["retrieved_at"]:
        return False

    try:
        if int(row["observation_count"]) != 1:
            return False
    except Exception:
        return False

    if not row["observation_signatures"]:
        return False

    if not row["observation_slots"]:
        return False

    # ========================================================
    # FIX:
    # Accept both canonical current unit and valid legacy
    # asset-specific unit.
    # ========================================================

    if row["price_unit"] not in expected_price_units:
        return False

    return True


# ============================================================
# FINAL VALIDATION
# ============================================================

def final_validate(conn):

    provenance_valid = True

    duplicates_rejected = 0

    market_results = []

    for asset, symbol, source_id, provider_symbol in MARKETS:

        rows = conn.execute(
            """
            SELECT
                id,
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
                price_unit
            FROM canonical_ohlcv
            WHERE asset = ?
              AND symbol = ?
              AND source_id = ?
              AND timeframe = ?
            ORDER BY timestamp
            """,
            (
                asset,
                symbol,
                source_id,
                TIMEFRAME,
            )
        ).fetchall()

        count = len(rows)

        seen = set()

        duplicate_count = 0

        invalid_count = 0

        for row in rows:

            ts = int(row["timestamp"])

            if ts in seen:
                duplicate_count += 1
                duplicates_rejected += 1
                provenance_valid = False
            else:
                seen.add(ts)

            if not validate_provenance_row(
                row,
                asset,
                symbol,
                source_id,
            ):
                invalid_count += 1
                provenance_valid = False

        market_results.append(
            (
                asset,
                symbol,
                count,
                duplicate_count,
                invalid_count,
            )
        )

        if count < TARGET_DEPTH:
            provenance_valid = False

    return (
        provenance_valid,
        duplicates_rejected,
        market_results,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "ARUNDA TRADER — "
        "ROLLING MULTI-HORIZON CONTEXT ACCUMULATOR v0.2"
    )

    print(f"ENGINE={ENGINE}")
    print(f"VERSION={VERSION}")
    print("PRODUCTION_DB_ACCESS=NONE")
    print(f"FABRIC_DB={FABRIC_DB}")
    print(f"TARGET_DEPTH={TARGET_DEPTH}")
    print(f"MIN_CONTEXT={MIN_CONTEXT}")
    print(f"TIMEFRAME={TIMEFRAME}")
    print(f"MARKETS={len(MARKETS)}")
    print()

    if PRODUCTION_DB.exists():
        # Deliberately do NOT open it.
        pass

    if not FABRIC_DB.exists():

        print("VALIDATION=FAIL")
        print("FAIL_CLOSED=True")
        print("STATUS=FAIL_CLOSED")
        print("ERROR=FABRIC_DB_NOT_FOUND")

        return 1

    if not KUCOIN_MODULE_PATH.exists():

        print("VALIDATION=FAIL")
        print("FAIL_CLOSED=True")
        print("STATUS=FAIL_CLOSED")
        print("ERROR=KUCOIN_MODULE_NOT_FOUND")

        return 1

    if not STORE_MODULE_PATH.exists():

        print("VALIDATION=FAIL")
        print("FAIL_CLOSED=True")
        print("STATUS=FAIL_CLOSED")
        print("ERROR=STORE_MODULE_NOT_FOUND")
        print(f"EXPECTED={STORE_MODULE_PATH}")

        return 1

    try:

        kucoin_module = load_module(
            KUCOIN_MODULE_PATH,
            "arunda_kucoin_runtime_v02"
        )

        store_module = load_module(
            STORE_MODULE_PATH,
            "arunda_local_canonical_store_v02"
        )

    except Exception as exc:

        print("VALIDATION=FAIL")
        print("FAIL_CLOSED=True")
        print("STATUS=FAIL_CLOSED")
        print(
            f"ERROR=MODULE_LOAD_FAILED "
            f"{type(exc).__name__}: {exc}"
        )

        return 1

    # Make sure existing store interface is available.
    if not hasattr(store_module, "insert_candle"):

        print("VALIDATION=FAIL")
        print("FAIL_CLOSED=True")
        print("STATUS=FAIL_CLOSED")
        print("ERROR=INSERT_CANDLE_NOT_FOUND")

        return 1

    insert_candle = store_module.insert_candle

    conn = sqlite3.connect(
        str(FABRIC_DB)
    )

    conn.row_factory = sqlite3.Row

    try:

        before_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM canonical_ohlcv
            """
        ).fetchone()[0]

        markets_ready_21 = 0
        markets_full_150 = 0
        min_depth = None
        max_depth = None

        total_inserted = 0
        total_raw = 0
        total_valid = 0

        market_output = []

        # ====================================================
        # ACCUMULATION
        # ====================================================

        for asset, symbol, source_id, provider_symbol in MARKETS:

            before_count, oldest_ts, newest_ts = (
                read_market_state(
                    conn,
                    asset,
                    symbol,
                    source_id,
                )
            )

            if before_count >= MIN_CONTEXT:
                markets_ready_21 += 1

            target_missing = max(
                0,
                TARGET_DEPTH - before_count
            )

            inserted = 0

            raw_bars = 0
            valid_bars = 0

            provider_used = "NONE"

            if target_missing > 0:

                if oldest_ts is None:

                    # First historical acquisition.
                    # Start immediately before current time,
                    # but never after launch boundary.

                    now = int(time.time())

                    end_ts = (
                        now // 3600
                    ) * 3600 - 3600

                    oldest_ts_for_fetch = (
                        end_ts + 1
                    )

                else:

                    oldest_ts_for_fetch = int(
                        oldest_ts
                    )

                # ====================================================
                # PRIMARY = KUCOIN
                # ====================================================

                try:

                    raw = fetch_kucoin(
                        provider_symbol,
                        oldest_ts_for_fetch,
                    )

                    provider_used = "KUCOIN"

                except Exception:

                    raw = []

                # ====================================================
                # FAILOVER = BITGET
                # ====================================================

                if not raw:

                    try:

                        raw = fetch_bitget(
                            provider_symbol,
                            oldest_ts_for_fetch,
                        )

                        provider_used = "BITGET"

                    except Exception:

                        raw = []

                total_raw += len(raw)

                # ====================================================
                # DEDUP RAW
                # ====================================================

                unique = {}

                for candle in raw:

                    try:
                        ts = int(candle["timestamp"])
                    except Exception:
                        continue

                    if ts < LAUNCH_UNIX:
                        continue

                    if ts in unique:
                        continue

                    unique[ts] = candle

                # ====================================================
                # VALIDATE
                # ====================================================

                valid = []

                for ts in sorted(unique):

                    candle = unique[ts]

                    if not validate_candle(candle):
                        continue

                    valid_bars += 1

                    valid.append(candle)

                total_valid += valid_bars

                # ====================================================
                # ONLY OLDER THAN CURRENT OLDEST
                # ====================================================

                existing = set()

                if before_count > 0:

                    existing_rows = conn.execute(
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
                        )
                    ).fetchall()

                    existing = {
                        int(r["timestamp"])
                        for r in existing_rows
                    }

                candidates = []

                for candle in valid:

                    ts = int(candle["timestamp"])

                    if ts in existing:
                        continue

                    candidates.append(candle)

                # Oldest real candles first.
                candidates.sort(
                    key=lambda x: int(x["timestamp"])
                )

                candidates = candidates[
                    :target_missing
                ]

                # ====================================================
                # INSERT THROUGH EXISTING STORE
                # ====================================================

                for candle in candidates:

                    canonical = build_canonical_candle(
                        asset=asset,
                        symbol=symbol,
                        source_id=source_id,
                        candle=candle,
                    )

                    # Identity assertion.
                    if canonical["asset"] != asset:
                        raise RuntimeError(
                            "IDENTITY_ASSERTION_FAILED_ASSET"
                        )

                    if canonical["symbol"] != symbol:
                        raise RuntimeError(
                            "IDENTITY_ASSERTION_FAILED_SYMBOL"
                        )

                    if canonical["source_id"] != source_id:
                        raise RuntimeError(
                            "IDENTITY_ASSERTION_FAILED_SOURCE"
                        )

                    if canonical["timeframe"] != TIMEFRAME:
                        raise RuntimeError(
                            "IDENTITY_ASSERTION_FAILED_TIMEFRAME"
                        )

                    # Only the canonical Fabric store is called.
                    ok = insert_candle(
                        conn,
                        canonical,
                    )

                    if ok:
                        inserted += 1
                        total_inserted += 1

            # ====================================================
            # POST MARKET COUNT
            # ====================================================

            after_count, new_oldest, new_newest = (
                read_market_state(
                    conn,
                    asset,
                    symbol,
                    source_id,
                )
            )

            if after_count >= MIN_CONTEXT:
                if before_count < MIN_CONTEXT:
                    markets_ready_21 += 1

            if after_count >= TARGET_DEPTH:
                markets_full_150 += 1

            if min_depth is None:
                min_depth = after_count
            else:
                min_depth = min(
                    min_depth,
                    after_count
                )

            if max_depth is None:
                max_depth = after_count
            else:
                max_depth = max(
                    max_depth,
                    after_count
                )

            status = (
                "FULL"
                if after_count >= TARGET_DEPTH
                else
                "READY"
                if after_count >= MIN_CONTEXT
                else
                "NOT_READY"
            )

            market_output.append(
                (
                    asset,
                    symbol,
                    before_count,
                    after_count,
                    inserted,
                    status,
                    provider_used,
                )
            )

        # ====================================================
        # FINAL PROVENANCE VALIDATION
        # ====================================================

        (
            provenance_valid,
            duplicates_rejected,
            validation_results,
        ) = final_validate(conn)

        after_rows = conn.execute(
            """
            SELECT COUNT(*)
            FROM canonical_ohlcv
            """
        ).fetchone()[0]

        # ====================================================
        # RUNTIME REPORT
        # ====================================================

        print(
            f"ASSETS_REQUESTED={len(MARKETS)}"
        )

        print(
            f"ASSETS_READY_21="
            f"{sum(1 for x in market_output if x[3] >= MIN_CONTEXT)}"
        )

        print(
            f"ASSETS_FULL_150="
            f"{sum(1 for x in market_output if x[3] >= TARGET_DEPTH)}"
        )

        print(
            f"MIN_DEPTH={min_depth or 0}"
        )

        print(
            f"MAX_DEPTH={max_depth or 0}"
        )

        print(
            f"PROVENANCE_VALID={provenance_valid}"
        )

        print(
            f"DUPLICATES_REJECTED={duplicates_rejected}"
        )

        print(
            f"SYNTHETIC={SYNTHETIC}"
        )

        print(
            f"INTERPOLATION={INTERPOLATION}"
        )

        print(
            f"FILL={FILL}"
        )

        print(
            f"BACKFILL={BACKFILL}"
        )

        print(
            f"PADDING={PADDING}"
        )

        print(
            f"BLENDING={BLENDING}"
        )

        print(
            f"PRODUCTION_DB_TOUCHED="
            f"{PRODUCTION_DB_TOUCHED}"
        )

        print(
            f"DB_WRITES="
            f"{total_inserted}"
        )

        print(
            f"SIGNAL_CHAIN_MODIFIED="
            f"{SIGNAL_CHAIN_MODIFIED}"
        )

        print(
            f"ORDER_INTENTS="
            f"{ORDER_INTENTS}"
        )

        print(
            f"EXECUTION="
            f"{EXECUTION}"
        )

        print(
            f"FABRIC_ROWS_BEFORE="
            f"{before_rows}"
        )

        print(
            f"FABRIC_ROWS_AFTER="
            f"{after_rows}"
        )

        print(
            f"CANONICAL_BARS_INSERTED="
            f"{total_inserted}"
        )

        print()

        for (
            asset,
            symbol,
            before_count,
            after_count,
            inserted,
            status,
            provider_used,
        ) in market_output:

            print(
                f"MARKET {asset} {symbol} "
                f"{before_count}->{after_count} "
                f"INSERTED={inserted} "
                f"STATUS={status}"
            )

        # ====================================================
        # FINAL STATE
        # ====================================================

        forbidden_activity = (
            SYNTHETIC
            or INTERPOLATION
            or FILL
            or BACKFILL
            or PADDING
            or BLENDING
            or PRODUCTION_DB_TOUCHED
            or PRODUCTION_DB_WRITES < 0
            or SIGNAL_CHAIN_MODIFIED
            or ORDER_INTENTS != 0
            or EXECUTION
        )

        if (
            provenance_valid
            and not forbidden_activity
            and after_rows >= before_rows
        ):

            print()
            print("VALIDATION=PASS")
            print("FAIL_CLOSED=False")
            print(
                "STATUS=READY_FOR_ROLLING_CONTEXT"
            )

            return 0

        else:

            print()
            print("VALIDATION=FAIL")
            print("FAIL_CLOSED=True")
            print("STATUS=FAIL_CLOSED")

            return 1

    except Exception as exc:

        print()
        print("VALIDATION=FAIL")
        print("FAIL_CLOSED=True")
        print("STATUS=FAIL_CLOSED")
        print(
            f"ERROR={type(exc).__name__}: {exc}"
        )

        return 1

    finally:

        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())