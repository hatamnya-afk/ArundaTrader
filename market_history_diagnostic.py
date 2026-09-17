# =============================================================================
# ARUNDA MARKET HISTORY DIAGNOSTIC v0.2
# READ-ONLY / HISTORY QUALITY & TECHNICAL READINESS ANALYSIS
# =============================================================================

import os
import sqlite3
import statistics
from datetime import datetime, timezone


# =============================================================================
# CONFIGURATION
# =============================================================================

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arunda.db")

HISTORY_TABLE = "market_history"

RETURN_WINDOWS = {
    "return_5": 5,
    "return_10": 10,
    "return_20": 20,
}

SMA_WINDOW = 20
EMA_WINDOW = 20
RSI_WINDOW = 14
VOLATILITY_WINDOW = 20

# Gap threshold.
# History engine is expected to run every 60 seconds.
# A gap larger than 2x the expected interval is considered abnormal.
EXPECTED_INTERVAL_SECONDS = 60
ABNORMAL_GAP_MULTIPLIER = 2.0

# Output control
MAX_ASSET_DETAIL_ROWS = None


# =============================================================================
# HEADER
# =============================================================================

def print_header():
    print("=" * 100)
    print("ARUNDA MARKET HISTORY DIAGNOSTIC v0.2")
    print("READ-ONLY / HISTORY QUALITY & TECHNICAL READINESS ANALYSIS")
    print("=" * 100)
    print(f"Database        : {os.path.basename(DB_PATH)}")
    print("Mode            : READ ONLY")
    print("Database Write  : DISABLED")
    print("Technical       : NOT CALCULATED")
    print("Signal          : NOT USED")
    print("Risk            : NOT USED")
    print("Execution       : NOT USED")
    print("=" * 100)


# =============================================================================
# DATABASE HELPERS
# =============================================================================

def connect_read_only():
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    uri = f"file:{DB_PATH}?mode=ro"

    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    return conn


def table_exists(conn, table_name):
    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type='table'
          AND name=?
        """,
        (table_name,),
    ).fetchone()

    return row is not None


def get_columns(conn, table_name):
    rows = conn.execute(
        f"PRAGMA table_info({table_name})"
    ).fetchall()

    return [row["name"] for row in rows]


# =============================================================================
# TIMESTAMP PARSING
# =============================================================================

def parse_timestamp(value):
    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        normalized = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)

        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    except Exception:
        return None


# =============================================================================
# ASSET HISTORY ANALYSIS
# =============================================================================

def analyze_asset(rows):
    timestamps = []
    valid_rows = 0

    for row in rows:
        timestamp = parse_timestamp(row["timestamp"])

        if timestamp is not None:
            timestamps.append(timestamp)
            valid_rows += 1

    timestamps.sort()

    total_records = len(rows)

    if not timestamps:
        return {
            "records": total_records,
            "valid": 0,
            "invalid": total_records,
            "first": None,
            "last": None,
            "duration_seconds": 0,
            "duration_hours": 0,
            "duration_days": 0,
            "median_interval": None,
            "median_interval_minutes": None,
            "gap_count": 0,
            "max_gap_seconds": None,
            "return_5": False,
            "return_10": False,
            "return_20": False,
            "sma20": False,
            "ema20": False,
            "rsi14": False,
            "volatility20": False,
        }

    intervals = []

    for i in range(1, len(timestamps)):
        delta = (
            timestamps[i] - timestamps[i - 1]
        ).total_seconds()

        if delta > 0:
            intervals.append(delta)

    median_interval = (
        statistics.median(intervals)
        if intervals
        else None
    )

    abnormal_gap_threshold = (
        EXPECTED_INTERVAL_SECONDS
        * ABNORMAL_GAP_MULTIPLIER
    )

    gap_count = sum(
        1
        for delta in intervals
        if delta > abnormal_gap_threshold
    )

    max_gap_seconds = (
        max(intervals)
        if intervals
        else None
    )

    first_timestamp = timestamps[0]
    last_timestamp = timestamps[-1]

    duration_seconds = (
        last_timestamp - first_timestamp
    ).total_seconds()

    duration_hours = duration_seconds / 3600
    duration_days = duration_seconds / 86400

    # -------------------------------------------------------------------------
    # Technical readiness is intentionally based on chronological record depth.
    # No indicators are calculated here.
    # -------------------------------------------------------------------------

    return {
        "records": total_records,
        "valid": valid_rows,
        "invalid": total_records - valid_rows,
        "first": first_timestamp,
        "last": last_timestamp,
        "duration_seconds": duration_seconds,
        "duration_hours": duration_hours,
        "duration_days": duration_days,
        "median_interval": median_interval,
        "median_interval_minutes": (
            median_interval / 60
            if median_interval is not None
            else None
        ),
        "gap_count": gap_count,
        "max_gap_seconds": max_gap_seconds,

        # Return readiness
        "return_5": valid_rows >= 6,
        "return_10": valid_rows >= 11,
        "return_20": valid_rows >= 21,

        # Moving averages
        "sma20": valid_rows >= SMA_WINDOW,
        "ema20": valid_rows >= EMA_WINDOW,

        # RSI
        "rsi14": valid_rows >= RSI_WINDOW + 1,

        # Volatility
        "volatility20": valid_rows >= VOLATILITY_WINDOW + 1,
    }


# =============================================================================
# LOAD UNIVERSE
# =============================================================================

def load_asset_history(conn):
    query = f"""
        SELECT
            symbol,
            name,
            timestamp,
            price,
            volume_24h
        FROM {HISTORY_TABLE}
        WHERE symbol IS NOT NULL
        ORDER BY symbol, timestamp
    """

    rows = conn.execute(query).fetchall()

    grouped = {}

    for row in rows:
        symbol = row["symbol"]

        if symbol not in grouped:
            grouped[symbol] = []

        grouped[symbol].append(row)

    return grouped


# =============================================================================
# FORMATTERS
# =============================================================================

def format_timestamp(value):
    if value is None:
        return "N/A"

    return value.isoformat()


def format_number(value, decimals=2):
    if value is None:
        return "N/A"

    return f"{value:.{decimals}f}"


def format_bool(value):
    return "READY" if value else "NOT READY"


# =============================================================================
# DATABASE SUMMARY
# =============================================================================

def print_database_summary(conn, columns):
    print()
    print("=" * 100)
    print("DATABASE")
    print("=" * 100)

    print(f"Database        : CONNECTED")
    print(f"History Table   : {HISTORY_TABLE}")
    print(f"Columns         : {len(columns)}")

    required = [
        "timestamp",
        "symbol",
    ]

    print()
    print("REQUIRED FIELD CHECK")
    print("-" * 100)

    for field in required:
        status = "PRESENT" if field in columns else "MISSING"
        print(f"{field:<20}: {status}")


# =============================================================================
# GLOBAL STATISTICS
# =============================================================================

def get_global_statistics(conn):
    total_rows = conn.execute(
        f"SELECT COUNT(*) FROM {HISTORY_TABLE}"
    ).fetchone()[0]

    distinct_symbols = conn.execute(
        f"""
        SELECT COUNT(DISTINCT symbol)
        FROM {HISTORY_TABLE}
        WHERE symbol IS NOT NULL
        """
    ).fetchone()[0]

    return total_rows, distinct_symbols


def print_global_statistics(
    total_rows,
    distinct_symbols,
    asset_count,
):
    print()
    print("=" * 100)
    print("GLOBAL HISTORY STATISTICS")
    print("=" * 100)

    print(f"Total History Rows       : {total_rows}")
    print(f"Distinct Symbols         : {distinct_symbols}")
    print(f"Analyzed Assets          : {asset_count}")

    if asset_count:
        average = total_rows / asset_count
    else:
        average = 0

    print(f"Average Records / Asset  : {average:.2f}")


# =============================================================================
# ASSET DETAIL
# =============================================================================

def print_asset_detail(symbol, analysis):
    print()
    print(f"{symbol:<12} "
          f"records={analysis['records']:<5} "
          f"valid={analysis['valid']:<5} "
          f"invalid={analysis['invalid']:<4} "
          f"gaps={analysis['gap_count']:<4} "
          f"median={format_number(analysis['median_interval_minutes'])}m")


# =============================================================================
# ASSET HISTORY ANALYSIS
# =============================================================================

def print_asset_analysis(asset_analysis):
    print()
    print("=" * 100)
    print("ASSET HISTORY ANALYSIS")
    print("=" * 100)

    print(
        f"{'SYMBOL':<12}"
        f"{'RECORDS':>10}"
        f"{'VALID':>10}"
        f"{'INVALID':>10}"
        f"{'DAYS':>12}"
        f"{'MEDIAN':>12}"
        f"{'GAPS':>8}"
    )

    print("-" * 100)

    items = list(asset_analysis.items())

    if MAX_ASSET_DETAIL_ROWS is not None:
        items = items[:MAX_ASSET_DETAIL_ROWS]

    for symbol, analysis in items:
        print(
            f"{symbol:<12}"
            f"{analysis['records']:>10}"
            f"{analysis['valid']:>10}"
            f"{analysis['invalid']:>10}"
            f"{analysis['duration_days']:>12.2f}"
            f"{format_number(analysis['median_interval_minutes']):>12}"
            f"{analysis['gap_count']:>8}"
        )


# =============================================================================
# READINESS STATISTICS
# =============================================================================

def count_ready(asset_analysis, key):
    return sum(
        1
        for analysis in asset_analysis.values()
        if analysis[key]
    )


def print_readiness(asset_analysis):
    total_assets = len(asset_analysis)

    print()
    print("=" * 100)
    print("TECHNICAL READINESS")
    print("=" * 100)

    readiness_items = [
        ("return_5", "return_5"),
        ("return_10", "return_10"),
        ("return_20", "return_20"),
        ("SMA_20", "sma20"),
        ("EMA_20", "ema20"),
        ("RSI_14", "rsi14"),
        ("volatility_20", "volatility20"),
    ]

    print(
        f"{'METRIC':<25}"
        f"{'READY':>12}"
        f"{'NOT READY':>15}"
        f"{'COVERAGE':>15}"
    )

    print("-" * 100)

    for label, key in readiness_items:
        ready = count_ready(asset_analysis, key)
        not_ready = total_assets - ready

        coverage = (
            (ready / total_assets) * 100
            if total_assets
            else 0
        )

        print(
            f"{label:<25}"
            f"{ready:>12}"
            f"{not_ready:>15}"
            f"{coverage:>14.2f}%"
        )


# =============================================================================
# HISTORY COVERAGE
# =============================================================================

def print_history_coverage(asset_analysis):
    print()
    print("=" * 100)
    print("HISTORY COVERAGE")
    print("=" * 100)

    total_assets = len(asset_analysis)

    if not total_assets:
        print("No assets found.")
        return

    depth_buckets = [
        (0, 0, "0 records"),
        (1, 5, "1-5 records"),
        (6, 20, "6-20 records"),
        (21, 99, "21-99 records"),
        (100, 199, "100-199 records"),
        (200, 299, "200-299 records"),
        (300, 999999999, "300+ records"),
    ]

    print(
        f"{'DEPTH':<20}"
        f"{'ASSETS':>12}"
        f"{'COVERAGE':>15}"
    )

    print("-" * 100)

    for minimum, maximum, label in depth_buckets:
        count = sum(
            1
            for analysis in asset_analysis.values()
            if minimum <= analysis["records"] <= maximum
        )

        coverage = (
            (count / total_assets) * 100
            if total_assets
            else 0
        )

        print(
            f"{label:<20}"
            f"{count:>12}"
            f"{coverage:>14.2f}%"
        )


# =============================================================================
# GAP ANALYSIS
# =============================================================================

def print_gap_analysis(asset_analysis):
    print()
    print("=" * 100)
    print("GAP ANALYSIS")
    print("=" * 100)

    total_assets = len(asset_analysis)

    assets_with_gaps = sum(
        1
        for analysis in asset_analysis.values()
        if analysis["gap_count"] > 0
    )

    total_gaps = sum(
        analysis["gap_count"]
        for analysis in asset_analysis.values()
    )

    max_gap = None
    max_gap_symbol = None

    for symbol, analysis in asset_analysis.items():
        value = analysis["max_gap_seconds"]

        if value is not None:
            if max_gap is None or value > max_gap:
                max_gap = value
                max_gap_symbol = symbol

    coverage = (
        (assets_with_gaps / total_assets) * 100
        if total_assets
        else 0
    )

    print(f"Assets With Abnormal Gaps : {assets_with_gaps}")
    print(f"Gap-Affected Coverage     : {coverage:.2f}%")
    print(f"Total Abnormal Gaps       : {total_gaps}")

    if max_gap is not None:
        print(
            f"Maximum Gap               : "
            f"{max_gap / 60:.2f} minutes"
        )
        print(
            f"Maximum Gap Asset         : "
            f"{max_gap_symbol}"
        )
    else:
        print("Maximum Gap               : N/A")
        print("Maximum Gap Asset         : N/A")


# =============================================================================
# VALID DATA ANALYSIS
# =============================================================================

def print_validity_analysis(asset_analysis):
    print()
    print("=" * 100)
    print("DATA VALIDITY")
    print("=" * 100)

    total_assets = len(asset_analysis)

    valid_assets = sum(
        1
        for analysis in asset_analysis.values()
        if analysis["invalid"] == 0
    )

    partially_invalid = sum(
        1
        for analysis in asset_analysis.values()
        if analysis["invalid"] > 0
        and analysis["valid"] > 0
    )

    completely_invalid = sum(
        1
        for analysis in asset_analysis.values()
        if analysis["valid"] == 0
    )

    print(f"Assets Fully Valid         : {valid_assets}")
    print(f"Assets Partially Invalid   : {partially_invalid}")
    print(f"Assets Completely Invalid  : {completely_invalid}")

    if total_assets:
        print(
            f"Fully Valid Coverage      : "
            f"{(valid_assets / total_assets) * 100:.2f}%"
        )


# =============================================================================
# DETAILED TECHNICAL READINESS CHECK
# =============================================================================

def print_readiness_thresholds():
    print()
    print("=" * 100)
    print("READINESS CONTRACT")
    print("=" * 100)

    print("return_5       : >= 6 valid chronological records")
    print("return_10      : >= 11 valid chronological records")
    print("return_20      : >= 21 valid chronological records")
    print("SMA_20         : >= 20 valid chronological records")
    print("EMA_20         : >= 20 valid chronological records")
    print("RSI_14         : >= 15 valid chronological records")
    print("volatility_20  : >= 21 valid chronological records")

    print()
    print("NOTE:")
    print("Readiness means sufficient historical depth.")
    print("Indicators are NOT calculated by this diagnostic.")


# =============================================================================
# EXTREME / INCOMPLETE ASSETS
# =============================================================================

def print_incomplete_assets(asset_analysis):
    print()
    print("=" * 100)
    print("INCOMPLETE HISTORY ASSETS")
    print("=" * 100)

    incomplete = []

    for symbol, analysis in asset_analysis.items():
        if (
            not analysis["return_20"]
            or analysis["gap_count"] > 0
            or analysis["invalid"] > 0
        ):
            incomplete.append((symbol, analysis))

    incomplete.sort(
        key=lambda item: (
            item[1]["records"],
            item[0],
        )
    )

    if not incomplete:
        print("No incomplete assets detected.")
        return

    print(
        f"{'SYMBOL':<12}"
        f"{'RECORDS':>10}"
        f"{'VALID':>10}"
        f"{'INVALID':>10}"
        f"{'GAPS':>8}"
        f"{'RETURN20':>12}"
    )

    print("-" * 100)

    for symbol, analysis in incomplete:
        print(
            f"{symbol:<12}"
            f"{analysis['records']:>10}"
            f"{analysis['valid']:>10}"
            f"{analysis['invalid']:>10}"
            f"{analysis['gap_count']:>8}"
            f"{format_bool(analysis['return_20']):>12}"
        )


# =============================================================================
# FINAL ASSESSMENT
# =============================================================================

def final_assessment(asset_analysis):
    print()
    print("=" * 100)
    print("DIAGNOSTIC ASSESSMENT")
    print("=" * 100)

    total_assets = len(asset_analysis)

    if total_assets == 0:
        print("RESULT : NO ASSETS FOUND")
        return

    ready_return20 = count_ready(
        asset_analysis,
        "return_20"
    )

    ready_sma20 = count_ready(
        asset_analysis,
        "sma20"
    )

    ready_rsi14 = count_ready(
        asset_analysis,
        "rsi14"
    )

    ready_vol20 = count_ready(
        asset_analysis,
        "volatility20"
    )

    coverage_return20 = (
        ready_return20 / total_assets
    ) * 100

    coverage_sma20 = (
        ready_sma20 / total_assets
    ) * 100

    coverage_rsi14 = (
        ready_rsi14 / total_assets
    ) * 100

    coverage_vol20 = (
        ready_vol20 / total_assets
    ) * 100

    print(
        f"Universe Assets             : {total_assets}"
    )

    print(
        f"RETURN_20 Coverage           : "
        f"{coverage_return20:.2f}%"
    )

    print(
        f"SMA_20 Coverage              : "
        f"{coverage_sma20:.2f}%"
    )

    print(
        f"RSI_14 Coverage              : "
        f"{coverage_rsi14:.2f}%"
    )

    print(
        f"VOLATILITY_20 Coverage       : "
        f"{coverage_vol20:.2f}%"
    )

    print()

    if coverage_return20 >= 95:
        print(
            "History Depth Status         : "
            "READY FOR STRUCTURAL ANALYSIS"
        )
    elif coverage_return20 >= 80:
        print(
            "History Depth Status         : "
            "PARTIALLY READY"
        )
    else:
        print(
            "History Depth Status         : "
            "NOT READY"
        )

    print()
    print("Technical calculations       : NOT PERFORMED")
    print("Signals                      : NOT PERFORMED")
    print("Trading decisions            : NOT PERFORMED")


# =============================================================================
# MAIN
# =============================================================================

def main():
    print_header()

    conn = None

    try:
        conn = connect_read_only()

        if not table_exists(conn, HISTORY_TABLE):
            print()
            print("ERROR")
            print("-" * 100)
            print(
                f"Required table '{HISTORY_TABLE}' "
                f"does not exist."
            )
            return

        columns = get_columns(
            conn,
            HISTORY_TABLE
        )

        print_database_summary(
            conn,
            columns
        )

        required_fields = {
            "timestamp",
            "symbol",
        }

        missing = required_fields - set(columns)

        if missing:
            print()
            print(
                "ERROR: Missing required fields: "
                + ", ".join(sorted(missing))
            )
            return

        total_rows, distinct_symbols = (
            get_global_statistics(conn)
        )

        asset_history = load_asset_history(conn)

        asset_analysis = {}

        for symbol, rows in asset_history.items():
            asset_analysis[symbol] = analyze_asset(rows)

        print_global_statistics(
            total_rows,
            distinct_symbols,
            len(asset_analysis),
        )

        print_history_coverage(
            asset_analysis
        )

        print_asset_analysis(
            asset_analysis
        )

        print_validity_analysis(
            asset_analysis
        )

        print_gap_analysis(
            asset_analysis
        )

        print_readiness_thresholds()

        print_readiness(
            asset_analysis
        )

        print_incomplete_assets(
            asset_analysis
        )

        final_assessment(
            asset_analysis
        )

        print()
        print("=" * 100)
        print("DIAGNOSTIC CONCLUSION")
        print("=" * 100)
        print("Analysis Mode              : READ ONLY")
        print("Database Modification      : NONE")
        print("History Engine Modification: NONE")
        print("Technical Calculation      : NONE")
        print("Signal Generation          : NONE")
        print("Risk Calculation           : NONE")
        print("Execution                  : NONE")
        print()
        print(
            "NO DATABASE OR ENGINE "
            "MODIFICATIONS WERE PERFORMED."
        )
        print("=" * 100)
        print(
            "ARUNDA MARKET HISTORY DIAGNOSTIC "
            "v0.2 COMPLETE"
        )
        print("=" * 100)

    except sqlite3.Error as exc:
        print()
        print("=" * 100)
        print("DATABASE ERROR")
        print("=" * 100)
        print(str(exc))

    except Exception as exc:
        print()
        print("=" * 100)
        print("DIAGNOSTIC ERROR")
        print("=" * 100)
        print(type(exc).__name__)
        print(str(exc))

    finally:
        if conn is not None:
            conn.close()


if __name__ == "__main__":
    main()