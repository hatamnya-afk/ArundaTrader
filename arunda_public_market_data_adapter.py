
"""
ARUNDA PUBLIC MARKET DATA ADAPTER v0.1

Purpose
-------
Independent public-market OHLCV adapter for ArundaTrader.

Architecture
------------
Public CEX API
      ↓
CCXT adapter
      ↓
REAL 1h OHLCV
      ↓
Canonical validation
      ↓
Normalized candle contract

Safety
------
- NO database writes
- NO API key required for public OHLCV
- NO synthetic candles
- NO interpolation
- NO forward fill
- NO back fill
- NO padding
- NO candle blending
- NO fabricated OHLC
- NO order submission
- NO private exchange endpoints

Current provider
----------------
CCXT -> Kraken

This file is intentionally independent from:
    market_data_engine.py
    arunda_pipeline.py
    risk_engine.py
    execution layers

It is a provider adapter only.
"""

from __future__ import annotations

import math
import sys
import time
from datetime import datetime, timezone
from typing import Any


# ============================================================
# CONFIG
# ============================================================

ENGINE_VERSION = "ARUNDA_PUBLIC_MARKET_DATA_ADAPTER_v0.1"

PROVIDER = "KRAKEN"

TIMEFRAME = "1h"

OHLCV_LOOKBACK = 100

REQUEST_LIMIT = 100

REQUEST_TIMEOUT_MS = 30000

REQUIRED_MIN_CANDLES = 14

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


# ============================================================
# CANONICAL SYMBOL MAP
# ============================================================

SYMBOL_MAP = {
    "BTC": "BTC/USD",
    "ETH": "ETH/USD",
    "SOL": "SOL/USD",
    "XRP": "XRP/USD",
    "ADA": "ADA/USD",
    "DOGE": "DOGE/USD",
    "SHIB": "SHIB/USD",
    "LINK": "LINK/USD",
    "AVAX": "AVAX/USD",
    "DOT": "DOT/USD",
    "LTC": "LTC/USD",
    "UNI": "UNI/USD",
    "AAVE": "AAVE/USD",
    "SUI": "SUI/USD",
    "NEAR": "NEAR/USD",
}


# ============================================================
# OPTIONAL PUBLIC PROVIDER CLASS
# ============================================================

def load_ccxt():
    """
    Import CCXT only when the adapter is actually used.
    """

    try:
        import ccxt
    except ImportError as exc:
        raise RuntimeError(
            "CCXT dependency unavailable. "
            "Install with: python -m pip install ccxt"
        ) from exc

    return ccxt


# ============================================================
# TIME
# ============================================================

def utc_now_iso() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def normalize_timestamp_ms(timestamp_ms: Any) -> str | None:
    """
    Convert exchange timestamp in milliseconds
    to canonical UTC ISO-8601.
    """

    try:
        value = int(timestamp_ms)
    except Exception:
        return None

    if value <= 0:
        return None

    try:
        dt = datetime.fromtimestamp(
            value / 1000.0,
            tz=timezone.utc,
        )
    except Exception:
        return None

    return dt.isoformat()


# ============================================================
# NUMERIC VALIDATION
# ============================================================

def safe_float(value: Any) -> float | None:
    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        result = float(value)
    except Exception:
        return None

    if not math.isfinite(result):
        return None

    return result


# ============================================================
# CANONICAL CANDLE CONTRACT
# ============================================================

def validate_canonical_candle(
    candle: dict[str, Any],
) -> tuple[bool, str]:
    """
    Validate one canonical real OHLCV candle.

    Contract
    --------
    asset
    timestamp
    open
    high
    low
    close
    volume
    timeframe
    source
    provider
    """

    required = (
        "asset",
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "timeframe",
        "source",
        "provider",
    )

    for key in required:
        if candle.get(key) is None:
            return False, f"MISSING_{key.upper()}"

    if candle["timeframe"] != TIMEFRAME:
        return False, "INVALID_TIMEFRAME"

    if candle["provider"] != PROVIDER:
        return False, "INVALID_PROVIDER"

    values = (
        candle["open"],
        candle["high"],
        candle["low"],
        candle["close"],
        candle["volume"],
    )

    numeric_values = []

    for value in values:

        if isinstance(value, bool):
            return False, "BOOLEAN_NUMERIC_VALUE"

        try:
            numeric = float(value)
        except Exception:
            return False, "NON_NUMERIC_VALUE"

        if not math.isfinite(numeric):
            return False, "NON_FINITE_VALUE"

        numeric_values.append(numeric)

    (
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
    ) = numeric_values

    if open_price <= 0:
        return False, "INVALID_OPEN"

    if high_price <= 0:
        return False, "INVALID_HIGH"

    if low_price <= 0:
        return False, "INVALID_LOW"

    if close_price <= 0:
        return False, "INVALID_CLOSE"

    if volume < 0:
        return False, "INVALID_VOLUME"

    if high_price < max(
        open_price,
        close_price,
    ):
        return False, "HIGH_BELOW_OC"

    if low_price > min(
        open_price,
        close_price,
    ):
        return False, "LOW_ABOVE_OC"

    if high_price < low_price:
        return False, "HIGH_BELOW_LOW"

    if not isinstance(
        candle["timestamp"],
        str,
    ):
        return False, "INVALID_TIMESTAMP"

    if not candle["timestamp"].strip():
        return False, "EMPTY_TIMESTAMP"

    return True, "VALID"


# ============================================================
# EXCHANGE CREATION
# ============================================================

def create_exchange():
    """
    Create a public-only CCXT exchange client.

    No API credentials are supplied.
    No private endpoints are used.
    """

    ccxt = load_ccxt()

    exchange_class = getattr(
        ccxt,
        "kraken",
        None,
    )

    if exchange_class is None:
        raise RuntimeError(
            "CCXT Kraken exchange class unavailable."
        )

    exchange = exchange_class(
        {
            "enableRateLimit": True,
            "timeout": REQUEST_TIMEOUT_MS,
        }
    )

    return exchange


# ============================================================
# MARKET AVAILABILITY
# ============================================================

def load_public_markets(exchange):
    """
    Load public market metadata.

    This does not authenticate.
    """

    try:
        markets = exchange.load_markets()
    except Exception as exc:
        raise RuntimeError(
            f"PUBLIC_MARKET_METADATA_ERROR: {repr(exc)}"
        ) from exc

    if not isinstance(markets, dict):
        raise RuntimeError(
            "INVALID_PUBLIC_MARKET_METADATA"
        )

    return markets


# ============================================================
# SYMBOL RESOLUTION
# ============================================================

def resolve_symbol(
    asset: str,
    markets: dict[str, Any],
) -> str:
    """
    Resolve canonical asset to a real exchange symbol.

    No alternate market is silently substituted.
    """

    asset = str(asset).strip().upper()

    configured_symbol = SYMBOL_MAP.get(asset)

    if configured_symbol is None:
        raise RuntimeError(
            f"{asset}: SYMBOL_NOT_CONFIGURED"
        )

    if configured_symbol not in markets:
        raise RuntimeError(
            f"{asset}: MARKET_UNAVAILABLE: "
            f"{configured_symbol}"
        )

    return configured_symbol


# ============================================================
# RAW OHLCV FETCH
# ============================================================

def fetch_raw_ohlcv(
    exchange,
    symbol: str,
    limit: int = OHLCV_LOOKBACK,
):
    """
    Fetch raw public OHLCV.

    Returned raw rows are not treated as canonical
    until validated.
    """

    if not exchange.has.get(
        "fetchOHLCV",
        False,
    ):
        raise RuntimeError(
            "EXCHANGE_DOES_NOT_SUPPORT_FETCH_OHLCV"
        )

    try:
        rows = exchange.fetch_ohlcv(
            symbol,
            timeframe=TIMEFRAME,
            limit=int(limit),
        )
    except Exception as exc:
        raise RuntimeError(
            f"PUBLIC_OHLCV_FETCH_ERROR: "
            f"{symbol}: {repr(exc)}"
        ) from exc

    if not isinstance(rows, list):
        raise RuntimeError(
            f"{symbol}: INVALID_OHLCV_RESPONSE"
        )

    return rows


# ============================================================
# RAW → CANONICAL
# ============================================================

def canonicalize_ohlcv_rows(
    asset: str,
    raw_rows: list[Any],
) -> list[dict[str, Any]]:
    """
    Convert raw CCXT OHLCV rows to canonical candles.

    Expected CCXT format:

        [
            timestamp_ms,
            open,
            high,
            low,
            close,
            volume
        ]

    Invalid rows are rejected.
    """

    candles = []

    for index, row in enumerate(raw_rows):

        if not isinstance(row, (list, tuple)):
            continue

        if len(row) < 6:
            continue

        timestamp = normalize_timestamp_ms(
            row[0]
        )

        candle = {
            "asset": asset,
            "timestamp": timestamp,
            "open": safe_float(row[1]),
            "high": safe_float(row[2]),
            "low": safe_float(row[3]),
            "close": safe_float(row[4]),
            "volume": safe_float(row[5]),
            "timeframe": TIMEFRAME,
            "source": (
                f"ARUNDA_PUBLIC_CEX_{PROVIDER}"
            ),
            "provider": PROVIDER,
        }

        valid, reason = validate_canonical_candle(
            candle
        )

        if not valid:
            print(
                f"REJECTED CANDLE | "
                f"{asset} | "
                f"INDEX={index} | "
                f"REASON={reason}"
            )
            continue

        candles.append(candle)

    return candles


# ============================================================
# CHRONOLOGY VALIDATION
# ============================================================

def validate_chronology(
    asset: str,
    candles: list[dict[str, Any]],
) -> tuple[bool, str]:
    """
    Require strict OLD -> NEW ordering.

    Duplicate timestamps are forbidden.
    """

    if not candles:
        return False, "NO_CANDLES"

    timestamps = [
        candle["timestamp"]
        for candle in candles
    ]

    if len(timestamps) != len(
        set(timestamps)
    ):
        return False, "DUPLICATE_TIMESTAMPS"

    for previous, current in zip(
        timestamps,
        timestamps[1:],
    ):

        if current <= previous:
            return False, (
                "NON_MONOTONIC_TIMESTAMPS"
            )

    return True, "VALID"


# ============================================================
# GAP DETECTION
# ============================================================

def detect_hourly_gaps(
    candles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Detect missing 1h intervals.

    IMPORTANT:
    Gaps are reported only.

    No filling is performed.
    """

    gaps = []

    if len(candles) < 2:
        return gaps

    for previous, current in zip(
        candles,
        candles[1:],
    ):

        previous_dt = datetime.fromisoformat(
            previous["timestamp"]
        )

        current_dt = datetime.fromisoformat(
            current["timestamp"]
        )

        delta_seconds = (
            current_dt - previous_dt
        ).total_seconds()

        if delta_seconds > 3600:

            missing_hours = int(
                delta_seconds // 3600
            ) - 1

            if missing_hours > 0:
                gaps.append(
                    {
                        "from": previous["timestamp"],
                        "to": current["timestamp"],
                        "missing_hours": missing_hours,
                    }
                )

    return gaps


# ============================================================
# ASSET FETCH
# ============================================================

def fetch_asset_ohlcv(
    exchange,
    markets: dict[str, Any],
    asset: str,
    count: int = OHLCV_LOOKBACK,
) -> dict[str, Any]:
    """
    Fetch and validate one asset.

    No database interaction.
    """

    asset = str(asset).strip().upper()

    if asset not in EXPECTED_ASSETS:
        raise RuntimeError(
            f"{asset}: UNEXPECTED_ASSET"
        )

    symbol = resolve_symbol(
        asset,
        markets,
    )

    started = time.perf_counter()

    raw_rows = fetch_raw_ohlcv(
        exchange,
        symbol,
        limit=count,
    )

    candles = canonicalize_ohlcv_rows(
        asset,
        raw_rows,
    )

    chronology_valid, chronology_reason = (
        validate_chronology(
            asset,
            candles,
        )
    )

    if not chronology_valid:
        raise RuntimeError(
            f"{asset}: "
            f"CHRONOLOGY_INVALID: "
            f"{chronology_reason}"
        )

    gaps = detect_hourly_gaps(
        candles
    )

    elapsed_ms = (
        time.perf_counter()
        - started
    ) * 1000.0

    latest_timestamp = (
        candles[-1]["timestamp"]
        if candles
        else None
    )

    return {
        "asset": asset,
        "symbol": symbol,
        "provider": PROVIDER,
        "source": (
            f"ARUNDA_PUBLIC_CEX_{PROVIDER}"
        ),
        "timeframe": TIMEFRAME,
        "candles": candles,
        "candle_count": len(candles),
        "valid_candles": len(candles),
        "latest_candle_timestamp": latest_timestamp,
        "gaps": gaps,
        "gap_count": len(gaps),
        "latency_ms": round(
            elapsed_ms,
            3,
        ),
        "status": (
            "READY"
            if len(candles)
            >= REQUIRED_MIN_CANDLES
            else "INSUFFICIENT_DATA"
        ),
    }


# ============================================================
# ALL ASSETS
# ============================================================

def fetch_all_assets(
    assets=EXPECTED_ASSETS,
    count=OHLCV_LOOKBACK,
) -> dict[str, dict[str, Any]]:
    """
    Fetch all configured assets.

    Failover/blending is intentionally NOT performed here.

    Each asset is independently validated.
    """

    exchange = create_exchange()

    print()
    print("=" * 90)
    print(
        "ARUNDA PUBLIC MARKET DATA ADAPTER v0.1"
    )
    print("=" * 90)
    print(
        f"Provider   : {PROVIDER}"
    )
    print(
        f"Timeframe  : {TIMEFRAME}"
    )
    print(
        f"Lookback   : {count}"
    )
    print(
        "Mode       : PUBLIC / READ ONLY"
    )
    print(
        "API KEY    : NOT USED"
    )
    print(
        "DB WRITE   : NONE"
    )
    print(
        "Synthetic  : FORBIDDEN"
    )
    print(
        "FILLING    : FORBIDDEN"
    )
    print("=" * 90)

    markets = load_public_markets(
        exchange
    )

    results = {}

    for asset in assets:

        try:

            result = fetch_asset_ohlcv(
                exchange,
                markets,
                asset,
                count=count,
            )

            results[asset] = result

            print(
                f"OHLCV | "
                f"{asset:<5} | "
                f"SYMBOL={result['symbol']:<10} | "
                f"CANDLES={result['candle_count']:<3} | "
                f"GAPS={result['gap_count']:<2} | "
                f"STATUS={result['status']}"
            )

        except Exception as exc:

            results[asset] = {
                "asset": asset,
                "provider": PROVIDER,
                "source": (
                    f"ARUNDA_PUBLIC_CEX_{PROVIDER}"
                ),
                "timeframe": TIMEFRAME,
                "candles": [],
                "candle_count": 0,
                "valid_candles": 0,
                "latest_candle_timestamp": None,
                "gaps": [],
                "gap_count": 0,
                "status": "ERROR",
                "error": repr(exc),
            }

            print(
                f"OHLCV | "
                f"{asset:<5} | "
                f"STATUS=ERROR | "
                f"{repr(exc)}"
            )

    return results


# ============================================================
# SUMMARY
# ============================================================

def print_summary(
    results: dict[str, dict[str, Any]],
):
    ready = 0
    insufficient = 0
    errors = 0

    print()
    print("=" * 90)
    print(
        "ARUNDA PUBLIC MARKET DATA SUMMARY"
    )
    print("=" * 90)

    for asset in EXPECTED_ASSETS:

        result = results.get(asset)

        if result is None:
            print(
                f"{asset:<5} | MISSING_RESULT"
            )
            errors += 1
            continue

        status = result.get(
            "status"
        )

        if status == "READY":
            ready += 1

        elif status == "INSUFFICIENT_DATA":
            insufficient += 1

        else:
            errors += 1

        print(
            f"{asset:<5} | "
            f"STATUS={status:<18} | "
            f"CANDLES="
            f"{result.get('candle_count', 0):<3} | "
            f"GAPS="
            f"{result.get('gap_count', 0):<3} | "
            f"LATEST="
            f"{result.get('latest_candle_timestamp')}"
        )

    print()
    print(
        f"Assets expected     : "
        f"{len(EXPECTED_ASSETS)}"
    )
    print(
        f"Assets ready        : "
        f"{ready}"
    )
    print(
        f"Insufficient        : "
        f"{insufficient}"
    )
    print(
        f"Errors              : "
        f"{errors}"
    )
    print(
        "Database writes     : NONE"
    )
    print(
        "Synthetic candles   : NONE"
    )
    print(
        "Interpolation       : NONE"
    )
    print(
        "Forward fill        : NONE"
    )
    print(
        "Back fill           : NONE"
    )
    print(
        "Blending            : NONE"
    )
    print("=" * 90)

    return (
        ready,
        insufficient,
        errors,
    )


# ============================================================
# SELF TEST
# ============================================================

def self_test() -> bool:
    """
    Static contract self-test.

    No network.
    No database.
    """

    valid_candle = {
        "asset": "BTC",
        "timestamp": (
            "2026-09-08T00:00:00+00:00"
        ),
        "open": 100.0,
        "high": 110.0,
        "low": 95.0,
        "close": 105.0,
        "volume": 1000.0,
        "timeframe": "1h",
        "source": "ARUNDA_PUBLIC_CEX_KRAKEN",
        "provider": "KRAKEN",
    }

    valid, reason = validate_canonical_candle(
        valid_candle
    )

    if not valid:
        print(
            f"SELF TEST FAILED: {reason}"
        )
        return False

    invalid_candle = dict(
        valid_candle
    )

    invalid_candle["high"] = 90.0

    valid, reason = validate_canonical_candle(
        invalid_candle
    )

    if valid:
        print(
            "SELF TEST FAILED: "
            "invalid candle accepted"
        )
        return False

    print(
        "SELF TEST : PASS"
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main():

    if not self_test():
        return 1

    try:

        results = fetch_all_assets(
            EXPECTED_ASSETS,
            OHLCV_LOOKBACK,
        )

        (
            ready,
            insufficient,
            errors,
        ) = print_summary(
            results
        )

        print()
        print(
            f"ADAPTER STATUS : "
            f"READY={ready}/"
            f"{len(EXPECTED_ASSETS)}"
        )

        if ready == len(
            EXPECTED_ASSETS
        ):
            print(
                "PUBLIC MARKET DATA "
                "ADAPTER STATUS : PASS"
            )
            return 0

        if ready > 0:
            print(
                "PUBLIC MARKET DATA "
                "ADAPTER STATUS : PARTIAL"
            )
            return 2

        print(
            "PUBLIC MARKET DATA "
            "ADAPTER STATUS : FAILED"
        )
        return 1

    except Exception as exc:

        print()
        print("=" * 90)
        print(
            "PUBLIC MARKET DATA ADAPTER ERROR"
        )
        print("=" * 90)
        print(
            repr(exc)
        )
        print("=" * 90)

        return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )