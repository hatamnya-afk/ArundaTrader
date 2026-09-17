import sqlite3
from datetime import datetime, timezone


# =============================================================================
# ARUNDA SNAPSHOT READER v0.3
# Database -> Valid 150 Point Windows -> In-Memory Snapshots
# READ ONLY
# =============================================================================

DB_PATH = "arunda.db"
TABLE_NAME = "market_records"

WINDOW_SIZE = 150
GAP_MAX_SECONDS = 30.0

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
# TIME
# =============================================================================

def parse_timestamp(value):
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

def open_database():
    return sqlite3.connect(DB_PATH)


# =============================================================================
# LOAD ASSET HISTORY
# =============================================================================

def load_asset_history(connection, asset):
    cursor = connection.cursor()

    rows = cursor.execute(
        """
        SELECT timestamp, price
        FROM market_records
        WHERE asset = ?
        ORDER BY id ASC
        """,
        (asset,)
    ).fetchall()

    history = []

    for timestamp_value, price_value in rows:

        timestamp = parse_timestamp(timestamp_value)

        if timestamp is None:
            continue

        try:
            price = float(price_value)
        except (TypeError, ValueError):
            continue

        if price <= 0:
            continue

        history.append(
            {
                "timestamp": timestamp,
                "price": price,
            }
        )

    return history


# =============================================================================
# GAP VALIDATION
# =============================================================================

def valid_window(window):
    if len(window) != WINDOW_SIZE:
        return False

    for index in range(1, len(window)):

        previous_time = window[index - 1]["timestamp"]
        current_time = window[index]["timestamp"]

        gap = (
            current_time - previous_time
        ).total_seconds()

        if gap < 0:
            return False

        if gap > GAP_MAX_SECONDS:
            return False

    return True


# =============================================================================
# FIND LATEST VALID WINDOW
# =============================================================================

def find_latest_window(history):

    if len(history) < WINDOW_SIZE:
        return None

    start = len(history) - WINDOW_SIZE

    while start >= 0:

        window = history[
            start:start + WINDOW_SIZE
        ]

        if valid_window(window):
            return window

        start -= 1

    return None


# =============================================================================
# BUILD SNAPSHOT
# =============================================================================

def build_snapshot(asset, history):

    window = find_latest_window(history)

    if window is None:
        return {
            "asset": asset,
            "status": "DATA_GAP",
            "history_points": len(history),
            "window": [],
        }

    return {
        "asset": asset,
        "status": "READY",
        "history_points": len(history),
        "window": window,
    }


# =============================================================================
# PUBLIC API
# =============================================================================

def load_snapshots():

    connection = open_database()

    try:

        snapshots = {}

        for asset in EXPECTED_ASSETS:

            history = load_asset_history(
                connection,
                asset
            )

            snapshot = build_snapshot(
                asset,
                history
            )

            snapshots[asset] = snapshot

        return snapshots

    finally:

        connection.close()


# =============================================================================
# DISPLAY
# =============================================================================

def print_summary(snapshots):

    print("=" * 78)
    print("ARUNDA SNAPSHOT READER v0.3")
    print("=" * 78)

    print("Database :", DB_PATH)
    print("Window   :", WINDOW_SIZE)
    print("Gap Max  :", GAP_MAX_SECONDS, "s")
    print("Mode     : READ ONLY")
    print("Writes   : NONE")
    print("=" * 78)

    print()

    print(
        "Asset  | History | Window | Status"
    )

    print("-" * 78)

    ready_count = 0

    for asset in EXPECTED_ASSETS:

        snapshot = snapshots[asset]

        history_points = snapshot[
            "history_points"
        ]

        window_points = len(
            snapshot["window"]
        )

        status = snapshot["status"]

        if status == "READY":
            ready_count += 1

        print(
            "{:<6} | {:>7} | {:>6} | {}".format(
                asset,
                history_points,
                window_points,
                status
            )
        )

    print()

    print("=" * 78)
    print("IN-MEMORY SNAPSHOT CONTRACT")
    print("=" * 78)

    print(
        "Expected Assets :",
        len(EXPECTED_ASSETS)
    )

    print(
        "Ready Assets    :",
        ready_count
    )

    print(
        "Window Size     :",
        WINDOW_SIZE
    )

    print(
        "Storage         : MEMORY ONLY"
    )

    print(
        "Database writes : NONE"
    )

    print(
        "Feature Engine  : NOT USED"
    )

    print(
        "Signal Engine   : NOT USED"
    )

    print(
        "Scoring         : NOT USED"
    )

    print(
        "Interpretation  : NOT USED"
    )

    print("=" * 78)


# =============================================================================
# DIRECT EXECUTION
# =============================================================================

def main():

    try:

        snapshots = load_snapshots()

        print_summary(
            snapshots
        )

        ready_count = 0

        for asset in EXPECTED_ASSETS:

            if snapshots[asset]["status"] == "READY":
                ready_count += 1

        if ready_count == len(EXPECTED_ASSETS):

            print()
            print(
                "SNAPSHOT READER STATUS : READY"
            )

            return 0

        print()
        print(
            "SNAPSHOT READER STATUS : PARTIAL"
        )

        return 1

    except Exception as error:

        print()
        print("=" * 78)
        print("SNAPSHOT READER ERROR")
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


if __name__ == "__main__":
    raise SystemExit(
        main()
    )