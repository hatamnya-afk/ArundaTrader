# =============================================================================
# ARUNDA OPPORTUNITY ENGINE v0.6
# PRODUCTION KUCOIN SOURCE BOUNDARY
# DISTINCT CONTIGUOUS CONTEXT
# =============================================================================
#
# PURPOSE
# -------
# Build production opportunity candidates exclusively from:
#
#     KUCOIN_SPOT
#     1h
#     MARKET_DATA_KUCOIN_OHLCV_1H_v1.1
#     LAUNCH_TIMESTAMP >= 2026-08-31T00:00:00+00:00
#
# IMPORTANT
# ---------
# This engine:
#
#     - READ ONLY
#     - DB_WRITES = 0
#     - EXECUTION = OFF
#     - CMC = FORBIDDEN
#     - SYNTHETIC = FALSE
#     - INTERPOLATION = FALSE
#     - FILL = FALSE
#     - BACKFILL = FALSE
#     - PADDING = FALSE
#
# Duplicate persisted DB rows are NOT deleted or repaired here.
#
# Runtime context:
#
#     RAW PRODUCTION ROWS
#          ↓
#     UNIQUE TIMESTAMPS
#          ↓
#     CLOSED CANDLES
#          ↓
#     CONTIGUOUS SUFFIX
#          ↓
#     MAX 150 REAL CANDLES
#          ↓
#     OPPORTUNITY
#
# =============================================================================

from __future__ import annotations

import math
import sqlite3
from datetime import datetime, timezone
from typing import Any, Mapping


# =============================================================================
# CONSTANTS
# =============================================================================

ENGINE_VERSION = "OPPORTUNITY_v0.6"

DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

PRODUCTION_MARKET_SOURCE = "KUCOIN_SPOT"

PRODUCTION_TIMEFRAME = "1h"

PRODUCTION_MARKET_ENGINE = (
    "MARKET_DATA_KUCOIN_OHLCV_1H_v1.1"
)

PRODUCTION_LAUNCH_TIMESTAMP = (
    "2026-08-31T00:00:00+00:00"
)

EXPECTED_ASSETS = [
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

EXPECTED_ASSET_COUNT = 15

MIN_HISTORY_POINTS = 60

MAX_HISTORY_POINTS = 150

MAX_CANDIDATES = 15

MIN_OPPORTUNITY_SCORE = 10.0

MIN_CONFIDENCE = 0.55

CANDLE_SECONDS = 3600

EPSILON = 1e-12


# =============================================================================
# SAFETY DECLARATION
# =============================================================================

REAL_DATA_ONLY = True

SYNTHETIC_DATA = False

INTERPOLATION = False

FILL = False

BACKFILL = False

PADDING = False

CMC_FORBIDDEN = True

DB_WRITES = 0

EXECUTION = False


# =============================================================================
# GENERIC HELPERS
# =============================================================================

def safe_float(
    value: Any,
    default: float | None = None,
) -> float | None:

    if value is None:
        return default

    if isinstance(value, bool):
        return default

    try:
        result = float(value)
    except Exception:
        return default

    if not math.isfinite(result):
        return default

    return result


def safe_upper(
    value: Any,
) -> str:

    if value is None:
        return ""

    return str(value).strip().upper()


def parse_timestamp(
    value: Any,
) -> int:

    if value is None:
        raise RuntimeError(
            "Timestamp is None"
        )

    if isinstance(value, bool):
        raise RuntimeError(
            "Invalid boolean timestamp"
        )

    if isinstance(value, (int, float)):

        result = int(float(value))

        if result <= 0:
            raise RuntimeError(
                f"Invalid timestamp: {value!r}"
            )

        return result

    text = str(value).strip()

    if not text:
        raise RuntimeError(
            "Empty timestamp"
        )

    try:

        result = int(float(text))

        if result > 0:
            return result

    except Exception:
        pass

    normalized = text.replace(
        "Z",
        "+00:00",
    )

    parsed = datetime.fromisoformat(
        normalized
    )

    if parsed.tzinfo is None:

        parsed = parsed.replace(
            tzinfo=timezone.utc
        )

    return int(
        parsed.timestamp()
    )


def timestamp_to_iso(
    timestamp: int,
) -> str:

    return (
        datetime.fromtimestamp(
            timestamp,
            tz=timezone.utc,
        ).isoformat()
    )


def is_finite(
    value: Any,
) -> bool:

    if isinstance(value, bool):
        return False

    try:
        return math.isfinite(
            float(value)
        )
    except Exception:
        return False


# =============================================================================
# DATABASE
# =============================================================================

def connect_database() -> sqlite3.Connection:

    uri = (
        "file:"
        + DB_PATH.replace(
            "\\",
            "/",
        )
        + "?mode=ro"
    )

    conn = sqlite3.connect(
        uri,
        uri=True,
        timeout=30,
    )

    conn.execute(
        "PRAGMA busy_timeout=30000"
    )

    conn.execute(
        "PRAGMA query_only=ON"
    )

    return conn


# =============================================================================
# PRODUCTION TIMESTAMP
# =============================================================================

PRODUCTION_LAUNCH_EPOCH = parse_timestamp(
    PRODUCTION_LAUNCH_TIMESTAMP
)


# =============================================================================
# SYMBOL LOADER
# =============================================================================

def get_symbols(
    conn: sqlite3.Connection,
) -> list[str]:

    rows = conn.execute(
        """
        SELECT DISTINCT symbol
        FROM market_data
        WHERE symbol IS NOT NULL
          AND TRIM(symbol) <> ''
          AND UPPER(TRIM(source)) = ?
          AND UPPER(TRIM(timeframe)) = ?
          AND TRIM(engine_version) = ?
        ORDER BY symbol
        """,
        (
            safe_upper(
                PRODUCTION_MARKET_SOURCE
            ),
            safe_upper(
                PRODUCTION_TIMEFRAME
            ),
            PRODUCTION_MARKET_ENGINE,
        ),
    ).fetchall()

    available = {
        safe_upper(row[0])
        for row in rows
        if row[0] is not None
    }

    return [
        asset
        for asset in EXPECTED_ASSETS
        if asset in available
    ]


# =============================================================================
# PRODUCTION ROW VALIDATION
# =============================================================================

def validate_production_row(
    symbol: str,
    row: Mapping[str, Any],
) -> None:

    asset = safe_upper(
        row.get("symbol")
    )

    if asset != safe_upper(symbol):

        raise RuntimeError(
            f"{symbol}: ASSET_MISMATCH"
        )

    source = safe_upper(
        row.get("source")
    )

    if source != safe_upper(
        PRODUCTION_MARKET_SOURCE
    ):

        raise RuntimeError(
            f"{symbol}: "
            f"INVALID_SOURCE={source!r}"
        )

    timeframe = safe_upper(
        row.get("timeframe")
    )

    expected_timeframe = safe_upper(
        PRODUCTION_TIMEFRAME
    )

    if timeframe != expected_timeframe:

        raise RuntimeError(
            f"{symbol}: "
            f"INVALID_TIMEFRAME={timeframe!r}"
        )

    engine = str(
        row.get("engine_version")
        or ""
    ).strip()

    if engine != PRODUCTION_MARKET_ENGINE:

        raise RuntimeError(
            f"{symbol}: "
            f"INVALID_ENGINE={engine!r}"
        )

    timestamp = parse_timestamp(
        row.get("timestamp")
    )

    if timestamp < PRODUCTION_LAUNCH_EPOCH:

        raise RuntimeError(
            f"{symbol}: "
            f"PRE_LAUNCH_ROW={timestamp}"
        )

    open_price = safe_float(
        row.get("open")
    )

    high_price = safe_float(
        row.get("high")
    )

    low_price = safe_float(
        row.get("low")
    )

    close_price = safe_float(
        row.get("close")
    )

    volume = safe_float(
        row.get("volume")
    )

    if (
        open_price is None
        or high_price is None
        or low_price is None
        or close_price is None
        or volume is None
    ):

        raise RuntimeError(
            f"{symbol}: INVALID_OHLCV"
        )

    if (
        open_price <= 0
        or high_price <= 0
        or low_price <= 0
        or close_price <= 0
    ):

        raise RuntimeError(
            f"{symbol}: NON_POSITIVE_PRICE"
        )

    if volume < 0:

        raise RuntimeError(
            f"{symbol}: NEGATIVE_VOLUME"
        )

    if high_price < max(
        open_price,
        close_price,
    ):

        raise RuntimeError(
            f"{symbol}: INVALID_HIGH"
        )

    if low_price > min(
        open_price,
        close_price,
    ):

        raise RuntimeError(
            f"{symbol}: INVALID_LOW"
        )


# =============================================================================
# HISTORY LOADER
# =============================================================================

def get_history(
    conn: sqlite3.Connection,
    symbol: str,
    limit: int = MAX_HISTORY_POINTS,
) -> list[dict[str, Any]]:

    if limit <= 0:

        raise RuntimeError(
            "History limit must be positive"
        )

    #
    # IMPORTANT
    # -------------------------------------------------------------------------
    # DB contains duplicated persisted KuCoin rows.
    #
    # We DO NOT delete or repair them.
    #
    # We first retrieve UNIQUE production timestamps.
    #
    # Timestamp parsing is performed in Python because SQLite may contain
    # integer/real/text timestamp representations.
    # -------------------------------------------------------------------------

    timestamp_rows = conn.execute(
        """
        SELECT timestamp
        FROM market_data
        WHERE symbol = ?
          AND UPPER(TRIM(source)) = ?
          AND UPPER(TRIM(timeframe)) = ?
          AND TRIM(engine_version) = ?
          AND timestamp IS NOT NULL
        """,
        (
            symbol,
            safe_upper(
                PRODUCTION_MARKET_SOURCE
            ),
            safe_upper(
                PRODUCTION_TIMEFRAME
            ),
            PRODUCTION_MARKET_ENGINE,
        ),
    ).fetchall()

    if not timestamp_rows:

        return []

    unique_timestamps: set[int] = set()

    for row in timestamp_rows:

        try:

            timestamp = parse_timestamp(
                row[0]
            )

        except Exception:

            raise RuntimeError(
                f"{symbol}: "
                f"INVALID_DB_TIMESTAMP={row[0]!r}"
            )

        if timestamp < PRODUCTION_LAUNCH_EPOCH:
            continue

        unique_timestamps.add(
            timestamp
        )

    if not unique_timestamps:

        return []

    #
    # Newest first.
    #

    ordered_timestamps = sorted(
        unique_timestamps,
        reverse=True,
    )

    records: list[dict[str, Any]] = []

    #
    # We retrieve the newest unique production candles.
    #
    # The final contiguous suffix will be determined after this stage.
    #

    for timestamp in ordered_timestamps:

        #
        # SQLite timestamp equality can differ between numeric/text storage.
        # Therefore we retrieve candidate rows for symbol/source/timeframe/
        # engine and resolve the timestamp in Python.
        #

        candidates = conn.execute(
            """
            SELECT
                id,
                symbol,
                timestamp,
                open,
                high,
                low,
                close,
                volume,
                source,
                source_timestamp,
                timeframe,
                engine_version
            FROM market_data
            WHERE symbol = ?
              AND UPPER(TRIM(source)) = ?
              AND UPPER(TRIM(timeframe)) = ?
              AND TRIM(engine_version) = ?
            ORDER BY id DESC
            """,
            (
                symbol,
                safe_upper(
                    PRODUCTION_MARKET_SOURCE
                ),
                safe_upper(
                    PRODUCTION_TIMEFRAME
                ),
                PRODUCTION_MARKET_ENGINE,
            ),
        ).fetchall()

        selected = None

        for candidate in candidates:

            candidate_timestamp = parse_timestamp(
                candidate[2]
            )

            if candidate_timestamp == timestamp:

                selected = candidate
                break

        if selected is None:
            continue

        record = {
            "id": selected[0],
            "symbol": selected[1],
            "timestamp": parse_timestamp(
                selected[2]
            ),
            "open": selected[3],
            "high": selected[4],
            "low": selected[5],
            "close": selected[6],
            "volume": selected[7],
            "source": selected[8],
            "source_timestamp": selected[9],
            "timeframe": selected[10],
            "engine_version": selected[11],
        }

        validate_production_row(
            symbol,
            record,
        )

        records.append(
            record
        )

        #
        # We only need a bounded amount of newest production context.
        # More than MAX_HISTORY_POINTS cannot increase the usable context.
        #

        if len(records) >= limit:

            break

    records.sort(
        key=lambda item: item["timestamp"]
    )

    return records


# =============================================================================
# CONTIGUITY
# =============================================================================

def build_contiguous_suffix(
    symbol: str,
    rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:

    if not rows:
        return []

    #
    # Ensure unique timestamps defensively.
    #

    unique: dict[int, dict[str, Any]] = {}

    for row in rows:

        timestamp = parse_timestamp(
            row["timestamp"]
        )

        unique[timestamp] = row

    ordered = [
        unique[timestamp]
        for timestamp in sorted(
            unique
        )
    ]

    if not ordered:
        return []

    #
    # Current/open candle must not anchor the production context.
    #

    now_epoch = int(
        datetime.now(
            timezone.utc
        ).timestamp()
    )

    current_hour = (
        now_epoch // CANDLE_SECONDS
    ) * CANDLE_SECONDS

    closed = [
        row
        for row in ordered
        if row["timestamp"] < current_hour
    ]

    if not closed:
        return []

    #
    # Start at newest CLOSED real candle.
    #

    newest = closed[-1]

    suffix = [
        newest
    ]

    expected_timestamp = (
        newest["timestamp"]
        - CANDLE_SECONDS
    )

    for index in range(
        len(closed) - 2,
        -1,
        -1,
    ):

        row = closed[index]

        timestamp = row["timestamp"]

        if timestamp == expected_timestamp:

            suffix.append(
                row
            )

            expected_timestamp -= (
                CANDLE_SECONDS
            )

            continue

        #
        # A real gap is encountered.
        #
        # STOP.
        #
        # Never jump over it.
        # Never fill it.
        # Never backfill it.
        #

        if timestamp < expected_timestamp:

            break

        #
        # Any unexpected ordering is also a hard boundary.
        #

        break

    suffix.reverse()

    #
    # Strict maximum.
    #

    if len(suffix) > MAX_HISTORY_POINTS:

        suffix = suffix[
            -MAX_HISTORY_POINTS:
        ]

    return suffix


# =============================================================================
# CLOSED CANDLE VALIDATION
# =============================================================================

def validate_closed_candles(
    symbol: str,
    rows: list[dict[str, Any]],
) -> None:

    if not rows:

        raise RuntimeError(
            f"{symbol}: EMPTY_PRODUCTION_CONTEXT"
        )

    now_epoch = int(
        datetime.now(
            timezone.utc
        ).timestamp()
    )

    current_hour = (
        now_epoch // CANDLE_SECONDS
    ) * CANDLE_SECONDS

    for row in rows:

        timestamp = parse_timestamp(
            row["timestamp"]
        )

        if timestamp >= current_hour:

            raise RuntimeError(
                f"{symbol}: "
                f"OPEN_CANDLE_INCLUDED "
                f"timestamp={timestamp}"
            )

        if timestamp < PRODUCTION_LAUNCH_EPOCH:

            raise RuntimeError(
                f"{symbol}: PRE_LAUNCH_CONTEXT"
            )


# =============================================================================
# CONTINUITY VALIDATION
# =============================================================================

def validate_continuity(
    symbol: str,
    rows: list[dict[str, Any]],
) -> None:

    if not rows:

        raise RuntimeError(
            f"{symbol}: EMPTY_CONTEXT"
        )

    seen: set[int] = set()

    for index, row in enumerate(rows):

        timestamp = parse_timestamp(
            row["timestamp"]
        )

        if timestamp in seen:

            raise RuntimeError(
                f"{symbol}: "
                f"DUPLICATE_RUNTIME_TIMESTAMP="
                f"{timestamp}"
            )

        seen.add(
            timestamp
        )

        if index == 0:
            continue

        previous = parse_timestamp(
            rows[index - 1]["timestamp"]
        )

        current = timestamp

        delta = current - previous

        if delta != CANDLE_SECONDS:

            raise RuntimeError(
                f"{symbol}: "
                f"NON_CONTIGUOUS_PRODUCTION_CONTEXT "
                f"previous={previous} "
                f"current={current} "
                f"delta={delta}"
            )


# =============================================================================
# PRICE SERIES
# =============================================================================

def close_series(
    rows: list[dict[str, Any]],
) -> list[float]:

    result: list[float] = []

    for row in rows:

        value = safe_float(
            row["close"]
        )

        if value is None:

            raise RuntimeError(
                "Invalid close in context"
            )

        result.append(
            value
        )

    return result


# =============================================================================
# MOMENTUM
# =============================================================================

def calculate_momentum_pct(
    closes: list[float],
    periods: int,
) -> float:

    if len(closes) <= periods:

        return 0.0

    latest = closes[-1]

    previous = closes[
        -(periods + 1)
    ]

    if previous <= 0:

        return 0.0

    return (
        (latest - previous)
        / previous
    ) * 100.0


# =============================================================================
# RSI
# =============================================================================

def calculate_rsi(
    closes: list[float],
    period: int = 14,
) -> float:

    if len(closes) <= period:

        return 50.0

    gains: list[float] = []

    losses: list[float] = []

    for index in range(
        1,
        len(closes),
    ):

        delta = (
            closes[index]
            - closes[index - 1]
        )

        if delta > 0:

            gains.append(
                delta
            )

            losses.append(
                0.0
            )

        else:

            gains.append(
                0.0
            )

            losses.append(
                -delta
            )

    recent_gains = gains[
        -period:
    ]

    recent_losses = losses[
        -period:
    ]

    average_gain = (
        sum(recent_gains)
        / period
    )

    average_loss = (
        sum(recent_losses)
        / period
    )

    if average_loss <= EPSILON:

        if average_gain > EPSILON:

            return 100.0

        return 50.0

    relative_strength = (
        average_gain
        / average_loss
    )

    rsi = (
        100.0
        -
        (
            100.0
            /
            (
                1.0
                + relative_strength
            )
        )
    )

    return max(
        0.0,
        min(
            100.0,
            rsi,
        ),
    )


# =============================================================================
# OPPORTUNITY SCORE
# =============================================================================

def calculate_opportunity_score(
    momentum_1h: float,
    momentum_24h: float,
    rsi: float,
) -> float:

    momentum_component = (
        abs(momentum_1h)
        * 8.0
    )

    momentum_24h_component = (
        abs(momentum_24h)
        * 2.0
    )

    rsi_component = 0.0

    if rsi >= 70.0:

        rsi_component = min(
            10.0,
            (rsi - 70.0) * 0.5,
        )

    elif rsi <= 30.0:

        rsi_component = min(
            10.0,
            (30.0 - rsi) * 0.5,
        )

    score = (
        momentum_component
        + momentum_24h_component
        + rsi_component
    )

    return max(
        0.0,
        min(
            100.0,
            score,
        ),
    )


# =============================================================================
# DIRECTION
# =============================================================================

def determine_direction(
    momentum_1h: float,
    momentum_24h: float,
) -> str:

    if (
        momentum_1h > 0
        and momentum_24h >= 0
    ):

        return "LONG"

    if (
        momentum_1h < 0
        and momentum_24h <= 0
    ):

        return "SHORT"

    if momentum_1h > 0:

        return "LONG"

    if momentum_1h < 0:

        return "SHORT"

    return "NONE"


# =============================================================================
# CONFIDENCE
# =============================================================================

def calculate_confidence(
    score: float,
    momentum_1h: float,
    momentum_24h: float,
    rsi: float,
) -> float:

    score_component = min(
        score / 100.0,
        1.0,
    )

    momentum_component = min(
        abs(momentum_1h) / 2.0,
        1.0,
    )

    momentum_24h_component = min(
        abs(momentum_24h) / 10.0,
        1.0,
    )

    rsi_distance = abs(
        rsi - 50.0
    )

    rsi_component = min(
        rsi_distance / 50.0,
        1.0,
    )

    confidence = (
        score_component * 0.40
        +
        momentum_component * 0.30
        +
        momentum_24h_component * 0.15
        +
        rsi_component * 0.15
    )

    return max(
        0.0,
        min(
            1.0,
            confidence,
        ),
    )


# =============================================================================
# STATUS
# =============================================================================

def determine_status(
    score: float,
    confidence: float,
    direction: str,
) -> str:

    if direction not in (
        "LONG",
        "SHORT",
    ):

        return "NO_TRADE"

    if score < MIN_OPPORTUNITY_SCORE:

        return "NO_TRADE"

    if confidence < MIN_CONFIDENCE:

        return "NO_TRADE"

    return "ELIGIBLE"


# =============================================================================
# BUILD OPPORTUNITY
# =============================================================================

def build_opportunity(
    symbol: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:

    if len(rows) < MIN_HISTORY_POINTS:

        return {
            "asset": symbol,
            "status": "WAITING_HISTORY",
            "direction": "NONE",
            "score": 0.0,
            "confidence": 0.0,
            "history_points": len(rows),
            "reason": (
                "INSUFFICIENT_CONTIGUOUS_PRODUCTION_CONTEXT"
            ),
            "source": PRODUCTION_MARKET_SOURCE,
            "timeframe": PRODUCTION_TIMEFRAME,
            "engine_version": ENGINE_VERSION,
            "market_engine": PRODUCTION_MARKET_ENGINE,
            "launch_timestamp": PRODUCTION_LAUNCH_TIMESTAMP,
            "db_writes": 0,
            "execution": False,
            "synthetic": False,
            "interpolation": False,
            "fill": False,
            "backfill": False,
            "padding": False,
        }

    context = rows[
        -MAX_HISTORY_POINTS:
    ]

    validate_closed_candles(
        symbol,
        context,
    )

    validate_continuity(
        symbol,
        context,
    )

    closes = close_series(
        context
    )

    latest_close = closes[-1]

    momentum_1h = (
        calculate_momentum_pct(
            closes,
            1,
        )
    )

    momentum_24h = (
        calculate_momentum_pct(
            closes,
            24,
        )
    )

    rsi = calculate_rsi(
        closes,
        14,
    )

    score = calculate_opportunity_score(
        momentum_1h,
        momentum_24h,
        rsi,
    )

    direction = determine_direction(
        momentum_1h,
        momentum_24h,
    )

    confidence = calculate_confidence(
        score,
        momentum_1h,
        momentum_24h,
        rsi,
    )

    status = determine_status(
        score,
        confidence,
        direction,
    )

    if status == "ELIGIBLE":

        reason = (
            "PRODUCTION_KUCOIN_CONTEXT_VALID"
        )

    else:

        reason = (
            "OPPORTUNITY_THRESHOLDS_NOT_MET"
        )

    return {
        "asset": symbol,
        "status": status,
        "direction": direction,
        "score": float(score),
        "confidence": float(confidence),
        "history_points": len(context),
        "latest_timestamp": context[-1][
            "timestamp"
        ],
        "latest_timestamp_iso": timestamp_to_iso(
            context[-1]["timestamp"]
        ),
        "latest_close": float(
            latest_close
        ),
        "momentum_1h": float(
            momentum_1h
        ),
        "momentum_24h": float(
            momentum_24h
        ),
        "rsi14": float(
            rsi
        ),
        "reason": reason,
        "source": PRODUCTION_MARKET_SOURCE,
        "timeframe": PRODUCTION_TIMEFRAME,
        "engine_version": ENGINE_VERSION,
        "market_engine": PRODUCTION_MARKET_ENGINE,
        "launch_timestamp": PRODUCTION_LAUNCH_TIMESTAMP,
        "db_writes": 0,
        "execution": False,
        "synthetic": False,
        "interpolation": False,
        "fill": False,
        "backfill": False,
        "padding": False,
    }


# =============================================================================
# SNAPSHOT VALIDATION
# =============================================================================

def validate_opportunity_snapshot(
    opportunities: Mapping[
        str,
        Mapping[str, Any],
    ],
) -> None:

    expected = set(
        EXPECTED_ASSETS
    )

    actual = set(
        opportunities.keys()
    )

    missing = expected - actual

    extra = actual - expected

    if missing:

        raise RuntimeError(
            f"Opportunity snapshot missing: "
            f"{sorted(missing)}"
        )

    if extra:

        raise RuntimeError(
            f"Opportunity snapshot extra: "
            f"{sorted(extra)}"
        )

    if len(opportunities) != EXPECTED_ASSET_COUNT:

        raise RuntimeError(
            "Opportunity asset count mismatch"
        )

    for asset in EXPECTED_ASSETS:

        item = opportunities[
            asset
        ]

        if not isinstance(
            item,
            Mapping,
        ):

            raise RuntimeError(
                f"{asset}: invalid opportunity record"
            )

        if item.get("asset") != asset:

            raise RuntimeError(
                f"{asset}: asset mismatch"
            )

        source = safe_upper(
            item.get("source")
        )

        if source != safe_upper(
            PRODUCTION_MARKET_SOURCE
        ):

            raise RuntimeError(
                f"{asset}: invalid opportunity source"
            )

        timeframe = safe_upper(
            item.get("timeframe")
        )

        if timeframe != safe_upper(
            PRODUCTION_TIMEFRAME
        ):

            raise RuntimeError(
                f"{asset}: invalid timeframe"
            )

        engine = str(
            item.get("market_engine")
            or ""
        ).strip()

        if engine != PRODUCTION_MARKET_ENGINE:

            raise RuntimeError(
                f"{asset}: invalid market engine"
            )

        if item.get("db_writes") != 0:

            raise RuntimeError(
                f"{asset}: DB_WRITES != 0"
            )

        if item.get("execution") is not False:

            raise RuntimeError(
                f"{asset}: execution must be OFF"
            )

        if item.get("synthetic") is not False:

            raise RuntimeError(
                f"{asset}: synthetic data detected"
            )

        if item.get("interpolation") is not False:

            raise RuntimeError(
                f"{asset}: interpolation detected"
            )

        if item.get("fill") is not False:

            raise RuntimeError(
                f"{asset}: fill detected"
            )

        if item.get("backfill") is not False:

            raise RuntimeError(
                f"{asset}: backfill detected"
            )

        if item.get("padding") is not False:

            raise RuntimeError(
                f"{asset}: padding detected"
            )

        score = safe_float(
            item.get("score")
        )

        confidence = safe_float(
            item.get("confidence")
        )

        if score is None:

            raise RuntimeError(
                f"{asset}: invalid score"
            )

        if confidence is None:

            raise RuntimeError(
                f"{asset}: invalid confidence"
            )

        if not (
            0.0
            <= score
            <= 100.0
        ):

            raise RuntimeError(
                f"{asset}: score outside [0,100]"
            )

        if not (
            0.0
            <= confidence
            <= 1.0
        ):

            raise RuntimeError(
                f"{asset}: confidence outside [0,1]"
            )

        direction = item.get(
            "direction"
        )

        if direction not in (
            "LONG",
            "SHORT",
            "NONE",
        ):

            raise RuntimeError(
                f"{asset}: invalid direction"
            )

        status = item.get(
            "status"
        )

        if status not in (
            "ELIGIBLE",
            "NO_TRADE",
            "WAITING_HISTORY",
        ):

            raise RuntimeError(
                f"{asset}: invalid status"
            )

        history_points = item.get(
            "history_points"
        )

        if not isinstance(
            history_points,
            int,
        ):

            raise RuntimeError(
                f"{asset}: invalid history_points"
            )

        if history_points < 0:

            raise RuntimeError(
                f"{asset}: negative history_points"
            )

        if history_points > MAX_HISTORY_POINTS:

            raise RuntimeError(
                f"{asset}: "
                f"history exceeds MAX_HISTORY_POINTS"
            )


# =============================================================================
# RUNTIME
# =============================================================================

def run() -> dict[str, Any]:

    print("=" * 90)

    print(
        "ARUNDA OPPORTUNITY ENGINE v0.6"
    )

    print("=" * 90)

    print(
        f"Database              : {DB_PATH}"
    )

    print(
        "Input                 : "
        "PRODUCTION KUCOIN MARKET DATA"
    )

    print(
        f"Source                : "
        f"{PRODUCTION_MARKET_SOURCE}"
    )

    print(
        f"Timeframe             : "
        f"{PRODUCTION_TIMEFRAME}"
    )

    print(
        f"Market Engine         : "
        f"{PRODUCTION_MARKET_ENGINE}"
    )

    print(
        f"Launch Boundary       : "
        f"{PRODUCTION_LAUNCH_TIMESTAMP}"
    )

    print(
        f"Min History           : "
        f"{MIN_HISTORY_POINTS}"
    )

    print(
        f"Max History           : "
        f"{MAX_HISTORY_POINTS}"
    )

    print(
        f"Max Candidates        : "
        f"{MAX_CANDIDATES}"
    )

    print(
        f"Min Score             : "
        f"{MIN_OPPORTUNITY_SCORE}"
    )

    print(
        f"Min Confidence        : "
        f"{MIN_CONFIDENCE}"
    )

    print(
        "CMC API               : FORBIDDEN"
    )

    print(
        "Synthetic             : FALSE"
    )

    print(
        "Interpolation         : FALSE"
    )

    print(
        "Fill                  : FALSE"
    )

    print(
        "Backfill              : FALSE"
    )

    print(
        "Padding               : FALSE"
    )

    print(
        "Duplicate Repair      : NOT PERFORMED"
    )

    print(
        "Runtime Dedup         : DISTINCT TIMESTAMP"
    )

    print(
        "Context Mode          : CONTIGUOUS SUFFIX"
    )

    print(
        "DB Mode               : READ ONLY"
    )

    print(
        "DB Writes             : 0"
    )

    print(
        "Execution             : OFF"
    )

    #
    # Static safety assertions.
    #

    if DB_WRITES != 0:

        raise RuntimeError(
            "Safety violation: DB_WRITES != 0"
        )

    if EXECUTION:

        raise RuntimeError(
            "Safety violation: EXECUTION enabled"
        )

    if SYNTHETIC_DATA:

        raise RuntimeError(
            "Safety violation: synthetic enabled"
        )

    if INTERPOLATION:

        raise RuntimeError(
            "Safety violation: interpolation enabled"
        )

    if FILL:

        raise RuntimeError(
            "Safety violation: fill enabled"
        )

    if BACKFILL:

        raise RuntimeError(
            "Safety violation: backfill enabled"
        )

    if PADDING:

        raise RuntimeError(
            "Safety violation: padding enabled"
        )

    if not CMC_FORBIDDEN:

        raise RuntimeError(
            "Safety violation: CMC boundary disabled"
        )

    conn = connect_database()

    try:

        #
        # Read-only verification.
        #

        query_only = conn.execute(
            "PRAGMA query_only"
        ).fetchone()[0]

        if int(query_only) != 1:

            raise RuntimeError(
                "SQLite QUERY_ONLY is not enabled"
            )

        print()
        print(
            "Database Mode          : READ ONLY"
        )

        print(
            "SQLite QUERY_ONLY      : ON"
        )

        #
        # market_data schema.
        #

        columns = conn.execute(
            "PRAGMA table_info(market_data)"
        ).fetchall()

        if not columns:

            raise RuntimeError(
                "market_data table unavailable"
            )

        print(
            f"Production DB Columns  : "
            f"{len(columns)}"
        )

        #
        # Production symbols.
        #

        symbols = get_symbols(
            conn
        )

        print(
            f"Production Symbols     : "
            f"{len(symbols)}"
        )

        if set(symbols) != set(
            EXPECTED_ASSETS
        ):

            missing = (
                set(EXPECTED_ASSETS)
                - set(symbols)
            )

            extra = (
                set(symbols)
                - set(EXPECTED_ASSETS)
            )

            raise RuntimeError(
                "Production symbol mismatch: "
                f"missing={sorted(missing)} "
                f"extra={sorted(extra)}"
            )

        opportunities: dict[
            str,
            dict[str, Any],
        ] = {}

        print()
        print(
            "PRODUCTION OPPORTUNITY BUILD"
        )

        print("-" * 110)

        for asset in EXPECTED_ASSETS:

            raw_rows = get_history(
                conn,
                asset,
                MAX_HISTORY_POINTS,
            )

            if not raw_rows:

                raise RuntimeError(
                    f"{asset}: "
                    f"NO_PRODUCTION_KUCOIN_DATA"
                )

            #
            # Build latest CLOSED contiguous suffix.
            #

            contiguous = (
                build_contiguous_suffix(
                    asset,
                    raw_rows,
                )
            )

            if contiguous:

                validate_closed_candles(
                    asset,
                    contiguous,
                )

                validate_continuity(
                    asset,
                    contiguous,
                )

            opportunity = (
                build_opportunity(
                    asset,
                    contiguous,
                )
            )

            opportunities[
                asset
            ] = opportunity

            print(
                f"{asset:<5} | "
                f"STATUS={opportunity['status']:<15} | "
                f"DIRECTION={opportunity['direction']:<5} | "
                f"SCORE={float(opportunity['score']):>9.4f} | "
                f"CONF={float(opportunity['confidence']):.4f} | "
                f"POINTS={opportunity['history_points']:<3} | "
                f"SOURCE={opportunity['source']}"
            )

        print("-" * 110)

        #
        # Snapshot validation.
        #

        validate_opportunity_snapshot(
            opportunities
        )

        eligible = sum(
            1
            for item in opportunities.values()
            if item["status"] == "ELIGIBLE"
        )

        no_trade = sum(
            1
            for item in opportunities.values()
            if item["status"] == "NO_TRADE"
        )

        waiting_history = sum(
            1
            for item in opportunities.values()
            if item["status"]
            == "WAITING_HISTORY"
        )

        long_count = sum(
            1
            for item in opportunities.values()
            if item["direction"] == "LONG"
        )

        short_count = sum(
            1
            for item in opportunities.values()
            if item["direction"] == "SHORT"
        )

        none_count = sum(
            1
            for item in opportunities.values()
            if item["direction"] == "NONE"
        )

        total_context = sum(
            int(
                item["history_points"]
            )
            for item in opportunities.values()
        )

        minimum_context = min(
            int(
                item["history_points"]
            )
            for item in opportunities.values()
        )

        maximum_context = max(
            int(
                item["history_points"]
            )
            for item in opportunities.values()
        )

        print()
        print("=" * 90)

        print(
            "OPPORTUNITY ENGINE v0.6 RESULT"
        )

        print("=" * 90)

        print(
            f"ASSETS                = "
            f"{len(opportunities)}"
        )

        print(
            f"ELIGIBLE              = "
            f"{eligible}"
        )

        print(
            f"NO_TRADE              = "
            f"{no_trade}"
        )

        print(
            f"WAITING_HISTORY       = "
            f"{waiting_history}"
        )

        print(
            f"LONG                  = "
            f"{long_count}"
        )

        print(
            f"SHORT                 = "
            f"{short_count}"
        )

        print(
            f"NONE                  = "
            f"{none_count}"
        )

        print(
            f"CONTEXT_MIN           = "
            f"{minimum_context}"
        )

        print(
            f"CONTEXT_MAX           = "
            f"{maximum_context}"
        )

        print(
            f"CONTEXT_TOTAL         = "
            f"{total_context}"
        )

        print(
            "PRODUCTION_SOURCE     = KUCOIN_SPOT"
        )

        print(
            "TIMEFRAME             = 1h"
        )

        print(
            "DISTINCT_CONTEXT      = TRUE"
        )

        print(
            "CONTIGUOUS_CONTEXT    = TRUE"
        )

        print(
            "CLOSED_CANDLES_ONLY   = TRUE"
        )

        print(
            "LAUNCH_BOUNDARY       = ENFORCED"
        )

        print(
            "REAL_DATA_ONLY        = TRUE"
        )

        print(
            "CMC_USED              = FALSE"
        )

        print(
            "SYNTHETIC_DATA        = FALSE"
        )

        print(
            "INTERPOLATION         = FALSE"
        )

        print(
            "FILL                  = FALSE"
        )

        print(
            "BACKFILL              = FALSE"
        )

        print(
            "PADDING               = FALSE"
        )

        print(
            "DUPLICATE_REPAIR      = FALSE"
        )

        print(
            "DB_WRITES             = 0"
        )

        print(
            "EXECUTION             = OFF"
        )

        print(
            "STATUS                = "
            "OPPORTUNITY_V0.6_PASS"
        )

        print("=" * 90)

        return {
            "engine_version": ENGINE_VERSION,
            "assets": opportunities,
            "summary": {
                "assets": len(
                    opportunities
                ),
                "eligible": eligible,
                "no_trade": no_trade,
                "waiting_history": waiting_history,
                "long": long_count,
                "short": short_count,
                "none": none_count,
                "context_min": minimum_context,
                "context_max": maximum_context,
                "context_total": total_context,
            },
            "production_source": (
                PRODUCTION_MARKET_SOURCE
            ),
            "timeframe": (
                PRODUCTION_TIMEFRAME
            ),
            "market_engine": (
                PRODUCTION_MARKET_ENGINE
            ),
            "launch_timestamp": (
                PRODUCTION_LAUNCH_TIMESTAMP
            ),
            "distinct_context": True,
            "contiguous_context": True,
            "closed_candles_only": True,
            "real_data_only": True,
            "cmc_used": False,
            "synthetic": False,
            "interpolation": False,
            "fill": False,
            "backfill": False,
            "padding": False,
            "duplicate_repair": False,
            "db_writes": 0,
            "execution": False,
        }

    finally:

        conn.close()


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":

    try:

        run()

    except Exception as exc:

        print()
        print("=" * 90)

        print(
            "OPPORTUNITY ENGINE v0.6 ERROR"
        )

        print("=" * 90)

        print(
            "Type   :",
            type(exc).__name__,
        )

        print(
            "Error  :",
            str(exc),
        )

        print(
            "STATUS : "
            "OPPORTUNITY_V0.6_FAILED"
        )

        raise