import sqlite3
import statistics
from datetime import datetime, timezone


# ============================================================
# FIND_FUTURE_PRICE TIMESTAMP CADENCE FORENSIC v0.3
# ============================================================

DB_PATH = r"C:\Users\ASUS\ArundaTrader\arunda.db"

TOLERANCE = 120.0

HORIZONS = {
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m": 60,
}


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    uri = f"file:{DB_PATH}?mode=ro"

    conn = sqlite3.connect(
        uri,
        uri=True
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# TIMESTAMP
# ============================================================

def parse_timestamp(value):

    if value is None:
        return None

    try:

        text = str(value).strip()

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            dt = dt.replace(
                tzinfo=timezone.utc
            )

        return dt.astimezone(
            timezone.utc
        )

    except Exception:

        return None


def epoch(value):

    dt = parse_timestamp(value)

    if dt is None:
        return None

    return dt.timestamp()


def format_epoch(value):

    if value is None:
        return "None"

    dt = datetime.fromtimestamp(
        value,
        tz=timezone.utc
    )

    return dt.isoformat()


# ============================================================
# LOAD GENUINE SIGNALS
# ============================================================

def load_signals(conn):

    rows = conn.execute(
        """
        SELECT
            id,
            asset,
            timestamp,
            entry_price,
            direction
        FROM fusion_signals
        WHERE
            engine_version IN (
                'FUSION_v0.5',
                'FUSION_v0.4'
            )
            AND entry_price IS NOT NULL
        ORDER BY id ASC
        LIMIT 10
        """
    ).fetchall()

    return rows


# ============================================================
# MARKET DATA TIMESTAMPS
# ============================================================

def load_market_rows(
    conn,
    asset
):

    rows = conn.execute(
        """
        SELECT
            id,
            timestamp,
            close,
            symbol
        FROM market_data
        WHERE
            symbol = ?
            AND close IS NOT NULL
        ORDER BY id ASC
        """,
        (asset,)
    ).fetchall()

    result = []

    for row in rows:

        ts = epoch(
            row["timestamp"]
        )

        if ts is None:
            continue

        result.append(
            {
                "id": row["id"],
                "timestamp": row["timestamp"],
                "epoch": ts,
                "close": row["close"],
                "symbol": row["symbol"],
            }
        )

    return result


# ============================================================
# NEAREST / PREVIOUS / NEXT
# ============================================================

def locate(rows, target_epoch):

    if not rows:

        return {
            "previous": None,
            "next": None,
            "nearest": None,
        }

    previous = None
    next_row = None
    nearest = None
    nearest_distance = None

    for row in rows:

        row_epoch = row["epoch"]

        distance = abs(
            row_epoch - target_epoch
        )

        if (
            nearest_distance is None
            or distance < nearest_distance
        ):
            nearest_distance = distance
            nearest = row

        if row_epoch <= target_epoch:

            if (
                previous is None
                or row_epoch > previous["epoch"]
            ):
                previous = row

        if row_epoch >= target_epoch:

            if (
                next_row is None
                or row_epoch < next_row["epoch"]
            ):
                next_row = row

    return {
        "previous": previous,
        "next": next_row,
        "nearest": nearest,
    }


# ============================================================
# CADENCE
# ============================================================

def calculate_cadence(rows):

    if len(rows) < 2:

        return []

    deltas = []

    previous = rows[0]["epoch"]

    for row in rows[1:]:

        current = row["epoch"]

        delta = current - previous

        if delta >= 0:

            deltas.append(delta)

        previous = current

    return deltas


def print_cadence(asset, rows):

    print()
    print("=" * 90)
    print(
        f"MARKET DATA CADENCE | {asset}"
    )
    print("=" * 90)

    print(
        f"ROWS : {len(rows)}"
    )

    if not rows:

        print("NO MARKET DATA")

        return

    print(
        f"FIRST : {rows[0]['timestamp']}"
    )

    print(
        f"LAST  : {rows[-1]['timestamp']}"
    )

    deltas = calculate_cadence(rows)

    if not deltas:

        print("CADENCE : INSUFFICIENT")

        return

    print()
    print(
        "INTER-ROW TIME DELTAS"
    )

    print(
        f"MIN    : {min(deltas):.3f} sec"
    )

    print(
        f"MAX    : {max(deltas):.3f} sec"
    )

    print(
        f"MEDIAN : "
        f"{statistics.median(deltas):.3f} sec"
    )

    print(
        f"MEAN   : "
        f"{statistics.mean(deltas):.3f} sec"
    )

    print()

    buckets = [
        ("<= 60s", lambda x: x <= 60),
        ("61-120s", lambda x: 60 < x <= 120),
        ("121-300s", lambda x: 120 < x <= 300),
        ("301-600s", lambda x: 300 < x <= 600),
        ("601-900s", lambda x: 600 < x <= 900),
        ("> 900s", lambda x: x > 900),
    ]

    print(
        "CADENCE DISTRIBUTION"
    )

    for name, predicate in buckets:

        count = sum(
            1
            for x in deltas
            if predicate(x)
        )

        pct = (
            count / len(deltas) * 100
        )

        print(
            f"{name:<10} | "
            f"{count:<6} | "
            f"{pct:7.2f}%"
        )


# ============================================================
# MAIN FORENSIC
# ============================================================

def main():

    print("=" * 90)
    print(
        "FIND_FUTURE_PRICE_TIMESTAMP_CADENCE_FORENSIC_v0.3"
    )
    print("=" * 90)

    print(
        "MODE              : READ ONLY"
    )

    print(
        f"DATABASE          : {DB_PATH}"
    )

    print(
        "DB WRITE          : FORBIDDEN"
    )

    print(
        "SYNTHETIC PRICES  : FORBIDDEN"
    )

    print(
        "INTERPOLATION     : FORBIDDEN"
    )

    print(
        "FORWARD FILL      : FORBIDDEN"
    )

    print(
        "PRODUCTION REPAIR : NONE"
    )

    print("=" * 90)

    conn = get_connection()

    try:

        signals = load_signals(
            conn
        )

        print()
        print(
            f"GENUINE SIGNALS : {len(signals)}"
        )

        cache = {}

        for signal in signals:

            asset = signal["asset"]

            if asset not in cache:

                cache[asset] = (
                    load_market_rows(
                        conn,
                        asset
                    )
                )

                print_cadence(
                    asset,
                    cache[asset]
                )

        # ----------------------------------------------------
        # TARGET ANALYSIS
        # ----------------------------------------------------

        print()
        print("=" * 90)
        print(
            "TARGET / NEAREST MARKET-DATA ANALYSIS"
        )
        print("=" * 90)

        all_distances = []

        call_number = 0

        for signal in signals:

            asset = signal["asset"]

            entry_timestamp = signal["timestamp"]

            entry_epoch = epoch(
                entry_timestamp
            )

            rows = cache.get(
                asset,
                []
            )

            for label, minutes in HORIZONS.items():

                call_number += 1

                target_epoch = (
                    entry_epoch
                    + minutes * 60
                )

                location = locate(
                    rows,
                    target_epoch
                )

                previous = location[
                    "previous"
                ]

                next_row = location[
                    "next"
                ]

                nearest = location[
                    "nearest"
                ]

                print()
                print("-" * 90)

                print(
                    f"CALL #{call_number}"
                )

                print(
                    f"Signal #{signal['id']} | "
                    f"{asset} | "
                    f"{label}"
                )

                print(
                    f"ENTRY   : "
                    f"{entry_timestamp}"
                )

                print(
                    f"TARGET  : "
                    f"{format_epoch(target_epoch)}"
                )

                if previous:

                    prev_distance = (
                        target_epoch
                        - previous["epoch"]
                    )

                    print(
                        f"PREVIOUS: "
                        f"{previous['timestamp']} | "
                        f"distance={prev_distance:.3f}s"
                    )

                else:

                    print(
                        "PREVIOUS: NONE"
                    )

                if next_row:

                    next_distance = (
                        next_row["epoch"]
                        - target_epoch
                    )

                    print(
                        f"NEXT    : "
                        f"{next_row['timestamp']} | "
                        f"distance={next_distance:.3f}s"
                    )

                else:

                    print(
                        "NEXT    : NONE"
                    )

                if nearest:

                    nearest_distance = abs(
                        nearest["epoch"]
                        - target_epoch
                    )

                    all_distances.append(
                        nearest_distance
                    )

                    print(
                        f"NEAREST : "
                        f"{nearest['timestamp']} | "
                        f"distance={nearest_distance:.3f}s | "
                        f"close={nearest['close']}"
                    )

                    if nearest_distance <= TOLERANCE:

                        print(
                            "STATUS  : "
                            "WITHIN CURRENT TOLERANCE"
                        )

                    else:

                        print(
                            "STATUS  : "
                            "OUTSIDE CURRENT TOLERANCE"
                        )

                else:

                    print(
                        "NEAREST : NONE"
                    )

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        print()
        print("=" * 90)
        print(
            "FORENSIC SUMMARY"
        )
        print("=" * 90)

        if all_distances:

            print(
                f"CALLS                 : "
                f"{len(all_distances)}"
            )

            print(
                f"NEAREST MIN           : "
                f"{min(all_distances):.3f} sec"
            )

            print(
                f"NEAREST MAX           : "
                f"{max(all_distances):.3f} sec"
            )

            print(
                f"NEAREST MEDIAN        : "
                f"{statistics.median(all_distances):.3f} sec"
            )

            print()
            print(
                "REQUIRED TOLERANCE ANALYSIS"
            )

            print(
                f"120 sec               : "
                f"{sum(x <= 120 for x in all_distances)} / "
                f"{len(all_distances)}"
            )

            print(
                f"300 sec               : "
                f"{sum(x <= 300 for x in all_distances)} / "
                f"{len(all_distances)}"
            )

            print(
                f"600 sec               : "
                f"{sum(x <= 600 for x in all_distances)} / "
                f"{len(all_distances)}"
            )

            print(
                f"900 sec               : "
                f"{sum(x <= 900 for x in all_distances)} / "
                f"{len(all_distances)}"
            )

            print()
            print(
                "IMPORTANT:"
            )

            print(
                "No production tolerance "
                "change is performed by this script."
            )

        print()
        print("=" * 90)
        print(
            "READ-ONLY FORENSIC COMPLETE"
        )
        print("=" * 90)

    finally:

        conn.close()


if __name__ == "__main__":
    main()