import sqlite3
import math
from datetime import datetime, timezone


# ============================================================
# ARUNDA TRADER
# OUTCOME v0.3 HORIZON DATA COMPLETENESS /
# TEMPORAL ELIGIBILITY FORENSIC v0.1
# ============================================================

DB_NAME = "arunda.db"
ENGINE_VERSION = "OUTCOME_v0.3.2"

HORIZONS = {
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m": 60,
}

TOLERANCES = {
    "5m": 600,
    "15m": 300,
    "30m": 600,
    "60m": 900,
}

FUSION_VERSIONS = (
    "FUSION_v0.5",
    "FUSION_v0.4",
)


# ============================================================
# DATABASE
# ============================================================

def get_connection():
    conn = sqlite3.connect(
        DB_NAME
    )

    conn.row_factory = sqlite3.Row

    return conn


# ============================================================
# NUMERIC / TIMESTAMP HELPERS
# ============================================================

def safe_float(value):

    try:

        if value is None:
            return None

        value = float(value)

        if not math.isfinite(value):
            return None

        return value

    except (TypeError, ValueError):

        return None


def parse_timestamp(value):

    if value is None:
        return None

    try:

        text = str(value).strip()

        if text.endswith("Z"):
            text = (
                text[:-1]
                + "+00:00"
            )

        dt = datetime.fromisoformat(
            text
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


def timestamp_to_epoch(value):

    dt = parse_timestamp(
        value
    )

    if dt is None:
        return None

    return dt.timestamp()


def epoch_to_timestamp(epoch):

    dt = datetime.fromtimestamp(
        epoch,
        tz=timezone.utc
    )

    return dt.isoformat()


# ============================================================
# TABLE CHECK
# ============================================================

def table_exists(
    conn,
    table_name
):

    row = conn.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE
            type = 'table'
            AND name = ?
        """,
        (
            table_name,
        )
    ).fetchone()

    return row is not None


# ============================================================
# LOAD ELIGIBLE SIGNALS
# ============================================================

def load_signals(conn):

    placeholders = ",".join(
        "?"
        for _ in FUSION_VERSIONS
    )

    rows = conn.execute(
        f"""
        SELECT
            id,
            snapshot_id,
            asset,
            timestamp,
            entry_price,
            direction,
            fused_score,
            confidence,
            regime,
            engine_version
        FROM fusion_signals
        WHERE
            engine_version IN (
                {placeholders}
            )
            AND entry_price IS NOT NULL
        ORDER BY id ASC
        """,
        FUSION_VERSIONS
    ).fetchall()

    return rows


# ============================================================
# LATEST MARKET DATA
# ============================================================

def get_market_data_bounds(
    conn,
    asset
):

    row = conn.execute(
        """
        SELECT
            MIN(timestamp) AS first_timestamp,
            MAX(timestamp) AS last_timestamp,
            COUNT(*) AS row_count
        FROM market_data
        WHERE
            symbol = ?
            AND timestamp IS NOT NULL
            AND close IS NOT NULL
        """,
        (
            asset,
        )
    ).fetchone()

    return row


# ============================================================
# NEAREST ACTUAL MARKET OBSERVATION
# ============================================================

def get_nearest_market_observation(
    conn,
    asset,
    target_epoch
):

    target_timestamp = (
        epoch_to_timestamp(
            target_epoch
        )
    )

    row = conn.execute(
        """
        SELECT
            id,
            timestamp,
            close,
            symbol
        FROM market_data
        WHERE
            symbol = ?
            AND timestamp IS NOT NULL
            AND close IS NOT NULL
        ORDER BY
            ABS(
                CAST(
                    strftime('%s', timestamp)
                    AS INTEGER
                )
                -
                CAST(
                    strftime('%s', ?)
                    AS INTEGER
                )
            ) ASC,
            timestamp ASC
        LIMIT 1
        """,
        (
            asset,
            target_timestamp,
        )
    ).fetchone()

    if row is None:

        return None

    row_epoch = timestamp_to_epoch(
        row["timestamp"]
    )

    if row_epoch is None:

        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "close": row["close"],
            "distance": None,
        }

    distance = abs(
        row_epoch
        - target_epoch
    )

    return {
        "id": row["id"],
        "timestamp": row["timestamp"],
        "close": row["close"],
        "distance": distance,
    }


# ============================================================
# TEMPORAL CLASSIFICATION
# ============================================================

def classify_temporal_state(
    entry_epoch,
    target_epoch,
    latest_epoch,
    nearest_distance,
    tolerance
):

    if entry_epoch is None:

        return "INVALID_ENTRY_TIMESTAMP"

    if latest_epoch is None:

        return "NO_MARKET_DATA"

    # --------------------------------------------------------
    # The target has not yet been reached by available
    # market-data history.
    # --------------------------------------------------------

    if latest_epoch < target_epoch:

        return "NOT_YET_ELIGIBLE"

    # --------------------------------------------------------
    # Target has passed. A nearest actual observation exists.
    # --------------------------------------------------------

    if nearest_distance is None:

        return "NO_NEAREST_OBSERVATION"

    if nearest_distance <= tolerance:

        return "ELIGIBLE"

    return "DATA_GAP"


# ============================================================
# MAIN FORENSIC
# ============================================================

def main():

    print("=" * 90)
    print(
        "OUTCOME v0.3 HORIZON DATA COMPLETENESS /"
    )
    print(
        "TEMPORAL ELIGIBILITY FORENSIC v0.1"
    )
    print("=" * 90)

    print(
        f"Database          : {DB_NAME}"
    )

    print(
        f"Outcome version   : {ENGINE_VERSION}"
    )

    print(
        "Mode              : READ ONLY"
    )

    print(
        "Production DB     : UNMODIFIED"
    )

    print(
        "Production source : UNMODIFIED"
    )

    print(
        "Synthetic data    : FORBIDDEN"
    )

    print(
        "Interpolation     : FORBIDDEN"
    )

    print(
        "Forward fill      : FORBIDDEN"
    )

    print(
        "Back fill         : FORBIDDEN"
    )

    print("=" * 90)

    conn = None

    try:

        conn = get_connection()

        # ----------------------------------------------------
        # TABLE CHECKS
        # ----------------------------------------------------

        print()
        print("=" * 90)
        print(
            "DATABASE STRUCTURE CHECK"
        )
        print("=" * 90)

        for table in (
            "fusion_signals",
            "market_data",
        ):

            exists = table_exists(
                conn,
                table
            )

            print(
                f"{table:<20} | "
                f"{'PASS' if exists else 'MISSING'}"
            )

            if not exists:

                print()
                print(
                    "FORENSIC ABORTED."
                )

                return

        # ----------------------------------------------------
        # LOAD SIGNALS
        # ----------------------------------------------------

        signals = load_signals(
            conn
        )

        print()
        print("=" * 90)
        print(
            "SIGNAL POPULATION"
        )
        print("=" * 90)

        print(
            f"Eligible Fusion signals : "
            f"{len(signals)}"
        )

        if not signals:

            print(
                "No eligible signals."
            )

            return

        # ----------------------------------------------------
        # CACHE MARKET DATA BOUNDS
        # ----------------------------------------------------

        bounds_cache = {}

        for signal in signals:

            asset = signal["asset"]

            if asset not in bounds_cache:

                bounds_cache[asset] = (
                    get_market_data_bounds(
                        conn,
                        asset
                    )
                )

        # ----------------------------------------------------
        # RESULT STORAGE
        # ----------------------------------------------------

        results = []

        # ----------------------------------------------------
        # SIGNAL-LEVEL FORENSIC
        # ----------------------------------------------------

        print()
        print("=" * 90)
        print(
            "SIGNAL / HORIZON TEMPORAL FORENSIC"
        )
        print("=" * 90)

        for signal in signals:

            signal_id = signal["id"]
            asset = signal["asset"]
            entry_timestamp = signal["timestamp"]
            direction = (
                signal["direction"]
                or "FLAT"
            ).upper()

            entry_epoch = (
                timestamp_to_epoch(
                    entry_timestamp
                )
            )

            bounds = bounds_cache[
                asset
            ]

            latest_timestamp = (
                bounds["last_timestamp"]
                if bounds
                else None
            )

            latest_epoch = (
                timestamp_to_epoch(
                    latest_timestamp
                )
                if latest_timestamp
                else None
            )

            print()
            print(
                "-" * 90
            )

            print(
                f"Signal #{signal_id} | "
                f"{asset:<6} | "
                f"{direction:<5}"
            )

            print(
                f"Entry : {entry_timestamp}"
            )

            print(
                f"Market rows : "
                f"{bounds['row_count'] if bounds else 0}"
            )

            print(
                f"Market first : "
                f"{bounds['first_timestamp'] if bounds else 'NONE'}"
            )

            print(
                f"Market latest: "
                f"{latest_timestamp or 'NONE'}"
            )

            for label, minutes in HORIZONS.items():

                tolerance = (
                    TOLERANCES[label]
                )

                if entry_epoch is None:

                    target_epoch = None

                    target_timestamp = (
                        "INVALID"
                    )

                    nearest = None

                    state = (
                        "INVALID_ENTRY_TIMESTAMP"
                    )

                else:

                    target_epoch = (
                        entry_epoch
                        + minutes * 60
                    )

                    target_timestamp = (
                        epoch_to_timestamp(
                            target_epoch
                        )
                    )

                    nearest = (
                        get_nearest_market_observation(
                            conn,
                            asset,
                            target_epoch
                        )
                    )

                    nearest_distance = (
                        nearest["distance"]
                        if nearest
                        else None
                    )

                    state = (
                        classify_temporal_state(
                            entry_epoch,
                            target_epoch,
                            latest_epoch,
                            nearest_distance,
                            tolerance
                        )
                    )

                # ------------------------------------------------
                # Existing outcome record
                # ------------------------------------------------

                outcome_row = conn.execute(
                    f"""
                    SELECT
                        price_{label},
                        return_{label},
                        outcome_{label}
                    FROM signal_outcomes
                    WHERE
                        snapshot_id = ?
                        AND asset = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (
                        signal["snapshot_id"],
                        asset,
                    )
                ).fetchone()

                existing_price = None
                existing_return = None
                existing_outcome = None

                if outcome_row:

                    existing_price = (
                        outcome_row[
                            f"price_{label}"
                        ]
                    )

                    existing_return = (
                        outcome_row[
                            f"return_{label}"
                        ]
                    )

                    existing_outcome = (
                        outcome_row[
                            f"outcome_{label}"
                        ]
                    )

                nearest_timestamp = (
                    nearest["timestamp"]
                    if nearest
                    else None
                )

                nearest_price = (
                    safe_float(
                        nearest["close"]
                    )
                    if nearest
                    else None
                )

                nearest_distance = (
                    nearest["distance"]
                    if nearest
                    else None
                )

                results.append(
                    {
                        "signal_id": signal_id,
                        "asset": asset,
                        "horizon": label,
                        "minutes": minutes,
                        "entry_timestamp": entry_timestamp,
                        "target_timestamp": target_timestamp,
                        "latest_market_timestamp": latest_timestamp,
                        "nearest_timestamp": nearest_timestamp,
                        "nearest_distance": nearest_distance,
                        "tolerance": tolerance,
                        "state": state,
                        "nearest_price": nearest_price,
                        "existing_price": existing_price,
                        "existing_return": existing_return,
                        "existing_outcome": existing_outcome,
                    }
                )

                distance_text = (
                    f"{nearest_distance:10.3f}s"
                    if nearest_distance is not None
                    else "       NONE"
                )

                print(
                    f"{label:<4} | "
                    f"Target={target_timestamp} | "
                    f"Nearest={nearest_timestamp or 'NONE'} | "
                    f"Distance={distance_text} | "
                    f"Tol={tolerance:4d}s | "
                    f"{state}"
                )

        # ====================================================
        # AGGREGATE SUMMARY
        # ====================================================

        print()
        print("=" * 90)
        print(
            "HORIZON AGGREGATE SUMMARY"
        )
        print("=" * 90)

        for label in HORIZONS:

            horizon_rows = [
                row
                for row in results
                if row["horizon"] == label
            ]

            eligible = sum(
                row["state"] == "ELIGIBLE"
                for row in horizon_rows
            )

            not_yet = sum(
                row["state"] == "NOT_YET_ELIGIBLE"
                for row in horizon_rows
            )

            gap = sum(
                row["state"] == "DATA_GAP"
                for row in horizon_rows
            )

            no_data = sum(
                row["state"] == "NO_MARKET_DATA"
                for row in horizon_rows
            )

            invalid = sum(
                row["state"]
                == "INVALID_ENTRY_TIMESTAMP"
                for row in horizon_rows
            )

            no_nearest = sum(
                row["state"]
                == "NO_NEAREST_OBSERVATION"
                for row in horizon_rows
            )

            populated = sum(
                row["existing_price"] is not None
                for row in horizon_rows
            )

            returns = sum(
                row["existing_return"] is not None
                for row in horizon_rows
            )

            print()
            print(
                f"{label}"
            )

            print(
                f"  Signals                  : "
                f"{len(horizon_rows)}"
            )

            print(
                f"  Temporally eligible      : "
                f"{eligible}"
            )

            print(
                f"  Not yet eligible         : "
                f"{not_yet}"
            )

            print(
                f"  Data gap                 : "
                f"{gap}"
            )

            print(
                f"  No market data           : "
                f"{no_data}"
            )

            print(
                f"  No nearest observation  : "
                f"{no_nearest}"
            )

            print(
                f"  Invalid entry timestamp  : "
                f"{invalid}"
            )

            print(
                f"  Existing prices          : "
                f"{populated}"
            )

            print(
                f"  Existing returns         : "
                f"{returns}"
            )

        # ====================================================
        # DISTANCE DISTRIBUTION
        # ====================================================

        print()
        print("=" * 90)
        print(
            "NEAREST DISTANCE DISTRIBUTION"
        )
        print("=" * 90)

        for label in HORIZONS:

            distances = [
                row["nearest_distance"]
                for row in results
                if (
                    row["horizon"] == label
                    and row["nearest_distance"]
                    is not None
                )
            ]

            if not distances:

                print(
                    f"{label:<4} | NO DISTANCE DATA"
                )

                continue

            distances.sort()

            count = len(
                distances
            )

            minimum = min(
                distances
            )

            maximum = max(
                distances
            )

            median = (
                distances[count // 2]
                if count % 2 == 1
                else (
                    distances[
                        count // 2 - 1
                    ]
                    +
                    distances[
                        count // 2
                    ]
                ) / 2
            )

            tolerance = (
                TOLERANCES[label]
            )

            print(
                f"{label:<4} | "
                f"N={count:<3} | "
                f"MIN={minimum:10.3f}s | "
                f"MEDIAN={median:10.3f}s | "
                f"MAX={maximum:10.3f}s | "
                f"TOL={tolerance:4d}s"
            )

        # ====================================================
        # DIAGNOSTIC CLASSIFICATION
        # ====================================================

        print()
        print("=" * 90)
        print(
            "ROOT-CAUSE CLASSIFICATION"
        )
        print("=" * 90)

        total_eligible = sum(
            row["state"] == "ELIGIBLE"
            for row in results
        )

        total_not_yet = sum(
            row["state"]
            == "NOT_YET_ELIGIBLE"
            for row in results
        )

        total_gap = sum(
            row["state"] == "DATA_GAP"
            for row in results
        )

        total_no_data = sum(
            row["state"]
            == "NO_MARKET_DATA"
            for row in results
        )

        total_checks = len(
            results
        )

        print(
            f"Total horizon checks : "
            f"{total_checks}"
        )

        print(
            f"Eligible             : "
            f"{total_eligible}"
        )

        print(
            f"Not yet eligible     : "
            f"{total_not_yet}"
        )

        print(
            f"Data gaps            : "
            f"{total_gap}"
        )

        print(
            f"No market data       : "
            f"{total_no_data}"
        )

        print()

        if total_gap > 0:

            print(
                "FINDING:"
            )

            print(
                "Actual historical market-data gaps "
                "exist beyond the configured tolerance."
            )

        elif total_not_yet > 0:

            print(
                "FINDING:"
            )

            print(
                "Some horizon targets are not yet "
                "temporally reachable from available "
                "market-data history."
            )

        elif total_eligible == total_checks:

            print(
                "FINDING:"
            )

            print(
                "All horizon checks have an actual "
                "market-data observation within tolerance."
            )

        else:

            print(
                "FINDING:"
            )

            print(
                "Mixed temporal/data conditions detected."
            )

        # ====================================================
        # PRODUCTION SAFETY
        # ====================================================

        print()
        print("=" * 90)
        print(
            "FINAL SAFETY VERDICT"
        )
        print("=" * 90)

        print(
            "Database writes       : NONE"
        )

        print(
            "INSERT                 : NONE"
        )

        print(
            "UPDATE                 : NONE"
        )

        print(
            "DELETE                 : NONE"
        )

        print(
            "ALTER                  : NONE"
        )

        print(
            "Tolerance modified    : NO"
        )

        print(
            "Production source     : UNMODIFIED"
        )

        print(
            "Production DB         : UNMODIFIED"
        )

        print(
            "Synthetic data        : NOT USED"
        )

        print(
            "Interpolation         : NOT USED"
        )

        print(
            "Forward fill          : NOT USED"
        )

        print(
            "Back fill             : NOT USED"
        )

        print("=" * 90)

        print(
            "FORENSIC COMPLETE."
        )

        print("=" * 90)

    except Exception as exc:

        print()
        print("=" * 90)
        print(
            "FORENSIC ERROR"
        )
        print("=" * 90)

        print(
            repr(exc)
        )

        print("=" * 90)

    finally:

        if conn is not None:

            conn.close()


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()