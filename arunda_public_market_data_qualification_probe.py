"""
ARUNDA PUBLIC MARKET DATA
PROVIDER QUALIFICATION PROBE v0.3

QUALIFICATION TARGET
--------------------
Current candidate providers only:

    BYBIT
    KUCOIN

Purpose
-------
Forensic qualification of public 1h OHLCV quality before selecting:

    CANONICAL PROVIDER
    FAILOVER PROVIDER

This probe does NOT select either provider.

Checks
------
1. Public connectivity
2. Public market metadata
3. Exact 15/15 asset market coverage
4. Spot-market identity
5. fetchOHLCV capability
6. Real 1h OHLCV availability
7. Minimum candle count
8. OHLCV structural validity
9. Duplicate timestamps
10. Strict timestamp ordering
11. Exact 1h interval spacing
12. Missing interval detection
13. Future timestamp detection
14. Latest candle freshness
15. Current/open candle classification
16. Latest candle completeness
17. Deterministic symbol mapping
18. Provider-level qualification

SAFETY
------
READ ONLY
NO API KEYS
NO PRIVATE ENDPOINTS
NO DB
NO DB WRITE
NO ORDERS
NO SYNTHETIC PRODUCTION DATA
NO INTERPOLATION
NO FORWARD FILL
NO BACK FILL
NO BLENDING
NO PROVIDER MIXING
NO AUTOMATIC CANONICAL SELECTION

IMPORTANT
---------
The current/open candle is not modified, removed, filled, or replaced.

It is explicitly classified.

The probe therefore preserves provider evidence exactly as returned.

EXIT CODES
----------
0 = At least one provider fully qualifies
1 = No usable provider
2 = Providers reachable but none fully qualifies
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any


# ============================================================
# VERSION
# ============================================================

ENGINE_VERSION = (
    "ARUNDA_PUBLIC_MARKET_DATA_QUALIFICATION_PROBE_v0.3"
)

EVIDENCE_CONTRACT_VERSION = (
    "ARUNDA_PUBLIC_MARKET_DATA_QUALIFICATION_EVIDENCE_v0.3"
)


# ============================================================
# DATA CONTRACT
# ============================================================

TIMEFRAME = "1h"

TIMEFRAME_MS = (
    60 * 60 * 1000
)

TIMEFRAME_SECONDS = (
    60 * 60
)

OHLCV_LIMIT = 100

MIN_CANDLES = 14

REQUEST_TIMEOUT_MS = 30_000


# ------------------------------------------------------------
# Latest-candle freshness
#
# We allow:
#
#   current/open candle
#   latest completed candle
#
# but reject stale data older than two full intervals.
# ------------------------------------------------------------

FRESHNESS_GRACE_SECONDS = (
    2 * TIMEFRAME_SECONDS
)


# ============================================================
# PROVIDERS
# ============================================================

PROVIDERS = (
    "bybit",
    "kucoin",
)


# ============================================================
# EXACT ARUNDA 15-ASSET UNIVERSE
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
# QUOTE PREFERENCE
# ============================================================

QUOTE_PREFERENCE = (
    "USD",
    "USDT",
    "USDC",
)


# ============================================================
# TIME HELPERS
# ============================================================

def now_ms() -> int:

    return int(
        time.time() * 1000
    )


def now_iso() -> str:

    return datetime.now(
        timezone.utc
    ).isoformat()


def timestamp_to_iso(
    timestamp_ms: Any,
) -> str | None:

    try:

        value = int(
            timestamp_ms
        )

    except Exception:

        return None

    if value <= 0:

        return None

    try:

        return datetime.fromtimestamp(
            value / 1000.0,
            tz=timezone.utc,
        ).isoformat()

    except Exception:

        return None


# ============================================================
# NUMERIC HELPERS
# ============================================================

def safe_float(
    value: Any,
) -> float | None:

    if value is None:

        return None

    if isinstance(
        value,
        bool,
    ):

        return None

    try:

        number = float(
            value
        )

    except Exception:

        return None

    if not math.isfinite(
        number
    ):

        return None

    return number


# ============================================================
# CCXT LOADER
# ============================================================

def load_ccxt():

    try:

        import ccxt

    except ImportError as exc:

        raise RuntimeError(
            "CCXT_NOT_INSTALLED: "
            "run: python -m pip install ccxt"
        ) from exc

    return ccxt


# ============================================================
# EXCHANGE FACTORY
# ============================================================

def create_exchange(
    ccxt_module,
    provider: str,
):

    exchange_class = getattr(
        ccxt_module,
        provider,
        None,
    )

    if exchange_class is None:

        raise RuntimeError(
            "CCXT_EXCHANGE_CLASS_UNAVAILABLE: "
            f"{provider}"
        )

    exchange = exchange_class(
        {
            "enableRateLimit": True,
            "timeout": REQUEST_TIMEOUT_MS,
        }
    )

    return exchange


# ============================================================
# MARKET TYPE VALIDATION
# ============================================================

def is_spot_market(
    market: dict[str, Any],
) -> bool:

    if not isinstance(
        market,
        dict,
    ):

        return False

    if market.get(
        "spot"
    ) is True:

        return True

    if market.get(
        "swap"
    ) is True:

        return False

    if market.get(
        "future"
    ) is True:

        return False

    if market.get(
        "option"
    ) is True:

        return False

    return (
        market.get("type")
        == "spot"
    )


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
            market.get(
                "base"
            )
            or ""
        ).upper()

        quote = str(
            market.get(
                "quote"
            )
            or ""
        ).upper()

        if base != asset:

            continue

        if quote not in (
            QUOTE_PREFERENCE
        ):

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
            "ROW_NOT_LIST_OR_TUPLE",
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

    numeric_values = []

    for value in row[1:6]:

        number = safe_float(
            value
        )

        if number is None:

            return (
                False,
                "INVALID_NUMERIC_VALUE",
            )

        numeric_values.append(
            number
        )

    (
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
    ) = numeric_values

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
            "HIGH_BELOW_OPEN_CLOSE",
        )

    if low_price > min(
        open_price,
        close_price,
    ):

        return (
            False,
            "LOW_ABOVE_OPEN_CLOSE",
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
# SERIES FORENSICS
# ============================================================

def analyze_ohlcv_series(
    rows: Any,
) -> dict[str, Any]:

    result = {
        "raw_count": 0,
        "valid_count": 0,
        "invalid_count": 0,

        "duplicate_timestamps": 0,
        "non_monotonic": False,

        "interval_count": 0,
        "exact_interval_count": 0,
        "invalid_interval_count": 0,

        "missing_intervals": 0,

        "future_timestamps": 0,

        "latest_timestamp_ms": None,
        "latest_timestamp": None,
        "latest_age_seconds": None,

        "oldest_timestamp": None,

        "latest_is_current_interval": None,
        "latest_candle_complete": None,

        "structural_valid": False,
        "continuity_valid": False,
        "freshness_valid": False,

        "errors": [],
    }

    if not isinstance(
        rows,
        list,
    ):

        result[
            "errors"
        ].append(
            "RESPONSE_NOT_LIST"
        )

        return result

    result[
        "raw_count"
    ] = len(rows)

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
                "invalid_count"
            ] += 1

            if len(
                result["errors"]
            ) < 10:

                result[
                    "errors"
                ].append(
                    reason
                )

    result[
        "valid_count"
    ] = len(
        valid_rows
    )

    if (
        result["valid_count"]
        < MIN_CANDLES
    ):

        result[
            "errors"
        ].append(
            "INSUFFICIENT_VALID_CANDLES"
        )

        return result

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

    intervals = []

    for previous, current in zip(
        timestamps,
        timestamps[1:],
    ):

        delta = (
            current
            - previous
        )

        intervals.append(
            delta
        )

    result[
        "interval_count"
    ] = len(
        intervals
    )

    for delta in intervals:

        if delta == TIMEFRAME_MS:

            result[
                "exact_interval_count"
            ] += 1

            continue

        if (
            delta > TIMEFRAME_MS
            and
            delta % TIMEFRAME_MS
            == 0
        ):

            missing = (
                delta
                // TIMEFRAME_MS
            ) - 1

            result[
                "missing_intervals"
            ] += missing

            continue

        result[
            "invalid_interval_count"
        ] += 1

        if len(
            result["errors"]
        ) < 10:

            result[
                "errors"
            ].append(
                f"INVALID_INTERVAL:{delta}"
            )

    current_ms = now_ms()

    for timestamp in timestamps:

        if timestamp > (
            current_ms
            + 60_000
        ):

            result[
                "future_timestamps"
            ] += 1

    oldest = timestamps[0]
    latest = timestamps[-1]

    result[
        "oldest_timestamp"
    ] = timestamp_to_iso(
        oldest
    )

    result[
        "latest_timestamp_ms"
    ] = latest

    result[
        "latest_timestamp"
    ] = timestamp_to_iso(
        latest
    )

    latest_age_seconds = (
        current_ms
        - latest
    ) / 1000.0

    result[
        "latest_age_seconds"
    ] = round(
        latest_age_seconds,
        3,
    )

    current_interval_start = (
        current_ms
        // TIMEFRAME_MS
    ) * TIMEFRAME_MS

    current_interval_end = (
        current_interval_start
        + TIMEFRAME_MS
    )

    latest_is_current = (
        current_interval_start
        <= latest
        < current_interval_end
    )

    result[
        "latest_is_current_interval"
    ] = latest_is_current

    result[
        "latest_candle_complete"
    ] = (
        latest
        + TIMEFRAME_MS
        <= current_ms
    )

    result[
        "structural_valid"
    ] = (
        result[
            "valid_count"
        ]
        >= MIN_CANDLES
        and
        result[
            "invalid_count"
        ]
        == 0
        and
        result[
            "duplicate_timestamps"
        ]
        == 0
        and
        result[
            "future_timestamps"
        ]
        == 0
    )

    result[
        "continuity_valid"
    ] = (
        result[
            "structural_valid"
        ]
        and
        not result[
            "non_monotonic"
        ]
        and
        result[
            "invalid_interval_count"
        ]
        == 0
        and
        result[
            "missing_intervals"
        ]
        == 0
        and
        all(
            delta == TIMEFRAME_MS
            for delta in intervals
        )
    )

    result[
        "freshness_valid"
    ] = (
        latest_age_seconds
        >= 0
        and
        latest_age_seconds
        <= FRESHNESS_GRACE_SECONDS
    )

    return result


# ============================================================
# ASSET PROBE
# ============================================================

def probe_asset(
    exchange,
    markets: dict[str, Any],
    asset: str,
) -> dict[str, Any]:

    result = {
        "asset": asset,
        "status": "NO_SPOT_MARKET",
        "symbols": [],
        "selected_symbol": None,

        "raw_count": 0,
        "valid_count": 0,
        "invalid_count": 0,

        "duplicate_timestamps": 0,
        "non_monotonic": False,

        "exact_interval_count": 0,
        "invalid_interval_count": 0,
        "missing_intervals": 0,

        "future_timestamps": 0,

        "latest_timestamp": None,
        "latest_age_seconds": None,

        "latest_is_current_interval": None,
        "latest_candle_complete": None,

        "structural_valid": False,
        "continuity_valid": False,
        "freshness_valid": False,

        "error": None,
    }

    symbols = find_asset_symbols(
        markets,
        asset,
    )

    result[
        "symbols"
    ] = symbols

    if not symbols:

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

        result[
            "status"
        ] = "OHLCV_ERROR"

        result[
            "error"
        ] = repr(exc)

        return result

    analysis = (
        analyze_ohlcv_series(
            rows
        )
    )

    for key in (
        "raw_count",
        "valid_count",
        "invalid_count",
        "duplicate_timestamps",
        "non_monotonic",
        "exact_interval_count",
        "invalid_interval_count",
        "missing_intervals",
        "future_timestamps",
        "latest_timestamp",
        "latest_age_seconds",
        "latest_is_current_interval",
        "latest_candle_complete",
        "structural_valid",
        "continuity_valid",
        "freshness_valid",
    ):

        result[key] = analysis[key]

    if (
        analysis[
            "structural_valid"
        ]
        and
        analysis[
            "continuity_valid"
        ]
        and
        analysis[
            "freshness_valid"
        ]
    ):

        result[
            "status"
        ] = "QUALIFIED"

    else:

        result[
            "status"
        ] = "FORENSIC_REJECT"

        result[
            "error"
        ] = (
            "; ".join(
                analysis[
                    "errors"
                ]
            )
            or
            "QUALITY_CONTRACT_FAILED"
        )

    return result


# ============================================================
# PROVIDER PROBE
# ============================================================

def probe_provider(
    ccxt_module,
    provider: str,
) -> dict[str, Any]:

    started = time.perf_counter()

    result = {
        "provider": provider,

        "metadata_loaded": False,
        "fetch_ohlcv_supported": False,

        "status": "NOT_STARTED",

        "market_coverage": 0,
        "qualified_assets": 0,

        "assets": {},

        "fatal_error": None,

        "latency_ms": None,
    }

    try:

        exchange = create_exchange(
            ccxt_module,
            provider,
        )

    except Exception as exc:

        result[
            "status"
        ] = "EXCHANGE_CREATE_ERROR"

        result[
            "fatal_error"
        ] = repr(exc)

        return finalize_provider(
            result,
            started,
        )

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

        result[
            "status"
        ] = "CAPABILITY_ERROR"

        result[
            "fatal_error"
        ] = repr(exc)

        return finalize_provider(
            result,
            started,
        )

    if not result[
        "fetch_ohlcv_supported"
    ]:

        result[
            "status"
        ] = "FETCH_OHLCV_UNSUPPORTED"

        return finalize_provider(
            result,
            started,
        )

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

        result[
            "status"
        ] = (
            "PUBLIC_MARKET_METADATA_ERROR"
        )

        result[
            "fatal_error"
        ] = repr(exc)

        return finalize_provider(
            result,
            started,
        )

    for asset in EXPECTED_ASSETS:

        try:

            asset_result = probe_asset(
                exchange,
                markets,
                asset,
            )

        except Exception as exc:

            asset_result = {
                "asset": asset,
                "status": "UNEXPECTED_ERROR",
                "symbols": [],
                "selected_symbol": None,
                "raw_count": 0,
                "valid_count": 0,
                "invalid_count": 0,
                "duplicate_timestamps": 0,
                "non_monotonic": False,
                "exact_interval_count": 0,
                "invalid_interval_count": 0,
                "missing_intervals": 0,
                "future_timestamps": 0,
                "latest_timestamp": None,
                "latest_age_seconds": None,
                "latest_is_current_interval": None,
                "latest_candle_complete": None,
                "structural_valid": False,
                "continuity_valid": False,
                "freshness_valid": False,
                "error": repr(exc),
            }

        result[
            "assets"
        ][asset] = asset_result

        if asset_result[
            "symbols"
        ]:

            result[
                "market_coverage"
            ] += 1

        if asset_result[
            "status"
        ] == "QUALIFIED":

            result[
                "qualified_assets"
            ] += 1

        print(
            f"{provider.upper():<8} | "
            f"{asset:<5} | "
            f"{asset_result['status']:<16} | "
            f"SYMBOL="
            f"{str(asset_result.get('selected_symbol')):<14} | "
            f"CANDLES="
            f"{asset_result.get('valid_count', 0):<3} | "
            f"MISSING="
            f"{asset_result.get('missing_intervals', 0):<3} | "
            f"DUP="
            f"{asset_result.get('duplicate_timestamps', 0):<2} | "
            f"AGE="
            f"{asset_result.get('latest_age_seconds')} | "
            f"CURRENT="
            f"{asset_result.get('latest_is_current_interval')} | "
            f"COMPLETE="
            f"{asset_result.get('latest_candle_complete')}"
        )

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
                    rate_limit
                    / 1000.0
                )

        except Exception:

            pass

    if (
        result[
            "qualified_assets"
        ]
        == len(
            EXPECTED_ASSETS
        )
    ):

        result[
            "status"
        ] = "FULLY_QUALIFIED"

    elif (
        result[
            "qualified_assets"
        ] > 0
    ):

        result[
            "status"
        ] = "PARTIALLY_QUALIFIED"

    else:

        result[
            "status"
        ] = "NOT_QUALIFIED"

    return finalize_provider(
        result,
        started,
    )


# ============================================================
# FINALIZE PROVIDER
# ============================================================

def finalize_provider(
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
# PROVIDER SUMMARY
# ============================================================

def print_provider_summary(
    result: dict[str, Any],
):

    print()
    print("-" * 100)

    print(
        f"PROVIDER           : "
        f"{result['provider'].upper()}"
    )

    print(
        f"STATUS             : "
        f"{result['status']}"
    )

    print(
        f"METADATA           : "
        f"{result['metadata_loaded']}"
    )

    print(
        f"FETCH OHLCV        : "
        f"{result['fetch_ohlcv_supported']}"
    )

    print(
        f"MARKET COVERAGE    : "
        f"{result['market_coverage']}/15"
    )

    print(
        f"QUALIFIED ASSETS   : "
        f"{result['qualified_assets']}/15"
    )

    print(
        f"LATENCY            : "
        f"{result['latency_ms']} ms"
    )

    if result[
        "fatal_error"
    ]:

        print(
            f"FATAL ERROR        : "
            f"{result['fatal_error']}"
        )

    print("-" * 100)


# ============================================================
# FORENSIC MATRIX
# ============================================================

def print_forensic_details(
    results: list[dict[str, Any]],
):

    print()
    print()
    print("=" * 100)
    print("FORENSIC DATA QUALITY MATRIX")
    print("=" * 100)

    for result in results:

        provider = result[
            "provider"
        ]

        print()
        print(
            f"[{provider.upper()}]"
        )

        print("-" * 100)

        for asset in EXPECTED_ASSETS:

            record = result[
                "assets"
            ].get(
                asset,
                {},
            )

            print(
                f"{asset:<5} "
                f"STATUS={str(record.get('status')):<16} "
                f"SYMBOL={str(record.get('selected_symbol')):<14} "
                f"N={str(record.get('valid_count', 0)):<3} "
                f"DUP={str(record.get('duplicate_timestamps', 0)):<3} "
                f"NONMONO={str(record.get('non_monotonic')):<5} "
                f"MISS={str(record.get('missing_intervals', 0)):<3} "
                f"BADINT={str(record.get('invalid_interval_count', 0)):<3} "
                f"FUTURE={str(record.get('future_timestamps', 0)):<3} "
                f"FRESH={str(record.get('freshness_valid')):<5} "
                f"CURRENT={str(record.get('latest_is_current_interval')):<5} "
                f"COMPLETE={str(record.get('latest_candle_complete')):<5}"
            )


# ============================================================
# SELF TEST
# ============================================================

def self_test() -> bool:

    print(
        "SELF TEST : START"
    )

    try:

        current_hour_start = (
            now_ms()
            // TIMEFRAME_MS
        ) * TIMEFRAME_MS

        base = (
            current_hour_start
            - (
                MIN_CANDLES
                * TIMEFRAME_MS
            )
        )

        rows = []

        for index in range(
            MIN_CANDLES
        ):

            rows.append(
                [
                    base
                    + (
                        index
                        * TIMEFRAME_MS
                    ),
                    100.0,
                    110.0,
                    95.0,
                    105.0,
                    1000.0,
                ]
            )

        valid, reason = (
            validate_ohlcv_row(
                rows[0]
            )
        )

        if not valid:

            print(
                "SELF TEST FAILED: "
                f"{reason}"
            )

            return False

        analysis = (
            analyze_ohlcv_series(
                rows
            )
        )

        if not analysis[
            "structural_valid"
        ]:

            print(
                "SELF TEST FAILED: "
                "structural validation"
            )

            print(
                f"DETAIL: {analysis}"
            )

            return False

        if not analysis[
            "continuity_valid"
        ]:

            print(
                "SELF TEST FAILED: "
                "continuity validation"
            )

            print(
                f"DETAIL: {analysis}"
            )

            return False

        if not analysis[
            "freshness_valid"
        ]:

            print(
                "SELF TEST FAILED: "
                "freshness validation"
            )

            print(
                f"DETAIL: {analysis}"
            )

            return False

        if not analysis[
            "latest_candle_complete"
        ]:

            print(
                "SELF TEST FAILED: "
                "latest candle completeness"
            )

            print(
                f"DETAIL: {analysis}"
            )

            return False

        duplicate_rows = [
            list(row)
            for row in rows
        ]

        duplicate_rows[-1][0] = (
            duplicate_rows[-2][0]
        )

        duplicate_analysis = (
            analyze_ohlcv_series(
                duplicate_rows
            )
        )

        if (
            duplicate_analysis[
                "duplicate_timestamps"
            ]
            == 0
        ):

            print(
                "SELF TEST FAILED: "
                "duplicate timestamp detection"
            )

            return False

        gap_rows = [
            list(row)
            for row in rows
        ]

        for index in range(
            7,
            len(gap_rows)
        ):

            gap_rows[index][0] += (
                TIMEFRAME_MS
            )

        gap_analysis = (
            analyze_ohlcv_series(
                gap_rows
            )
        )

        if (
            gap_analysis[
                "missing_intervals"
            ]
            <= 0
        ):

            print(
                "SELF TEST FAILED: "
                "missing interval detection"
            )

            print(
                f"DETAIL: {gap_analysis}"
            )

            return False

        nonmono_rows = [
            list(row)
            for row in rows
        ]

        (
            nonmono_rows[7][0],
            nonmono_rows[8][0],
        ) = (
            nonmono_rows[8][0],
            nonmono_rows[7][0],
        )

        nonmono_analysis = (
            analyze_ohlcv_series(
                nonmono_rows
            )
        )

        if not nonmono_analysis[
            "non_monotonic"
        ]:

            print(
                "SELF TEST FAILED: "
                "non-monotonic detection"
            )

            print(
                f"DETAIL: {nonmono_analysis}"
            )

            return False

        future_rows = [
            list(row)
            for row in rows
        ]

        future_rows[-1][0] = (
            now_ms()
            + (
                10
                * TIMEFRAME_MS
            )
        )

        future_analysis = (
            analyze_ohlcv_series(
                future_rows
            )
        )

        if (
            future_analysis[
                "future_timestamps"
            ]
            == 0
        ):

            print(
                "SELF TEST FAILED: "
                "future timestamp detection"
            )

            print(
                f"DETAIL: {future_analysis}"
            )

            return False

        invalid_rows = [
            list(row)
            for row in rows
        ]

        invalid_rows[0][2] = 50.0
        invalid_rows[0][3] = 90.0

        invalid_analysis = (
            analyze_ohlcv_series(
                invalid_rows
            )
        )

        if (
            invalid_analysis[
                "invalid_count"
            ]
            == 0
        ):

            print(
                "SELF TEST FAILED: "
                "invalid OHLC detection"
            )

            print(
                f"DETAIL: {invalid_analysis}"
            )

            return False

        print(
            "SELF TEST : PASS"
        )

        return True

    except Exception as exc:

        print(
            "SELF TEST FAILED: "
            "exception"
        )

        print(
            f"DETAIL: "
            f"{type(exc).__name__}: {exc}"
        )

        return False


# ============================================================
# EVIDENCE NORMALIZATION
# ============================================================

def normalize_asset_evidence(
    asset: dict[str, Any],
) -> dict[str, Any]:

    return {
        "asset": asset.get(
            "asset"
        ),
        "status": asset.get(
            "status"
        ),
        "symbols": list(
            asset.get(
                "symbols",
                [],
            )
            or []
        ),
        "selected_symbol": asset.get(
            "selected_symbol"
        ),
        "raw_count": asset.get(
            "raw_count",
            0,
        ),
        "valid_count": asset.get(
            "valid_count",
            0,
        ),
        "invalid_count": asset.get(
            "invalid_count",
            0,
        ),
        "duplicate_timestamps": asset.get(
            "duplicate_timestamps",
            0,
        ),
        "non_monotonic": asset.get(
            "non_monotonic",
            False,
        ),
        "exact_interval_count": asset.get(
            "exact_interval_count",
            0,
        ),
        "invalid_interval_count": asset.get(
            "invalid_interval_count",
            0,
        ),
        "missing_intervals": asset.get(
            "missing_intervals",
            0,
        ),
        "future_timestamps": asset.get(
            "future_timestamps",
            0,
        ),
        "latest_timestamp": asset.get(
            "latest_timestamp"
        ),
        "latest_age_seconds": asset.get(
            "latest_age_seconds"
        ),
        "latest_is_current_interval": asset.get(
            "latest_is_current_interval"
        ),
        "latest_candle_complete": asset.get(
            "latest_candle_complete"
        ),
        "structural_valid": asset.get(
            "structural_valid",
            False,
        ),
        "continuity_valid": asset.get(
            "continuity_valid",
            False,
        ),
        "freshness_valid": asset.get(
            "freshness_valid",
            False,
        ),
        "error": asset.get(
            "error"
        ),
    }


def normalize_provider_evidence(
    result: dict[str, Any],
) -> dict[str, Any]:

    normalized_assets = {}

    for asset in EXPECTED_ASSETS:

        normalized_assets[
            asset
        ] = normalize_asset_evidence(
            result.get(
                "assets",
                {},
            ).get(
                asset,
                {
                    "asset": asset,
                    "status": "NOT_PROBED",
                },
            )
        )

    return {
        "provider": str(
            result.get(
                "provider"
            )
            or ""
        ).upper(),

        "status": result.get(
            "status"
        ),

        "metadata_loaded": bool(
            result.get(
                "metadata_loaded",
                False,
            )
        ),

        "fetch_ohlcv_supported": bool(
            result.get(
                "fetch_ohlcv_supported",
                False,
            )
        ),

        "market_coverage": (
            f"{result.get('market_coverage', 0)}/"
            f"{len(EXPECTED_ASSETS)}"
        ),

        "qualified_assets": (
            f"{result.get('qualified_assets', 0)}/"
            f"{len(EXPECTED_ASSETS)}"
        ),

        "qualified_asset_count": result.get(
            "qualified_assets",
            0,
        ),

        "market_coverage_count": result.get(
            "market_coverage",
            0,
        ),

        "latency_ms": result.get(
            "latency_ms"
        ),

        "fatal_error": result.get(
            "fatal_error"
        ),

        "assets": normalized_assets,
    }


# ============================================================
# EVIDENCE ARTIFACT
# ============================================================

def build_evidence_artifact(
    results: list[dict[str, Any]],
) -> dict[str, Any]:

    normalized_providers = [
        normalize_provider_evidence(
            result
        )
        for result in results
    ]

    return {
        # ----------------------------------------------------
        # CONTRACT IDENTITY
        # ----------------------------------------------------
        #
        # IMPORTANT:
        # `engine` identifies the evidence artifact contract.
        #
        # `source_engine` identifies the producer that generated
        # this evidence.
        # ----------------------------------------------------

        "engine": EVIDENCE_CONTRACT_VERSION,

        "source_engine": ENGINE_VERSION,

        "evidence_contract": (
            EVIDENCE_CONTRACT_VERSION
        ),

        # ----------------------------------------------------
        # RUN METADATA
        # ----------------------------------------------------

        "run_utc": now_iso(),

        "timeframe": TIMEFRAME,

        "timeframe_ms": TIMEFRAME_MS,

        "lookback": OHLCV_LIMIT,

        "minimum_candles": MIN_CANDLES,

        "freshness_grace_seconds": (
            FRESHNESS_GRACE_SECONDS
        ),

        "mode": (
            "PUBLIC / READ ONLY"
        ),

        # ----------------------------------------------------
        # SAFETY
        # ----------------------------------------------------

        "safety": {
            "database_writes": False,
            "api_keys": False,
            "private_endpoints": False,
            "orders": False,
            "synthetic_production_data": False,
            "interpolation": False,
            "forward_fill": False,
            "back_fill": False,
            "provider_blending": False,
            "provider_mixing": False,
            "automatic_canonical_selection": False,
        },

        # ----------------------------------------------------
        # UNIVERSE
        # ----------------------------------------------------

        "expected_assets": list(
            EXPECTED_ASSETS
        ),

        "expected_asset_count": len(
            EXPECTED_ASSETS
        ),

        "quote_preference": list(
            QUOTE_PREFERENCE
        ),

        # ----------------------------------------------------
        # PROVIDERS
        # ----------------------------------------------------

        "providers": normalized_providers,

        "provider_count": len(
            normalized_providers
        ),

        # ----------------------------------------------------
        # DECISION STATUS
        # ----------------------------------------------------

        "canonical_selection": (
            "DEFERRED"
        ),

        "failover_selection": (
            "DEFERRED"
        ),

        "selection_authority": (
            "PROVIDER_SELECTION_PROBE"
        ),
    }


# ============================================================
# ATOMIC JSON EXPORT
# ============================================================

def export_evidence_artifact(
    artifact: dict[str, Any],
    output_path: str,
) -> str:

    output_path = os.path.abspath(
        output_path
    )

    directory = os.path.dirname(
        output_path
    )

    if directory:

        os.makedirs(
            directory,
            exist_ok=True,
        )

    temp_path = (
        output_path
        + ".tmp"
    )

    with open(
        temp_path,
        "w",
        encoding="utf-8",
    ) as handle:

        json.dump(
            artifact,
            handle,
            ensure_ascii=False,
            indent=2,
            sort_keys=False,
        )

        handle.write(
            "\n"
        )

    os.replace(
        temp_path,
        output_path,
    )

    return output_path


# ============================================================
# CLI
# ============================================================

def parse_args():

    parser = argparse.ArgumentParser(
        description=(
            "ARUNDA PUBLIC MARKET DATA "
            "PROVIDER QUALIFICATION PROBE v0.3"
        )
    )

    parser.add_argument(
        "--json-out",
        default=(
            "arunda_public_market_data_"
            "qualification_evidence_v0.3.json"
        ),
        help=(
            "Evidence JSON output path."
        ),
    )

    return parser.parse_args()


# ============================================================
# FINAL DECISION REPORT
# ============================================================

def print_final_report(
    results: list[dict[str, Any]],
) -> int:

    fully_qualified = [
        result
        for result in results
        if result[
            "status"
        ]
        == "FULLY_QUALIFIED"
    ]

    reachable = [
        result
        for result in results
        if result[
            "metadata_loaded"
        ] is True
    ]

    print()
    print()
    print("=" * 100)
    print("QUALIFICATION FINAL REPORT")
    print("=" * 100)

    for result in results:

        print(
            f"{result['provider'].upper():<10} | "
            f"{result['status']:<30} | "
            f"MARKET="
            f"{result['market_coverage']:>2}/15 | "
            f"QUALIFIED="
            f"{result['qualified_assets']:>2}/15 | "
            f"LATENCY="
            f"{result['latency_ms']} ms"
        )

    print("=" * 100)

    print(
        "SAFETY CONTRACT"
    )

    print("-" * 100)

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
        "Orders                : NONE"
    )

    print(
        "Synthetic production  : NONE"
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
        "Failover selection    : DEFERRED"
    )

    print("-" * 100)

    if fully_qualified:

        print()
        print(
            "QUALIFICATION RESULT : PASS"
        )

        print()
        print(
            "FULLY QUALIFIED PROVIDERS:"
        )

        for result in fully_qualified:

            print(
                f"  - "
                f"{result['provider'].upper()}"
            )

        print()
        print(
            "IMPORTANT:"
        )

        print(
            "Qualification PASS does NOT automatically "
            "select canonical/failover."
        )

        print(
            "Provider selection remains a separate "
            "architecture decision based on evidence."
        )

        print()
        print(
            "NEXT STAGE:"
        )

        print(
            "Provider Selection Probe will consume "
            "the exported evidence artifact."
        )

        print(
            "No blending."
        )

        print(
            "No simultaneous market-data mixing."
        )

        print("=" * 100)

        return 0

    if reachable:

        print()
        print(
            "QUALIFICATION RESULT : PARTIAL"
        )

        print(
            "Providers are reachable, but no provider "
            "passed the complete forensic contract."
        )

        print(
            "CANONICAL : DEFERRED"
        )

        print(
            "FAILOVER  : DEFERRED"
        )

        print(
            "NO BLENDING PERFORMED."
        )

        print("=" * 100)

        return 2

    print()
    print(
        "QUALIFICATION RESULT : FAIL"
    )

    print(
        "No provider successfully reached "
        "public market metadata."
    )

    print(
        "CANONICAL : DEFERRED"
    )

    print(
        "FAILOVER  : DEFERRED"
    )

    print("=" * 100)

    return 1


# ============================================================
# MAIN
# ============================================================

def main() -> int:

    args = parse_args()

    print()
    print("=" * 100)

    print(
        "ARUNDA PUBLIC MARKET DATA"
    )

    print(
        "PROVIDER QUALIFICATION PROBE v0.3"
    )

    print("=" * 100)

    print(
        f"Engine          : "
        f"{ENGINE_VERSION}"
    )

    print(
        f"Evidence        : "
        f"{EVIDENCE_CONTRACT_VERSION}"
    )

    print(
        f"Run UTC         : "
        f"{now_iso()}"
    )

    print(
        f"Timeframe       : "
        f"{TIMEFRAME}"
    )

    print(
        f"Lookback        : "
        f"{OHLCV_LIMIT}"
    )

    print(
        f"Minimum candles : "
        f"{MIN_CANDLES}"
    )

    print(
        "Mode            : "
        "PUBLIC / READ ONLY"
    )

    print(
        "API KEY         : "
        "NONE"
    )

    print(
        "DB WRITE        : "
        "NONE"
    )

    print(
        "BLENDING        : "
        "FORBIDDEN"
    )

    print(
        "CANONICAL       : "
        "DEFERRED"
    )

    print(
        f"JSON OUT        : "
        f"{os.path.abspath(args.json_out)}"
    )

    print("=" * 100)

    # --------------------------------------------------------
    # SELF TEST
    # --------------------------------------------------------

    if not self_test():

        print()
        print(
            "PROBE ABORTED:"
        )

        print(
            "Internal self-test failed. "
            "No provider was evaluated."
        )

        return 1

    # --------------------------------------------------------
    # CCXT
    # --------------------------------------------------------

    try:

        ccxt_module = load_ccxt()

    except Exception as exc:

        print()
        print(
            f"CCXT ERROR : "
            f"{repr(exc)}"
        )

        return 1

    print()
    print(
        f"CCXT VERSION : "
        f"{getattr(ccxt_module, '__version__', 'UNKNOWN')}"
    )

    # --------------------------------------------------------
    # PROVIDER LIST
    # --------------------------------------------------------

    print()
    print(
        "QUALIFICATION PROVIDERS:"
    )

    for provider in PROVIDERS:

        print(
            f"  - {provider.upper()}"
        )

    # --------------------------------------------------------
    # INDEPENDENT PROVIDER PROBES
    # --------------------------------------------------------

    results = []

    for provider in PROVIDERS:

        print()
        print("=" * 100)

        print(
            f"PROBING PROVIDER: "
            f"{provider.upper()}"
        )

        print("=" * 100)

        try:

            result = probe_provider(
                ccxt_module,
                provider,
            )

        except Exception as exc:

            result = {
                "provider": provider,
                "metadata_loaded": False,
                "fetch_ohlcv_supported": False,
                "status": (
                    "UNEXPECTED_PROVIDER_ERROR"
                ),
                "market_coverage": 0,
                "qualified_assets": 0,
                "assets": {},
                "fatal_error": repr(exc),
                "latency_ms": None,
            }

        results.append(
            result
        )

        print_provider_summary(
            result
        )

    # --------------------------------------------------------
    # FORENSIC DETAIL
    # --------------------------------------------------------

    print_forensic_details(
        results
    )

    # --------------------------------------------------------
    # EVIDENCE EXPORT
    # --------------------------------------------------------

    print()
    print("=" * 100)
    print(
        "EVIDENCE ARTIFACT EXPORT"
    )
    print("=" * 100)

    try:

        evidence = (
            build_evidence_artifact(
                results
            )
        )

        output_path = (
            export_evidence_artifact(
                evidence,
                args.json_out,
            )
        )

        print(
            f"EVIDENCE CONTRACT : "
            f"{EVIDENCE_CONTRACT_VERSION}"
        )

        print(
            f"SOURCE ENGINE     : "
            f"{ENGINE_VERSION}"
        )

        print(
            f"JSON ARTIFACT     : "
            f"{output_path}"
        )

        print(
            "PRODUCTION CHANGE : NONE"
        )

    except Exception as exc:

        print()
        print(
            "EVIDENCE EXPORT : FAILED"
        )

        print(
            f"DETAIL: "
            f"{type(exc).__name__}: {exc}"
        )

        return 1

    # --------------------------------------------------------
    # FINAL
    # --------------------------------------------------------

    return print_final_report(
        results
    )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )