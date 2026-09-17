"""
ARUNDA SNAPSHOT INDICATOR VALIDATION v0.1
==========================================

Purpose
-------
Validate the temporal meaning of indicators calculated from
CoinMarketCap snapshot history.

IMPORTANT
---------
READ ONLY.
NO INSERT
NO UPDATE
NO DELETE
NO ALTER
NO CREATE

Rules
-----
- No synthetic OHLC
- No interpolation
- No forward fill
- No back fill
- No temporal repair
- No trading signal
- No trading decision
- No database mutation

This validator does NOT judge profitability.
It determines whether indicators are:
    1. structurally calculable
    2. temporally interpretable
    3. safe to pass to the next layer

Supported snapshot indicators:
    RSI
    EMA
    MACD
    Bollinger Bands
    Volatility

Explicitly unsupported:
    ATR
    ADX

Reason:
Snapshot history contains price observations but does not provide
genuine OHLC candles.
"""

from __future__ import annotations

import math
import sqlite3
import statistics
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH = Path(r"C:\Users\ASUS\ArundaTrader\arunda.db")

HISTORY_LIMIT = 150
MIN_POINTS = 60

# Expected CMC snapshot cadence observed in the existing dataset.
EXPECTED_INTERVAL_MINUTES = 5.0

# These are validation thresholds only.
# They DO NOT repair or reject database rows.
SOFT_GAP_MINUTES = 15.0
HARD_GAP_MINUTES = 60.0
SEVERE_GAP_MINUTES = 180.0

RSI_PERIOD = 14
EMA_FAST = 12
EMA_SLOW = 26
MACD_SIGNAL = 9
BB_PERIOD = 20
BB_STD = 2.0


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class SnapshotPoint:
    timestamp: datetime
    price: float


@dataclass
class TemporalStats:
    points: int
    coverage_hours: float
    median_gap_minutes: Optional[float]
    mean_gap_minutes: Optional[float]
    max_gap_minutes: Optional[float]
    gaps_over_15: int
    gaps_over_60: int
    gaps_over_180: int
    usable_continuous: bool


@dataclass
class IndicatorValidation:
    name: str
    calculable: bool
    temporal_status: str
    interpretation: str
    reason: str


# =============================================================================
# DATABASE
# =============================================================================

def connect_read_only() -> sqlite3.Connection:
    """
    Open SQLite database in true read-only URI mode.
    """

    db_uri = f"file:{DB_PATH.as_posix()}?mode=ro"

    connection = sqlite3.connect(
        db_uri,
        uri=True,
        timeout=10,
    )

    connection.row_factory = sqlite3.Row

    return connection


# =============================================================================
# SCHEMA DISCOVERY
# =============================================================================

def get_columns(
    connection: sqlite3.Connection,
    table_name: str,
) -> list[str]:

    rows = connection.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row["name"] for row in rows]


def resolve_column(
    columns: list[str],
    candidates: list[str],
) -> Optional[str]:

    normalized = {
        column.lower(): column
        for column in columns
    }

    for candidate in candidates:
        if candidate.lower() in normalized:
            return normalized[candidate.lower()]

    return None


# =============================================================================
# SNAPSHOT TABLE RESOLUTION
# =============================================================================

def resolve_market_data_schema(
    connection: sqlite3.Connection,
) -> tuple[str, str, str]:
    """
    Resolve:
        table
        symbol column
        timestamp column
        price column
    """

    tables = connection.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
        """
    ).fetchall()

    candidates = [
        "market_data",
        "market_records",
        "market_history",
    ]

    table_name = None

    available_tables = {
        row["name"].lower(): row["name"]
        for row in tables
    }

    for candidate in candidates:
        if candidate.lower() in available_tables:
            table_name = available_tables[candidate.lower()]
            break

    if table_name is None:
        raise RuntimeError(
            "Could not locate a compatible market-data table."
        )

    columns = get_columns(connection, table_name)

    symbol_column = resolve_column(
        columns,
        [
            "symbol",
            "asset",
            "coin",
        ],
    )

    timestamp_column = resolve_column(
        columns,
        [
            "timestamp",
            "time",
            "datetime",
            "created_at",
            "observed_at",
        ],
    )

    price_column = resolve_column(
        columns,
        [
            "price",
            "close",
            "last_price",
            "current_price",
        ],
    )

    if not symbol_column:
        raise RuntimeError(
            f"Symbol column not found in {table_name}."
        )

    if not timestamp_column:
        raise RuntimeError(
            f"Timestamp column not found in {table_name}."
        )

    if not price_column:
        raise RuntimeError(
            f"Price column not found in {table_name}."
        )

    return (
        table_name,
        symbol_column,
        timestamp_column,
        price_column,
    )


# =============================================================================
# TIMESTAMP PARSING
# =============================================================================

def parse_timestamp(value) -> datetime:

    if value is None:
        raise ValueError("NULL timestamp")

    text = str(value).strip()

    if not text:
        raise ValueError("EMPTY timestamp")

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    dt = datetime.fromisoformat(text)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


# =============================================================================
# PRICE PARSING
# =============================================================================

def parse_price(value) -> float:

    price = float(value)

    if not math.isfinite(price):
        raise ValueError("Non-finite price")

    if price <= 0:
        raise ValueError("Non-positive price")

    return price


# =============================================================================
# SNAPSHOT LOADING
# =============================================================================

def load_symbols(
    connection: sqlite3.Connection,
    table: str,
    symbol_column: str,
) -> list[str]:

    query = f"""
        SELECT DISTINCT {symbol_column}
        FROM {table}
        WHERE {symbol_column} IS NOT NULL
        ORDER BY {symbol_column}
    """

    rows = connection.execute(query).fetchall()

    return [
        str(row[0]).strip().upper()
        for row in rows
        if row[0]
    ]


def load_snapshot_history(
    connection: sqlite3.Connection,
    table: str,
    symbol_column: str,
    timestamp_column: str,
    price_column: str,
    symbol: str,
) -> tuple[list[SnapshotPoint], int]:

    query = f"""
        SELECT
            {timestamp_column} AS ts,
            {price_column} AS price
        FROM {table}
        WHERE UPPER({symbol_column}) = ?
        ORDER BY {timestamp_column} DESC
        LIMIT ?
    """

    rows = connection.execute(
        query,
        (symbol, HISTORY_LIMIT),
    ).fetchall()

    points: list[SnapshotPoint] = []
    invalid = 0

    for row in rows:

        try:
            timestamp = parse_timestamp(row["ts"])
            price = parse_price(row["price"])

            points.append(
                SnapshotPoint(
                    timestamp=timestamp,
                    price=price,
                )
            )

        except Exception:
            invalid += 1

    points.sort(
        key=lambda point: point.timestamp
    )

    return points, invalid


# =============================================================================
# TEMPORAL ANALYSIS
# =============================================================================

def calculate_temporal_stats(
    points: list[SnapshotPoint],
) -> TemporalStats:

    if len(points) < 2:

        return TemporalStats(
            points=len(points),
            coverage_hours=0.0,
            median_gap_minutes=None,
            mean_gap_minutes=None,
            max_gap_minutes=None,
            gaps_over_15=0,
            gaps_over_60=0,
            gaps_over_180=0,
            usable_continuous=False,
        )

    gaps = []

    for previous, current in zip(
        points,
        points[1:],
    ):

        delta_minutes = (
            current.timestamp - previous.timestamp
        ).total_seconds() / 60.0

        if delta_minutes >= 0:
            gaps.append(delta_minutes)

    if not gaps:

        return TemporalStats(
            points=len(points),
            coverage_hours=0.0,
            median_gap_minutes=None,
            mean_gap_minutes=None,
            max_gap_minutes=None,
            gaps_over_15=0,
            gaps_over_60=0,
            gaps_over_180=0,
            usable_continuous=False,
        )

    coverage_hours = (
        points[-1].timestamp - points[0].timestamp
    ).total_seconds() / 3600.0

    median_gap = statistics.median(gaps)
    mean_gap = statistics.mean(gaps)
    max_gap = max(gaps)

    gaps_over_15 = sum(
        gap > SOFT_GAP_MINUTES
        for gap in gaps
    )

    gaps_over_60 = sum(
        gap >= HARD_GAP_MINUTES
        for gap in gaps
    )

    gaps_over_180 = sum(
        gap >= SEVERE_GAP_MINUTES
        for gap in gaps
    )

    usable_continuous = (
        len(points) >= MIN_POINTS
        and gaps_over_60 == 0
    )

    return TemporalStats(
        points=len(points),
        coverage_hours=coverage_hours,
        median_gap_minutes=median_gap,
        mean_gap_minutes=mean_gap,
        max_gap_minutes=max_gap,
        gaps_over_15=gaps_over_15,
        gaps_over_60=gaps_over_60,
        gaps_over_180=gaps_over_180,
        usable_continuous=usable_continuous,
    )


# =============================================================================
# INDICATOR MATHEMATICAL CHECKS
# =============================================================================

def can_calculate_rsi(points: list[SnapshotPoint]) -> bool:
    return len(points) >= RSI_PERIOD + 1


def can_calculate_ema(
    points: list[SnapshotPoint],
    period: int,
) -> bool:

    return len(points) >= period


def can_calculate_macd(
    points: list[SnapshotPoint],
) -> bool:

    required = EMA_SLOW + MACD_SIGNAL

    return len(points) >= required


def can_calculate_bollinger(
    points: list[SnapshotPoint],
) -> bool:

    return len(points) >= BB_PERIOD


def calculate_rsi(
    prices: list[float],
    period: int = RSI_PERIOD,
) -> Optional[float]:

    if len(prices) < period + 1:
        return None

    changes = [
        prices[index] - prices[index - 1]
        for index in range(1, len(prices))
    ]

    gains = [
        max(change, 0.0)
        for change in changes
    ]

    losses = [
        max(-change, 0.0)
        for change in changes
    ]

    average_gain = (
        sum(gains[:period]) / period
    )

    average_loss = (
        sum(losses[:period]) / period
    )

    for index in range(period, len(changes)):

        average_gain = (
            (average_gain * (period - 1))
            + gains[index]
        ) / period

        average_loss = (
            (average_loss * (period - 1))
            + losses[index]
        ) / period

    if average_loss == 0:

        if average_gain == 0:
            return 50.0

        return 100.0

    relative_strength = (
        average_gain / average_loss
    )

    return (
        100.0
        - (
            100.0
            / (1.0 + relative_strength)
        )
    )


def calculate_ema(
    prices: list[float],
    period: int,
) -> Optional[float]:

    if len(prices) < period:
        return None

    multiplier = 2.0 / (period + 1)

    ema = sum(
        prices[:period]
    ) / period

    for price in prices[period:]:

        ema = (
            (price - ema) * multiplier
        ) + ema

    return ema


# =============================================================================
# INDICATOR VALIDATION
# =============================================================================

def validate_indicator(
    name: str,
    calculable: bool,
    temporal: TemporalStats,
) -> IndicatorValidation:

    if not calculable:

        return IndicatorValidation(
            name=name,
            calculable=False,
            temporal_status="NOT_CALCULABLE",
            interpretation="BLOCKED",
            reason="Insufficient snapshot observations.",
        )

    if temporal.gaps_over_60 > 0:

        return IndicatorValidation(
            name=name,
            calculable=True,
            temporal_status="IRREGULAR_TIME",
            interpretation="COUNT_BASED_ONLY",
            reason=(
                "Indicator can be mathematically calculated, "
                "but the underlying observations contain large "
                "temporal gaps. Periods represent observations, "
                "not guaranteed fixed-duration intervals."
            ),
        )

    if temporal.gaps_over_15 > 0:

        return IndicatorValidation(
            name=name,
            calculable=True,
            temporal_status="MILDLY_IRREGULAR",
            interpretation="CONDITIONALLY_USABLE",
            reason=(
                "Indicator is calculable, but snapshot cadence "
                "is not perfectly regular."
            ),
        )

    return IndicatorValidation(
        name=name,
        calculable=True,
        temporal_status="REGULAR",
        interpretation="TEMPORALLY_INTERPRETABLE",
        reason=(
            "Snapshot spacing is sufficiently regular "
            "for observation-based interpretation."
        ),
    )


# =============================================================================
# SYMBOL REPORT
# =============================================================================

def analyze_symbol(
    symbol: str,
    points: list[SnapshotPoint],
    invalid_points: int,
) -> None:

    temporal = calculate_temporal_stats(points)

    prices = [
        point.price
        for point in points
    ]

    rsi = calculate_rsi(prices)

    ema_fast = calculate_ema(
        prices,
        EMA_FAST,
    )

    ema_slow = calculate_ema(
        prices,
        EMA_SLOW,
    )

    macd_calculable = (
        ema_fast is not None
        and ema_slow is not None
        and len(points) >= EMA_SLOW + MACD_SIGNAL
    )

    validations = [

        validate_indicator(
            "RSI",
            can_calculate_rsi(points),
            temporal,
        ),

        validate_indicator(
            "EMA",
            can_calculate_ema(
                points,
                EMA_SLOW,
            ),
            temporal,
        ),

        validate_indicator(
            "MACD",
            macd_calculable,
            temporal,
        ),

        validate_indicator(
            "BOLLINGER",
            can_calculate_bollinger(points),
            temporal,
        ),

        validate_indicator(
            "VOLATILITY",
            len(points) >= 2,
            temporal,
        ),

        IndicatorValidation(
            name="ATR",
            calculable=False,
            temporal_status="UNSUPPORTED",
            interpretation="BLOCKED",
            reason=(
                "No genuine OHLC candle structure. "
                "ATR must not be manufactured from snapshots."
            ),
        ),

        IndicatorValidation(
            name="ADX",
            calculable=False,
            temporal_status="UNSUPPORTED",
            interpretation="BLOCKED",
            reason=(
                "ADX requires genuine OHLC directional movement. "
                "Snapshot data does not provide it."
            ),
        ),
    ]

    print()
    print("-" * 90)
    print(f"SYMBOL : {symbol}")
    print("-" * 90)

    print(
        f"Points                  : {temporal.points}"
    )

    print(
        f"Invalid points          : {invalid_points}"
    )

    print(
        f"Coverage                : "
        f"{temporal.coverage_hours:.2f} h"
    )

    if temporal.median_gap_minutes is not None:

        print(
            f"Median gap             : "
            f"{temporal.median_gap_minutes:.2f} min"
        )

        print(
            f"Mean gap               : "
            f"{temporal.mean_gap_minutes:.2f} min"
        )

        print(
            f"Maximum gap            : "
            f"{temporal.max_gap_minutes:.2f} min"
        )

    print(
        f"Gaps > 15 min          : "
        f"{temporal.gaps_over_15}"
    )

    print(
        f"Gaps >= 60 min         : "
        f"{temporal.gaps_over_60}"
    )

    print(
        f"Gaps >= 180 min        : "
        f"{temporal.gaps_over_180}"
    )

    print()
    print(
        f"RSI value              : "
        f"{rsi:.4f}"
        if rsi is not None
        else "RSI value              : N/A"
    )

    print(
        f"EMA-{EMA_FAST}                 : "
        f"{ema_fast:.8f}"
        if ema_fast is not None
        else f"EMA-{EMA_FAST}                 : N/A"
    )

    print(
        f"EMA-{EMA_SLOW}                 : "
        f"{ema_slow:.8f}"
        if ema_slow is not None
        else f"EMA-{EMA_SLOW}                 : N/A"
    )

    print()
    print(
        "INDICATOR VALIDATION"
    )

    for validation in validations:

        print(
            f"{validation.name:<12} | "
            f"CALCULABLE={str(validation.calculable):<5} | "
            f"TEMPORAL={validation.temporal_status:<20} | "
            f"INTERPRETATION={validation.interpretation}"
        )

        print(
            f"             | {validation.reason}"
        )


# =============================================================================
# CROSS-SYMBOL SUMMARY
# =============================================================================

def print_cross_symbol_summary(
    results: list[dict],
) -> None:

    print()
    print("=" * 90)
    print("CROSS-SYMBOL INDICATOR VALIDATION SUMMARY")
    print("=" * 90)

    print(
        f"{'SYMBOL':<8}"
        f"{'POINTS':>8}"
        f"{'MEDIAN':>12}"
        f"{'MAX GAP':>12}"
        f"{'RSI':>10}"
        f"{'EMA':>10}"
        f"{'MACD':>10}"
        f"{'BB':>10}"
        f"{'ATR':>12}"
        f"{'ADX':>12}"
    )

    print("-" * 90)

    for result in results:

        print(
            f"{result['symbol']:<8}"
            f"{result['points']:>8}"
            f"{result['median_gap']:>12.2f}"
            f"{result['max_gap']:>12.2f}"
            f"{result['rsi']:<10}"
            f"{result['ema']:<10}"
            f"{result['macd']:<10}"
            f"{result['bb']:<10}"
            f"{'BLOCKED':<12}"
            f"{'BLOCKED':<12}"
        )


# =============================================================================
# FINAL VERDICT
# =============================================================================

def final_verdict(
    results: list[dict],
) -> None:

    total = len(results)

    if total == 0:

        print()
        print(
            "TEMPORAL INDICATOR STATUS : NO DATA"
        )

        return

    irregular = sum(
        result["gaps_over_60"] > 0
        for result in results
    )

    insufficient = sum(
        result["points"] < MIN_POINTS
        for result in results
    )

    print()
    print("=" * 90)
    print("INDICATOR VALIDATION VERDICT")
    print("=" * 90)

    print(
        f"Symbols evaluated          : {total}"
    )

    print(
        f"Symbols < {MIN_POINTS} points     : "
        f"{insufficient}"
    )

    print(
        f"Symbols with >=60m gaps    : "
        f"{irregular}"
    )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This validator does NOT determine profitability."
    )

    print(
        "It does NOT repair timestamps."
    )

    print(
        "It does NOT manufacture candles."
    )

    print(
        "It does NOT create signals."
    )

    print()

    if irregular > 0:

        print(
            "SNAPSHOT INDICATOR STATUS : "
            "COUNT-BASED / TEMPORALLY IRREGULAR"
        )

        print(
            "Reason:"
        )

        print(
            "Indicators such as RSI/EMA/MACD/Bollinger "
            "can be mathematically calculated, but their "
            "periods represent observations rather than "
            "guaranteed fixed-time intervals."
        )

    else:

        print(
            "SNAPSHOT INDICATOR STATUS : "
            "TEMPORALLY ACCEPTABLE"
        )

    print()
    print(
        "ATR STATUS : BLOCKED"
    )

    print(
        "ADX STATUS : BLOCKED"
    )

    print()
    print(
        "NEXT STEP : "
        "DECIDE WHICH SNAPSHOT FEATURES ARE CONTRACT-SAFE "
        "FOR THE NEXT ARUNDA LAYER."
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    started = datetime.now(timezone.utc)

    print("=" * 90)
    print(
        "             ARUNDA SNAPSHOT INDICATOR VALIDATION v0.1"
    )
    print("=" * 90)

    print(
        f"Database       : {DB_PATH}"
    )

    print(
        "Provider       : COINMARKETCAP"
    )

    print(
        f"History        : LAST {HISTORY_LIMIT} SNAPSHOTS"
    )

    print(
        f"Minimum        : {MIN_POINTS} SNAPSHOTS"
    )

    print(
        "Mode           : READ ONLY VALIDATION"
    )

    print(
        "Synthetic OHLC : FORBIDDEN"
    )

    print(
        "Interpolation  : FORBIDDEN"
    )

    print(
        "Forward Fill   : FORBIDDEN"
    )

    print(
        "Back Fill      : FORBIDDEN"
    )

    print("=" * 90)

    if not DB_PATH.exists():

        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    connection = connect_read_only()

    try:

        print()
        print(
            "Checking market-data schema..."
        )

        (
            table,
            symbol_column,
            timestamp_column,
            price_column,
        ) = resolve_market_data_schema(connection)

        print(
            f"Table          : {table}"
        )

        print(
            f"Symbol column  : {symbol_column}"
        )

        print(
            f"Timestamp      : {timestamp_column}"
        )

        print(
            f"Price column   : {price_column}"
        )

        symbols = load_symbols(
            connection,
            table,
            symbol_column,
        )

        # Restrict validation to the established Arunda core universe.
        core_symbols = [
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

        symbols = [
            symbol
            for symbol in core_symbols
            if symbol in symbols
        ]

        print()
        print(
            f"Symbols evaluated : {len(symbols)}"
        )

        results = []

        for symbol in symbols:

            points, invalid = load_snapshot_history(
                connection,
                table,
                symbol_column,
                timestamp_column,
                price_column,
                symbol,
            )

            temporal = calculate_temporal_stats(
                points
            )

            prices = [
                point.price
                for point in points
            ]

            rsi = calculate_rsi(prices)

            ema = calculate_ema(
                prices,
                EMA_SLOW,
            )

            macd = (
                "YES"
                if (
                    ema is not None
                    and len(points)
                    >= EMA_SLOW + MACD_SIGNAL
                )
                else "NO"
            )

            bb = (
                "YES"
                if can_calculate_bollinger(points)
                else "NO"
            )

            analyze_symbol(
                symbol,
                points,
                invalid,
            )

            results.append(
                {
                    "symbol": symbol,
                    "points": temporal.points,
                    "median_gap": (
                        temporal.median_gap_minutes
                        if temporal.median_gap_minutes is not None
                        else 0.0
                    ),
                    "max_gap": (
                        temporal.max_gap_minutes
                        if temporal.max_gap_minutes is not None
                        else 0.0
                    ),
                    "rsi": (
                        f"{rsi:.2f}"
                        if rsi is not None
                        else "NO"
                    ),
                    "ema": (
                        "YES"
                        if ema is not None
                        else "NO"
                    ),
                    "macd": macd,
                    "bb": bb,
                    "gaps_over_60": temporal.gaps_over_60,
                }
            )

        print_cross_symbol_summary(
            results
        )

        final_verdict(
            results
        )

    finally:

        connection.close()

    elapsed = (
        datetime.now(timezone.utc)
        - started
    ).total_seconds()

    print()
    print("=" * 90)
    print(
        "ARUNDA SNAPSHOT INDICATOR VALIDATION COMPLETE"
    )
    print(
        f"Run Time      : {elapsed:.2f} sec"
    )
    print(
        "Database Write : NONE"
    )
    print("=" * 90)


if __name__ == "__main__":
    main()