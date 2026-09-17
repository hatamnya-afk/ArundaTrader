"""
ARUNDA MARKET HISTORY INGESTION INTEGRITY DIAGNOSTIC v0.1

Purpose
-------
Read-only diagnostic for identifying the origin of temporal anomalies
inside market_history.

This diagnostic investigates:

- Duplicate timestamp rows
- Same symbol + same timestamp collisions
- Source-level collisions
- Name-level collisions
- Price conflicts at identical timestamps
- Volume conflicts at identical timestamps
- Static-price runs
- Repeated identical records
- Temporal gaps
- Ingestion pattern consistency
- Evidence of duplicated ingestion batches

Forbidden
---------
- Database writes
- Database repair
- Row deletion
- Row merging
- Identity repair
- History modification
- Technical calculation
- Signal generation
- Prediction
- Opportunity generation
- Risk calculation
- Execution

Storage
-------
ANALYSIS ONLY / MEMORY ONLY
"""

from __future__ import annotations

import math
import sqlite3
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from statistics import median
from typing import Any, Dict, List, Optional, Tuple


# =============================================================================
# CONTRACT
# =============================================================================

ENGINE_NAME = "ARUNDA_MARKET_HISTORY_INGESTION_INTEGRITY_DIAGNOSTIC"
ENGINE_VERSION = "INGESTION_INTEGRITY_v0.1"

DATABASE_FILE = "arunda.db"
HISTORY_TABLE = "market_history"

# Expected approximate collection interval.
EXPECTED_INTERVAL_SECONDS = 60.0

# A gap larger than this multiple of the expected interval is considered
# diagnostically abnormal.
ABNORMAL_GAP_MULTIPLIER = 2.5

# Static run diagnostic threshold.
STATIC_RUN_THRESHOLD = 20

# Maximum number of representative samples printed.
SAMPLE_LIMIT = 20


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


def parse_timestamp(value: Any) -> Optional[datetime]:
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

    except ValueError:
        return None


def timestamp_seconds(
    value: Any,
) -> Optional[float]:

    dt = parse_timestamp(value)

    if dt is None:
        return None

    return dt.timestamp()


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
) -> List[str]:

    if not table_exists(
        conn,
        HISTORY_TABLE,
    ):
        raise RuntimeError(
            f"Required table '{HISTORY_TABLE}' does not exist."
        )

    columns = get_columns(
        conn,
        HISTORY_TABLE,
    )

    required = {
        "timestamp",
        "symbol",
        "price",
        "volume_24h",
    }

    missing = sorted(
        required - set(columns)
    )

    if missing:
        raise RuntimeError(
            "market_history schema missing required columns: "
            + ", ".join(missing)
        )

    return columns


# =============================================================================
# RECORD MODEL
# =============================================================================

@dataclass
class HistoryRow:

    row_id: Optional[int]
    timestamp: Any
    symbol: str
    name: Optional[str]
    source: Optional[str]
    price: Optional[float]
    volume_24h: Optional[float]

    def identity_key(
        self,
    ) -> Tuple[Any, ...]:

        return (
            self.timestamp,
            self.symbol,
            self.name,
            self.source,
        )

    def timestamp_symbol_key(
        self,
    ) -> Tuple[Any, ...]:

        return (
            self.timestamp,
            self.symbol,
        )

    def timestamp_symbol_source_key(
        self,
    ) -> Tuple[Any, ...]:

        return (
            self.timestamp,
            self.symbol,
            self.source,
        )


@dataclass
class AssetTemporalStats:

    symbol: str
    name: Optional[str]

    rows: int
    unique_timestamps: int

    first_timestamp: Optional[str]
    last_timestamp: Optional[str]

    price_valid_rows: int
    unique_prices: int
    price_changes: int

    duplicate_timestamp_rows: int
    exact_duplicate_rows: int

    same_timestamp_price_conflicts: int
    same_timestamp_volume_conflicts: int

    median_interval_seconds: Optional[float]
    minimum_interval_seconds: Optional[float]
    maximum_interval_seconds: Optional[float]

    abnormal_gaps: int

    longest_static_run: int

    classification: str

    def to_dict(
        self,
    ) -> Dict[str, Any]:

        return asdict(self)


# =============================================================================
# LOAD DATA
# =============================================================================

def load_rows(
    conn: sqlite3.Connection,
    columns: List[str],
) -> List[HistoryRow]:

    optional_name = (
        "name"
        if "name" in columns
        else "NULL AS name"
    )

    optional_source = (
        "source"
        if "source" in columns
        else "NULL AS source"
    )

    id_column = (
        "rowid"
    )

    query = f"""
        SELECT
            {id_column},
            timestamp,
            symbol,
            {optional_name},
            {optional_source},
            price,
            volume_24h
        FROM {HISTORY_TABLE}
        WHERE symbol IS NOT NULL
        ORDER BY timestamp ASC, rowid ASC
    """

    rows = conn.execute(
        query
    ).fetchall()

    result: List[HistoryRow] = []

    for row in rows:

        result.append(
            HistoryRow(
                row_id=row[0],
                timestamp=row[1],
                symbol=str(row[2]),
                name=row[3],
                source=row[4],
                price=safe_float(row[5]),
                volume_24h=safe_float(row[6]),
            )
        )

    return result


# =============================================================================
# BASIC COUNTS
# =============================================================================

def count_distinct_assets(
    rows: List[HistoryRow],
) -> int:

    return len(
        {
            row.symbol
            for row in rows
        }
    )


def count_distinct_sources(
    rows: List[HistoryRow],
) -> int:

    sources = {
        row.source
        for row in rows
        if row.source is not None
    }

    return len(sources)


# =============================================================================
# DUPLICATE ANALYSIS
# =============================================================================

def analyze_exact_duplicates(
    rows: List[HistoryRow],
) -> Tuple[int, Dict[Tuple[Any, ...], int]]:

    groups: Dict[
        Tuple[Any, ...],
        int
    ] = defaultdict(int)

    for row in rows:

        groups[
            row.identity_key()
            + (
                row.price,
                row.volume_24h,
            )
        ] += 1

    duplicate_rows = 0

    for count in groups.values():

        if count > 1:
            duplicate_rows += count - 1

    return duplicate_rows, groups


def analyze_timestamp_symbol_duplicates(
    rows: List[HistoryRow],
) -> Dict[Tuple[Any, ...], List[HistoryRow]]:

    groups: Dict[
        Tuple[Any, ...],
        List[HistoryRow]
    ] = defaultdict(list)

    for row in rows:

        groups[
            row.timestamp_symbol_key()
        ].append(row)

    return {
        key: value
        for key, value in groups.items()
        if len(value) > 1
    }


def analyze_source_collisions(
    rows: List[HistoryRow],
) -> Dict[Tuple[Any, ...], List[HistoryRow]]:

    groups: Dict[
        Tuple[Any, ...],
        List[HistoryRow]
    ] = defaultdict(list)

    for row in rows:

        groups[
            row.timestamp_symbol_source_key()
        ].append(row)

    return {
        key: value
        for key, value in groups.items()
        if len(value) > 1
    }


# =============================================================================
# CONFLICT ANALYSIS
# =============================================================================

def count_price_conflicts(
    groups: Dict[
        Tuple[Any, ...],
        List[HistoryRow]
    ],
) -> int:

    conflicts = 0

    for rows in groups.values():

        prices = {
            row.price
            for row in rows
            if row.price is not None
        }

        if len(prices) > 1:
            conflicts += 1

    return conflicts


def count_volume_conflicts(
    groups: Dict[
        Tuple[Any, ...],
        List[HistoryRow]
    ],
) -> int:

    conflicts = 0

    for rows in groups.values():

        volumes = {
            row.volume_24h
            for row in rows
            if row.volume_24h is not None
        }

        if len(volumes) > 1:
            conflicts += 1

    return conflicts


# =============================================================================
# STATIC RUN
# =============================================================================

def calculate_longest_static_run(
    rows: List[HistoryRow],
) -> int:

    if not rows:
        return 0

    ordered = sorted(
        rows,
        key=lambda row: (
            timestamp_seconds(row.timestamp)
            if timestamp_seconds(row.timestamp) is not None
            else float("inf")
        ),
    )

    longest = 1
    current_run = 1

    previous_price = ordered[0].price

    for row in ordered[1:]:

        if (
            row.price is not None
            and previous_price is not None
            and row.price == previous_price
        ):
            current_run += 1

        else:
            current_run = 1

        longest = max(
            longest,
            current_run,
        )

        previous_price = row.price

    return longest


# =============================================================================
# TEMPORAL INTERVALS
# =============================================================================

def calculate_intervals(
    rows: List[HistoryRow],
) -> List[float]:

    timestamps = []

    for row in rows:

        value = timestamp_seconds(
            row.timestamp
        )

        if value is not None:
            timestamps.append(value)

    timestamps = sorted(timestamps)

    intervals = []

    for index in range(
        1,
        len(timestamps),
    ):

        interval = (
            timestamps[index]
            - timestamps[index - 1]
        )

        intervals.append(
            interval
        )

    return intervals


def calculate_abnormal_gaps(
    intervals: List[float],
) -> int:

    threshold = (
        EXPECTED_INTERVAL_SECONDS
        * ABNORMAL_GAP_MULTIPLIER
    )

    return sum(
        1
        for interval in intervals
        if interval > threshold
    )


# =============================================================================
# CLASSIFICATION
# =============================================================================

def classify_asset(
    rows: List[HistoryRow],
    duplicate_timestamp_rows: int,
    exact_duplicate_rows: int,
    abnormal_gaps: int,
) -> str:

    if not rows:
        return "NO_HISTORY"

    prices = [
        row.price
        for row in rows
        if row.price is not None
    ]

    unique_prices = len(
        set(prices)
    )

    if duplicate_timestamp_rows > 0:
        return "TEMPORAL_DUPLICATE"

    if (
        unique_prices <= 1
        and len(prices) >= STATIC_RUN_THRESHOLD
    ):
        return "STATIC_PRICE"

    if exact_duplicate_rows > 0:
        return "EXACT_DUPLICATE"

    if abnormal_gaps > 0:
        return "REAL_TIME_SERIES_WITH_GAPS"

    if len(prices) > 1:
        return "REAL_TIME_SERIES"

    return "INSUFFICIENT"


# =============================================================================
# ASSET ANALYSIS
# =============================================================================

def analyze_asset(
    rows: List[HistoryRow],
) -> AssetTemporalStats:

    ordered = sorted(
        rows,
        key=lambda row: (
            timestamp_seconds(row.timestamp)
            if timestamp_seconds(row.timestamp) is not None
            else float("inf")
        ),
    )

    symbol = ordered[0].symbol

    names = {
        row.name
        for row in ordered
        if row.name is not None
    }

    name = (
        next(iter(names))
        if len(names) == 1
        else None
    )

    timestamps = [
        row.timestamp
        for row in ordered
    ]

    unique_timestamps = len(
        set(timestamps)
    )

    duplicate_timestamp_rows = (
        len(ordered)
        - unique_timestamps
    )

    prices = [
        row.price
        for row in ordered
        if row.price is not None
    ]

    unique_prices = len(
        set(prices)
    )

    price_changes = 0

    for index in range(
        1,
        len(prices),
    ):

        if prices[index] != prices[index - 1]:
            price_changes += 1

    exact_duplicate_rows, _ = (
        analyze_exact_duplicates(
            ordered
        )
    )

    timestamp_groups = defaultdict(list)

    for row in ordered:

        timestamp_groups[
            row.timestamp
        ].append(row)

    duplicate_timestamp_groups = {
        key: value
        for key, value in timestamp_groups.items()
        if len(value) > 1
    }

    same_timestamp_price_conflicts = (
        count_price_conflicts(
            duplicate_timestamp_groups
        )
    )

    same_timestamp_volume_conflicts = (
        count_volume_conflicts(
            duplicate_timestamp_groups
        )
    )

    intervals = calculate_intervals(
        ordered
    )

    positive_intervals = [
        interval
        for interval in intervals
        if interval > 0
    ]

    abnormal_gaps = calculate_abnormal_gaps(
        positive_intervals
    )

    longest_static_run = (
        calculate_longest_static_run(
            ordered
        )
    )

    classification = classify_asset(
        ordered,
        duplicate_timestamp_rows,
        exact_duplicate_rows,
        abnormal_gaps,
    )

    return AssetTemporalStats(
        symbol=symbol,
        name=name,

        rows=len(ordered),
        unique_timestamps=unique_timestamps,

        first_timestamp=(
            ordered[0].timestamp
            if ordered
            else None
        ),

        last_timestamp=(
            ordered[-1].timestamp
            if ordered
            else None
        ),

        price_valid_rows=len(prices),
        unique_prices=unique_prices,
        price_changes=price_changes,

        duplicate_timestamp_rows=(
            duplicate_timestamp_rows
        ),

        exact_duplicate_rows=(
            exact_duplicate_rows
        ),

        same_timestamp_price_conflicts=(
            same_timestamp_price_conflicts
        ),

        same_timestamp_volume_conflicts=(
            same_timestamp_volume_conflicts
        ),

        median_interval_seconds=(
            median(positive_intervals)
            if positive_intervals
            else None
        ),

        minimum_interval_seconds=(
            min(positive_intervals)
            if positive_intervals
            else None
        ),

        maximum_interval_seconds=(
            max(positive_intervals)
            if positive_intervals
            else None
        ),

        abnormal_gaps=abnormal_gaps,

        longest_static_run=longest_static_run,

        classification=classification,
    )


# =============================================================================
# GLOBAL INGESTION PATTERN ANALYSIS
# =============================================================================

def analyze_global_patterns(
    rows: List[HistoryRow],
) -> Dict[str, Any]:

    timestamp_counts = defaultdict(int)

    symbol_timestamp_counts = defaultdict(int)

    source_timestamp_counts = defaultdict(int)

    for row in rows:

        timestamp_counts[
            row.timestamp
        ] += 1

        symbol_timestamp_counts[
            (
                row.symbol,
                row.timestamp,
            )
        ] += 1

        if row.source is not None:

            source_timestamp_counts[
                (
                    row.source,
                    row.timestamp,
                )
            ] += 1

    repeated_global_timestamps = {
        key: count
        for key, count in timestamp_counts.items()
        if count > 1
    }

    repeated_symbol_timestamps = {
        key: count
        for key, count in symbol_timestamp_counts.items()
        if count > 1
    }

    repeated_source_timestamps = {
        key: count
        for key, count in source_timestamp_counts.items()
        if count > 1
    }

    return {
        "distinct_timestamps": len(
            timestamp_counts
        ),

        "timestamps_with_multiple_rows": len(
            repeated_global_timestamps
        ),

        "symbol_timestamp_collision_groups": len(
            repeated_symbol_timestamps
        ),

        "source_timestamp_collision_groups": len(
            repeated_source_timestamps
        ),
    }


# =============================================================================
# DIAGNOSTIC SUMMARY
# =============================================================================

def build_summary(
    rows: List[HistoryRow],
    asset_stats: List[AssetTemporalStats],
    columns: List[str],
) -> Dict[str, Any]:

    status_distribution = defaultdict(int)

    for stat in asset_stats:

        status_distribution[
            stat.classification
        ] += 1

    total_duplicate_timestamp_rows = sum(
        stat.duplicate_timestamp_rows
        for stat in asset_stats
    )

    total_exact_duplicate_rows = sum(
        stat.exact_duplicate_rows
        for stat in asset_stats
    )

    total_price_conflicts = sum(
        stat.same_timestamp_price_conflicts
        for stat in asset_stats
    )

    total_volume_conflicts = sum(
        stat.same_timestamp_volume_conflicts
        for stat in asset_stats
    )

    total_abnormal_gaps = sum(
        stat.abnormal_gaps
        for stat in asset_stats
    )

    longest_static_run = max(
        (
            stat.longest_static_run
            for stat in asset_stats
        ),
        default=0,
    )

    return {
        "database_rows": len(rows),

        "universe_assets": len(asset_stats),

        "distinct_sources": count_distinct_sources(
            rows
        ),

        "source_column_present": (
            "source" in columns
        ),

        "duplicate_timestamp_rows": (
            total_duplicate_timestamp_rows
        ),

        "exact_duplicate_rows": (
            total_exact_duplicate_rows
        ),

        "same_timestamp_price_conflicts": (
            total_price_conflicts
        ),

        "same_timestamp_volume_conflicts": (
            total_volume_conflicts
        ),

        "abnormal_gap_count": (
            total_abnormal_gaps
        ),

        "longest_static_run": longest_static_run,

        "status_distribution": dict(
            sorted(
                status_distribution.items()
            )
        ),

        "global_patterns": analyze_global_patterns(
            rows
        ),
    }


# =============================================================================
# REPRESENTATIVE SAMPLES
# =============================================================================

def select_samples(
    asset_stats: List[AssetTemporalStats],
) -> List[AssetTemporalStats]:

    priority = {
        "TEMPORAL_DUPLICATE": 0,
        "EXACT_DUPLICATE": 1,
        "REAL_TIME_SERIES_WITH_GAPS": 2,
        "STATIC_PRICE": 3,
        "REAL_TIME_SERIES": 4,
        "INSUFFICIENT": 5,
    }

    ordered = sorted(
        asset_stats,
        key=lambda stat: (
            priority.get(
                stat.classification,
                99,
            ),
            -stat.duplicate_timestamp_rows,
            -stat.longest_static_run,
            stat.symbol,
        ),
    )

    return ordered[
        :SAMPLE_LIMIT
    ]


# =============================================================================
# PRINT HELPERS
# =============================================================================

def print_header() -> None:

    print(
        "=" * 92
    )

    print(
        "ARUNDA MARKET HISTORY INGESTION INTEGRITY DIAGNOSTIC v0.1"
    )

    print(
        "READ-ONLY / INGESTION ANALYSIS"
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


def print_summary(
    summary: Dict[str, Any],
) -> None:

    print(
        "\n"
        + "=" * 92
    )

    print(
        "INGESTION INTEGRITY SUMMARY"
    )

    print(
        "=" * 92
    )

    print(
        f"Database Rows                    : "
        f"{summary['database_rows']}"
    )

    print(
        f"Universe Assets                  : "
        f"{summary['universe_assets']}"
    )

    print(
        f"Distinct Sources                 : "
        f"{summary['distinct_sources']}"
    )

    print(
        f"Source Column Present            : "
        f"{summary['source_column_present']}"
    )

    print(
        "\n"
        + "-" * 92
    )

    print(
        "DUPLICATION"
    )

    print(
        "-" * 92
    )

    print(
        f"Duplicate Timestamp Rows         : "
        f"{summary['duplicate_timestamp_rows']}"
    )

    print(
        f"Exact Duplicate Rows             : "
        f"{summary['exact_duplicate_rows']}"
    )

    print(
        f"Same Timestamp Price Conflicts   : "
        f"{summary['same_timestamp_price_conflicts']}"
    )

    print(
        f"Same Timestamp Volume Conflicts  : "
        f"{summary['same_timestamp_volume_conflicts']}"
    )

    print(
        "\n"
        + "-" * 92
    )

    print(
        "TEMPORAL"
    )

    print(
        "-" * 92
    )

    print(
        f"Abnormal Gap Count               : "
        f"{summary['abnormal_gap_count']}"
    )

    print(
        f"Longest Static Run               : "
        f"{summary['longest_static_run']}"
    )

    print(
        "\n"
        + "-" * 92
    )

    print(
        "STATUS DISTRIBUTION"
    )

    print(
        "-" * 92
    )

    for status, count in summary[
        "status_distribution"
    ].items():

        print(
            f"{status:<34}: {count}"
        )

    print(
        "\n"
        + "-" * 92
    )

    print(
        "GLOBAL INGESTION PATTERN"
    )

    print(
        "-" * 92
    )

    patterns = summary[
        "global_patterns"
    ]

    print(
        f"Distinct Timestamps              : "
        f"{patterns['distinct_timestamps']}"
    )

    print(
        f"Timestamps With Multiple Rows    : "
        f"{patterns['timestamps_with_multiple_rows']}"
    )

    print(
        f"Symbol + Timestamp Collisions    : "
        f"{patterns['symbol_timestamp_collision_groups']}"
    )

    print(
        f"Source + Timestamp Collisions    : "
        f"{patterns['source_timestamp_collision_groups']}"
    )


def print_asset_sample(
    stat: AssetTemporalStats,
) -> None:

    print(
        "\n"
        + "-" * 92
    )

    print(
        f"INGESTION RECORD : {stat.symbol}"
    )

    print(
        "-" * 92
    )

    print(
        f"Name                         : {stat.name}"
    )

    print(
        f"Classification               : {stat.classification}"
    )

    print(
        f"Rows                         : {stat.rows}"
    )

    print(
        f"Unique Timestamps            : {stat.unique_timestamps}"
    )

    print(
        f"Duplicate Timestamp Rows    : "
        f"{stat.duplicate_timestamp_rows}"
    )

    print(
        f"Exact Duplicate Rows         : "
        f"{stat.exact_duplicate_rows}"
    )

    print(
        f"Price Conflicts              : "
        f"{stat.same_timestamp_price_conflicts}"
    )

    print(
        f"Volume Conflicts             : "
        f"{stat.same_timestamp_volume_conflicts}"
    )

    print(
        f"Valid Price Rows             : "
        f"{stat.price_valid_rows}"
    )

    print(
        f"Unique Prices                : "
        f"{stat.unique_prices}"
    )

    print(
        f"Price Changes                : "
        f"{stat.price_changes}"
    )

    print(
        f"Longest Static Run           : "
        f"{stat.longest_static_run}"
    )

    print(
        f"First Timestamp              : "
        f"{stat.first_timestamp}"
    )

    print(
        f"Last Timestamp               : "
        f"{stat.last_timestamp}"
    )

    print(
        f"Median Interval (sec)        : "
        f"{stat.median_interval_seconds}"
    )

    print(
        f"Minimum Interval (sec)       : "
        f"{stat.minimum_interval_seconds}"
    )

    print(
        f"Maximum Interval (sec)       : "
        f"{stat.maximum_interval_seconds}"
    )

    print(
        f"Abnormal Gaps                : "
        f"{stat.abnormal_gaps}"
    )


# =============================================================================
# DETAILED COLLISION SAMPLES
# =============================================================================

def print_collision_samples(
    rows: List[HistoryRow],
) -> None:

    groups = analyze_timestamp_symbol_duplicates(
        rows
    )

    if not groups:
        print(
            "\nNo symbol + timestamp collision groups found."
        )
        return

    print(
        "\n"
        + "=" * 92
    )

    print(
        "REPRESENTATIVE COLLISION GROUPS"
    )

    print(
        "=" * 92
    )

    count = 0

    for key, group in groups.items():

        print(
            "\n"
            + "-" * 92
        )

        print(
            f"Timestamp : {key[0]}"
        )

        print(
            f"Symbol    : {key[1]}"
        )

        print(
            f"Rows      : {len(group)}"
        )

        for row in group:

            print(
                "  "
                f"rowid={row.row_id} | "
                f"name={row.name} | "
                f"source={row.source} | "
                f"price={row.price} | "
                f"volume={row.volume_24h}"
            )

        count += 1

        if count >= 10:
            break


# =============================================================================
# CONCLUSION
# =============================================================================

def determine_conclusion(
    summary: Dict[str, Any],
) -> str:

    duplicate_rows = summary[
        "duplicate_timestamp_rows"
    ]

    exact_duplicates = summary[
        "exact_duplicate_rows"
    ]

    price_conflicts = summary[
        "same_timestamp_price_conflicts"
    ]

    static_run = summary[
        "longest_static_run"
    ]

    if price_conflicts > 0:

        return (
            "INGESTION CONFLICT DETECTED: "
            "multiple records for the same symbol and timestamp "
            "contain different prices."
        )

    if duplicate_rows > 0:

        return (
            "TEMPORAL DUPLICATION DETECTED: "
            "multiple rows share the same symbol and timestamp. "
            "Further upstream/source analysis is required."
        )

    if exact_duplicates > 0:

        return (
            "EXACT DUPLICATION DETECTED: "
            "identical historical rows appear to have been ingested "
            "more than once."
        )

    if static_run >= STATIC_RUN_THRESHOLD:

        return (
            "STATIC INGESTION PATTERN DETECTED: "
            "long repeated price runs exist. "
            "Upstream price freshness requires verification."
        )

    return (
        "NO DIRECT INGESTION DUPLICATION PATTERN DETECTED "
        "FROM CURRENT HISTORY FIELDS."
    )


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:

    print_header()

    conn = sqlite3.connect(
        DATABASE_FILE
    )

    try:

        columns = validate_schema(
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

        print(
            f"Detected Columns: {', '.join(columns)}"
        )

        rows = load_rows(
            conn,
            columns,
        )

        if not rows:

            print(
                "\nNo market_history rows found."
            )

            return

        # ---------------------------------------------------------------------
        # GROUP BY SYMBOL
        # ---------------------------------------------------------------------

        grouped: Dict[
            str,
            List[HistoryRow]
        ] = defaultdict(list)

        for row in rows:
            grouped[
                row.symbol
            ].append(row)

        asset_stats = []

        for symbol, asset_rows in sorted(
            grouped.items()
        ):

            try:

                stat = analyze_asset(
                    asset_rows
                )

                asset_stats.append(
                    stat
                )

            except Exception as exc:

                print(
                    f"[ASSET DIAGNOSTIC ERROR] "
                    f"{symbol}: {exc}"
                )

        summary = build_summary(
            rows,
            asset_stats,
            columns,
        )

        print_summary(
            summary
        )

        # ---------------------------------------------------------------------
        # REPRESENTATIVE SAMPLES
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

        samples = select_samples(
            asset_stats
        )

        for stat in samples:

            print_asset_sample(
                stat
            )

        # ---------------------------------------------------------------------
        # COLLISION DETAILS
        # ---------------------------------------------------------------------

        print_collision_samples(
            rows
        )

        # ---------------------------------------------------------------------
        # CONCLUSION
        # ---------------------------------------------------------------------

        conclusion = determine_conclusion(
            summary
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
            f"Universe Assets             : "
            f"{summary['universe_assets']}"
        )

        print(
            f"Duplicate Timestamp Rows    : "
            f"{summary['duplicate_timestamp_rows']}"
        )

        print(
            f"Exact Duplicate Rows        : "
            f"{summary['exact_duplicate_rows']}"
        )

        print(
            f"Price Conflict Groups       : "
            f"{summary['same_timestamp_price_conflicts']}"
        )

        print(
            f"Volume Conflict Groups      : "
            f"{summary['same_timestamp_volume_conflicts']}"
        )

        print(
            f"Abnormal Gaps               : "
            f"{summary['abnormal_gap_count']}"
        )

        print(
            f"Longest Static Run          : "
            f"{summary['longest_static_run']}"
        )

        print(
            "\nConclusion                  : "
            + conclusion
        )

        print(
            "\nTechnical calculations      : NOT PERFORMED"
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
            "Ingestion Repair            : NONE"
        )

        print(
            "\nNO DATABASE OR ENGINE MODIFICATIONS WERE PERFORMED."
        )

        print(
            "=" * 92
        )

        print(
            "ARUNDA MARKET HISTORY INGESTION "
            "INTEGRITY DIAGNOSTIC v0.1 COMPLETE"
        )

    finally:

        conn.close()


if __name__ == "__main__":
    main()