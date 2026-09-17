"""
ARUNDA MARKET HISTORY TEMPORAL INTEGRITY DIAGNOSTIC v0.1

Purpose
-------
Read-only diagnostic for temporal integrity of market_history.

Responsibilities
----------------
- Inspect historical timestamps
- Inspect historical price movement
- Detect repeated snapshots
- Detect static price series
- Detect duplicate timestamps
- Measure temporal spacing
- Determine whether each asset contains a real time series

Forbidden
---------
- Database writes
- UPDATE
- INSERT
- DELETE
- ALTER
- Identity repair
- Technical calculations
- Signal generation
- Opportunity generation
- Risk calculation
- Execution

Storage
-------
READ ONLY / ANALYSIS ONLY
"""

from __future__ import annotations

import math
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median
from typing import Any, Dict, List, Optional


# =============================================================================
# CONTRACT
# =============================================================================

ENGINE_NAME = "ARUNDA_MARKET_HISTORY_TEMPORAL_INTEGRITY_DIAGNOSTIC"
ENGINE_VERSION = "TEMPORAL_INTEGRITY_v0.1"

DATABASE_FILE = "arunda.db"
HISTORY_TABLE = "market_history"

STATIC_PRICE_UNIQUE_THRESHOLD = 1
MIN_REAL_PRICE_MOVEMENTS = 1

# A gap larger than this multiple of the median interval is considered unusual.
GAP_MULTIPLIER = 3.0

# Maximum number of detailed asset records printed.
SAMPLE_LIMIT = 20


# =============================================================================
# UTILITY
# =============================================================================

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


def parse_timestamp(value: Any) -> Optional[datetime]:
    """
    Parse ISO timestamps stored in market_history.

    Supports:
    - 2026-08-17T22:13:59.662142+00:00
    - 2026-08-17T22:13:59
    - timestamps ending with Z
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt

    except (TypeError, ValueError):
        return None


def seconds_between(
    first: datetime,
    second: datetime,
) -> float:

    return (
        second - first
    ).total_seconds()


# =============================================================================
# DATABASE HELPERS
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

    return [
        row[1]
        for row in rows
    ]


def validate_schema(
    conn: sqlite3.Connection,
) -> None:

    if not table_exists(
        conn,
        HISTORY_TABLE,
    ):
        raise RuntimeError(
            f"Required table '{HISTORY_TABLE}' does not exist."
        )

    columns = set(
        get_columns(
            conn,
            HISTORY_TABLE,
        )
    )

    required = {
        "timestamp",
        "symbol",
        "price",
    }

    missing = sorted(
        required - columns
    )

    if missing:
        raise RuntimeError(
            "market_history schema missing required columns: "
            + ", ".join(missing)
        )


# =============================================================================
# ASSET HISTORY
# =============================================================================

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


def load_asset_history(
    conn: sqlite3.Connection,
    symbol: str,
) -> List[Dict[str, Any]]:

    rows = conn.execute(
        """
        SELECT
            timestamp,
            symbol,
            name,
            price
        FROM market_history
        WHERE symbol = ?
        ORDER BY timestamp ASC
        """,
        (symbol,),
    ).fetchall()

    history = []

    for row in rows:

        timestamp = row[0]
        price = safe_float(row[3])

        history.append(
            {
                "timestamp": timestamp,
                "symbol": row[1],
                "name": row[2],
                "price": price,
            }
        )

    return history


# =============================================================================
# PRICE ANALYSIS
# =============================================================================

def count_valid_prices(
    history: List[Dict[str, Any]],
) -> int:

    return sum(
        1
        for row in history
        if row["price"] is not None
        and row["price"] > 0
    )


def unique_prices(
    history: List[Dict[str, Any]],
) -> List[float]:

    values = []

    for row in history:

        price = row["price"]

        if price is None:
            continue

        if price <= 0:
            continue

        values.append(price)

    return sorted(
        set(values)
    )


def count_price_changes(
    history: List[Dict[str, Any]],
) -> int:

    previous_price = None
    changes = 0

    for row in history:

        price = row["price"]

        if price is None or price <= 0:
            continue

        if previous_price is not None:

            if price != previous_price:
                changes += 1

        previous_price = price

    return changes


def calculate_longest_static_run(
    history: List[Dict[str, Any]],
) -> int:

    longest = 0
    current_run = 0
    previous_price = None

    for row in history:

        price = row["price"]

        if price is None or price <= 0:

            current_run = 0
            previous_price = None

            continue

        if previous_price is not None:

            if price == previous_price:
                current_run += 1
            else:
                current_run = 1

        else:
            current_run = 1

        if current_run > longest:
            longest = current_run

        previous_price = price

    return longest


def calculate_price_change_ratio(
    history: List[Dict[str, Any]],
) -> Optional[float]:

    valid_prices = [
        row["price"]
        for row in history
        if row["price"] is not None
        and row["price"] > 0
    ]

    if len(valid_prices) < 2:
        return None

    first = valid_prices[0]
    last = valid_prices[-1]

    if first <= 0:
        return None

    return (
        last / first
    ) - 1.0


# =============================================================================
# TIMESTAMP ANALYSIS
# =============================================================================

def timestamp_values(
    history: List[Dict[str, Any]],
) -> List[datetime]:

    values = []

    for row in history:

        dt = parse_timestamp(
            row["timestamp"]
        )

        if dt is not None:
            values.append(dt)

    return values


def count_unique_timestamps(
    history: List[Dict[str, Any]],
) -> int:

    values = [
        row["timestamp"]
        for row in history
        if row["timestamp"] is not None
    ]

    return len(
        set(values)
    )


def count_duplicate_timestamp_rows(
    history: List[Dict[str, Any]],
) -> int:

    values = [
        row["timestamp"]
        for row in history
        if row["timestamp"] is not None
    ]

    counter = Counter(values)

    duplicates = 0

    for count in counter.values():

        if count > 1:
            duplicates += count - 1

    return duplicates


def calculate_intervals(
    history: List[Dict[str, Any]],
) -> List[float]:

    timestamps = timestamp_values(
        history
    )

    timestamps.sort()

    intervals = []

    for index in range(1, len(timestamps)):

        delta = seconds_between(
            timestamps[index - 1],
            timestamps[index],
        )

        if delta >= 0:
            intervals.append(delta)

    return intervals


def calculate_median_interval(
    intervals: List[float],
) -> Optional[float]:

    if not intervals:
        return None

    return median(
        intervals
    )


def count_zero_intervals(
    intervals: List[float],
) -> int:

    return sum(
        1
        for value in intervals
        if value == 0
    )


def calculate_abnormal_gaps(
    intervals: List[float],
) -> int:

    positive = [
        value
        for value in intervals
        if value > 0
    ]

    if len(positive) < 2:
        return 0

    typical = median(
        positive
    )

    if typical <= 0:
        return 0

    threshold = (
        typical
        * GAP_MULTIPLIER
    )

    return sum(
        1
        for value in positive
        if value > threshold
    )


# =============================================================================
# STATUS CLASSIFICATION
# =============================================================================

def classify_temporal_status(
    history_points: int,
    valid_prices: int,
    unique_price_count: int,
    price_changes: int,
    unique_timestamp_count: int,
    duplicate_timestamp_rows: int,
    median_interval: Optional[float],
) -> str:

    if history_points == 0:
        return "NO_HISTORY"

    if valid_prices < 2:
        return "INSUFFICIENT"

    if unique_price_count <= STATIC_PRICE_UNIQUE_THRESHOLD:
        return "STATIC_PRICE"

    if price_changes < MIN_REAL_PRICE_MOVEMENTS:
        return "STATIC_PRICE"

    if unique_timestamp_count < 2:
        return "INSUFFICIENT"

    if median_interval is None:
        return "INSUFFICIENT"

    if duplicate_timestamp_rows > 0:
        return "TEMPORAL_DUPLICATE"

    return "REAL_TIME_SERIES"


# =============================================================================
# ASSET DIAGNOSTIC RECORD
# =============================================================================

@dataclass
class TemporalDiagnosticRecord:

    symbol: str
    name: Optional[str]

    history_points: int
    valid_prices: int

    unique_prices: int
    price_changes: int
    longest_static_run: int

    first_price: Optional[float]
    last_price: Optional[float]

    min_price: Optional[float]
    max_price: Optional[float]

    total_price_change: Optional[float]

    first_timestamp: Optional[str]
    last_timestamp: Optional[str]

    unique_timestamps: int
    duplicate_timestamp_rows: int

    median_interval_seconds: Optional[float]
    min_interval_seconds: Optional[float]
    max_interval_seconds: Optional[float]

    zero_interval_count: int
    abnormal_gap_count: int

    status: str


# =============================================================================
# SINGLE ASSET DIAGNOSTIC
# =============================================================================

def diagnose_asset(
    history: List[Dict[str, Any]],
) -> TemporalDiagnosticRecord:

    if not history:

        raise ValueError(
            "Cannot diagnose empty history."
        )

    symbol = history[-1]["symbol"]
    name = history[-1]["name"]

    valid_price_values = [
        row["price"]
        for row in history
        if row["price"] is not None
        and row["price"] > 0
    ]

    valid_price_count = len(
        valid_price_values
    )

    unique_price_values = unique_prices(
        history
    )

    price_change_count = count_price_changes(
        history
    )

    longest_static_run = calculate_longest_static_run(
        history
    )

    total_change = calculate_price_change_ratio(
        history
    )

    timestamps = timestamp_values(
        history
    )

    timestamps.sort()

    intervals = calculate_intervals(
        history
    )

    median_interval = calculate_median_interval(
        intervals
    )

    min_interval = (
        min(intervals)
        if intervals
        else None
    )

    max_interval = (
        max(intervals)
        if intervals
        else None
    )

    unique_timestamp_count = count_unique_timestamps(
        history
    )

    duplicate_timestamp_rows = count_duplicate_timestamp_rows(
        history
    )

    zero_interval_count = count_zero_intervals(
        intervals
    )

    abnormal_gap_count = calculate_abnormal_gaps(
        intervals
    )

    status = classify_temporal_status(
        history_points=len(history),
        valid_prices=valid_price_count,
        unique_price_count=len(unique_price_values),
        price_changes=price_change_count,
        unique_timestamp_count=unique_timestamp_count,
        duplicate_timestamp_rows=duplicate_timestamp_rows,
        median_interval=median_interval,
    )

    first_timestamp = (
        timestamps[0].isoformat()
        if timestamps
        else None
    )

    last_timestamp = (
        timestamps[-1].isoformat()
        if timestamps
        else None
    )

    return TemporalDiagnosticRecord(
        symbol=symbol,
        name=name,

        history_points=len(history),
        valid_prices=valid_price_count,

        unique_prices=len(
            unique_price_values
        ),
        price_changes=price_change_count,
        longest_static_run=longest_static_run,

        first_price=(
            valid_price_values[0]
            if valid_price_values
            else None
        ),

        last_price=(
            valid_price_values[-1]
            if valid_price_values
            else None
        ),

        min_price=(
            min(valid_price_values)
            if valid_price_values
            else None
        ),

        max_price=(
            max(valid_price_values)
            if valid_price_values
            else None
        ),

        total_price_change=total_change,

        first_timestamp=first_timestamp,
        last_timestamp=last_timestamp,

        unique_timestamps=unique_timestamp_count,
        duplicate_timestamp_rows=duplicate_timestamp_rows,

        median_interval_seconds=median_interval,
        min_interval_seconds=min_interval,
        max_interval_seconds=max_interval,

        zero_interval_count=zero_interval_count,
        abnormal_gap_count=abnormal_gap_count,

        status=status,
    )


# =============================================================================
# ALL ASSETS
# =============================================================================

def diagnose_all_assets(
    conn: sqlite3.Connection,
) -> List[TemporalDiagnosticRecord]:

    symbols = get_symbols(
        conn
    )

    records = []

    for symbol in symbols:

        history = load_asset_history(
            conn,
            symbol,
        )

        if not history:
            continue

        try:

            record = diagnose_asset(
                history
            )

            records.append(
                record
            )

        except Exception as exc:

            print(
                f"[TEMPORAL ERROR] "
                f"{symbol}: {exc}"
            )

    return records


# =============================================================================
# SUMMARY
# =============================================================================

def summarize_records(
    records: List[TemporalDiagnosticRecord],
) -> Dict[str, Any]:

    summary = {

        "total_assets": len(records),

        "total_history_points": 0,

        "static_price": 0,
        "real_time_series": 0,
        "temporal_duplicate": 0,
        "insufficient": 0,
        "no_history": 0,

        "assets_with_price_movement": 0,

        "assets_with_abnormal_gaps": 0,

        "total_duplicate_timestamp_rows": 0,

        "total_zero_intervals": 0,

        "max_longest_static_run": 0,

    }

    for record in records:

        summary[
            "total_history_points"
        ] += record.history_points

        status = record.status

        if status == "STATIC_PRICE":

            summary["static_price"] += 1

        elif status == "REAL_TIME_SERIES":

            summary["real_time_series"] += 1

        elif status == "TEMPORAL_DUPLICATE":

            summary["temporal_duplicate"] += 1

        elif status == "INSUFFICIENT":

            summary["insufficient"] += 1

        elif status == "NO_HISTORY":

            summary["no_history"] += 1

        if record.price_changes > 0:

            summary[
                "assets_with_price_movement"
            ] += 1

        if record.abnormal_gap_count > 0:

            summary[
                "assets_with_abnormal_gaps"
            ] += 1

        summary[
            "total_duplicate_timestamp_rows"
        ] += record.duplicate_timestamp_rows

        summary[
            "total_zero_intervals"
        ] += record.zero_interval_count

        if (
            record.longest_static_run
            > summary["max_longest_static_run"]
        ):

            summary[
                "max_longest_static_run"
            ] = record.longest_static_run

    return summary


# =============================================================================
# PRINT ASSET RECORD
# =============================================================================

def print_record(
    record: TemporalDiagnosticRecord,
) -> None:

    print(
        "\n"
        + "-" * 92
    )

    print(
        f"TEMPORAL RECORD : {record.symbol}"
    )

    print(
        "-" * 92
    )

    print(
        f"Name                       : {record.name}"
    )

    print(
        f"Status                     : {record.status}"
    )

    print(
        f"History Points             : {record.history_points}"
    )

    print(
        f"Valid Prices               : {record.valid_prices}"
    )

    print(
        f"Unique Prices              : {record.unique_prices}"
    )

    print(
        f"Price Changes              : {record.price_changes}"
    )

    print(
        f"Longest Static Run         : {record.longest_static_run}"
    )

    print(
        f"First Price                : {record.first_price}"
    )

    print(
        f"Last Price                 : {record.last_price}"
    )

    print(
        f"Minimum Price              : {record.min_price}"
    )

    print(
        f"Maximum Price              : {record.max_price}"
    )

    print(
        f"Total Price Change        : {record.total_price_change}"
    )

    print(
        f"First Timestamp            : {record.first_timestamp}"
    )

    print(
        f"Last Timestamp             : {record.last_timestamp}"
    )

    print(
        f"Unique Timestamps          : {record.unique_timestamps}"
    )

    print(
        f"Duplicate Timestamp Rows   : {record.duplicate_timestamp_rows}"
    )

    print(
        f"Median Interval (sec)      : {record.median_interval_seconds}"
    )

    print(
        f"Minimum Interval (sec)     : {record.min_interval_seconds}"
    )

    print(
        f"Maximum Interval (sec)     : {record.max_interval_seconds}"
    )

    print(
        f"Zero Intervals             : {record.zero_interval_count}"
    )

    print(
        f"Abnormal Gaps              : {record.abnormal_gap_count}"
    )


# =============================================================================
# SUMMARY PRINT
# =============================================================================

def print_summary(
    summary: Dict[str, Any],
) -> None:

    print(
        "\n"
        + "=" * 92
    )

    print(
        "TEMPORAL INTEGRITY SUMMARY"
    )

    print(
        "=" * 92
    )

    print(
        f"Universe Assets                  : "
        f"{summary['total_assets']}"
    )

    print(
        f"Total History Points             : "
        f"{summary['total_history_points']}"
    )

    print(
        f"Assets With Price Movement       : "
        f"{summary['assets_with_price_movement']}"
    )

    print(
        "\nSTATUS DISTRIBUTION"
    )

    print(
        "-" * 92
    )

    print(
        f"REAL_TIME_SERIES                 : "
        f"{summary['real_time_series']}"
    )

    print(
        f"STATIC_PRICE                     : "
        f"{summary['static_price']}"
    )

    print(
        f"TEMPORAL_DUPLICATE               : "
        f"{summary['temporal_duplicate']}"
    )

    print(
        f"INSUFFICIENT                     : "
        f"{summary['insufficient']}"
    )

    print(
        f"NO_HISTORY                       : "
        f"{summary['no_history']}"
    )

    print(
        "\nTEMPORAL ANOMALIES"
    )

    print(
        "-" * 92
    )

    print(
        f"Assets With Abnormal Gaps        : "
        f"{summary['assets_with_abnormal_gaps']}"
    )

    print(
        f"Duplicate Timestamp Rows         : "
        f"{summary['total_duplicate_timestamp_rows']}"
    )

    print(
        f"Zero-Length Intervals             : "
        f"{summary['total_zero_intervals']}"
    )

    print(
        f"Longest Static Run                : "
        f"{summary['max_longest_static_run']}"
    )


# =============================================================================
# DIAGNOSTIC CONCLUSION
# =============================================================================

def print_conclusion(
    summary: Dict[str, Any],
) -> None:

    total = summary[
        "total_assets"
    ]

    real_series = summary[
        "real_time_series"
    ]

    static = summary[
        "static_price"
    ]

    duplicates = summary[
        "temporal_duplicate"
    ]

    if total == 0:

        conclusion = (
            "NO ASSETS AVAILABLE FOR TEMPORAL ANALYSIS."
        )

    elif static == total:

        conclusion = (
            "ALL ASSETS APPEAR TO HAVE STATIC PRICES."
        )

    elif real_series == total:

        conclusion = (
            "ALL ASSETS CONTAIN PRICE MOVEMENT "
            "AND VALID TEMPORAL SERIES."
        )

    elif real_series > 0:

        conclusion = (
            "MIXED TEMPORAL STATE: "
            "SOME ASSETS HAVE REAL PRICE MOVEMENT "
            "WHILE OTHERS REQUIRE ATTENTION."
        )

    else:

        conclusion = (
            "NO ASSET QUALIFIES AS A CLEAN "
            "REAL-TIME SERIES."
        )

    print(
        "\n"
        + "=" * 92
    )

    print(
        "DIAGNOSTIC ASSESSMENT"
    )

    print(
        "=" * 92
    )

    print(
        f"Universe Assets             : {total}"
    )

    print(
        f"REAL_TIME_SERIES            : "
        f"{real_series}"
    )

    print(
        f"STATIC_PRICE                : "
        f"{static}"
    )

    print(
        f"TEMPORAL_DUPLICATE          : "
        f"{duplicates}"
    )

    print(
        "\n"
        f"Conclusion                  : "
        f"{conclusion}"
    )

    print(
        "\n"
        "Technical calculations      : NOT PERFORMED"
    )

    print(
        "Signals                     : NOT PERFORMED"
    )

    print(
        "Opportunity                 : NOT PERFORMED"
    )

    print(
        "Risk                        : NOT PERFORMED"
    )

    print(
        "Execution                   : NOT PERFORMED"
    )

    print(
        "\n"
        + "=" * 92
    )

    print(
        "DIAGNOSTIC CONCLUSION"
    )

    print(
        "=" * 92
    )

    print(
        "Analysis Mode               : READ ONLY"
    )

    print(
        "Database Modification       : NONE"
    )

    print(
        "Technical Modification     : NONE"
    )

    print(
        "Identity Repair             : NONE"
    )

    print(
        "Historical Repair           : NONE"
    )

    print(
        "\n"
        "NO DATABASE OR ENGINE "
        "MODIFICATIONS WERE PERFORMED."
    )

    print(
        "=" * 92
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print(
        "=" * 92
    )

    print(
        "ARUNDA MARKET HISTORY TEMPORAL "
        "INTEGRITY DIAGNOSTIC v0.1"
    )

    print(
        "READ-ONLY / TEMPORAL ANALYSIS"
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
        "Mode            : READ ONLY"
    )

    print(
        "Database Write  : DISABLED"
    )

    print(
        "Storage         : ANALYSIS ONLY"
    )

    print(
        "=" * 92
    )

    conn = sqlite3.connect(
        f"file:{DATABASE_FILE}?mode=ro",
        uri=True,
    )

    try:

        validate_schema(
            conn
        )

        print(
            "\nDATABASE"
        )

        print(
            "-" * 92
        )

        print(
            "Database        : CONNECTED"
        )

        print(
            "History Table   : market_history"
        )

        print(
            "Write Mode      : READ ONLY"
        )

        records = diagnose_all_assets(
            conn
        )

        summary = summarize_records(
            records
        )

        print_summary(
            summary
        )

        # ---------------------------------------------------------------------
        # Print representative samples
        # ---------------------------------------------------------------------

        print(
            "\n"
            + "=" * 92
        )

        print(
            "REPRESENTATIVE ASSET SAMPLES"
        )

        print(
            "=" * 92
        )

        # Prefer showing one example from each important state.
        selected = []

        preferred_statuses = [
            "STATIC_PRICE",
            "REAL_TIME_SERIES",
            "TEMPORAL_DUPLICATE",
            "INSUFFICIENT",
        ]

        for status in preferred_statuses:

            for record in records:

                if record.status == status:

                    selected.append(
                        record
                    )

                    break

        # Fill remaining slots.
        for record in records:

            if len(selected) >= SAMPLE_LIMIT:
                break

            if record not in selected:
                selected.append(record)

        for record in selected[:SAMPLE_LIMIT]:

            print_record(
                record
            )

        print_conclusion(
            summary
        )

        print(
            "\n"
            + "=" * 92
        )

        print(
            "ARUNDA MARKET HISTORY TEMPORAL "
            "INTEGRITY DIAGNOSTIC v0.1 COMPLETE"
        )

        print(
            "=" * 92
        )

    finally:

        conn.close()


if __name__ == "__main__":
    main()