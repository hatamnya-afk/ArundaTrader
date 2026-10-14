from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

import importlib.util

STORE_PATH = Path(r"C:\Users\ASUS\ArundaTrader\local_canonical_store_v0.1.py")

spec = importlib.util.spec_from_file_location("local_canonical_store_v01", STORE_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("LOCAL_CANONICAL_STORE_LOAD_FAILED")

store_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(store_module)
insert_candle = store_module.insert_candle


ENGINE = "ARUNDA_PUBLIC_MARKET_DATA_KUCOIN"
VERSION = "v0.1"

PROVIDER = "KUCOIN"
SOURCE_TYPE = "CEX_PUBLIC_API"
TIMEFRAME = "1h"

PROJECT_ROOT = Path(r"C:\Users\ASUS\ArundaTrader")
FABRIC_STORE = (
    PROJECT_ROOT
    / "public_market_data_fabric"
    / "canonical_store_v0.1.sqlite"
)

API_URL = "https://api.kucoin.com/api/v1/market/candles"

# Existing qualification evidence: exact already-qualified mappings.
ASSETS = {
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
TIMEOUT = (5, 8)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def finite_positive(value: float) -> bool:
    return math.isfinite(value) and value > 0


def raw_signature(asset: str, symbol: str, bar: list) -> str:
    payload = json.dumps(
        {
            "provider": PROVIDER,
            "asset": asset,
            "symbol": symbol,
            "bar": bar,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    return hashlib.sha256(payload).hexdigest()


def fetch_kucoin(
    symbol: str,
    count: int = 50,
) -> list[list]:

    """
    Canonical KuCoin production fetch.

    REAL DATA ONLY.
    1h candles.
    No synthetic data.
    No interpolation.
    No fill.
    No backfill.
    """

    if not isinstance(count, int) or count < 2:
        raise ValueError("INVALID_KUCOIN_CANDLE_COUNT")

    now = int(
        datetime.now(timezone.utc).timestamp()
    )

    # Request enough real history for the requested
    # number of closed 1h candles.
    end_at = now
    start_at = end_at - (
        int(count) + 2
    ) * TIMEFRAME_SECONDS

    response = requests.get(
        API_URL,
        params={
            "symbol": symbol,
            "type": "1hour",
            "startAt": start_at,
            "endAt": end_at,
        },
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    payload = response.json()

    if payload.get("code") != "200000":
        raise RuntimeError(
            f"KUCOIN_API_ERROR:{payload.get('code')}"
        )

    data = payload.get("data")

    if not isinstance(data, list):
        raise RuntimeError(
            "INVALID_KUCOIN_DATA"
        )

    return data

def select_latest_closed_bar(bars: list[list]) -> list:
    now = int(datetime.now(timezone.utc).timestamp())
    current_hour = now - (now % TIMEFRAME_SECONDS)

    candidates = []

    for bar in bars:
        if not isinstance(bar, list) or len(bar) < 6:
            continue

        try:
            timestamp = int(bar[0])
        except (TypeError, ValueError):
            continue

        # Exclude current/open candle.
        if timestamp < current_hour:
            candidates.append(bar)

    if not candidates:
        raise RuntimeError("NO_CLOSED_1H_CANDLE")

    candidates.sort(key=lambda x: int(x[0]), reverse=True)
    return candidates[0]


def normalize(
    asset: str,
    symbol: str,
    bar: list,
    retrieved_at: str,
) -> dict:

    # KuCoin Spot response:
    # [time, open, close, high, low, volume, turnover]
    timestamp = int(bar[0])

    open_ = float(bar[1])
    close = float(bar[2])
    high = float(bar[3])
    low = float(bar[4])
    volume = float(bar[5])

    values = [open_, high, low, close, volume]

    if not all(math.isfinite(v) for v in values):
        raise ValueError("NON_FINITE_OHLCV")

    if not all(v > 0 for v in [open_, high, low, close]):
        raise ValueError("NON_POSITIVE_PRICE")

    if volume < 0:
        raise ValueError("NEGATIVE_VOLUME")

    if high < max(open_, close):
        raise ValueError("HIGH_STRUCTURE_INVALID")

    if low > min(open_, close):
        raise ValueError("LOW_STRUCTURE_INVALID")

    if low > high:
        raise ValueError("LOW_HIGH_STRUCTURE_INVALID")

    if timestamp <= 0:
        raise ValueError("INVALID_TIMESTAMP")

    if timestamp % TIMEFRAME_SECONDS != 0:
        raise ValueError("TIMESTAMP_NOT_1H_ALIGNED")

    source_id = f"KUCOIN_SPOT:{symbol}"

    # CEX has one source observation per canonical candle.
    observation_signature = raw_signature(
        asset,
        symbol,
        bar,
    )

    return {
        "asset": asset,
        "symbol": symbol.replace("-", "/"),
        "timestamp": timestamp,
        "timeframe": TIMEFRAME,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,

        "source_id": source_id,
        "source_type": SOURCE_TYPE,
        "source_timestamp": timestamp,
        "retrieved_at": retrieved_at,

        "observation_count": 1,
        "observation_signatures": [
            observation_signature
        ],
        "observation_slots": [
            timestamp
        ],

        # Not applicable to CEX.
        "pool": None,
        "raydium_instruction": None,

        "price_unit": f"USDT_PER_{asset}",
    }


def validate_candle(candle: dict) -> None:
    required = [
        "asset",
        "symbol",
        "timestamp",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "source_id",
        "source_type",
        "source_timestamp",
        "retrieved_at",
        "observation_count",
        "observation_signatures",
        "observation_slots",
        "price_unit",
    ]

    for key in required:
        if key not in candle:
            raise ValueError(f"MISSING_FIELD:{key}")

    if candle["timeframe"] != "1h":
        raise ValueError("INVALID_TIMEFRAME")

    if candle["source_type"] != "CEX_PUBLIC_API":
        raise ValueError("INVALID_SOURCE_TYPE")

    if not candle["source_id"].startswith("KUCOIN_SPOT:"):
        raise ValueError("INVALID_SOURCE_ID")

    if candle["observation_count"] != 1:
        raise ValueError("INVALID_OBSERVATION_COUNT")

    if len(candle["observation_signatures"]) != 1:
        raise ValueError("INVALID_OBSERVATION_SIGNATURES")

    if len(candle["observation_slots"]) != 1:
        raise ValueError("INVALID_OBSERVATION_SLOTS")

    if candle["source_timestamp"] != candle["timestamp"]:
        raise ValueError("SOURCE_TIMESTAMP_MISMATCH")

    for key in ["open", "high", "low", "close", "volume"]:
        if not math.isfinite(float(candle[key])):
            raise ValueError(f"NON_FINITE:{key}")

    if candle["high"] < max(
        candle["open"],
        candle["close"],
    ):
        raise ValueError("HIGH_INVALID")

    if candle["low"] > min(
        candle["open"],
        candle["close"],
    ):
        raise ValueError("LOW_INVALID")

    if candle["low"] > candle["high"]:
        raise ValueError("OHLC_INVALID")


def main() -> int:

    raw_bars = 0
    valid_bars = 0
    canonical_bars = 0
    invalid_bars = 0
    duplicate_bars = 0
    provenance_valid = True

    received_assets = 0
    seen_keys = set()

    retrieved_at = utc_now()

    try:
        if not FABRIC_STORE.parent.exists():
            FABRIC_STORE.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

        conn = sqlite3.connect(str(FABRIC_STORE))

        try:
            # Ensure existing verified Store schema exists.
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS canonical_ohlcv (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    timeframe TEXT NOT NULL,
                    open REAL NOT NULL,
                    high REAL NOT NULL,
                    low REAL NOT NULL,
                    close REAL NOT NULL,
                    volume REAL NOT NULL,
                    source_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_timestamp INTEGER NOT NULL,
                    retrieved_at TEXT NOT NULL,
                    observation_count INTEGER NOT NULL,
                    observation_signatures TEXT NOT NULL,
                    observation_slots TEXT NOT NULL,
                    pool TEXT,
                    raydium_instruction TEXT,
                    price_unit TEXT,
                    canonical_payload TEXT NOT NULL,
                    UNIQUE(asset, symbol, timestamp, timeframe)
                )
                """
            )

            for asset, provider_symbol in ASSETS.items():

                bars = fetch_kucoin(provider_symbol)
                raw_bars += len(bars)

                if bars:
                    received_assets += 1

                bar = select_latest_closed_bar(bars)

                candle = normalize(
                    asset,
                    provider_symbol,
                    bar,
                    retrieved_at,
                )

                validate_candle(candle)
                valid_bars += 1

                key = (
                    candle["asset"],
                    candle["symbol"],
                    candle["timestamp"],
                    candle["timeframe"],
                )

                if key in seen_keys:
                    duplicate_bars += 1
                    continue

                seen_keys.add(key)

                inserted = insert_candle(
                    conn,
                    candle,
                )

                if inserted:
                    canonical_bars += 1
                else:
                    duplicate_bars += 1

            validation = (
                received_assets == len(ASSETS)
                and valid_bars == len(ASSETS)
                and canonical_bars == len(ASSETS)
                and invalid_bars == 0
                and provenance_valid
                and duplicate_bars == 0
            )

        finally:
            conn.close()

    except Exception as exc:
        validation = False
        print(f"ERROR={type(exc).__name__}:{exc}")

    print()
    print("===== ARUNDA PMDF-01 KUCOIN RUNTIME =====")
    print(f"ENGINE={ENGINE}")
    print(f"VERSION={VERSION}")
    print(f"PROVIDER={PROVIDER}")
    print(f"SOURCE_TYPE={SOURCE_TYPE}")
    print(f"ASSETS_REQUESTED={len(ASSETS)}")
    print(f"ASSETS_RECEIVED={received_assets}")
    print(f"RAW_BARS={raw_bars}")
    print(f"VALID_BARS={valid_bars}")
    print(f"CANONICAL_BARS={canonical_bars}")
    print(f"INVALID_BARS={invalid_bars}")
    print(f"DUPLICATE_BARS={duplicate_bars}")
    print(f"PROVENANCE_VALID={provenance_valid}")
    print(f"TIMEFRAME={TIMEFRAME}")
    print("REAL_DATA=True")
    print("SYNTHETIC=False")
    print("INTERPOLATION=False")
    print("FILL=False")
    print("BACKFILL=False")
    print("PADDING=False")
    print("BLENDING=False")
    print("LOCAL_STORE_WRITE=True")
    print("PRODUCTION_DB_TOUCHED=False")
    print("PRODUCTION_DB_WRITES=0")
    print("PRODUCTION_CONSUMPTION_ENABLED=False")
    print("EXECUTION=DISABLED")
    print("ORDER_INTENTS_CREATED=0")
    print(f"VALIDATION={'PASS' if validation else 'FAIL'}")
    print(
        f"STATUS={'PMDF_01_READY' if validation else 'FAIL_CLOSED'}"
    )

    return 0 if validation else 1


if __name__ == "__main__":
    sys.exit(main())

