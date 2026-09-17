"""
ARUNDA TECHNICAL ENGINE v0.5

Purpose
-------
Read-only technical market analysis engine.

Responsibilities
----------------
- Read market_history
- Calculate technical state in memory
- Trend
- Momentum
- Volatility
- Volume
- Market Structure
- Regime
- Data Quality

Forbidden
---------
- Database writes
- Signal generation
- Prediction
- Opportunity generation
- Risk calculation
- Execution
- Identity repair

Storage
-------
MEMORY ONLY
"""

from __future__ import annotations

import math
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from statistics import mean, pstdev
from typing import Any, Dict, List, Optional


# =============================================================================
# CONTRACT
# =============================================================================

ENGINE_NAME = "ARUNDA_TECHNICAL_ENGINE"
ENGINE_VERSION = "TECHNICAL_v0.5"

DATABASE_FILE = "arunda.db"
HISTORY_TABLE = "market_history"

# Momentum / Return
MIN_RETURN_5_POINTS = 6
MIN_RETURN_10_POINTS = 11
MIN_RETURN_20_POINTS = 21

# Trend
MIN_SMA_20_POINTS = 20
MIN_EMA_20_POINTS = 20
MIN_SMA_50_POINTS = 50
MIN_EMA_50_POINTS = 50

# RSI / Volatility
MIN_RSI_14_POINTS = 15
MIN_VOLATILITY_20_POINTS = 21

# Volume
MIN_VOLUME_SMA_20_POINTS = 20

# Market Structure
MIN_STRUCTURE_20_POINTS = 20


# =============================================================================
# UTILITY
# =============================================================================

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    try:
        number = float(value)

        if not math.isfinite(number):
            return None

        return number

    except (TypeError, ValueError):
        return None


def is_valid_price(value: Any) -> bool:
    number = safe_float(value)

    return number is not None and number > 0


# =============================================================================
# DATABASE READ HELPERS
# =============================================================================

def table_exists(
    conn: sqlite3.Connection,
    table_name: str,
) -> bool:

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = ?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(
    conn: sqlite3.Connection,
    table_name: str,
) -> List[str]:

    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row[1] for row in rows]


def validate_history_schema(
    conn: sqlite3.Connection,
) -> None:

    required = {
        "timestamp",
        "symbol",
        "price",
        "volume_24h",
    }

    if not table_exists(conn, HISTORY_TABLE):
        raise RuntimeError(
            f"Required table '{HISTORY_TABLE}' does not exist."
        )

    columns = set(
        get_columns(
            conn,
            HISTORY_TABLE,
        )
    )

    missing = sorted(
        required - columns
    )

    if missing:
        raise RuntimeError(
            "market_history schema missing required columns: "
            + ", ".join(missing)
        )


# =============================================================================
# MARKET HISTORY LOADING
# =============================================================================

def load_history(
    conn: sqlite3.Connection,
    symbol: str,
) -> List[Dict[str, Any]]:

    rows = conn.execute(
        """
        SELECT
            timestamp,
            symbol,
            name,
            price,
            volume_24h
        FROM market_history
        WHERE symbol = ?
          AND price IS NOT NULL
          AND price > 0
        ORDER BY timestamp ASC
        """,
        (symbol,),
    ).fetchall()

    result: List[Dict[str, Any]] = []

    for row in rows:

        price = safe_float(row[3])
        volume = safe_float(row[4])

        if price is None or price <= 0:
            continue

        result.append(
            {
                "timestamp": row[0],
                "symbol": row[1],
                "name": row[2],
                "price": price,
                "volume_24h": volume,
            }
        )

    return result


def get_symbols(
    conn: sqlite3.Connection,
) -> List[str]:

    rows = conn.execute(
        """
        SELECT DISTINCT symbol
        FROM market_history
        WHERE symbol IS NOT NULL
        ORDER BY symbol
        """
    ).fetchall()

    return [
        row[0]
        for row in rows
    ]


# =============================================================================
# BASIC SERIES
# =============================================================================

def prices_from_history(
    history: List[Dict[str, Any]],
) -> List[float]:

    return [
        row["price"]
        for row in history
        if is_valid_price(row["price"])
    ]


def volumes_from_history(
    history: List[Dict[str, Any]],
) -> List[Optional[float]]:

    return [
        safe_float(
            row.get("volume_24h")
        )
        for row in history
    ]


# =============================================================================
# RETURN
# =============================================================================

def calculate_return(
    prices: List[float],
    periods: int,
) -> Optional[float]:

    if len(prices) < periods + 1:
        return None

    old_price = prices[-(periods + 1)]
    current_price = prices[-1]

    if old_price <= 0:
        return None

    return (
        current_price / old_price
    ) - 1.0


# =============================================================================
# SMA
# =============================================================================

def calculate_sma(
    values: List[float],
    period: int,
) -> Optional[float]:

    if len(values) < period:
        return None

    window = values[-period:]

    return mean(window)


# =============================================================================
# EMA
# =============================================================================

def calculate_ema(
    values: List[float],
    period: int,
) -> Optional[float]:

    if len(values) < period:
        return None

    seed = mean(
        values[:period]
    )

    multiplier = 2.0 / (
        period + 1.0
    )

    ema = seed

    for value in values[period:]:
        ema = (
            (value - ema)
            * multiplier
        ) + ema

    return ema


# =============================================================================
# RSI
# =============================================================================

def calculate_rsi(
    prices: List[float],
    period: int = 14,
) -> Optional[float]:

    if len(prices) < period + 1:
        return None

    changes: List[float] = []

    for index in range(
        1,
        len(prices),
    ):

        changes.append(
            prices[index]
            - prices[index - 1]
        )

    recent = changes[-period:]

    gains = [
        change
        for change in recent
        if change > 0
    ]

    losses = [
        abs(change)
        for change in recent
        if change < 0
    ]

    average_gain = (
        sum(gains) / period
    )

    average_loss = (
        sum(losses) / period
    )

    if average_loss == 0:

        if average_gain == 0:
            return 50.0

        return 100.0

    rs = (
        average_gain
        / average_loss
    )

    return 100.0 - (
        100.0
        / (1.0 + rs)
    )


# =============================================================================
# VOLATILITY
# =============================================================================

def calculate_returns_series(
    prices: List[float],
) -> List[float]:

    returns: List[float] = []

    for index in range(
        1,
        len(prices),
    ):

        previous = prices[index - 1]
        current = prices[index]

        if previous <= 0:
            continue

        returns.append(
            (current / previous)
            - 1.0
        )

    return returns


def calculate_volatility(
    prices: List[float],
    period: int = 20,
) -> Optional[float]:

    returns = calculate_returns_series(
        prices
    )

    if len(returns) < period:
        return None

    window = returns[-period:]

    return pstdev(window)


# =============================================================================
# VOLUME
# =============================================================================

def calculate_volume_sma(
    volumes: List[Optional[float]],
    period: int = 20,
) -> Optional[float]:

    valid = [
        value
        for value in volumes
        if value is not None
        and value >= 0
    ]

    if len(valid) < period:
        return None

    return mean(
        valid[-period:]
    )


def calculate_volume_ratio(
    volumes: List[Optional[float]],
    period: int = 20,
) -> Optional[float]:

    if not volumes:
        return None

    current = volumes[-1]

    if current is None or current < 0:
        return None

    average = calculate_volume_sma(
        volumes,
        period,
    )

    if average is None or average <= 0:
        return None

    return current / average


# =============================================================================
# MARKET STRUCTURE
# =============================================================================

def calculate_structure(
    prices: List[float],
    period: int = 20,
) -> Dict[str, Optional[float]]:

    if len(prices) < period:

        return {
            "high_20": None,
            "low_20": None,
            "price_position_20": None,
            "distance_from_high_20": None,
            "distance_from_low_20": None,
        }

    window = prices[-period:]

    high_value = max(window)
    low_value = min(window)
    current = prices[-1]

    price_range = (
        high_value - low_value
    )

    if price_range == 0:

        position = 0.5

    else:

        position = (
            (current - low_value)
            / price_range
        )

    distance_high = (
        (current / high_value) - 1.0
        if high_value > 0
        else None
    )

    distance_low = (
        (current / low_value) - 1.0
        if low_value > 0
        else None
    )

    return {
        "high_20": high_value,
        "low_20": low_value,
        "price_position_20": position,
        "distance_from_high_20": distance_high,
        "distance_from_low_20": distance_low,
    }


def detect_structure_state(
    prices: List[float],
) -> str:

    if len(prices) < MIN_STRUCTURE_20_POINTS:
        return "UNKNOWN"

    window = prices[
        -MIN_STRUCTURE_20_POINTS:
    ]

    midpoint = (
        MIN_STRUCTURE_20_POINTS // 2
    )

    first_half = window[:midpoint]
    second_half = window[midpoint:]

    first_high = max(first_half)
    second_high = max(second_half)

    first_low = min(first_half)
    second_low = min(second_half)

    if (
        second_high > first_high
        and second_low > first_low
    ):
        return "BULLISH_STRUCTURE"

    if (
        second_high < first_high
        and second_low < first_low
    ):
        return "BEARISH_STRUCTURE"

    return "RANGE_STRUCTURE"


# =============================================================================
# TREND STATE
# =============================================================================

def detect_trend_direction(
    prices: List[float],
    sma_20: Optional[float],
    ema_20: Optional[float],
) -> str:

    if (
        not prices
        or sma_20 is None
        or ema_20 is None
    ):
        return "UNKNOWN"

    current = prices[-1]

    above_sma = (
        current > sma_20
    )

    above_ema = (
        current > ema_20
    )

    if above_sma and above_ema:
        return "UP"

    if (
        not above_sma
        and not above_ema
    ):
        return "DOWN"

    return "SIDEWAYS"


def calculate_trend_strength(
    prices: List[float],
    sma_20: Optional[float],
    ema_20: Optional[float],
) -> Optional[float]:

    if not prices:
        return None

    if (
        sma_20 is None
        or ema_20 is None
    ):
        return None

    current = prices[-1]

    if current <= 0:
        return None

    distance_sma = (
        current - sma_20
    ) / current

    distance_ema = (
        current - ema_20
    ) / current

    return (
        abs(distance_sma)
        + abs(distance_ema)
    ) / 2.0


def detect_trend_alignment(
    sma_20: Optional[float],
    ema_20: Optional[float],
    sma_50: Optional[float],
    ema_50: Optional[float],
) -> str:

    if any(
        value is None
        for value in (
            sma_20,
            ema_20,
            sma_50,
            ema_50,
        )
    ):
        return "UNKNOWN"

    if (
        ema_20 > sma_20
        and sma_20 > sma_50
        and ema_20 > ema_50
    ):
        return "BULLISH_ALIGNMENT"

    if (
        ema_20 < sma_20
        and sma_20 < sma_50
        and ema_20 < ema_50
    ):
        return "BEARISH_ALIGNMENT"

    return "MIXED_ALIGNMENT"


# =============================================================================
# MOMENTUM STATE
# =============================================================================

def detect_momentum_state(
    return_20: Optional[float],
    rsi_14: Optional[float],
) -> str:

    if (
        return_20 is None
        and rsi_14 is None
    ):
        return "UNKNOWN"

    positive = 0
    negative = 0

    if return_20 is not None:

        if return_20 > 0:
            positive += 1

        elif return_20 < 0:
            negative += 1

    if rsi_14 is not None:

        if rsi_14 > 50:
            positive += 1

        elif rsi_14 < 50:
            negative += 1

    if positive > negative:
        return "POSITIVE"

    if negative > positive:
        return "NEGATIVE"

    return "NEUTRAL"


# =============================================================================
# VOLATILITY STATE
# =============================================================================

def detect_volatility_state(
    volatility: Optional[float],
) -> str:

    if volatility is None:
        return "UNKNOWN"

    if volatility < 0.01:
        return "LOW"

    if volatility < 0.03:
        return "NORMAL"

    if volatility < 0.06:
        return "HIGH"

    return "EXTREME"


# =============================================================================
# VOLUME STATE
# =============================================================================

def detect_volume_state(
    volume_ratio: Optional[float],
) -> str:

    if volume_ratio is None:
        return "UNKNOWN"

    if volume_ratio < 0.5:
        return "LOW"

    if volume_ratio < 1.5:
        return "NORMAL"

    if volume_ratio < 3.0:
        return "ELEVATED"

    return "EXTREME"


# =============================================================================
# REGIME
# =============================================================================

def detect_regime(
    trend_direction: str,
    trend_alignment: str,
    volatility_state: str,
    structure_state: str,
) -> str:

    if (
        trend_direction == "UNKNOWN"
        or volatility_state == "UNKNOWN"
    ):
        return "UNKNOWN"

    if volatility_state == "EXTREME":
        return "HIGH_VOLATILITY"

    if (
        trend_direction == "UP"
        and trend_alignment
        == "BULLISH_ALIGNMENT"
        and structure_state
        == "BULLISH_STRUCTURE"
    ):
        return "TRENDING_UP"

    if (
        trend_direction == "DOWN"
        and trend_alignment
        == "BEARISH_ALIGNMENT"
        and structure_state
        == "BEARISH_STRUCTURE"
    ):
        return "TRENDING_DOWN"

    if (
        structure_state
        == "RANGE_STRUCTURE"
    ):
        return "RANGING"

    if volatility_state == "LOW":
        return "LOW_VOLATILITY"

    return "TRANSITION"


# =============================================================================
# DATA QUALITY
# =============================================================================

def calculate_data_quality(
    prices: List[float],
) -> str:

    if not prices:
        return "INVALID"

    if (
        len(prices)
        < MIN_RETURN_5_POINTS
    ):
        return "INSUFFICIENT"

    if (
        len(prices)
        < MIN_VOLATILITY_20_POINTS
    ):
        return "PARTIAL"

    return "READY"


# =============================================================================
# TECHNICAL RECORD
# =============================================================================

@dataclass
class TechnicalRecord:

    symbol: str
    timestamp: str

    data_quality: str
    history_points: int

    trend: Dict[str, Any]
    momentum: Dict[str, Any]
    volatility: Dict[str, Any]
    volume: Dict[str, Any]
    structure: Dict[str, Any]
    regime: Dict[str, Any]

    engine_version: str = ENGINE_VERSION

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return asdict(self)


# =============================================================================
# SINGLE ASSET CALCULATION
# =============================================================================

def calculate_asset(
    history: List[Dict[str, Any]],
) -> TechnicalRecord:

    if not history:

        raise ValueError(
            "Cannot calculate TechnicalRecord "
            "from empty history."
        )

    symbol = history[-1]["symbol"]
    timestamp = history[-1]["timestamp"]

    prices = prices_from_history(
        history
    )

    volumes = volumes_from_history(
        history
    )

    data_quality = calculate_data_quality(
        prices
    )

    # =========================================================================
    # TREND
    # =========================================================================

    sma_20 = calculate_sma(
        prices,
        20,
    )

    ema_20 = calculate_ema(
        prices,
        20,
    )

    sma_50 = calculate_sma(
        prices,
        50,
    )

    ema_50 = calculate_ema(
        prices,
        50,
    )

    trend_direction = detect_trend_direction(
        prices,
        sma_20,
        ema_20,
    )

    trend_strength = calculate_trend_strength(
        prices,
        sma_20,
        ema_20,
    )

    trend_alignment = detect_trend_alignment(
        sma_20,
        ema_20,
        sma_50,
        ema_50,
    )

    trend = {
        "sma_20": sma_20,
        "ema_20": ema_20,
        "sma_50": sma_50,
        "ema_50": ema_50,
        "direction": trend_direction,
        "strength": trend_strength,
        "alignment": trend_alignment,
    }

    # =========================================================================
    # MOMENTUM
    # =========================================================================

    return_5 = calculate_return(
        prices,
        5,
    )

    return_10 = calculate_return(
        prices,
        10,
    )

    return_20 = calculate_return(
        prices,
        20,
    )

    rsi_14 = calculate_rsi(
        prices,
        14,
    )

    momentum_state = detect_momentum_state(
        return_20,
        rsi_14,
    )

    momentum = {
        "return_5": return_5,
        "return_10": return_10,
        "return_20": return_20,
        "rsi_14": rsi_14,
        "state": momentum_state,
    }

    # =========================================================================
    # VOLATILITY
    # =========================================================================

    volatility_20 = calculate_volatility(
        prices,
        20,
    )

    volatility_state = detect_volatility_state(
        volatility_20
    )

    volatility = {
        "volatility_20": volatility_20,
        "state": volatility_state,
    }

    # =========================================================================
    # VOLUME
    # =========================================================================

    volume_sma_20 = calculate_volume_sma(
        volumes,
        20,
    )

    volume_ratio_20 = calculate_volume_ratio(
        volumes,
        20,
    )

    volume_state = detect_volume_state(
        volume_ratio_20
    )

    volume = {
        "volume_sma_20": volume_sma_20,
        "volume_ratio_20": volume_ratio_20,
        "state": volume_state,
    }

    # =========================================================================
    # STRUCTURE
    # =========================================================================

    structure_values = calculate_structure(
        prices,
        MIN_STRUCTURE_20_POINTS,
    )

    structure_state = detect_structure_state(
        prices
    )

    structure = {
        **structure_values,
        "state": structure_state,
    }

    # =========================================================================
    # REGIME
    # =========================================================================

    regime_state = detect_regime(
        trend_direction,
        trend_alignment,
        volatility_state,
        structure_state,
    )

    regime = {
        "state": regime_state,
    }

    # =========================================================================
    # RECORD
    # =========================================================================

    return TechnicalRecord(
        symbol=symbol,
        timestamp=timestamp,
        data_quality=data_quality,
        history_points=len(prices),
        trend=trend,
        momentum=momentum,
        volatility=volatility,
        volume=volume,
        structure=structure,
        regime=regime,
    )


# =============================================================================
# MULTI ASSET CALCULATION
# =============================================================================

def calculate_all_assets(
    conn: sqlite3.Connection,
) -> List[TechnicalRecord]:

    symbols = get_symbols(
        conn
    )

    records: List[TechnicalRecord] = []

    for symbol in symbols:

        history = load_history(
            conn,
            symbol,
        )

        if not history:
            continue

        try:

            record = calculate_asset(
                history
            )

            records.append(
                record
            )

        except Exception as exc:

            print(
                f"[TECHNICAL ERROR] "
                f"{symbol}: {exc}"
            )

    return records


# =============================================================================
# SUMMARY
# =============================================================================

def summarize_records(
    records: List[TechnicalRecord],
) -> Dict[str, Any]:

    summary = {
        "total_assets": len(records),
        "ready": 0,
        "partial": 0,
        "insufficient": 0,
        "invalid": 0,
        "regimes": {},
    }

    for record in records:

        quality = record.data_quality

        if quality == "READY":
            summary["ready"] += 1

        elif quality == "PARTIAL":
            summary["partial"] += 1

        elif quality == "INSUFFICIENT":
            summary["insufficient"] += 1

        elif quality == "INVALID":
            summary["invalid"] += 1

        regime = record.regime.get(
            "state"
        )

        summary["regimes"][regime] = (
            summary["regimes"].get(
                regime,
                0,
            )
            + 1
        )

    return summary


# =============================================================================
# PRINTING
# =============================================================================

def print_record(
    record: TechnicalRecord,
) -> None:

    print(
        "\n"
        + "=" * 92
    )

    print(
        f"TECHNICAL RECORD : {record.symbol}"
    )

    print(
        "=" * 92
    )

    print(
        f"Timestamp        : {record.timestamp}"
    )

    print(
        f"History Points   : {record.history_points}"
    )

    print(
        f"Data Quality     : {record.data_quality}"
    )

    print(
        "\n[TREND]"
    )

    for key, value in record.trend.items():

        print(
            f"  {key:<20}: {value}"
        )

    print(
        "\n[MOMENTUM]"
    )

    for key, value in record.momentum.items():

        print(
            f"  {key:<20}: {value}"
        )

    print(
        "\n[VOLATILITY]"
    )

    for key, value in record.volatility.items():

        print(
            f"  {key:<20}: {value}"
        )

    print(
        "\n[VOLUME]"
    )

    for key, value in record.volume.items():

        print(
            f"  {key:<20}: {value}"
        )

    print(
        "\n[MARKET STRUCTURE]"
    )

    for key, value in record.structure.items():

        print(
            f"  {key:<20}: {value}"
        )

    print(
        "\n[REGIME]"
    )

    for key, value in record.regime.items():

        print(
            f"  {key:<20}: {value}"
        )


def print_summary(
    summary: Dict[str, Any],
) -> None:

    print(
        "\n"
        + "=" * 92
    )

    print(
        "ARUNDA TECHNICAL ENGINE v0.5"
    )

    print(
        "=" * 92
    )

    print(
        f"Engine Version : {ENGINE_VERSION}"
    )

    print(
        "Mode           : READ ONLY"
    )

    print(
        "Storage        : MEMORY ONLY"
    )

    print(
        "Database Write : DISABLED"
    )

    print(
        "\n"
        + "-" * 92
    )

    print(
        "TECHNICAL SUMMARY"
    )

    print(
        "-" * 92
    )

    print(
        f"Total Assets   : "
        f"{summary['total_assets']}"
    )

    print(
        f"READY          : "
        f"{summary['ready']}"
    )

    print(
        f"PARTIAL        : "
        f"{summary['partial']}"
    )

    print(
        f"INSUFFICIENT   : "
        f"{summary['insufficient']}"
    )

    print(
        f"INVALID        : "
        f"{summary['invalid']}"
    )

    print(
        "\nREGIMES"
    )

    for regime, count in sorted(
        summary["regimes"].items()
    ):

        print(
            f"  {str(regime):<24}: "
            f"{count}"
        )

    print(
        "\n"
        + "-" * 92
    )

    print(
        "TECHNICAL CALCULATION : COMPLETED"
    )

    print(
        "SIGNAL                 : NOT USED"
    )

    print(
        "OPPORTUNITY            : NOT USED"
    )

    print(
        "RISK                   : NOT USED"
    )

    print(
        "EXECUTION              : NOT USED"
    )

    print(
        "-" * 92
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print(
        "=" * 92
    )

    print(
        "ARUNDA TECHNICAL ENGINE v0.5"
    )

    print(
        "READ-ONLY / STRUCTURAL ANALYSIS"
    )

    print(
        "=" * 92
    )

    print(
        f"Database        : {DATABASE_FILE}"
    )

    print(
        f"History Table   : {HISTORY_TABLE}"
    )

    print(
        f"Engine Version  : {ENGINE_VERSION}"
    )

    print(
        "Database Write  : DISABLED"
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "=" * 92
    )

    conn = sqlite3.connect(
        DATABASE_FILE
    )

    try:

        validate_history_schema(
            conn
        )

        records = calculate_all_assets(
            conn
        )

        summary = summarize_records(
            records
        )

        print_summary(
            summary
        )

        # ---------------------------------------------------------------------
        # SAMPLE OUTPUT ONLY
        # No signal or trading decision is generated.
        # ---------------------------------------------------------------------

        for record in records[:5]:

            print_record(
                record
            )

        print(
            "\n"
            + "=" * 92
        )

        print(
            "ARCHITECTURAL SAFETY CHECK"
        )

        print(
            "=" * 92
        )

        print(
            "Database Modification : NONE"
        )

        print(
            "Identity Repair       : NONE"
        )

        print(
            "Signal Generation     : NONE"
        )

        print(
            "Prediction            : NONE"
        )

        print(
            "Opportunity           : NONE"
        )

        print(
            "Risk Calculation      : NONE"
        )

        print(
            "Execution             : NONE"
        )

        print(
            "=" * 92
        )

        print(
            "ARUNDA TECHNICAL ENGINE "
            "v0.5 COMPLETE"
        )

    finally:

        conn.close()


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    main()