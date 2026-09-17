import sqlite3
import math
from datetime import datetime, timezone


# ============================================================
# ARUNDA SNAPSHOT TEMPORAL FORENSIC v0.1
# ============================================================
#
# PURPOSE
# -------
# Determine whether real CMC snapshots stored in market_data
# have sufficient temporal integrity for predictive testing.
#
# MODE
# ----
# READ ONLY
#
# NO:
#   INSERT
#   UPDATE
#   DELETE
#   ALTER
#   CREATE
#
# IMPORTANT
# ---------
# This script does NOT modify the database.
#
# It does NOT calculate trading signals.
# It does NOT modify market_data.
# It does NOT manufacture candles.
#
# It only measures the temporal structure of the existing
# CMC snapshot history.
# ============================================================


# ============================================================
# CONFIG
# ============================================================

DB = "arunda.db"

SNAPSHOT_SOURCE = "COINMARKETCAP"

TIMEFRAME = "SNAPSHOT"

SYMBOLS = [
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

LATEST_N = 150

# Gap thresholds in minutes.
GAP_SMALL_MIN = 15
GAP_MEDIUM_MIN = 60
GAP_LARGE_MIN = 180

# ============================================================
# DATABASE
# ============================================================


def connect_database():

    conn = sqlite3.connect(
        f"file:{DB}?mode=ro",
        uri=True
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# SAFE PARSING
# ============================================================


def parse_timestamp(value):

    if value is None:
        return None

    try:

        text = str(value).strip()

        if not text:
            return None

        # SQLite timestamps in this project are generally ISO8601
        # with UTC offset.
        dt = datetime.fromisoformat(
            text.replace(
                "Z",
                "+00:00"
            )
        )

        if dt.tzinfo is None:

            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except Exception:

        return None


def safe_float(value):

    try:

        if value is None:
            return None

        result = float(value)

        if not math.isfinite(result):
            return None

        return result

    except Exception:

        return None


# ============================================================
# BASIC DATABASE FINGERPRINT
# ============================================================


def database_fingerprint(conn):

    print()
    print("=" * 100)
    print("DATABASE FINGERPRINT")
    print("=" * 100)

    row = conn.execute(
        """
        SELECT
            COUNT(*) AS total_rows
        FROM market_data
        """
    ).fetchone()

    total_rows = int(
        row["total_rows"]
    )

    print(
        f"market_data total rows : {total_rows:,}"
    )

    row = conn.execute(
        """
        SELECT
            COUNT(*) AS snapshot_rows
        FROM market_data
        WHERE
            source = ?
            AND timeframe = ?
        """,
        (
            SNAPSHOT_SOURCE,
            TIMEFRAME,
        )
    ).fetchone()

    snapshot_rows = int(
        row["snapshot_rows"]
    )

    print(
        f"CMC snapshot rows      : {snapshot_rows:,}"
    )

    row = conn.execute(
        """
        SELECT
            COUNT(*) AS analysis_rows
        FROM market_data
        WHERE
            source != ?
            OR timeframe != ?
        """,
        (
            SNAPSHOT_SOURCE,
            TIMEFRAME,
        )
    ).fetchone()

    analysis_rows = int(
        row["analysis_rows"]
    )

    print(
        f"Non-snapshot rows      : {analysis_rows:,}"
    )


# ============================================================
# SYMBOL TEMPORAL ANALYSIS
# ============================================================


def analyze_symbol(
    conn,
    symbol
):

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            source_timestamp,
            close,
            volume,
            price_change_1h,
            price_change_24h
        FROM market_data
        WHERE
            symbol = ?
            AND source = ?
            AND timeframe = ?
        ORDER BY id ASC
        """,
        (
            symbol,
            SNAPSHOT_SOURCE,
            TIMEFRAME,
        )
    ).fetchall()

    total_rows = len(rows)

    parsed = []

    invalid_timestamps = 0

    for row in rows:

        dt = parse_timestamp(
            row["timestamp"]
        )

        if dt is None:

            invalid_timestamps += 1

            continue

        parsed.append(
            {
                "id": row["id"],
                "timestamp": dt,
                "source_timestamp":
                    row["source_timestamp"],
                "close":
                    safe_float(
                        row["close"]
                    ),
            }
        )

    timestamp_duplicates = 0

    timestamp_map = {}

    for item in parsed:

        key = item["timestamp"]

        timestamp_map[key] = (
            timestamp_map.get(
                key,
                0
            ) + 1
        )

    for count in timestamp_map.values():

        if count > 1:

            timestamp_duplicates += (
                count - 1
            )

    unique_timestamps = len(
        timestamp_map
    )

    # --------------------------------------------------------
    # Calculate gaps
    # --------------------------------------------------------

    gaps = []

    for i in range(
        1,
        len(parsed)
    ):

        previous = parsed[
            i - 1
        ]["timestamp"]

        current = parsed[
            i
        ]["timestamp"]

        seconds = (
            current
            - previous
        ).total_seconds()

        gaps.append(
            seconds
        )

    positive_gaps = [
        gap
        for gap in gaps
        if gap >= 0
    ]

    negative_gaps = [
        gap
        for gap in gaps
        if gap < 0
    ]

    if positive_gaps:

        sorted_gaps = sorted(
            positive_gaps
        )

        median_gap = (
            sorted_gaps[
                len(sorted_gaps) // 2
            ]
        )

        min_gap = min(
            positive_gaps
        )

        max_gap = max(
            positive_gaps
        )

        mean_gap = (
            sum(positive_gaps)
            / len(positive_gaps)
        )

    else:

        median_gap = None
        min_gap = None
        max_gap = None
        mean_gap = None

    small_gaps = 0
    medium_gaps = 0
    large_gaps = 0
    backward_gaps = len(
        negative_gaps
    )

    for gap in positive_gaps:

        minutes = gap / 60.0

        if minutes >= GAP_LARGE_MIN:

            large_gaps += 1

        elif minutes >= GAP_MEDIUM_MIN:

            medium_gaps += 1

        elif minutes > GAP_SMALL_MIN:

            small_gaps += 1

    # --------------------------------------------------------
    # Latest 150
    # --------------------------------------------------------

    latest = parsed[
        -LATEST_N:
    ]

    latest_gaps = []

    for i in range(
        1,
        len(latest)
    ):

        seconds = (
            latest[i]["timestamp"]
            - latest[i - 1]["timestamp"]
        ).total_seconds()

        latest_gaps.append(
            seconds
        )

    latest_positive = [
        gap
        for gap in latest_gaps
        if gap >= 0
    ]

    if latest_positive:

        sorted_latest = sorted(
            latest_positive
        )

        latest_median_gap = (
            sorted_latest[
                len(sorted_latest) // 2
            ]
        )

        latest_min_gap = min(
            latest_positive
        )

        latest_max_gap = max(
            latest_positive
        )

        latest_mean_gap = (
            sum(latest_positive)
            / len(latest_positive)
        )

    else:

        latest_median_gap = None
        latest_min_gap = None
        latest_max_gap = None
        latest_mean_gap = None

    # --------------------------------------------------------
    # Latest window temporal coverage
    # --------------------------------------------------------

    if len(latest) >= 2:

        latest_start = latest[
            0
        ]["timestamp"]

        latest_end = latest[
            -1
        ]["timestamp"]

        latest_span_seconds = (
            latest_end
            - latest_start
        ).total_seconds()

    else:

        latest_start = None
        latest_end = None
        latest_span_seconds = None

    # --------------------------------------------------------
    # Price availability
    # --------------------------------------------------------

    latest_prices = [
        item["close"]
        for item in latest
        if item["close"] is not None
    ]

    price_missing = (
        len(latest)
        - len(latest_prices)
    )

    # --------------------------------------------------------
    # Return summary
    # --------------------------------------------------------

    return {
        "symbol": symbol,

        "total_rows": total_rows,

        "parsed_rows": len(parsed),

        "invalid_timestamps":
            invalid_timestamps,

        "unique_timestamps":
            unique_timestamps,

        "timestamp_duplicates":
            timestamp_duplicates,

        "backward_gaps":
            backward_gaps,

        "mean_gap":
            mean_gap,

        "median_gap":
            median_gap,

        "min_gap":
            min_gap,

        "max_gap":
            max_gap,

        "small_gaps":
            small_gaps,

        "medium_gaps":
            medium_gaps,

        "large_gaps":
            large_gaps,

        "latest_count":
            len(latest),

        "latest_start":
            latest_start,

        "latest_end":
            latest_end,

        "latest_span_seconds":
            latest_span_seconds,

        "latest_mean_gap":
            latest_mean_gap,

        "latest_median_gap":
            latest_median_gap,

        "latest_min_gap":
            latest_min_gap,

        "latest_max_gap":
            latest_max_gap,

        "latest_price_missing":
            price_missing,
    }


# ============================================================
# FORMAT HELPERS
# ============================================================


def fmt_minutes(seconds):

    if seconds is None:
        return "N/A"

    return (
        f"{seconds / 60.0:.2f}"
    )


def fmt_hours(seconds):

    if seconds is None:
        return "N/A"

    return (
        f"{seconds / 3600.0:.2f}"
    )


def fmt_timestamp(dt):

    if dt is None:
        return "N/A"

    return dt.isoformat()


# ============================================================
# PRINT SYMBOL REPORT
# ============================================================


def print_symbol_report(result):

    print()
    print(
        "-" * 100
    )

    print(
        f"SYMBOL : {result['symbol']}"
    )

    print(
        "-" * 100
    )

    print(
        f"Total snapshots          : "
        f"{result['total_rows']}"
    )

    print(
        f"Parsed timestamps        : "
        f"{result['parsed_rows']}"
    )

    print(
        f"Invalid timestamps       : "
        f"{result['invalid_timestamps']}"
    )

    print(
        f"Unique timestamps        : "
        f"{result['unique_timestamps']}"
    )

    print(
        f"Duplicate timestamps     : "
        f"{result['timestamp_duplicates']}"
    )

    print(
        f"Backward gaps            : "
        f"{result['backward_gaps']}"
    )

    print()

    print(
        "FULL HISTORY GAP ANALYSIS"
    )

    print(
        f"Mean gap                 : "
        f"{fmt_minutes(result['mean_gap'])} min"
    )

    print(
        f"Median gap               : "
        f"{fmt_minutes(result['median_gap'])} min"
    )

    print(
        f"Minimum gap              : "
        f"{fmt_minutes(result['min_gap'])} min"
    )

    print(
        f"Maximum gap              : "
        f"{fmt_minutes(result['max_gap'])} min"
    )

    print(
        f"Gaps > {GAP_SMALL_MIN} min       : "
        f"{result['small_gaps']}"
    )

    print(
        f"Gaps >= {GAP_MEDIUM_MIN} min      : "
        f"{result['medium_gaps']}"
    )

    print(
        f"Gaps >= {GAP_LARGE_MIN} min     : "
        f"{result['large_gaps']}"
    )

    print()

    print(
        f"LATEST {LATEST_N} SNAPSHOTS"
    )

    print(
        f"Count                    : "
        f"{result['latest_count']}"
    )

    print(
        f"Start                    : "
        f"{fmt_timestamp(result['latest_start'])}"
    )

    print(
        f"End                      : "
        f"{fmt_timestamp(result['latest_end'])}"
    )

    print(
        f"Coverage                 : "
        f"{fmt_hours(result['latest_span_seconds'])} hours"
    )

    print(
        f"Mean gap                 : "
        f"{fmt_minutes(result['latest_mean_gap'])} min"
    )

    print(
        f"Median gap               : "
        f"{fmt_minutes(result['latest_median_gap'])} min"
    )

    print(
        f"Minimum gap              : "
        f"{fmt_minutes(result['latest_min_gap'])} min"
    )

    print(
        f"Maximum gap              : "
        f"{fmt_minutes(result['latest_max_gap'])} min"
    )

    print(
        f"Missing close values     : "
        f"{result['latest_price_missing']}"
    )


# ============================================================
# CROSS-SYMBOL SUMMARY
# ============================================================


def print_cross_symbol_summary(
    results
):

    print()
    print("=" * 100)
    print("CROSS-SYMBOL TEMPORAL SUMMARY")
    print("=" * 100)

    print(
        f"{'SYMBOL':<7}"
        f"{'ROWS':>7}"
        f"{'DUP':>7}"
        f"{'BACK':>7}"
        f"{'MEDIAN':>12}"
        f"{'MAX GAP':>12}"
        f"{'LATEST':>10}"
        f"{'COVERAGE':>13}"
    )

    print(
        "-" * 100
    )

    for result in results:

        print(
            f"{result['symbol']:<7}"
            f"{result['total_rows']:>7}"
            f"{result['timestamp_duplicates']:>7}"
            f"{result['backward_gaps']:>7}"
            f"{fmt_minutes(result['latest_median_gap']):>12}"
            f"{fmt_minutes(result['latest_max_gap']):>12}"
            f"{result['latest_count']:>10}"
            f"{fmt_hours(result['latest_span_seconds']):>12} h"
        )


# ============================================================
# TEMPORAL VERDICT
# ============================================================


def temporal_verdict(
    results
):

    print()
    print("=" * 100)
    print("TEMPORAL INTEGRITY VERDICT")
    print("=" * 100)

    total_duplicates = sum(
        r["timestamp_duplicates"]
        for r in results
    )

    total_backward = sum(
        r["backward_gaps"]
        for r in results
    )

    total_invalid = sum(
        r["invalid_timestamps"]
        for r in results
    )

    insufficient_latest = sum(
        1
        for r in results
        if r["latest_count"] < LATEST_N
    )

    large_gap_symbols = [
        r["symbol"]
        for r in results
        if (
            r["latest_max_gap"] is not None
            and r["latest_max_gap"]
            >= GAP_LARGE_MIN * 60
        )
    ]

    print(
        f"Duplicate timestamps : "
        f"{total_duplicates}"
    )

    print(
        f"Backward gaps         : "
        f"{total_backward}"
    )

    print(
        f"Invalid timestamps    : "
        f"{total_invalid}"
    )

    print(
        f"Symbols < {LATEST_N} latest points : "
        f"{insufficient_latest}"
    )

    print(
        f"Symbols with latest gap >= "
        f"{GAP_LARGE_MIN} min : "
        f"{len(large_gap_symbols)}"
    )

    if large_gap_symbols:

        print(
            "Large-gap symbols     : "
            + ", ".join(
                large_gap_symbols
            )
        )

    print()
    print(
        "IMPORTANT:"
    )

    print(
        "This verdict does NOT determine trading profitability."
    )

    print(
        "It only determines whether the snapshot timeline "
        "is structurally suitable for the next forensic step."
    )

    print()

    if total_invalid > 0:

        print(
            "TEMPORAL STATUS : FAIL"
        )

        print(
            "Reason: invalid timestamps exist."
        )

        return False

    if total_backward > 0:

        print(
            "TEMPORAL STATUS : FAIL"
        )

        print(
            "Reason: backward time movement detected."
        )

        return False

    if insufficient_latest > 0:

        print(
            "TEMPORAL STATUS : INCOMPLETE"
        )

        print(
            "Reason: some symbols do not have "
            f"{LATEST_N} usable observations."
        )

        return False

    if total_duplicates > 0:

        print(
            "TEMPORAL STATUS : WARNING"
        )

        print(
            "Reason: duplicate timestamps exist."
        )

        return False

    if large_gap_symbols:

        print(
            "TEMPORAL STATUS : WARNING"
        )

        print(
            "Reason: large gaps exist inside latest windows."
        )

        return False

    print(
        "TEMPORAL STATUS : STRUCTURALLY CLEAN"
    )

    return True


# ============================================================
# MAIN
# ============================================================


def main():

    print("=" * 100)

    print(
        "             ARUNDA SNAPSHOT TEMPORAL FORENSIC v0.1"
    )

    print("=" * 100)

    print(
        f"Database       : {DB}"
    )

    print(
        f"Provider       : {SNAPSHOT_SOURCE}"
    )

    print(
        f"Timeframe      : {TIMEFRAME}"
    )

    print(
        f"Latest window  : {LATEST_N} snapshots"
    )

    print(
        "Mode           : READ ONLY"
    )

    print(
        "Writes         : NONE"
    )

    print(
        "=" * 100
    )

    conn = None

    try:

        conn = connect_database()

        database_fingerprint(
            conn
        )

        results = []

        print()
        print(
            "ANALYZING SYMBOL TIMELINES..."
        )

        for symbol in SYMBOLS:

            try:

                result = analyze_symbol(
                    conn,
                    symbol
                )

                results.append(
                    result
                )

                print_symbol_report(
                    result
                )

            except Exception as exc:

                print()
                print(
                    f"{symbol:<7} | ERROR | "
                    f"{repr(exc)}"
                )

        print_cross_symbol_summary(
            results
        )

        clean = temporal_verdict(
            results
        )

        print()
        print("=" * 100)
        print(
            "             SNAPSHOT TEMPORAL FORENSIC COMPLETE"
        )
        print("=" * 100)

        if clean:

            print(
                "NEXT STEP : FEATURE -> FUTURE RETURN FORENSIC"
            )

        else:

            print(
                "NEXT STEP : REPAIR / UNDERSTAND TEMPORAL ISSUES"
            )

        print("=" * 100)

        return 0

    except Exception as exc:

        print()
        print("=" * 100)
        print(
            "FORENSIC ERROR"
        )
        print("=" * 100)

        print(
            repr(exc)
        )

        print("=" * 100)

        return 1

    finally:

        if conn is not None:

            conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    raise SystemExit(
        main()
    )