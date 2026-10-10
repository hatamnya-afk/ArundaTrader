import sqlite3
import math
from datetime import datetime, timezone


# =============================================================================
# ARUNDA MARKET ANALYSIS ENGINE v0.2.1
# Real History -> Deterministic Analysis -> Snapshot Contract
# READ ONLY
# =============================================================================

DB_PATH = "arunda.db"
TABLE_NAME = "market_records"

EXPECTED_INTERVAL = 15.0
GAP_THRESHOLD = 30.0

MINIMUM_HISTORY = 60
VALIDATION_POINTS = 150

CONTRACT_VERSION = "MARKET_ANALYSIS_SNAPSHOT_v0.2.1"

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


# =============================================================================
# TIME PARSER
# =============================================================================

def parse_timestamp(value):
    """
    Converts both of these forms safely:

        2026-08-15T00:23:45.778676
        2026-08-15T00:48:27.677600+00:00

    into timezone-aware UTC datetime objects.
    """

    if value is None:
        return None

    text = str(value).strip()

    if not text:
        return None

    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


# =============================================================================
# DATABASE
# =============================================================================

def connect_database():
    return sqlite3.connect(DB_PATH)


# =============================================================================
# SCHEMA VALIDATION
# =============================================================================

def validate_schema(connection):
    cursor = connection.cursor()

    rows = cursor.execute(
        "PRAGMA table_info(market_records)"
    ).fetchall()

    columns = {}

    for row in rows:
        columns[row[1]] = row

    required = [
        "id",
        "timestamp",
        "market",
        "asset",
        "price",
    ]

    missing = []

    for column in required:
        if column not in columns:
            missing.append(column)

    if missing:
        return False, "Missing columns: " + ", ".join(missing)

    return True, "OK"


# =============================================================================
# LOAD HISTORY
# =============================================================================

def load_asset_history(connection, asset):
    cursor = connection.cursor()

    query = """
        SELECT timestamp, price
        FROM market_records
        WHERE asset = ?
        ORDER BY id ASC
    """

    rows = cursor.execute(query, (asset,)).fetchall()

    history = []

    for timestamp_text, price in rows:
        timestamp = parse_timestamp(timestamp_text)

        if timestamp is None:
            continue

        try:
            price_value = float(price)
        except (TypeError, ValueError):
            continue

        if not math.isfinite(price_value):
            continue

        if price_value <= 0:
            continue

        history.append(
            {
                "timestamp": timestamp,
                "price": price_value,
            }
        )

    return history


# =============================================================================
# GAP ANALYSIS
# =============================================================================

def calculate_gaps(history):
    gaps = []

    if len(history) < 2:
        return gaps

    for index in range(1, len(history)):
        previous = history[index - 1]["timestamp"]
        current = history[index]["timestamp"]

        seconds = (current - previous).total_seconds()

        if seconds < 0:
            seconds = 0.0

        gaps.append(seconds)

    return gaps


def find_latest_contiguous_window(history, required_points):
    """
    Searches backward from the newest point.

    A contiguous window is valid when every internal gap
    is <= GAP_THRESHOLD.

    This prevents old historical holes from poisoning the
    current snapshot.
    """

    if len(history) < required_points:
        return None

    start_index = len(history) - required_points

    while start_index >= 0:
        window = history[start_index:]

        if len(window) > required_points:
            window = window[:required_points]

        gaps = calculate_gaps(window)

        bad_gap = False

        for gap in gaps:
            if gap > GAP_THRESHOLD:
                bad_gap = True
                break

        if not bad_gap and len(window) == required_points:
            return window

        start_index -= 1

    return None


# =============================================================================
# BASIC MATH
# =============================================================================

def percentage_return(old_price, new_price):
    if old_price == 0:
        return 0.0

    return ((new_price / old_price) - 1.0) * 100.0


def standard_deviation(values):
    if len(values) < 2:
        return 0.0

    mean = sum(values) / len(values)

    variance = sum(
        (value - mean) ** 2
        for value in values
    ) / len(values)

    return math.sqrt(variance)


def linear_slope(values):
    count = len(values)

    if count < 2:
        return 0.0

    x_mean = (count - 1) / 2.0
    y_mean = sum(values) / count

    numerator = 0.0
    denominator = 0.0

    for index, value in enumerate(values):
        dx = index - x_mean
        dy = value - y_mean

        numerator += dx * dy
        denominator += dx * dx

    if denominator == 0:
        return 0.0

    return numerator / denominator


# =============================================================================
# SNAPSHOT CALCULATION
# =============================================================================

def calculate_snapshot(asset, window):
    prices = [
        item["price"]
        for item in window
    ]

    timestamps = [
        item["timestamp"]
        for item in window
    ]

    latest_price = prices[-1]

    ret_1 = percentage_return(prices[-2], latest_price)
    ret_3 = percentage_return(prices[-4], latest_price)
    ret_5 = percentage_return(prices[-6], latest_price)
    ret_10 = percentage_return(prices[-11], latest_price)
    ret_20 = percentage_return(prices[-21], latest_price)

    returns = []

    for index in range(1, len(prices)):
        value = percentage_return(
            prices[index - 1],
            prices[index]
        )
        returns.append(value)

    recent_returns_10 = returns[-10:]
    recent_returns_20 = returns[-20:]

    volatility_10 = standard_deviation(
        recent_returns_10
    )

    volatility_20 = standard_deviation(
        recent_returns_20
    )

    range_10 = percentage_return(
        min(prices[-10:]),
        max(prices[-10:])
    )

    range_20 = percentage_return(
        min(prices[-20:]),
        max(prices[-20:])
    )

    slope_10 = linear_slope(
        prices[-10:]
    )

    slope_20 = linear_slope(
        prices[-20:]
    )

    slope_10_pct = (
        slope_10 / latest_price
    ) * 100.0

    slope_20_pct = (
        slope_20 / latest_price
    ) * 100.0

    acceleration = slope_10_pct - slope_20_pct

    low_20 = min(prices[-20:])
    high_20 = max(prices[-20:])

    if high_20 == low_20:
        position = 0.0
    else:
        position = (
            (latest_price - low_20)
            / (high_20 - low_20)
        )

    gaps = calculate_gaps(window)

    max_gap = max(gaps) if gaps else 0.0

    average_gap = (
        sum(gaps) / len(gaps)
        if gaps
        else 0.0
    )

    return {
        "asset": asset,
        "status": "READY",
        "points": len(window),
        "timestamp": timestamps[-1].isoformat(),
        "price": latest_price,
        "return_1": ret_1,
        "return_3": ret_3,
        "return_5": ret_5,
        "return_10": ret_10,
        "return_20": ret_20,
        "momentum_5": ret_5,
        "momentum_10": ret_10,
        "momentum_20": ret_20,
        "volatility_10": volatility_10,
        "volatility_20": volatility_20,
        "range_10": range_10,
        "range_20": range_20,
        "trend_slope_10": slope_10_pct,
        "trend_slope_20": slope_20_pct,
        "acceleration": acceleration,
        "position": position,
        "max_gap": max_gap,
        "average_gap": average_gap,
    }


# =============================================================================
# ASSET ANALYSIS
# =============================================================================

def analyze_asset(connection, asset):
    history = load_asset_history(
        connection,
        asset
    )

    history_count = len(history)

    if history_count < MINIMUM_HISTORY:
        return {
            "asset": asset,
            "status": "INSUFFICIENT",
            "points": history_count,
            "error": "INSUFFICIENT_HISTORY",
        }

    window = find_latest_contiguous_window(
        history,
        VALIDATION_POINTS
    )

    if window is None:
        return {
            "asset": asset,
            "status": "ERROR",
            "points": history_count,
            "error": "DATA_GAP",
        }

    snapshot = calculate_snapshot(
        asset,
        window
    )

    return snapshot


# =============================================================================
# PRINT HELPERS
# =============================================================================

def print_header():
    print("=" * 78)
    print("ARUNDA MARKET ANALYSIS ENGINE v0.2.1")
    print("Real History -> Deterministic Analysis -> Snapshot Contract")
    print("=" * 78)
    print("Database          :", DB_PATH)
    print("Source            :", TABLE_NAME)
    print("Expected Interval :", str(EXPECTED_INTERVAL) + "s")
    print("Gap Threshold     :", str(GAP_THRESHOLD) + "s")
    print("Minimum History   :", MINIMUM_HISTORY)
    print("Validation Points :", VALIDATION_POINTS)
    print("Engine            :", "MARKET_ANALYSIS_v0.2.1")
    print()


def print_summary(results):
    print("=" * 78)
    print("SNAPSHOT ANALYSIS")
    print("=" * 78)

    print(
        "Asset  | Status     | Points | Ret20      | Vol20      | "
        "Trend20    | Position"
    )

    print("-" * 78)

    for asset in EXPECTED_ASSETS:
        result = results[asset]

        status = result["status"]
        points = result.get("points", 0)

        if status == "READY":
            ret20 = result["return_20"]
            vol20 = result["volatility_20"]
            trend20 = result["trend_slope_20"]
            position = result["position"]

            print(
                "{:<6} | {:<10} | {:>6} | {:+.5f}% | {:+.5f}% | "
                "{:+.5f}% | {:>8.4f}".format(
                    asset,
                    status,
                    points,
                    ret20,
                    vol20,
                    trend20,
                    position,
                )
            )

        else:
            error = result.get("error", "UNKNOWN")

            print(
                "{:<6} | {:<10} | {:>6} | {}".format(
                    asset,
                    status,
                    points,
                    error,
                )
            )

    print()


def print_snapshot_details(result):
    if result["status"] != "READY":
        return

    asset = result["asset"]

    print("=" * 78)
    print(asset)
    print("=" * 78)

    print("STATUS             :", result["status"])
    print("TIMESTAMP          :", result["timestamp"])
    print("PRICE              :", result["price"])
    print("HISTORY POINTS     :", result["points"])

    print()
    print("RETURNS")
    print("-" * 78)
    print(
        "RETURN 1           : {:+.5f}%".format(
            result["return_1"]
        )
    )
    print(
        "RETURN 3           : {:+.5f}%".format(
            result["return_3"]
        )
    )
    print(
        "RETURN 5           : {:+.5f}%".format(
            result["return_5"]
        )
    )
    print(
        "RETURN 10          : {:+.5f}%".format(
            result["return_10"]
        )
    )
    print(
        "RETURN 20          : {:+.5f}%".format(
            result["return_20"]
        )
    )

    print()
    print("MOMENTUM")
    print("-" * 78)
    print(
        "MOMENTUM 5         : {:+.5f}%".format(
            result["momentum_5"]
        )
    )
    print(
        "MOMENTUM 10        : {:+.5f}%".format(
            result["momentum_10"]
        )
    )
    print(
        "MOMENTUM 20        : {:+.5f}%".format(
            result["momentum_20"]
        )
    )

    print()
    print("VOLATILITY")
    print("-" * 78)
    print(
        "VOLATILITY 10      : {:+.5f}%".format(
            result["volatility_10"]
        )
    )
    print(
        "VOLATILITY 20      : {:+.5f}%".format(
            result["volatility_20"]
        )
    )

    print()
    print("RANGE")
    print("-" * 78)
    print(
        "RANGE 10           : {:+.5f}%".format(
            result["range_10"]
        )
    )
    print(
        "RANGE 20           : {:+.5f}%".format(
            result["range_20"]
        )
    )

    print()
    print("TREND")
    print("-" * 78)
    print(
        "TREND SLOPE 10     : {:+.5f}%".format(
            result["trend_slope_10"]
        )
    )
    print(
        "TREND SLOPE 20     : {:+.5f}%".format(
            result["trend_slope_20"]
        )
    )
    print(
        "ACCELERATION       : {:+.5f}%".format(
            result["acceleration"]
        )
    )

    print()
    print("PRICE POSITION")
    print("-" * 78)
    print(
        "POSITION IN 20     : {:.6f}".format(
            result["position"]
        )
    )

    print()
    print("DATA QUALITY")
    print("-" * 78)
    print(
        "MAX GAP            : {:.3f}s".format(
            result["max_gap"]
        )
    )
    print(
        "AVERAGE GAP        : {:.3f}s".format(
            result["average_gap"]
        )
    )

    print()


def print_contract(results):
    ready_count = 0
    validation_errors = 0
    snapshots_built = 0

    for asset in EXPECTED_ASSETS:
        result = results[asset]

        if result["status"] == "READY":
            ready_count += 1
            snapshots_built += 1
        else:
            validation_errors += 1

    contract_valid = (
        len(EXPECTED_ASSETS) == 15
        and snapshots_built == 15
        and validation_errors == 0
    )

    print("=" * 78)
    print("SNAPSHOT CONTRACT VALIDATION")
    print("=" * 78)

    print(
        "Expected Assets       :",
        len(EXPECTED_ASSETS)
    )

    print(
        "Snapshots Built       :",
        snapshots_built
    )

    print(
        "Validation Errors     :",
        validation_errors
    )

    print(
        "Ready Assets          :",
        ready_count
    )

    print(
        "Contract Version      :",
        CONTRACT_VERSION
    )

    if contract_valid:
        print(
            "Contract Status       : VALID"
        )
    else:
        print(
            "Contract Status       : INVALID"
        )

    print()

    return contract_valid


def print_output_contract(results):
    print("=" * 78)
    print("ANALYSIS OUTPUT CONTRACT")
    print("=" * 78)

    print(
        "Asset  | Status     | Points | Price        | Ret20      | "
        "Vol20      | Trend20    | Position"
    )

    print("-" * 94)

    for asset in EXPECTED_ASSETS:
        result = results[asset]

        if result["status"] != "READY":
            continue

        print(
            "{:<6} | {:<10} | {:>6} | {:>12.6f} | {:+.5f}% | "
            "{:+.5f}% | {:+.5f}% | {:>8.4f}".format(
                asset,
                result["status"],
                result["points"],
                result["price"],
                result["return_20"],
                result["volatility_20"],
                result["trend_slope_20"],
                result["position"],
            )
        )

    print()


def print_read_only_confirmation():
    print("=" * 78)
    print("READ-ONLY CONFIRMATION")
    print("=" * 78)

    print("market_records       : READ ONLY")
    print("market_data          : NOT TOUCHED")
    print("Database writes      : NONE")
    print("Synthetic data       : NONE")
    print("Interpolation        : NONE")
    print("Forward fill         : NONE")
    print("Back fill            : NONE")
    print("Trading signal       : NONE")
    print("Order execution      : NONE")
    print("Analysis write       : NONE")
    print("Snapshot write       : NONE")

    print("=" * 78)
    print()


def print_errors(results):
    errors = []

    for asset in EXPECTED_ASSETS:
        result = results[asset]

        if result["status"] != "READY":
            errors.append(
                "{}: {}".format(
                    asset,
                    result.get("error", "UNKNOWN")
                )
            )

    if not errors:
        return

    print("=" * 78)
    print("ERROR DETAILS")
    print("=" * 78)

    for error in errors:
        print(error)

    print()


# =============================================================================
# MAIN ENGINE
# =============================================================================

def run_engine():
    print_header()

    connection = None

    try:
        connection = connect_database()

        print("Checking market_records schema...")

        schema_ok, schema_message = validate_schema(
            connection
        )

        if not schema_ok:
            print("Schema            :", "FAILED")
            print("Reason            :", schema_message)
            print()
            print(
                "MARKET ANALYSIS STATUS : FAILED"
            )
            return 1

        print("Schema            :", "OK")
        print()

        results = {}

        for asset in EXPECTED_ASSETS:
            results[asset] = analyze_asset(
                connection,
                asset
            )

        print_summary(results)

        for asset in EXPECTED_ASSETS:
            result = results[asset]

            if result["status"] == "READY":
                print_snapshot_details(result)

        contract_valid = print_contract(
            results
        )

        print_output_contract(
            results
        )

        print_read_only_confirmation()

        print_errors(
            results
        )

        if contract_valid:
            print(
                "MARKET ANALYSIS STATUS : ANALYSIS READY"
            )
            return 0

        print(
            "MARKET ANALYSIS STATUS : FAILED"
        )

        return 1

    except Exception as error:
        print("=" * 78)
        print("ENGINE ERROR")
        print("=" * 78)
        print(
            "Type   :",
            type(error).__name__
        )
        print(
            "Error  :",
            str(error)
        )
        print("=" * 78)

        return 1

    finally:
        if connection is not None:
            connection.close()


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

if __name__ == "__main__":
    raise SystemExit(
        run_engine()
    )