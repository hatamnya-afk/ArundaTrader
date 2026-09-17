
"""
ARUNDA PUBLIC MARKET DATA PROBE v0.2
FORENSIC-SAFE / READ-ONLY

Purpose
-------
Verify actual public CEX market-data availability for the exact
15-asset production universe before selecting a canonical provider.

Providers:
    kraken
    coinbase
    okx
    bybit
    kucoin

PASS condition
--------------
PASS is allowed ONLY when at least ONE SINGLE provider has:

    - public market metadata successfully loaded
    - spot market coverage for ALL 15 assets
    - real 1h OHLCV successfully fetched for ALL 15 assets
    - >= 14 valid candles for EVERY asset
    - no duplicate timestamps
    - strictly increasing timestamps
    - valid OHLCV structure for EVERY asset

Important:
---------
Partial coverage is NOT PASS.
Multiple providers collectively covering 15 assets is NOT PASS.
Blending providers is NOT allowed.
Provider selection is NOT performed by this file.

Safety
------
- READ ONLY
- NO API KEY
- NO PRIVATE ENDPOINT
- NO DATABASE
- NO DB WRITE
- NO ORDERS
- NO ACCOUNT ACCESS
- NO SYNTHETIC DATA
- NO INTERPOLATION
- NO FORWARD FILL
- NO BACK FILL
- NO CANDLE FABRICATION
- NO PROVIDER BLENDING
- NO PROVIDER MIXING

Each provider receives an independent result record.

One provider failing MUST NOT terminate the probe.

Exit codes
----------
0 = PASS: one provider has complete 15/15 real 1h coverage
1 = FAIL: no provider has complete coverage
2 = PARTIAL: at least one provider was reachable, but none
    has complete coverage
"""

from __future__ import annotations

import math
import sys
import time
from datetime import datetime, timezone
from typing import Any


# ============================================================
# VERSION / CONFIG
# ============================================================

ENGINE_VERSION = (
    "ARUNDA_PUBLIC_MARKET_DATA_PROBE_v0.2"
)

TIMEFRAME = "1h"

OHLCV_LIMIT = 100

MIN_CANDLES = 14

REQUEST_TIMEOUT_MS = 30000


# ============================================================
# EXACT PRODUCTION UNIVERSE
# ============================================================

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

EXPECTED_ASSET_SET = set(
    EXPECTED_ASSETS
)


# ============================================================
# EXACT PROVIDER SET
# ============================================================

EXCHANGE_IDS = (
    "kraken",
    "coinbase",
    "okx",
    "bybit",
    "kucoin",
)


# ============================================================
# QUOTE PREFERENCE
# ============================================================

QUOTE_PREFERENCE = (
    "USD",
    "USDT",
    "USDC",
)


# ============================================================
# PUBLIC CCXT LOADER
# ============================================================

def load_ccxt():

    try:
        import ccxt
    except ImportError as exc:
        raise RuntimeError(
            "CCXT_NOT_INSTALLED: "
            "python -m pip install ccxt"
        ) from exc

    return ccxt


# ============================================================
# TIME HELPERS
# ============================================================

def now_iso() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def timestamp_to_iso(
    timestamp_ms: Any,
) -> str | None:

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
# NUMERIC HELPERS
# ============================================================

def safe_float(
    value: Any,
) -> float | None:

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
# EXCHANGE CREATION
# ============================================================

def create_exchange(
    ccxt_module,
    exchange_id: str,
):

    exchange_class = getattr(
        ccxt_module,
        exchange_id,
        None,
    )

    if exchange_class is None:
        raise RuntimeError(
            "CCXT_EXCHANGE_CLASS_UNAVAILABLE: "
            f"{exchange_id}"
        )

    return exchange_class(
        {
            "enableRateLimit": True,
            "timeout": REQUEST_TIMEOUT_MS,
        }
    )


# ============================================================
# SPOT MARKET DETECTION
# ============================================================

def is_spot_market(
    market: dict[str, Any],
) -> bool:

    if not isinstance(
        market,
        dict,
    ):
        return False

    if market.get("spot") is True:
        return True

    if market.get("swap") is True:
        return False

    if market.get("future") is True:
        return False

    if market.get("option") is True:
        return False

    if market.get("type") == "spot":
        return True

    return False


# ============================================================
# SYMBOL DISCOVERY
# ============================================================

def find_asset_symbols(
    markets: dict[str, Any],
    asset: str,
) -> list[str]:

    candidates = []

    for symbol, market in markets.items():

        if not isinstance(
            market,
            dict,
        ):
            continue

        if not is_spot_market(
            market
        ):
            continue

        base = str(
            market.get("base") or ""
        ).upper()

        quote = str(
            market.get("quote") or ""
        ).upper()

        if base != asset:
            continue

        if quote not in QUOTE_PREFERENCE:
            continue

        if market.get(
            "active"
        ) is False:
            continue

        quote_rank = (
            QUOTE_PREFERENCE.index(
                quote
            )
        )

        candidates.append(
            (
                quote_rank,
                symbol,
            )
        )

    candidates.sort(
        key=lambda item: (
            item[0],
            item[1],
        )
    )

    return [
        symbol
        for _, symbol in candidates
    ]


# ============================================================
# OHLCV ROW VALIDATION
# ============================================================

def validate_ohlcv_row(
    row: Any,
) -> tuple[bool, str]:

    if not isinstance(
        row,
        (list, tuple),
    ):
        return (
            False,
            "ROW_NOT_LIST",
        )

    if len(row) < 6:
        return (
            False,
            "ROW_LENGTH_LT_6",
        )

    try:
        timestamp = int(
            row[0]
        )
    except Exception:
        return (
            False,
            "INVALID_TIMESTAMP",
        )

    if timestamp <= 0:
        return (
            False,
            "NON_POSITIVE_TIMESTAMP",
        )

    numeric = []

    for value in row[1:6]:

        number = safe_float(
            value
        )

        if number is None:
            return (
                False,
                "INVALID_NUMERIC_VALUE",
            )

        numeric.append(
            number
        )

    (
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
    ) = numeric

    if open_price <= 0:
        return (
            False,
            "INVALID_OPEN",
        )

    if high_price <= 0:
        return (
            False,
            "INVALID_HIGH",
        )

    if low_price <= 0:
        return (
            False,
            "INVALID_LOW",
        )

    if close_price <= 0:
        return (
            False,
            "INVALID_CLOSE",
        )

    if volume < 0:
        return (
            False,
            "INVALID_VOLUME",
        )

    if high_price < max(
        open_price,
        close_price,
    ):
        return (
            False,
            "HIGH_BELOW_OC",
        )

    if low_price > min(
        open_price,
        close_price,
    ):
        return (
            False,
            "LOW_ABOVE_OC",
        )

    if high_price < low_price:
        return (
            False,
            "HIGH_BELOW_LOW",
        )

    return (
        True,
        "VALID",
    )


# ============================================================
# OHLCV SERIES VALIDATION
# ============================================================

def validate_ohlcv_series(
    rows: list[Any],
) -> dict[str, Any]:

    result = {
        "valid": False,
        "reason": None,
        "raw_rows": 0,
        "valid_rows": 0,
        "invalid_rows": 0,
        "duplicate_timestamps": 0,
        "non_monotonic": False,
        "latest_timestamp": None,
        "invalid_reasons": {},
    }

    if not isinstance(
        rows,
        list,
    ):
        result["reason"] = (
            "RESPONSE_NOT_LIST"
        )
        return result

    result["raw_rows"] = len(
        rows
    )

    valid_rows = []

    for row in rows:

        valid, reason = (
            validate_ohlcv_row(
                row
            )
        )

        if valid:

            valid_rows.append(
                row
            )

        else:

            result[
                "invalid_rows"
            ] += 1

            reasons = result[
                "invalid_reasons"
            ]

            reasons[reason] = (
                reasons.get(
                    reason,
                    0,
                )
                + 1
            )

    result[
        "valid_rows"
    ] = len(
        valid_rows
    )

    timestamps = [
        int(row[0])
        for row in valid_rows
    ]

    result[
        "duplicate_timestamps"
    ] = (
        len(timestamps)
        - len(set(timestamps))
    )

    for previous, current in zip(
        timestamps,
        timestamps[1:],
    ):

        if current <= previous:

            result[
                "non_monotonic"
            ] = True

            break

    if timestamps:

        result[
            "latest_timestamp"
        ] = timestamp_to_iso(
            timestamps[-1]
        )

    if len(valid_rows) < MIN_CANDLES:

        result["reason"] = (
            "INSUFFICIENT_VALID_CANDLES"
        )

        return result

    if (
        result[
            "duplicate_timestamps"
        ]
        > 0
    ):

        result["reason"] = (
            "DUPLICATE_TIMESTAMPS"
        )

        return result

    if result["non_monotonic"]:

        result["reason"] = (
            "NON_MONOTONIC_TIMESTAMPS"
        )

        return result

    result["valid"] = True
    result["reason"] = "VALID"

    return result


# ============================================================
# SINGLE ASSET PROBE
# ============================================================

def probe_asset(
    exchange,
    markets: dict[str, Any],
    asset: str,
) -> dict[str, Any]:

    result = {
        "asset": asset,
        "status": "NO_MARKET",
        "symbols": [],
        "selected_symbol": None,
        "raw_candles": 0,
        "valid_candles": 0,
        "latest_timestamp": None,
        "duplicate_timestamps": 0,
        "non_monotonic": False,
        "invalid_rows": 0,
        "error": None,
    }

    symbols = find_asset_symbols(
        markets,
        asset,
    )

    result["symbols"] = symbols

    if not symbols:

        result["status"] = (
            "NO_SPOT_MARKET"
        )

        return result

    selected_symbol = symbols[0]

    result[
        "selected_symbol"
    ] = selected_symbol

    try:

        rows = exchange.fetch_ohlcv(
            selected_symbol,
            timeframe=TIMEFRAME,
            limit=OHLCV_LIMIT,
        )

    except Exception as exc:

        result["status"] = (
            "OHLCV_ERROR"
        )

        result["error"] = repr(
            exc
        )

        return result

    structure = (
        validate_ohlcv_series(
            rows
        )
    )

    result[
        "raw_candles"
    ] = structure[
        "raw_rows"
    ]

    result[
        "valid_candles"
    ] = structure[
        "valid_rows"
    ]

    result[
        "latest_timestamp"
    ] = structure[
        "latest_timestamp"
    ]

    result[
        "duplicate_timestamps"
    ] = structure[
        "duplicate_timestamps"
    ]

    result[
        "non_monotonic"
    ] = structure[
        "non_monotonic"
    ]

    result[
        "invalid_rows"
    ] = structure[
        "invalid_rows"
    ]

    if structure["valid"]:

        result["status"] = (
            "READY"
        )

    else:

        result["status"] = (
            "INVALID_OHLCV"
        )

        result["error"] = (
            structure["reason"]
        )

    return result


# ============================================================
# SINGLE PROVIDER PROBE
# ============================================================

def probe_provider(
    ccxt_module,
    exchange_id: str,
) -> dict[str, Any]:

    started = time.perf_counter()

    result = {
        "exchange": exchange_id,
        "engine_version": ENGINE_VERSION,
        "probe_timestamp": now_iso(),

        "exchange_created": False,
        "fetch_ohlcv_supported": False,
        "metadata_loaded": False,

        "status": "NOT_STARTED",

        "coverage_count": 0,
        "ohlcv_ready_count": 0,

        "covered_assets": [],
        "ohlcv_ready_assets": [],

        "assets": {},

        "fatal_error": None,

        "latency_ms": None,
    }

    # --------------------------------------------------------
    # CREATE
    # --------------------------------------------------------

    try:

        exchange = create_exchange(
            ccxt_module,
            exchange_id,
        )

        result[
            "exchange_created"
        ] = True

    except Exception as exc:

        result["status"] = (
            "EXCHANGE_CREATE_ERROR"
        )

        result[
            "fatal_error"
        ] = repr(exc)

        return finalize_provider_result(
            result,
            started,
        )

    # --------------------------------------------------------
    # CAPABILITY
    # --------------------------------------------------------

    try:

        result[
            "fetch_ohlcv_supported"
        ] = (
            exchange.has.get(
                "fetchOHLCV",
                False,
            )
            is True
        )

    except Exception as exc:

        result["status"] = (
            "CAPABILITY_ERROR"
        )

        result[
            "fatal_error"
        ] = repr(exc)

        return finalize_provider_result(
            result,
            started,
        )

    if not result[
        "fetch_ohlcv_supported"
    ]:

        result["status"] = (
            "FETCH_OHLCV_UNSUPPORTED"
        )

        return finalize_provider_result(
            result,
            started,
        )

    # --------------------------------------------------------
    # LOAD PUBLIC MARKET METADATA
    # --------------------------------------------------------

    try:

        markets = exchange.load_markets()

        if not isinstance(
            markets,
            dict,
        ):
            raise RuntimeError(
                "INVALID_MARKET_METADATA"
            )

        result[
            "metadata_loaded"
        ] = True

    except Exception as exc:

        result["status"] = (
            "PUBLIC_MARKET_METADATA_ERROR"
        )

        result[
            "fatal_error"
        ] = repr(exc)

        return finalize_provider_result(
            result,
            started,
        )

    # --------------------------------------------------------
    # PROBE EVERY ASSET
    # --------------------------------------------------------

    for asset in EXPECTED_ASSETS:

        try:

            asset_result = probe_asset(
                exchange,
                markets,
                asset,
            )

        except Exception as exc:

            # Defensive boundary:
            # one asset must never terminate
            # the provider probe.

            asset_result = {
                "asset": asset,
                "status": "UNEXPECTED_ERROR",
                "symbols": [],
                "selected_symbol": None,
                "raw_candles": 0,
                "valid_candles": 0,
                "latest_timestamp": None,
                "duplicate_timestamps": 0,
                "non_monotonic": False,
                "invalid_rows": 0,
                "error": repr(exc),
            }

        result[
            "assets"
        ][asset] = asset_result

        if asset_result[
            "status"
        ] != "NO_SPOT_MARKET":

            result[
                "covered_assets"
            ].append(asset)

        if asset_result[
            "status"
        ] == "READY":

            result[
                "ohlcv_ready_assets"
            ].append(asset)

        print(
            f"{exchange_id.upper():<10} | "
            f"{asset:<5} | "
            f"{asset_result['status']:<22} | "
            f"SYMBOL="
            f"{str(asset_result.get('selected_symbol')):<14} | "
            f"VALID="
            f"{asset_result.get('valid_candles', 0):<3}"
        )

        # Respect exchange rate limit.
        try:

            rate_limit = float(
                getattr(
                    exchange,
                    "rateLimit",
                    0,
                )
            )

            if rate_limit > 0:
                time.sleep(
                    rate_limit / 1000.0
                )

        except Exception:
            pass

    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    result[
        "coverage_count"
    ] = len(
        result[
            "covered_assets"
        ]
    )

    result[
        "ohlcv_ready_count"
    ] = len(
        result[
            "ohlcv_ready_assets"
        ]
    )

    # --------------------------------------------------------
    # CRITICAL PASS CONDITION
    # --------------------------------------------------------

    if (
        result[
            "ohlcv_ready_count"
        ]
        == len(EXPECTED_ASSETS)
    ):

        result["status"] = (
            "FULL_OHLCV_COVERAGE"
        )

    elif (
        result[
            "coverage_count"
        ]
        > 0
    ):

        result["status"] = (
            "PARTIAL_COVERAGE"
        )

    else:

        result["status"] = (
            "NO_PRODUCTION_COVERAGE"
        )

    return finalize_provider_result(
        result,
        started,
    )


# ============================================================
# PROVIDER FINALIZER
# ============================================================

def finalize_provider_result(
    result: dict[str, Any],
    started: float,
) -> dict[str, Any]:

    result[
        "latency_ms"
    ] = round(
        (
            time.perf_counter()
            - started
        )
        * 1000.0,
        3,
    )

    return result


# ============================================================
# PRINT PROVIDER HEADER
# ============================================================

def print_provider_header(
    exchange_id: str,
):

    print()
    print(
        "=" * 90
    )
    print(
        f"PROBING PROVIDER: "
        f"{exchange_id.upper()}"
    )
    print(
        "=" * 90
    )


# ============================================================
# PRINT PROVIDER RESULT
# ============================================================

def print_provider_result(
    result: dict[str, Any],
):

    print()
    print(
        "-" * 90
    )

    print(
        f"PROVIDER        : "
        f"{result['exchange'].upper()}"
    )

    print(
        f"STATUS          : "
        f"{result['status']}"
    )

    print(
        f"METADATA        : "
        f"{result['metadata_loaded']}"
    )

    print(
        f"FETCH OHLCV     : "
        f"{result['fetch_ohlcv_supported']}"
    )

    print(
        f"MARKET COVERAGE : "
        f"{result['coverage_count']}/"
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        f"REAL 1h READY   : "
        f"{result['ohlcv_ready_count']}/"
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        f"LATENCY         : "
        f"{result['latency_ms']} ms"
    )

    if result.get(
        "fatal_error"
    ):

        print(
            f"FATAL ERROR     : "
            f"{result['fatal_error']}"
        )

    print(
        "-" * 90
    )


# ============================================================
# FINAL FORENSIC REPORT
# ============================================================

def print_final_report(
    results: list[dict[str, Any]],
):

    complete = []

    partial = []

    failed = []

    print()
    print()
    print(
        "=" * 90
    )
    print(
        "ARUNDA PUBLIC MARKET DATA PROBE v0.2"
    )
    print(
        "FORENSIC FINAL REPORT"
    )
    print(
        "=" * 90
    )

    print(
        f"Expected assets : "
        f"{len(EXPECTED_ASSETS)}"
    )

    print(
        f"Providers       : "
        f"{len(EXCHANGE_IDS)}"
    )

    print()

    print(
        "PROVIDER RESULTS"
    )

    print(
        "-" * 90
    )

    for result in results:

        exchange = result[
            "exchange"
        ]

        status = result[
            "status"
        ]

        coverage = result[
            "coverage_count"
        ]

        ready = result[
            "ohlcv_ready_count"
        ]

        print(
            f"{exchange.upper():<10} | "
            f"{status:<28} | "
            f"MARKETS={coverage:>2}/15 | "
            f"REAL_1H={ready:>2}/15"
        )

        if status == (
            "FULL_OHLCV_COVERAGE"
        ):

            complete.append(
                exchange
            )

        elif status == (
            "PARTIAL_COVERAGE"
        ):

            partial.append(
                exchange
            )

        else:

            failed.append(
                exchange
            )

    print(
        "-" * 90
    )

    print()
    print(
        "COMPLETE SINGLE-PROVIDER COVERAGE:"
    )

    if complete:

        for exchange in complete:
            print(
                f"  PASS CANDIDATE: "
                f"{exchange.upper()}"
            )

    else:

        print(
            "  NONE"
        )

    print()
    print(
        "PARTIAL PROVIDERS:"
    )

    if partial:

        for exchange in partial:
            print(
                f"  {exchange.upper()}"
            )

    else:

        print(
            "  NONE"
        )

    print()
    print(
        "FAILED / BLOCKED PROVIDERS:"
    )

    if failed:

        for exchange in failed:
            print(
                f"  {exchange.upper()}"
            )

    else:

        print(
            "  NONE"
        )

    print()
    print(
        "=" * 90
    )
    print(
        "SAFETY VERIFICATION"
    )
    print(
        "=" * 90
    )

    print(
        "Database writes       : NONE"
    )

    print(
        "API keys              : NONE"
    )

    print(
        "Private endpoints     : NONE"
    )

    print(
        "Order submission      : NONE"
    )

    print(
        "Synthetic data        : NONE"
    )

    print(
        "Interpolation         : NONE"
    )

    print(
        "Forward fill          : NONE"
    )

    print(
        "Back fill             : NONE"
    )

    print(
        "Provider blending     : NONE"
    )

    print(
        "Provider mixing       : NONE"
    )

    print(
        "Canonical selection   : DEFERRED"
    )

    print(
        "=" * 90
    )

    return complete


# ============================================================
# SELF TEST
# ============================================================

def self_test() -> bool:

    # Valid OHLCV row.

    valid_row = [
        1788825600000,
        100.0,
        110.0,
        95.0,
        105.0,
        1000.0,
    ]

    valid, reason = (
        validate_ohlcv_row(
            valid_row
        )
    )

    if not valid:

        print(
            "SELF TEST FAILED: "
            f"valid row rejected: {reason}"
        )

        return False

    # Invalid OHLCV row.

    invalid_row = [
        1788825600000,
        100.0,
        90.0,
        95.0,
        105.0,
        1000.0,
    ]

    valid, _ = (
        validate_ohlcv_row(
            invalid_row
        )
    )

    if valid:

        print(
            "SELF TEST FAILED: "
            "invalid row accepted"
        )

        return False

    # Valid 14-candle sequence.

    rows = []

    base_ts = (
        1788825600000
    )

    for index in range(
        MIN_CANDLES
    ):

        rows.append(
            [
                base_ts
                + index * 3600000,
                100.0,
                110.0,
                95.0,
                105.0,
                1000.0,
            ]
        )

    series = (
        validate_ohlcv_series(
            rows
        )
    )

    if not series[
        "valid"
    ]:

        print(
            "SELF TEST FAILED: "
            "valid series rejected"
        )

        return False

    # Duplicate timestamp must fail.

    duplicate_rows = list(
        rows
    )

    duplicate_rows[-1] = (
        duplicate_rows[-2]
    )

    series = (
        validate_ohlcv_series(
            duplicate_rows
        )
    )

    if series[
        "valid"
    ]:

        print(
            "SELF TEST FAILED: "
            "duplicate timestamps accepted"
        )

        return False

    # Insufficient candles must fail.

    insufficient_rows = rows[
        : MIN_CANDLES - 1
    ]

    series = (
        validate_ohlcv_series(
            insufficient_rows
        )
    )

    if series[
        "valid"
    ]:

        print(
            "SELF TEST FAILED: "
            "insufficient candles accepted"
        )

        return False

    print(
        "SELF TEST : PASS"
    )

    return True


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    print()
    print(
        "=" * 90
    )
    print(
        "ARUNDA PUBLIC MARKET DATA PROBE v0.2"
    )
    print(
        "FORENSIC-SAFE"
    )
    print(
        "=" * 90
    )

    print(
        f"Engine          : "
        f"{ENGINE_VERSION}"
    )

    print(
        f"Timeframe       : "
        f"{TIMEFRAME}"
    )

    print(
        f"OHLCV lookback  : "
        f"{OHLCV_LIMIT}"
    )

    print(
        f"Minimum candles : "
        f"{MIN_CANDLES}"
    )

    print(
        "Mode            : PUBLIC / READ ONLY"
    )

    print(
        "API KEY         : NONE"
    )

    print(
        "DB WRITE        : NONE"
    )

    print(
        "BLENDING        : FORBIDDEN"
    )

    print(
        "=" * 90
    )

    # --------------------------------------------------------
    # SELF TEST
    # --------------------------------------------------------

    if not self_test():

        print(
            "PROBE ABORTED: "
            "SELF TEST FAILURE"
        )

        return 1

    # --------------------------------------------------------
    # CCXT
    # --------------------------------------------------------

    try:

        ccxt_module = load_ccxt()

    except Exception as exc:

        print(
            "CCXT LOAD ERROR: "
            f"{repr(exc)}"
        )

        return 1

    print()

    print(
        "CCXT VERSION   : "
        f"{getattr(ccxt_module, '__version__', 'UNKNOWN')}"
    )

    # --------------------------------------------------------
    # PROVIDERS
    # --------------------------------------------------------

    print()

    print(
        "PROVIDERS TO TEST:"
    )

    for exchange_id in EXCHANGE_IDS:

        print(
            f"  - {exchange_id}"
        )

    # --------------------------------------------------------
    # IMPORTANT:
    # EVERY PROVIDER IS ALWAYS ATTEMPTED.
    # ONE FAILURE NEVER TERMINATES THE LOOP.
    # --------------------------------------------------------

    results = []

    for exchange_id in EXCHANGE_IDS:

        print_provider_header(
            exchange_id
        )

        try:

            result = probe_provider(
                ccxt_module,
                exchange_id,
            )

        except Exception as exc:

            # Absolute outer forensic boundary.

            result = {
                "exchange": exchange_id,
                "engine_version": ENGINE_VERSION,
                "probe_timestamp": now_iso(),
                "exchange_created": False,
                "fetch_ohlcv_supported": False,
                "metadata_loaded": False,
                "status": "UNEXPECTED_PROVIDER_ERROR",
                "coverage_count": 0,
                "ohlcv_ready_count": 0,
                "covered_assets": [],
                "ohlcv_ready_assets": [],
                "assets": {},
                "fatal_error": repr(exc),
                "latency_ms": None,
            }

        results.append(
            result
        )

        print_provider_result(
            result
        )

    # --------------------------------------------------------
    # FINAL REPORT
    # --------------------------------------------------------

    complete = (
        print_final_report(
            results
        )
    )

    # --------------------------------------------------------
    # HARD PASS CONDITION
    # --------------------------------------------------------

    if complete:

        print()
        print(
            "=" * 90
        )

        print(
            "PROBE RESULT : "
            "PASS"
        )

        print(
            "PASS BASIS:"
        )

        print(
            "At least one SINGLE provider "
            "returned valid real 1h OHLCV "
            "for ALL 15 production assets "
            f"with >= {MIN_CANDLES} candles each."
        )

        print(
            "CANONICAL PROVIDER DECISION : "
            "DEFERRED"
        )

        print(
            "=" * 90
        )

        return 0

    # --------------------------------------------------------
    # NO COMPLETE PROVIDER
    # --------------------------------------------------------

    reachable = [
        result
        for result in results
        if result[
            "metadata_loaded"
        ] is True
    ]

    print()
    print(
        "=" * 90
    )

    if reachable:

        print(
            "PROBE RESULT : "
            "PARTIAL"
        )

        print(
            "No SINGLE provider has complete "
            "15/15 real 1h coverage."
        )

        print(
            "NO BLENDING PERFORMED."
        )

        print(
            "CANONICAL PROVIDER DECISION : "
            "DEFERRED"
        )

        print(
            "=" * 90
        )

        return 2

    print(
        "PROBE RESULT : "
        "FAIL"
    )

    print(
        "NO PUBLIC PROVIDER REACHED "
        "SUCCESSFUL MARKET METADATA."
    )

    print(
        "CANONICAL PROVIDER DECISION : "
        "DEFERRED"
    )

    print(
        "=" * 90
    )

    return 1


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    raise SystemExit(
        main()
    )